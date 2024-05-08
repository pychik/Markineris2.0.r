from datetime import datetime, timedelta
from flask import jsonify, request, render_template, Response, url_for
from io import BytesIO
from pandas import DataFrame, ExcelWriter
from pandas import to_datetime as pd_datetime
from time import sleep as t_sleep
from sqlalchemy import text
from sqlalchemy.engine.row import Row
from typing import Optional

from config import settings
from models import db, User
from utilities.support import helper_paginate_data


def process_admin_report(u_id: int, sheet_name: str) -> Optional[BytesIO]:
    res = db.session.execute(text(f"""
                                    SELECT
                                     os.saved_at AS saved_at_d,
                                     os.saved_at AS saved_at_h,
                                     u.login_name AS login_name, 
                                     u.client_code AS client_code,
                                     os.order_idn as order_idn,
                                     os.category as category,
                                     os.company_type AS company_type,
                                     os.company_name AS company_name,
                                     os.rows_count AS row_count,
                                     os.marks_count AS marks_count,
                                     os.op_cost AS op_cost
                                     FROM public.users u
                                      JOIN public.orders_stats os ON u.id = os.user_id
                                    WHERE u.admin_parent_id={u_id} OR u.id = {u_id}
                                    ORDER BY login_name, saved_at_d
                            """))
    report_info = res.fetchall()
    if not report_info:
        return None
    df: DataFrame = DataFrame(report_info)
    df['saved_at_d'] = pd_datetime(df['saved_at_d']).dt.strftime('%d.%m.%Y')
    df['saved_at_h'] = pd_datetime(df['saved_at_h']).dt.strftime('%H:%M:%S')
    df.loc[df['op_cost'] == 0, 'op_cost'] = 'Не оплачен'

    df.rename(columns=settings.ADMIN_REPORT_HEAD, inplace=True)
    output = BytesIO()

    with ExcelWriter(output, engine='xlsxwriter') as writer:

        df.to_excel(writer, sheet_name=sheet_name, index=False)
        df = df.astype(str)

        for column in df:
            column_length = max(df[column].astype(str).map(len).max(), len(column)) + 1
            col_idx = df.columns.get_loc(column)
            writer.sheets[sheet_name].set_column(col_idx, col_idx, column_length)

    output.seek(0)
    output.flush()
    t_sleep(1)
    return output


def helper_get_orders_stats(admin_id: int = None) -> Response:
    extend_agent = request.args.get('extend_agent', 0, type=int)
    additional_stmt = ""
    sub_stmt = f" OR u.id={admin_id}" if extend_agent else ""
    if admin_id:
        additional_stmt = f"""WHERE os.user_id in (SELECT u.id FROM public.users u WHERE u.admin_parent_id={admin_id} {sub_stmt})"""
    order_stmt = f"""SELECT os.order_idn as order_idn,
                                os.company_idn as company_idn,
                                os.company_type as company_type,
                                os.company_name as company_name,
                                os.rows_count as rows_count,
                                os.marks_count as marks_count,
                                os.op_cost as op_cost,
                                os.category as category,
                                os.created_at as created_at,
                                MAX(u.login_name) as user_name,
                                MAX(u.phone) as phone,
                                MAX(pc.code) as partner_code
                             FROM public.orders_stats os
                             LEFT JOIN public.users u on u.id=os.user_id
                             LEFT JOIN public.users_partners up on up.user_id =u.id
                             LEFT JOIN public.partner_codes pc on pc.id = up.partner_code_id
                             {additional_stmt}
                             GROUP BY os.id
                             ORDER BY os.created_at DESC
                         """

    order_stats = db.session.execute(text(order_stmt)).fetchall()

    bck = request.args.get('bck', 0, type=int)

    if not order_stats:
        return render_template('admin/orders_stats/os_main.html', **locals()) if not bck \
            else jsonify({'htmlresponse': render_template(f'admin/orders_stats/os_table.html',
                                                        **locals())})
    # link_filters = f'tr_type=1&tr_status={settings.Transactions.PENDING}&'
    link_filters = 'bck=1&'
    link = f'javascript:bck_get_orders_stats(\'' + url_for(
        'admin_control.users_orders_stats', admin_id=admin_id) + f'?extend_agent={extend_agent}&{link_filters}' + 'page={0}\');'
    page, per_page, \
        offset, pagination, \
        os_list = helper_paginate_data(data=order_stats, per_page=settings.PAGINATION_PER_PAGE, href=link)

    return render_template('admin/orders_stats/os_main.html', **locals()) if not bck \
        else jsonify({'htmlresponse': render_template(f'admin/orders_stats/os_table.html',
                                                      **locals())})


def helper_get_clients_os(admin_id: int, client: User) -> Response:
    order_stmt = text(f"""SELECT os.order_idn as order_idn,
                                os.company_idn as company_idn,
                                os.company_type as company_type,
                                os.company_name as company_name,
                                os.rows_count as rows_count,
                                os.marks_count as marks_count,
                                os.op_cost as op_cost,
                                os.category as category,
                                os.created_at as created_at,
                                MAX(u.login_name) as user_name,
                                MAX(u.phone) as phone,
                                MAX(pc.code) as partner_code
                             FROM public.orders_stats os
                             LEFT JOIN public.users u on u.id=os.user_id
                             LEFT JOIN public.users_partners up on up.user_id =u.id
                             LEFT JOIN public.partner_codes pc on pc.id = up.partner_code_id
                             WHERE os.user_id=:client_id
                             GROUP BY os.id, os.created_at
                             ORDER BY os.created_at DESC
                         """).bindparams(client_id=client.id)

    order_stats = db.session.execute(order_stmt).fetchall()

    bck = request.args.get('bck', 0, type=int)

    if not order_stats:
        return render_template('admin/client_orders/main.html', **locals()) if not bck \
            else jsonify({'htmlresponse': render_template(f'admin/client_orders/orders_table.html',
                                                        **locals())})
    # link_filters = f'tr_type=1&tr_status={settings.Transactions.PENDING}&'
    link_filters = 'bck=1&'
    link = f'javascript:bck_get_orders_stats(\'' + url_for(
        'admin_control.client_orders_stats', admin_id=admin_id, client_id=client.id) + f'?{link_filters}' + 'page={0}\');'
    page, per_page, \
        offset, pagination, \
        os_list = helper_paginate_data(data=order_stats, per_page=settings.PAGINATION_PER_PAGE, href=link)

    return render_template('admin/client_orders/main.html', **locals()) if not bck \
        else jsonify({'htmlresponse': render_template(f'admin/client_orders/orders_table.html',
                                                      **locals())})


def helper_prev_day_orders_marks() -> Row:
    yesterday = datetime.now() - timedelta(days=1)
    stmt = text(""" SELECT count(id) as orders_count, sum(marks_count) as marks_count 
                         FROM public.orders_stats WHERE saved_at >= '{yesterday_from}' 
                        AND saved_at < '{yesterday_to}';""".format(
        yesterday_from=yesterday.strftime('%Y-%m-%d 00:00:00'),
        yesterday_to=yesterday.strftime('%Y-%m-%d 23:59:59')))
    return db.session.execute(stmt).fetchone()
