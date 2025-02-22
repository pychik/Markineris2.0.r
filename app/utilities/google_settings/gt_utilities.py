from datetime import datetime, timedelta
from sqlalchemy import text

from models import db
from .schema import OrderRow, RuznakRow, TransactionRow
from .google_tables import GoogleProcess
from config import settings
from utilities.sql_categories_aggregations import SQLQueryCategoriesAll


def helper_get_orders_for_google(tr_pack: TransactionRow):
    data_packet_stmt = f"""SELECT 
                                u.login_name as login_name, 
                                u.phone as phone, 
                                MAX(p_code.code) as partner_code, 
                                o.category as category,
                                o.company_type as company_type,
                                o.company_name as company_name,
                                o.company_idn as company_idn,
                                o.order_idn as order_idn,
                                o.category as category,
                                {SQLQueryCategoriesAll.get_stmt(field='rows_count')} as rows_count,    
                                {SQLQueryCategoriesAll.get_stmt(field='marks_count')} as marks_count    
                            FROM public.users u
                                JOIN public.orders o ON o.user_id = u.id
                                LEFT JOIN public.users_partners up ON up.user_id = u.id
                                LEFT JOIN public.partner_codes p_code ON p_code.id = up.partner_code_id 
                                {SQLQueryCategoriesAll.get_joins()}
                            WHERE u.id = {tr_pack.u_id} AND o.transaction_id={tr_pack.tr_id}
                            GROUP BY u.id, o.id;"""
    return db.session.execute(text(data_packet_stmt)).fetchall()


def helper_get_orders_for_google_rz(tr_pack: TransactionRow):
    data_packet_stmt = f"""SELECT 
                                u.login_name as login_name,
                                MAX(p_code.code) as partner_code, 
                                o.order_idn as order_idn, 
                                o.category as category,
                                o.company_type as company_type,
                                o.company_name as company_name,
                                o.category as category,
                                {SQLQueryCategoriesAll.get_stmt(field='rows_count')} as rows_count,    
                                {SQLQueryCategoriesAll.get_stmt(field='marks_count')} as marks_count    
                            FROM public.users u
                                JOIN public.orders o ON o.user_id = u.id
                                LEFT JOIN public.users_partners up ON up.user_id = u.id
                                LEFT JOIN public.partner_codes p_code ON p_code.id = up.partner_code_id 
                                {SQLQueryCategoriesAll.get_joins()} 
                            WHERE u.id = {tr_pack.u_id} AND o.transaction_id={tr_pack.tr_id}
                            GROUP BY u.id, o.id;"""
    return db.session.execute(text(data_packet_stmt)).fetchall()


def helper_google_order_list(transaction_packets: list[TransactionRow],
                             date_info: str,
                             rz_flag: bool = False) -> list[OrderRow | RuznakRow]:
    google_orders = []
    if not rz_flag:
        for tr_pack in transaction_packets:
            price_for_google = str(tr_pack.transaction_price).replace('.', ',')
            res_orders_db = helper_get_orders_for_google(tr_pack=tr_pack)
            if not res_orders_db:
                continue
            for dp in res_orders_db:
                google_orders.append(
                    OrderRow(date_value=date_info, order_idn=dp.order_idn, partner_code=dp.partner_code,
                             login_name=dp.login_name, company_name=f"{dp.company_type} {dp.company_name}",
                             phone=dp.phone, marks_count=dp.marks_count, rows_count=dp.rows_count,
                             category=dp.category, price=price_for_google, status="Оплачено",
                             agent_type="Единый счет" if tr_pack.is_at2 else "Обычный агент"))

    else:
        for tr_pack in transaction_packets:
            price_for_google = str(tr_pack.transaction_price).replace('.', ',')
            res_orders_db = helper_get_orders_for_google_rz(tr_pack=tr_pack)
            if not res_orders_db:
                continue
            for dp in res_orders_db:
                google_orders.append(
                    RuznakRow(date_value=date_info, company_composed=f"{dp.company_type} {dp.company_name}",
                              marks_count=dp.marks_count, rows_count=dp.rows_count, category=dp.category,
                              transaction_price=price_for_google,
                              final_price=round(dp.marks_count * tr_pack.transaction_price), partner_code=dp.partner_code if dp.partner_code else "",
                              order_idn=dp.order_idn))
    return google_orders


def helper_google_collect_and_send_stat(transaction_google_packets: list[TransactionRow],
                                        transaction_rz_packets: list[TransactionRow]) -> None:
    _date = datetime.now() - timedelta(days=1)

    # Set the time to 23:59:59
    date_info = _date.replace(hour=23, minute=59, second=59).strftime("%d.%m.%Y %H:%M")
    if transaction_google_packets:
        gp_common = GoogleProcess(data_list=helper_google_order_list(transaction_packets=transaction_google_packets,
                                                                     date_info=date_info))
        gp_common.send_data_packet()

    # hardcoded rz
    if transaction_rz_packets:
        gp_rz = GoogleProcess(data_list=helper_google_order_list(transaction_packets=transaction_rz_packets,
                                                                 date_info=date_info, rz_flag=True),
                              spreadsheet=settings.GoogleTables.RuZnak.SPREADSHEET_ID_RUZNAK,
                              sheet_name=settings.GoogleTables.RuZnak.SHEET_NAME_RUZNAK)
        gp_rz.send_data_packet()
