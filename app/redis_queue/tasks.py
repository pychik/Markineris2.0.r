import os
from datetime import datetime, timedelta

import sqlalchemy.exc
from sqlalchemy import delete, select, and_, or_, text

from config import settings
from logger import logger
from models import db, RestoreLink, OrderFile, Order
from utilities.admin.h_finance_control import h_su_wo_transactions
from views.crm.helpers import helpers_move_orders_to_processed


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

        stmt = select(OrderFile).join(Order).where(or_(Order.to_delete == True,
                                                       and_(Order.processed, Order.closed_at < threshold_time)))
        order_files = db.session.scalars(stmt).fetchall()

        links = [order_file.file_link for order_file in order_files]

        archive_deleted = len(links)

        try:
            for order_file in order_files:
                db.session.delete(order_file)
        except sqlalchemy.exc.SQLAlchemyError as e:
            logger.error(str(e))

        try:
            for link in links:
                os.remove(link)
        except OSError as e:
            logger.error(str(e))

    return {"archive_deleted": archive_deleted}


def daily_tasks():
    """
    scheduler daily tasks united in one func
    :return:
    """

    # change maintenance mode to ON Hhere
    h_su_wo_transactions()
    helpers_move_orders_to_processed()
    # change maintenance mode to OFF here
    return {"status": "transactions performed; orders from sent moved to PROCESSED"}
