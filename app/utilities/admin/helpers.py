import urllib
from datetime import datetime, timedelta
from flask import jsonify, request, render_template, Response, url_for, make_response
from io import BytesIO
from pandas import DataFrame, ExcelWriter
from pandas import to_datetime as pd_datetime
from time import sleep as t_sleep
from sqlalchemy import asc, desc, text, TextClause
from sqlalchemy.engine.row import Row
from typing import Optional

from config import settings
from models import db, User
from utilities.admin.excel_report import ExcelReport
from utilities.sql_categories_aggregations import SQLQueryCategoriesAll
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
                                    WHERE u.admin_parent_id=:u_id OR u.id = :u_id
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


def helper_get_orders_stats_stmt(date_from, date_to, admin_id: Optional[int] = None,
                                 extend_agent: int = 0, ) -> TextClause:
    additional_stmt = ""
    sub_stmt = " OR u.id=:admin_id" if extend_agent else ""
    if admin_id:
        additional_stmt = f"""and os.user_id in (SELECT u.id FROM public.users u WHERE u.admin_parent_id=:admin_id {sub_stmt})"""
    order_stmt = text(f"""SELECT    
                                    os.created_at as created_at,
                                    os.order_idn as order_idn,
                                    MAX(pc.code) as partner_code,
                                    MAX(u.login_name) as user_name,
                                    os.company_idn as company_idn,
                                    os.company_type || ' ' ||
                                    os.company_name as company_name,
                                     MAX(u.phone) as phone,
                                    os.rows_count as rows_count,
                                    os.marks_count as marks_count,
                                    os.op_cost as op_cost,
                                    os.category as category,
                                    os.op_cost * os.marks_count as price,
                                    case when os.op_cost is not null then 'Оплачен' else 'Не оплачен' end as order_status

                                 FROM public.orders_stats os
                                 LEFT JOIN public.users u on u.id=os.user_id
                                 LEFT JOIN public.users_partners up on up.user_id =u.id
                                 LEFT JOIN public.partner_codes pc on pc.id = up.partner_code_id
                                 WHERE
                                 os.created_at >= :date_from
                                 and os.created_at < :date_to
                                 {additional_stmt}
                                 GROUP BY os.id, os.created_at
                                 ORDER BY os.created_at DESC
                             """)

    params = {
        "date_from": datetime.strptime(date_from, '%d.%m.%Y').strftime('%Y-%m-%d'),
        "date_to": datetime.strptime(date_to, '%d.%m.%Y').strftime('%Y-%m-%d'),
    }
    if admin_id:
        params["admin_id"] = admin_id

    return order_stmt.bindparams(**params)


def helper_get_orders_stats_param(report: bool = False):
    admin_id = None
    default_day_to = (datetime.today() + timedelta(days=1)).strftime('%d.%m.%Y')
    default_day_from = (datetime.today() - timedelta(days=settings.ORDERS_REPORT_TIMEDELTA)).strftime('%d.%m.%Y')
    if report:
        url_date_from = request.form.get('date_from', '', type=str)
        url_date_to = request.form.get('date_to', '', type=str)
        extend_agent = request.form.get('extend_agent', 0, type=int)
        admin_id = request.form.get('admin_id', 0, type=int)

    else:
        url_date_from = request.args.get('date_from', '', type=str)
        url_date_to = request.args.get('date_to', '', type=str)
        extend_agent = request.args.get('extend_agent', 0, type=int)

    date_to = datetime.strptime(url_date_to, '%d.%m.%Y').strftime('%d.%m.%Y') if url_date_to else default_day_to
    date_from = (datetime.strptime(url_date_from, '%d.%m.%Y') + timedelta(days=1)).strftime(
        '%d.%m.%Y') if url_date_from else default_day_from

    return date_from, date_to, extend_agent, admin_id


def helper_get_orders_stats(admin_id: Optional[int] = None) -> Response:
    date_from, date_to, extend_agent, _ = helper_get_orders_stats_param()
    order_stmt = helper_get_orders_stats_stmt(date_from, date_to, admin_id, extend_agent, )
    order_stats = db.session.execute(order_stmt).fetchall()

    bck = request.args.get('bck', 0, type=int)
    if not order_stats:
        return render_template('admin/orders_stats/os_main.html', **locals()) if not bck \
            else jsonify(
            {
                'htmlresponse': render_template(
                    f'admin/orders_stats/os_table.html',
                    **locals()
                )
             }
        )

    link_filters = 'bck=1&'
    link = f'javascript:bck_get_orders_stats(\'' + url_for(
        'admin_control.users_orders_stats', admin_id=admin_id) + f'?extend_agent={extend_agent}&{link_filters}' + 'page={0}\');'
    page, per_page, \
        offset, pagination, \
        os_list = helper_paginate_data(data=order_stats, per_page=settings.PAGINATION_PER_PAGE, href=link)
    return render_template('admin/orders_stats/os_main.html', **locals()) if not bck \
        else jsonify({'htmlresponse': render_template(f'admin/orders_stats/os_table.html',
                                                      **locals())})


def helper_get_orders_stats_rpt():
    date_from, date_to, extend_agent, admin_id = helper_get_orders_stats_param(report=True)
    order_stmt = helper_get_orders_stats_stmt(date_from, date_to, admin_id, extend_agent)
    order_stats = db.session.execute(order_stmt).fetchall()
    order_stats = [row[:4] + row[5:9] + row[10:] for row in order_stats]
    excel_filters = {
        'дата начала': date_from,
        'дата окончания': (datetime.strptime(date_to, '%d.%m.%Y') - timedelta(days=1)).strftime('%d.%m.%Y'),
        'с заказами агента': 'да' if extend_agent else 'нет'
    }
    if not admin_id:
        del excel_filters['с заказами агента']

    report_name = f'статистика заказов ({datetime.today().strftime("%d.%m.%y %H-%M")})'

    excel = ExcelReport(
        data=order_stats,
        filters=excel_filters,
        columns_name=[
            'дата',
            'номер заказа',
            'код партнера',
            'аккаунт ID',
            'фирма',
            'телефонный номер',
            'сколько строк',
            'сколько марок',
            'категория',
            'цена заказа(руб)',
            'статус',
        ],
        sheet_name='История заказов',
        output_file_name=report_name,
        condition_format={10: [{
            'type': 'cell',
            'criteria': 'equal',
            'value': '"Оплачен"',
            'format': {'bg_color': 'green'}
        }, {
            'type': 'cell',
            'criteria': '!=',
            'value': '"Оплачен"',
            'format': {'bg_color': 'red'}
        }]
        }
    )

    excel_io = excel.create_report()
    content = excel_io.getvalue()
    response = make_response(content)
    response.headers['data_file_name'] = urllib.parse.quote(excel.output_file_name)
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['data_status'] = 'success'
    return response


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
                                  {SQLQueryCategoriesAll.get_stmt(field='marks_count')} as pos_count
                              FROM public.users u
                                  JOIN public.orders o ON o.user_id = u.id  
                                  LEFT JOIN public.users a ON u.admin_parent_id = a.id  
                                  {SQLQueryCategoriesAll.get_joins()} 
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
    stmt = text(""" SELECT count(id) as orders_count, coalesce(sum(marks_count), 0) as marks_count 
                     FROM public.orders_stats WHERE saved_at >= :yesterday_from
                    AND saved_at < :yesterday_to;""").bindparams(
        yesterday_from=yesterday.strftime('%Y-%m-%d 00:00:00'),
        yesterday_to=yesterday.strftime('%Y-%m-%d 23:59:59'))
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
