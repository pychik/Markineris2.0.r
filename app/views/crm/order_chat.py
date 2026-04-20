from datetime import datetime

from flask import jsonify, request
from flask_login import current_user
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from config import settings
from models import db, Order, OrderMessage, OrderChatRead, User

ORDER_CHAT_ALLOWED_ROLES = {
    settings.SUPER_USER,
    settings.SUPER_MANAGER,
    settings.MARKINERIS_ADMIN_USER,
    settings.MANAGER_USER,
    settings.ADMIN_USER,
}


def h_order_chat_is_agent_admin(user: User | None) -> bool:
    return bool(user and getattr(user, "role", None) == settings.ADMIN_USER)


def h_order_chat_can_access(
    order_stage: int,
    order_manager_id: int,
    order_user_id: int,
    order_user_admin_parent_id: int | None,
    user: User,
) -> bool:
    if user.role not in ORDER_CHAT_ALLOWED_ROLES:
        return False

    if user.role == settings.MANAGER_USER:
        # Оператор имеет доступ к POOL заказам и к своим назначенным заказам.
        if order_stage == settings.OrderStage.POOL:
            return True

        # Для остальных стадий чат доступен только назначенному оператору.
        return order_manager_id == user.id

    if h_order_chat_is_agent_admin(user):
        # Агент (admin) видит чаты только своих клиентов (и свои заказы, если есть).
        return order_user_id == user.id or order_user_admin_parent_id == user.id

    return True


def h_get_order_access_data(o_id: int):
    """Fetch only fields needed for access checks to avoid heavy Order ORM loading."""
    return (
        db.session.query(
            Order.id,
            Order.stage,
            Order.manager_id,
            Order.user_id,
            User.admin_parent_id.label("user_admin_parent_id"),
        )
        .join(User, User.id == Order.user_id)
        .filter(Order.id == o_id)
        .first()
    )


def h_order_chat_unread_map(order_ids: list[int], user_id: int) -> dict[int, int]:
    if not order_ids or not user_id:
        return {}

    q = (
        db.session.query(OrderMessage.order_id, func.count(OrderMessage.id))
        .outerjoin(
            OrderChatRead,
            (OrderChatRead.order_id == OrderMessage.order_id) & (OrderChatRead.user_id == user_id),
        )
        .filter(OrderMessage.order_id.in_(order_ids))
        .filter(OrderMessage.id > func.coalesce(OrderChatRead.last_read_message_id, 0))
        .group_by(OrderMessage.order_id)
    )

    rows = q.all()
    result = {oid: 0 for oid in order_ids}
    for oid, cnt in rows:
        result[oid] = int(cnt or 0)
    return result


def h_order_chat_serialize_attachment(attachment: OrderMessageAttachment) -> dict:
    return {
        "id": attachment.id,
        "name": attachment.original_name,
        "size_bytes": attachment.size_bytes,
    }


def h_order_chat_get_messages(o_id: int):
    order = h_get_order_access_data(o_id)
    if not order or not h_order_chat_can_access(
        order.stage,
        order.manager_id,
        order.user_id,
        order.user_admin_parent_id,
        current_user,
    ):
        return jsonify({"status": "error", "message": "Нет доступа"}), 403

    msgs = (
        OrderMessage.query
        .options(
            joinedload(OrderMessage.author).load_only(User.id, User.login_name),
            selectinload(OrderMessage.attachments),
        )
        .filter(OrderMessage.order_id == o_id)
        .order_by(OrderMessage.created_at.asc(), OrderMessage.id.asc())
        .all()
    )

    payload = []
    for m in msgs:
        payload.append({
            "id": m.id,
            "text": m.text,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "author_id": m.author_id,
            "author_login": m.author.login_name if m.author else "",
            "attachments": [h_order_chat_serialize_attachment(a) for a in m.attachments],
        })

    read_row = OrderChatRead.query.filter_by(order_id=o_id, user_id=current_user.id).first()
    last_read_id = read_row.last_read_message_id if read_row else 0
    unread_count = sum(1 for m in msgs if (m.id or 0) > last_read_id)

    return jsonify({
        "status": "success",
        "order_id": o_id,
        "unread_count": unread_count,
        "messages": payload,
    })


def h_order_chat_send(o_id: int):
    order = h_get_order_access_data(o_id)
    if not order or not h_order_chat_can_access(
        order.stage,
        order.manager_id,
        order.user_id,
        order.user_admin_parent_id,
        current_user,
    ):
        return jsonify({"status": "error", "message": "Нет доступа"}), 403

    text = (request.form.get("text") or "").strip()
    files = collect_chat_files(request)
    prepared_files, validation_error = validate_chat_files(files)
    if validation_error:
        return jsonify({"status": "error", "message": validation_error}), 400

    if not text and not prepared_files:
        return jsonify({"status": "error", "message": "Пустое сообщение"}), 400
    if len(text) > 300:
        return jsonify({"status": "error", "message": "Сообщение слишком длинное (макс 300)"}), 400

    uploaded_files = []
    try:
        msg = OrderMessage(
            order_id=o_id,
            text=text,
            author_id=current_user.id,
        )
        db.session.add(msg)
        db.session.flush()

        uploaded_files, upload_error = upload_chat_files(
            prepared_files,
            object_prefix=f"chat_attachments/orders/{o_id}/{msg.id}",
        )
        if upload_error:
            db.session.rollback()
            return jsonify({"status": "error", "message": upload_error}), 400

        for uploaded_file in uploaded_files:
            db.session.add(OrderMessageAttachment(
                message_id=msg.id,
                original_name=uploaded_file['original_name'],
                storage_name=uploaded_file['storage_name'],
                content_type=uploaded_file['content_type'],
                size_bytes=uploaded_file['size_bytes'],
            ))

        db.session.commit()
        return jsonify({
            "status": "success",
            "message_id": msg.id,
            "attachments_count": len(uploaded_files),
        })
    except Exception:
        db.session.rollback()
        cleanup_chat_files([item['storage_name'] for item in uploaded_files])
        logger.exception("Ошибка отправки сообщения в чат заказа")
        return jsonify({"status": "error", "message": "Ошибка отправки"}), 500


def h_order_chat_download_attachment(o_id: int, attachment_id: int):
    order = h_get_order_access_data(o_id)
    if not order or not h_order_chat_can_access(order.stage, order.manager_id, current_user):
        return jsonify({"status": "error", "message": "Нет доступа"}), 403

    attachment = (
        OrderMessageAttachment.query
        .join(OrderMessage, OrderMessageAttachment.message_id == OrderMessage.id)
        .filter(OrderMessage.order_id == o_id, OrderMessageAttachment.id == attachment_id)
        .first()
    )
    if not attachment:
        abort(404)

    return download_file_from_minio(
        bucket_name=settings.MINIO_CRM_BUCKET_NAME,
        object_name=attachment.storage_name,
        download_name=attachment.original_name,
        content_type=attachment.content_type,
    )


def h_order_chat_mark_read(o_id: int):
    order = h_get_order_access_data(o_id)
    if not order or not h_order_chat_can_access(
        order.stage,
        order.manager_id,
        order.user_id,
        order.user_admin_parent_id,
        current_user,
    ):
        return jsonify({"status": "error", "message": "Нет доступа"}), 403

    last_id = request.form.get("last_id", type=int)
    if not last_id:
        return jsonify({"status": "error", "message": "last_id required"}), 400

    try:
        row = OrderChatRead.query.filter_by(order_id=o_id, user_id=current_user.id).first()
        if not row:
            row = OrderChatRead(order_id=o_id, user_id=current_user.id, last_read_message_id=last_id)
            db.session.add(row)
            db.session.commit()
            return jsonify({"status": "success"})
        else:
            current_last = row.last_read_message_id or 0
            if last_id <= current_last:
                return jsonify({"status": "success"})
            row.last_read_message_id = last_id
            row.last_read_at = datetime.now()

        db.session.commit()
        return jsonify({"status": "success"})
    except Exception:
        db.session.rollback()
        return jsonify({"status": "error", "message": "Ошибка"}), 500
