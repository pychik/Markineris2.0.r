import os
from datetime import datetime, timedelta

import sqlalchemy.exc
from sqlalchemy import create_engine, MetaData
from sqlalchemy import delete, select, and_, or_
from sqlalchemy.orm import sessionmaker

from config import settings
from logger import logger
from models import db, RestoreLink, OrderFile, Order, OrderMessage, OrderMessageAttachment
from utilities.admin.h_finance_control import h_su_wo_transactions
from utilities.minio_service.services import get_s3_service
from views.crm.helpers import helpers_move_orders_to_processed, helper_auto_new_cancel_order
from views.main.product_cards.crm.helpers import helper_reject_cards_by_rd_date_to_today
from utilities.chat_attachments import (
    DELETED_CHAT_ATTACHMENT_CONTENT_TYPE,
    build_deleted_chat_attachment_storage_name,
)


def delete_restore_link_periodic_task() -> dict[str, int]:
    with db.session.begin():
        threshold_time = datetime.now() - timedelta(minutes=30)

        stmt = delete(RestoreLink).where(RestoreLink.created_at < threshold_time)

        links = db.session.execute(stmt)
        links_to_remove = links.rowcount

    return {"deleted_restore_link": links_to_remove}


def delete_order_files_from_server() -> dict[str, int]:

    with db.session.begin():
        threshold_time = datetime.now() - timedelta(days=settings.OrderStage.DEFAULT_ORDER_FILE_TO_REMOVE)

        stmt = select(OrderFile).join(Order).where(
            or_(Order.to_delete.is_(True), and_(Order.processed, Order.closed_at < threshold_time))
        )
        order_files = db.session.scalars(stmt).fetchall()

        file_names = [order_file.file_system_name for order_file in order_files]

        archive_deleted = len(file_names)

        if not archive_deleted:
            return {"archive_deleted": archive_deleted}

        s3_service = get_s3_service()
        try:

            for order_file in order_files:
                db.session.delete(order_file)
        except sqlalchemy.exc.SQLAlchemyError as e:
            logger.error(str(e))

        try:
            list_objects = s3_service.list_objects(settings.MINIO_CRM_BUCKET_NAME)

            for obj in list_objects:
                if obj in file_names:
                    s3_service.remove_object(bucket_name=settings.MINIO_CRM_BUCKET_NAME, object_name=obj)
        except OSError as e:
            logger.error(str(e))

    return {"archive_deleted": archive_deleted}


def delete_old_order_chat_attachments(retention_days: int = 14) -> dict[str, int]:
    """Delete order chat files from storage and keep placeholder rows in chat history."""
    threshold_time = datetime.now() - timedelta(days=retention_days)

    attachment_rows = (
        db.session.query(OrderMessageAttachment)
        .join(OrderMessage, OrderMessageAttachment.message_id == OrderMessage.id)
        .join(Order, OrderMessage.order_id == Order.id)
        .filter(OrderMessageAttachment.content_type != DELETED_CHAT_ATTACHMENT_CONTENT_TYPE)
        .filter(
            or_(
                and_(
                    Order.stage == settings.OrderStage.SENT,
                    Order.sent_at.isnot(None),
                    Order.sent_at < threshold_time,
                ),
                and_(
                    Order.stage == settings.OrderStage.CANCELLED,
                    Order.cc_created.isnot(None),
                    Order.cc_created < threshold_time,
                ),
                and_(
                    Order.stage == settings.OrderStage.CRM_PROCESSED,
                    Order.closed_at.isnot(None),
                    Order.closed_at < threshold_time,
                ),
            )
        )
        .all()
    )

    if not attachment_rows:
        return {
            "eligible_order_chat_attachments": 0,
            "deleted_order_chat_attachment_files": 0,
            "marked_order_chat_attachment_placeholders": 0,
            "failed_order_chat_attachment_files": 0,
            "retention_days": retention_days,
        }

    s3_service = get_s3_service()
    deleted_files = 0
    marked_placeholders = 0
    failed_files = 0

    for attachment in attachment_rows:
        attachment_id = attachment.id
        storage_name = attachment.storage_name

        if storage_name:
            try:
                s3_service.remove_object(
                    bucket_name=settings.MINIO_CRM_BUCKET_NAME,
                    object_name=storage_name,
                )
                deleted_files += 1
            except Exception:
                failed_files += 1
                logger.exception(
                    "Ошибка при удалении файла вложения из чата заказа: attachment_id={}, storage_name={}",
                    attachment_id,
                    storage_name,
                )
                continue

        attachment.storage_name = build_deleted_chat_attachment_storage_name(attachment_id)
        attachment.content_type = DELETED_CHAT_ATTACHMENT_CONTENT_TYPE
        attachment.size_bytes = 0
        marked_placeholders += 1

    if marked_placeholders:
        try:
            db.session.commit()
        except sqlalchemy.exc.SQLAlchemyError:
            db.session.rollback()
            logger.exception("Ошибка при сохранении заглушек вложений чата заказов")
            marked_placeholders = 0

    return {
        "eligible_order_chat_attachments": len(attachment_rows),
        "deleted_order_chat_attachment_files": deleted_files,
        "marked_order_chat_attachment_placeholders": marked_placeholders,
        "failed_order_chat_attachment_files": failed_files,
        "retention_days": retention_days,
    }


def daily_tasks():
    """
    scheduler daily tasks united in one func
    :return:
    """

    # change maintenance mode to ON Hhere
    h_su_wo_transactions()
    helpers_move_orders_to_processed()
    helper_auto_new_cancel_order()
    helper_reject_cards_by_rd_date_to_today()
    order_chat_cleanup = delete_old_order_chat_attachments()
    # change maintenance mode to OFF here
    return {
        "status": "transactions performed; orders stage changes performed",
        "order_chat_attachments_eligible": order_chat_cleanup["eligible_order_chat_attachments"],
        "order_chat_attachment_files_deleted": order_chat_cleanup["deleted_order_chat_attachment_files"],
        "order_chat_attachment_placeholders_marked": order_chat_cleanup["marked_order_chat_attachment_placeholders"],
        "order_chat_attachment_files_failed": order_chat_cleanup["failed_order_chat_attachment_files"],
    }


def backup_database():
    def delete_oldest_backup(backup_dir: str) -> None:

        """Delete the oldest backup file if there are more than one."""
        backup_files = [os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if f.endswith('.sql')]

        if len(backup_files) > 1:
            backup_files.sort(key=os.path.getctime)
            os.remove(backup_files[0])
            logger.info(f'Deleted oldest backup: {backup_files[0]}')

    backup_dir = settings.DB_BACKUP_DIR
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    delete_oldest_backup(backup_dir)

    backup_file = os.path.join(backup_dir, f'backup_{datetime.now().strftime("%Y%m%d%H%M%S")}.sql')

    from settings.start import app
    engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    sm = sessionmaker(bind=engine)
    session = sm()

    metadata = MetaData()
    metadata.reflect(bind=engine)

    try:
        with open(backup_file, 'w') as f:
            for table in metadata.sorted_tables:
                write_table_data(session, f, table)
    except Exception as e:
        logger.error(f'Error during backup: {e}')
        return {"status": "Backup not created"}
    else:
        logger.info(f'Backup created: {backup_file}')
        return {"status": "Backup created successfully"}


def write_table_data(session, f, table):
    f.write(f"-- Dumping data for table {table.name}\n")
    rows = session.execute(table.select()).fetchall()

    for row in rows:
        row_dict = {column.name: value for column, value in zip(table.columns, row)}
        columns = ', '.join(row_dict.keys())

        # Handle values separately to avoid nested comprehensions
        values_list = []
        for value in row_dict.values():
            if value is None:
                values_list.append('NULL')
            else:
                safe_value = str(value).replace("'", "''")
                values_list.append(f"'{safe_value}'")

        values = ', '.join(values_list)
        insert_stmt = f"INSERT INTO {table.name} ({columns}) VALUES ({values});\n"
        f.write(insert_stmt)
