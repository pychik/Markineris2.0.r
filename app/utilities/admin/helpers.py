from datetime import datetime, timedelta
from flask import jsonify, request, render_template, Response, url_for
from io import BytesIO
from pandas import DataFrame, ExcelWriter
from pandas import to_datetime as pd_datetime
from time import sleep as t_sleep
from sqlalchemy import asc, desc, text
from sqlalchemy.engine.row import Row
from typing import Optional

from config import settings
from models import db, User
from utilities.support import helper_paginate_data


def process_admin_report(u_id: int, sheet_name: str) -> Optional[BytesIO]:
    res = db.session.execute(text("""
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
                                    WHERE u.admin_parent_id=:u_id OR u.id = :u_ir
                                    ORDER BY login_name, saved_at_d
                            """).bindparams(u_id=u_id))
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
    order_stmt = text("""SELECT os.order_idn as order_idn,
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


def helper_get_new_orders_at2(admin_id: int) -> list:
    stmt_get_agent = f"CASE WHEN MAX(a.login_name) IS NOT NULL THEN MAX(a.login_name) ELSE u.login_name end"
    stmt_orders = text(f"""
                              SELECT 
                                  {stmt_get_agent} as agent_name ,
                                  u.login_name as login_name, 
                                  u.phone as phone, 
                                  u.email as email, 
                                  o.id as id,
                                  o.order_idn as order_idn,
                                  o.company_type as company_type,
                                  o.company_name as company_name,
                                  o.crm_created_at as crm_created_at,
                                  COUNT(o.id) as row_count,
                                  SUM(coalesce(sh.box_quantity*sh_qs.quantity, cl.box_quantity*cl_qs.quantity, l.box_quantity*l_qs.quantity, p.quantity)) as pos_count
                              FROM public.users u
                                  JOIN public.orders o ON o.user_id = u.id  
                                  LEFT JOIN public.users a ON u.admin_parent_id = a.id  
                                  LEFT JOIN public.shoes sh ON o.id = sh.order_id
                                  LEFT JOIN public.shoes_quantity_sizes sh_qs ON sh.id = sh_qs.shoe_id 
                                  LEFT JOIN public.clothes  cl ON o.id = cl.order_id
                                  LEFT JOIN public.cl_quantity_sizes cl_qs ON cl.id = cl_qs.cl_id
                                  LEFT JOIN public.linen l ON o.id = l.order_id
                                  LEFT JOIN public.linen_quantity_sizes l_qs ON l.id = l_qs.lin_id
                                  LEFT JOIN public.parfum p ON o.id = p.order_id 
                              WHERE ((a.id=:admin_id  and a.is_at2=True) OR (u.id=:admin_id AND u.is_at2 = True)) AND o.stage=:order_stage AND o.to_delete != True
                              GROUP BY u.id, o.id, o.crm_created_at
                              ORDER BY o.crm_created_at DESC 
                               """).bindparams(admin_id=admin_id, order_stage=settings.OrderStage.NEW)

    return db.session.execute(stmt_orders).fetchall()


def helper_check_new_order_at2(admin_id: int, o_id: int) -> Row | None:
    stmt_order = text("""
                              SELECT 
                                  o.order_idn as order_idn,
                                  o.user_id as user_id,
                                  o.payment as payment
                              FROM public.users u
                                  JOIN public.orders o ON o.user_id = u.id  
                              WHERE  (u.admin_parent_id=:admin_id OR u.id=:admin_id) AND o.id=:order_id AND o.stage=:stage AND o.to_delete != True
                               """).bindparams(admin_id=admin_id, order_id=o_id, stage=settings.OrderStage.NEW)

    return db.session.execute(stmt_order).fetchone()


def helper_prev_day_orders_marks() -> Row:
    yesterday = datetime.now() - timedelta(days=1)
    stmt = text(""" SELECT count(id) as orders_count, sum(marks_count) as marks_count 
                         FROM public.orders_stats WHERE saved_at >= '{yesterday_from}' 
                        AND saved_at < '{yesterday_to}';""".format(
        yesterday_from=yesterday.strftime('%Y-%m-%d 00:00:00'),
        yesterday_to=yesterday.strftime('%Y-%m-%d 23:59:59')))
    return db.session.execute(stmt).fetchone()


def helper_get_users_reanimate(date_quantity: int, date_type: str, sort_type: str, u_id: int = None) -> None | list:
    if sort_type == 0:
        order_clause = desc('u.login_name')
    else:
        order_clause = asc('u.login_name')

    user_filter = ''
    if u_id:
        user_filter = f'and u.admin_parent_id = :u_id'

    date_condition = f"HAVING max(os.saved_at) <= CURRENT_DATE - INTERVAL '{settings.Users.FILTER_MAX_QUANTITY} days' OR COUNT(os.id) = 0"
    match date_type:
        case settings.Users.FILTER_DATE_HOURS:
            date_condition = f"HAVING max(os.saved_at) <= CURRENT_TIMESTAMP - INTERVAL '{date_quantity} hours' OR COUNT(os.id) = 0"
        case settings.Users.FILTER_DATE_DAYS:
            date_condition = f"HAVING max(os.saved_at) <= CURRENT_DATE - INTERVAL '{date_quantity} days' OR COUNT(os.id) = 0"
        case settings.Users.FILTER_DATE_MONTH:
            date_condition = f"HAVING max(os.saved_at) <= CURRENT_DATE - INTERVAL '{date_quantity} month' OR COUNT(os.id) = 0"
    query = text(f"""SELECT
                           u.id as id,
                           u.login_name as login_name,
                           u.phone as phone,
                           u.balance as balance,
                           u.email as email,
                           u.role as role,
                           u.status as status,
                           CASE WHEN MAX(a.id) IS NOT NULL THEN MAX(a.id) ELSE u.id END as admin_id,
                           CASE WHEN MAX(a.login_name) IS NOT NULL THEN MAX(a.login_name) ELSE u.login_name END as admin_name,
                           MAX(pr.price_code) as price_code,
                           MAX(pr.price_1) as price_1,
                           MAX(pr.price_2) as price_2,
                           MAX(pr.price_3) as price_3,
                           MAX(pr.price_4) as price_4,
                           MAX(pr.price_5) as price_5,
                           MAX(pr.price_6) as price_6,
                           MAX(pr.price_7) as price_7,
                           MAX(pr.price_8) as price_8,
                           MAX(pr.price_9) as price_9,
                           MAX(pr.price_10) as price_10,
                           MAX(pr.price_11) as price_11,
                           bool_and(pr.price_at2) as price_at2,
                           u.client_code as client_code,
                           u.created_at as created_at,
                           MAX(pc.code) as partners_code,
                           COUNT(os.id) as orders_count,
                           sum(os.marks_count) as total_marks_count,
                           MAX(os.created_at) as os_created_at,
                           COALESCE(max(rs.comment), '') as comment,
                           MAX(rs.call_result) as call_result,
                           COALESCE(to_char(MAX(rs.updated_at),'dd-mm-yyyy hh24:mi'), '-') as last_call_update
                    FROM public.users u
                    LEFT JOIN public.users a ON u.admin_parent_id = a.id
                    LEFT JOIN public.orders_stats as os on os.user_id=u.id
                    LEFT JOIN public.prices pr on pr.id=u.price_id
                    LEFT JOIN public.users_partners as up on up.user_id=u.id
                    LEFT JOIN public.partner_codes as pc on pc.id=up.partner_code_id
                    LEFT JOIN public.reanimate_status as rs on rs.user_id = u.id
                    WHERE u.role=:role
                    {user_filter}
                    GROUP BY u.id, u.login_name
                    {date_condition}
                    ORDER BY """ + str(order_clause) + ";").bindparams(role=settings.ORD_USER)

    stmt = query.bindparams(u_id=u_id) if u_id else query
    return db.session.execute(stmt).fetchall()


def helper_get_reanimate_call_result() -> tuple[int, str, str]:
    user_id = request.json.get('user_id', None)
    comment = request.json.get('comment', None)
    call_result = request.json.get('call_result', None)
    return user_id, comment, call_result
