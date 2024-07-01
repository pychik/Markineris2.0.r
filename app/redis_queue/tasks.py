import os
from datetime import datetime, timedelta

import sqlalchemy.exc
from sqlalchemy import delete, select, and_, or_, text

from config import settings
from logger import logger
from models import db, RestoreLink, OrderFile, Order
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, MetaData
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
