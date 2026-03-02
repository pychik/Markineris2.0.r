from datetime import datetime

from flask import jsonify, request
from flask_login import current_user
from models import db, ProductCard, CardMessage, CardChatRead
from views.main.product_cards.chat.helpers import h_pc_chat_can_access, h_pc_chat_visible_filter


def h_pc_chat_get_messages(pc_id: int):
    card = ProductCard.query.filter_by(id=pc_id).first()
    if not card or not h_pc_chat_can_access(card, current_user):
        return jsonify({"status": "error", "message": "Нет доступа"}), 403

    q = (CardMessage.query
         .filter(CardMessage.card_id == pc_id)
         .order_by(CardMessage.created_at.asc(), CardMessage.id.asc()))
    q = h_pc_chat_visible_filter(q, current_user)
    msgs = q.all()

    payload = []
    for m in msgs:
        payload.append({
            "id": m.id,
            "text": m.text,
            "is_internal": bool(m.is_internal),
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "author_id": m.author_id,
            "author_login": m.author.login_name if m.author else "",
        })

    # unread count (messages with id > last_read)
    read_row = CardChatRead.query.filter_by(card_id=pc_id, user_id=current_user.id).first()
    last_read_id = read_row.last_read_message_id if read_row else 0

    unread_count = sum(1 for m in msgs if (m.id or 0) > last_read_id)

    return jsonify({
        "status": "success",
        "card_id": pc_id,
        "unread_count": unread_count,
        "messages": payload,
    })


def h_pc_chat_send(pc_id: int):
    card = ProductCard.query.filter_by(id=pc_id).first()
    if not card or not h_pc_chat_can_access(card, current_user):
        return jsonify({"status": "error", "message": "Нет доступа"}), 403

    text = (request.form.get("text") or "").strip()
    if not text:
        return jsonify({"status": "error", "message": "Пустое сообщение"}), 400
    if len(text) > 300:
        return jsonify({"status": "error", "message": "Сообщение слишком длинное (макс 300)"}), 400

    # ordinary_user не может слать internal
    is_internal = False
    if current_user.role != "ordinary_user":
        is_internal = bool(request.form.get("is_internal"))  

    try:
        msg = CardMessage(
            card_id=pc_id,
            text=text,
            is_internal=is_internal,
            author_id=current_user.id,
        )
        db.session.add(msg)
        db.session.flush()

        # лог карточки (учитывай твой h_append_card_log)
        # line = f"\n{datetime.now():%d-%m-%Y %H:%M:%S} сообщение в чате от {current_user.login_name};"
        # card.card_log = h_append_card_log(card.card_log, line)

        db.session.commit()
        return jsonify({"status": "success", "message_id": msg.id})
    except Exception:
        db.session.rollback()
        return jsonify({"status": "error", "message": "Ошибка отправки"}), 500


def h_pc_chat_mark_read(pc_id: int):
    card = ProductCard.query.filter_by(id=pc_id).first()
    if not card or not h_pc_chat_can_access(card, current_user):
        return jsonify({"status": "error", "message": "Нет доступа"}), 403

    last_id = request.form.get("last_id", type=int)
    if not last_id:
        return jsonify({"status": "error", "message": "last_id required"}), 400

    try:
        row = CardChatRead.query.filter_by(card_id=pc_id, user_id=current_user.id).first()
        if not row:
            row = CardChatRead(card_id=pc_id, user_id=current_user.id, last_read_message_id=last_id)
            db.session.add(row)
        else:
            if last_id > (row.last_read_message_id or 0):
                row.last_read_message_id = last_id
            row.last_read_at = datetime.now()

        db.session.commit()
        return jsonify({"status": "success"})
    except Exception:
        db.session.rollback()
        return jsonify({"status": "error", "message": "Ошибка"}), 500
