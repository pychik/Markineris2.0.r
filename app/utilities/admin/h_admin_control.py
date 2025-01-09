import re
import urllib
from datetime import datetime, timedelta
from decimal import Decimal

from flask import flash, render_template, redirect, send_file, url_for, request, Response, jsonify, make_response
from flask_login import current_user
from sqlalchemy.orm import joinedload

from views.crm.crm_support import h_cancel_order_process_payment
from sqlalchemy import asc, desc, func, text, select, bindparam
from sqlalchemy.exc import NoResultFound

from sqlalchemy.exc import IntegrityError
from urllib import parse
from werkzeug.security import generate_password_hash

from config import settings
from logger import logger
from models import db, Order, OrderStat, PartnerCode, RestoreLink, Telegram, TelegramMessage, User, users_partners, \
    Price, TgUser, ReanimateStatus
from utilities.download import orders_process_send_order
from utilities.support import (url_encrypt, helper_check_form, helper_update_order_note, helper_paginate_data,
                               helper_strange_response, sql_count, helper_get_filter_users,
                               helper_get_at2_pending_balance, get_partner_code_max_id)
from utilities.admin.schemas import AROrdersSchema, ar_categories_types
from utilities.admin.helpers import (process_admin_report, helper_get_clients_os, helper_get_orders_stats,
                                     helper_prev_day_orders_marks, helper_get_users_reanimate,
                                     helper_get_reanimate_call_result, helper_get_new_orders_at2,
                                     helper_check_new_order_at2, helper_get_orders_stats_rpt)
from utilities.admin.excel_report import ExcelReport


def h_index():
    if current_user.role != settings.SUPER_USER:
        return redirect(url_for('admin_control.admin', u_id=current_user.id))

    users_stmt = text(f"""SELECT au.id as id,
                                au.role as role,
                                au.balance as balance,
                                au.login_name as login_name,
                                au.email as email,
                                au.client_code as client_code,
                                au.agent_fee as agent_fee,
                                au.trust_limit as trust_limit,
                                au.is_crm as is_crm,
                                au.is_at2 as is_at2, au.status as status, au.phone as phone,
                                au.created_at as created_at, pq.price_code as price_code, pq.price_1 as price_1, pq.price_2 as price_2,
                                pq.price_3 as price_3, pq.price_4 as price_4, pq.price_5 as price_5, pq.price_6 as price_6, pq.price_7 as price_7,
                                pq.price_8 as price_8, pq.price_9 as price_9, pq.price_10 as price_10, pq.price_11 as price_11,
                                pq.price_at2 as price_at2, tq.channel_id as tg_channel_id, tq.name as tg_name,
                                tq.comment as tg_comment,
                                count(u.id) as reg_clients,
                                (select array[count(os.id), sum(os.rows_count), sum(os.marks_count)] from public.orders_stats os where os.user_id in (select uu.id from public.users uu where uu.admin_parent_id=au.id or uu.id=au.id) limit 1) as data_orders_array
                            FROM public.users au
                            LEFT JOIN public.users_telegrams ut on ut.user_id = au.id
                            LEFT JOIN public.telegram tq on ut.telegram_id = tq.id
                            LEFT JOIN public.prices pq on au.price_id = pq.id
                            LEFT JOIN public.users u on u.admin_parent_id = au.id
                            WHERE au.role in :roles
                            group by au.id, pq.price_code, pq.price_1, pq.price_2,pq.price_3, pq.price_4, pq.price_5, pq.price_6, pq.price_7, pq.price_8, pq.price_9, pq.price_10, pq.price_11, pq.price_at2, tg_channel_id, tg_name, tg_comment
                            order by au.id""").bindparams(bindparam("roles", expanding=True))

    su_list = db.session.execute(users_stmt, {"roles": [settings.ADMIN_USER, settings.SUPER_USER]}).fetchall()
    new_user_stmt = text("""
           SELECT
               count(1) as new_user_cnt  
           FROM public.users
           WHERE
               created_at >= DATE_TRUNC('DAY', NOW()) - interval '1 DAY'
               and created_at < DATE_TRUNC('DAY', NOW());
               """)
    new_user_cnt = db.session.execute(new_user_stmt).one()
    registration_date = datetime.today() - timedelta(days=1)

    ou_quantity = User.query.filter(User.role == settings.ORD_USER) \
        .order_by(User.id).count()

    telegram_list = Telegram.query.all()
    if current_user.role == settings.SUPER_USER:
        tg_group_list = Telegram.query.filter_by(status=False).all()
        prev_day_orders_marks = helper_prev_day_orders_marks()
    markineris_url_coi = settings.MARKINERIS_CHECK_CROSS_OI_LINK
    markineris_secret = settings.MARKINERIS_SECRET

    basic_prices = settings.Prices.BASIC_PRICES
    all_prices = Price.query.with_entities(Price.id, Price.price_code, Price.price_at2).order_by(
        desc(Price.created_at)).all()
    return render_template('admin/a_control/main_admin.html', **locals())


def h_su_get_telegram() -> Response:
    telegram_list = Telegram.query.all()
    return jsonify({'htmlresponse': render_template('admin/a_control/tg_table.html', **locals())})


def h_admin(u_id: int):

    page = request.args.get('page', 1, type=int)

    admin_info = User.query.filter_by(id=u_id).first()
    if admin_info:
        os_query = db.session.query(
            func.count(OrderStat.id).label("orders_count"),
            func.sum(OrderStat.rows_count).label("total_rows_count"),
            func.sum(OrderStat.marks_count).label("total_marks_count"),
            func.max(OrderStat.created_at).label("os_created_at"),
            OrderStat.user_id
        ).filter(User.id == OrderStat.user_id).group_by(OrderStat.user_id)\
            .subquery()

        partner_query = db.session.query(users_partners.c.user_id, PartnerCode.code)\
            .join(PartnerCode, PartnerCode.id == users_partners.c.partner_code_id)\
            .subquery()

        sort_type = request.args.get("sort_type")
        order_type = desc(User.created_at) if sort_type != 'orders' else asc(os_query.c.os_created_at)

        users_info = db.session.query(
            User.id, User.role, User.balance, User.login_name, User.email, User.client_code, User.status,
            User.phone, User.created_at, partner_query.c.user_id, partner_query.c.code, os_query.c.orders_count,
            os_query.c.total_rows_count, os_query.c.total_marks_count, os_query.c.os_created_at,
            Price.price_code, Price.price_1, Price.price_2, Price.price_3, Price.price_4, Price.price_5,
            Price.price_6, Price.price_7, Price.price_8, Price.price_9, Price.price_10, Price.price_11, Price.price_at2
        ).outerjoin(
            Price, User.price_id == Price.id,
        ).outerjoin(
            os_query, User.id == os_query.c.user_id,
        ).outerjoin(
            partner_query, User.id == partner_query.c.user_id,
        ).filter(
            User.admin_parent_id == u_id,
        ).group_by(
            User.id, os_query.c.orders_count, os_query.c.total_rows_count, os_query.c.total_marks_count,
            os_query.c.os_created_at, partner_query.c.user_id, partner_query.c.code, Price.price_code,
            Price.price_1, Price.price_2, Price.price_3, Price.price_4, Price.price_5, Price.price_6,
            Price.price_7, Price.price_8, Price.price_9, Price.price_10, Price.price_11, Price.price_at2
        ).order_by(order_type).all()

        page, per_page, \
            offset, pagination, \
            users_list = helper_paginate_data(data=users_info, per_page=settings.PAGINATION_PER_PAGE)
        basic_prices = settings.Prices.BASIC_PRICES

        all_prices = Price.query.with_entities(Price.id, Price.price_code, Price.price_at2) \
                          .order_by(desc(Price.created_at)).all()

        order_notification = admin_info.order_notification if admin_info.order_notification is not None\
                                                             and admin_info.order_notification != '' \
                                                             else settings.AGENT_DEFAULT_NOTE

        order_edit_description = settings.ORDER_EDIT_DESCRIPTION
        partner_code_id = PartnerCode.query.with_entities(PartnerCode.id).\
            filter_by(code=settings.NO_PARTNER_CODE).first().id

        admin_partner_codes = [(p.code, f"{u_id}__{p.id}") for p in admin_info.partners]

        partner_sign_up_list = [(
            apc[0], url_for('auth.sign_up', p_link=url_encrypt(apc[1]))
        ) for apc in admin_partner_codes]
        auto_increment_id = get_partner_code_max_id(admin_info.partners)

        if admin_info.telegram_message:
            telegram_message = admin_info.telegram_message[0]
        else:
            telegram_message = None

        return render_template('admin/a_user_control/main.html', **locals())

    else:
        flash(message=settings.Messages.USER_NOT_EXIST, category='error')
        return redirect(url_for('main.enter'))

def h_get_partner_codes(u_id: int):
    admin_info = None
    partner_codes = User.query.join(users_partners, User.id == users_partners.c.user_id).join(PartnerCode, users_partners.c.partner_code_id == PartnerCode.id).with_entities(PartnerCode.id.label('id'), PartnerCode.code.label('code'), PartnerCode.name.label('name'), PartnerCode.phone.label('phone'), PartnerCode.required_phone.label('required_phone')).filter(User.id == u_id).all()

    return jsonify({'htmlresponse': render_template('admin/a_user_control/registered_partners_code_modal.html', **locals())})


def h_get_registration_link(u_id: int):
    admin_info = User.query.join(users_partners, User.id == users_partners.c.user_id).join(PartnerCode, users_partners.c.partner_code_id == PartnerCode.id).with_entities(User.id.label('u_id'), PartnerCode.code.label('code'), PartnerCode.id.label('id')).filter(User.id == u_id).all()
    if admin_info:
        admin_partner_codes = [(p.code, f"{u_id}__{p.id}") for p in admin_info]
        partner_sign_up_list = [(
            apc[0], url_for('auth.sign_up', p_link=url_encrypt(apc[1]))
        ) for apc in admin_partner_codes]

        return jsonify({'htmlresponse': render_template('admin/a_user_control/new_registration_link_modal.html', **locals())})

    return Response(status=200)

def h_set_order_notification(u_id: int):
    message_status = 'error'
    form_dict = request.form.to_dict()
    order_note = form_dict.get("order_note")
    if not helper_check_form(on=order_note) or not helper_update_order_note(on=order_note, u_id=u_id):
        message = settings.Messages.FORM_CONTENT_ERROR

    else:
        message = settings.Messages.ORDER_NOTE_UPDATE_SUCCESS
        message_status = 'success'

    return jsonify({'message': message, 'type': message_status})


def h_create_admin():
    set_dict = request.form.to_dict()
    tg_id = set_dict.get("tg_select_id")
    login_name = set_dict.get("admin_login_name")
    password = set_dict.get("admin_password")

    is_at2 = True if set_dict.get("radio_is_telegram") else False
    is_crm = True if set_dict.get("radio_is_crm") else False
    email = "{login}{postfix}".format(login=login_name.replace(' ', '').lower(), postfix=settings.ADMIN_USER_POSTFIX)
    if is_at2 == is_crm:
        flash(message=f"{settings.Messages.ADMIN_CREATE_ERROR} некорректные входные данные", category='error')
        return redirect(url_for('admin_control.index'))
    elif is_at2:
        return helper_create_at2_admin(login_name=login_name, email=email, password=password, tg_id=tg_id)
    elif is_crm:
        return helper_create_crm_admin(login_name=login_name, email=email, password=password)
    else:
        flash(message=f"{settings.Messages.ADMIN_CREATE_ERROR} не выбран тип агента", category='error')

        return redirect(url_for('admin_control.index', expanded=settings.EXP_USERS))


def h_partner_code(u_id: int, auto: int = 0):
    message_status = 'error'
    admin_info = User.query.get(u_id)
    required_email = True  # if form_dict.get("required_email") else False
    required_phone = True  # if set_dict.get("required_phone") else False

    if auto == 1:
        auto_increment_id = get_partner_code_max_id(admin_info.partners)
        name = admin_info.login_name + '_' + auto_increment_id
        code = name
        phone = settings.SU_PHONE
    elif auto == 0:
        set_dict = request.form.to_dict()
        name = set_dict.get("name")
        code = set_dict.get("code")
        phone = set_dict.get("phone")
        if '__' in code:
            message = (f"{settings.Messages.PARTNER_CODE_ERROR} В партнер код нельзя ставить подряд __. "
                       f"Попробуйте придумать другой код")
            return jsonify({'message': message, 'status': message_status}), 400

    else:
        message = (f"{settings.Messages.PARTNER_CODE_ERROR} В партнер код нельзя ставить подряд __. "
                   f"Попробуйте придумать другой код")
        message_status = 'error'
        return jsonify({'message': message, 'message_status': message_status}), 400

    partner_code = PartnerCode(
        name=name,
        code=code,
        phone=phone,
        required_phone=required_phone,
        required_email=required_email
    )
    try:
        admin_info.partners.append(partner_code)
        db.session.add(admin_info)
        db.session.commit()
        message = f"{settings.Messages.PARTNER_CODE_CREATE} {name} "
        message_status = 'success'
        partners_name = [partner.name for partner in admin_info.partners]

        auto_increment_id = get_partner_code_max_id(admin_info.partners)
        return jsonify(
            {'message': message,
             'status': message_status,
             'htmlresponse': render_template('admin/a_user_control/partner_code_add_modal_body.html', **locals())
             })

    except IntegrityError as e:
        message_status = 'error'
        db.session.rollback()
        message = f"{settings.Messages.PARTNER_CODE_DUPLICATE_ERROR} {code}" if "psycopg2.errors.UniqueViolation)" \
                                                                                in str(e) \
            else f"{settings.Messages.PARTNER_CODE_ERROR} {e}"

        logger.error(message)
        return jsonify({'message': message, 'status': message_status}), 400


def h_su_not_basic_price_report() -> Response:
    column_names = [
        'e-mail',
        'login',
        'agent_login',
        'Наименование',
        'Цена [1, 99], руб',
        'Цена [100, 499], руб.',
        'Цена [500, 999], руб.',
        'Цена [1000, 2999], руб.',
        'Цена [3000+], руб',
    ]
    price_stmt = text("""
        SELECT
        U.EMAIL as EMAIL,
        U.LOGIN_NAME as LOGIN_NAME,
        U_AGENT.LOGIN_NAME as AGENT_NAME,
        P.PRICE_CODE AS PRICE_CODE,
        P.PRICE_1 as PRICE_FROM_1_TO_99,
        P.PRICE_2 as PRICE_FROM_100_TO_499,
        P.PRICE_3 as PRICE_FROM_500_TO_999,
        P.PRICE_4 as PRICE_FROM_1000_TO_2999,
        P.PRICE_5 as PRICE_FROM_3000
    FROM
        USERS U
        LEFT JOIN USERS AS U_AGENT ON U.ADMIN_PARENT_ID = U_AGENT.ID
        JOIN PRICES P ON U.PRICE_ID = P.ID
    WHERE
        P.PRICE_CODE != 'BASIC'
    ORDER BY
        P.PRICE_CODE,
        U.EMAIL
    """)
    prises = db.session.execute(price_stmt).all()
    excel = ExcelReport(
        data=prises,
        columns_name=column_names,
        sheet_name=settings.Prices.NOT_BASIC_PRICE_REPORT_SHEET_NAME,
        output_file_name=settings.Prices.NOT_BASIC_PRICE_REPORT_FILE_NAME.format(datetime.today().strftime('%d.%m.%Y'))
    )

    excel_io = excel.create_report()
    content = excel_io.getvalue()
    response = make_response(content)
    response.headers['data_file_name'] = urllib.parse.quote(excel.output_file_name)
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['data_status'] = 'success'

    return response


def h_delete_partner_code(u_id: int, p_id: int) -> Response:

    message_status = 'error'
    partner_code = PartnerCode.query.filter_by(id=p_id).first()
    if not partner_code:
        return jsonify({'message': settings.Messages.STRANGE_REQUESTS, 'status': message_status})

    try:
        db.session.delete(partner_code)
        db.session.commit()
        message = settings.Messages.PARTNER_CODE_DELETE_SUCCESS.format(partner_code=partner_code.code)
        message_status = 'success'
        admin_info = User.query.get(u_id)
        auto_increment_id = get_partner_code_max_id(admin_info.partners)
    except Exception as e:
        message = settings.Messages.PARTNER_CODE_DELETE_ERROR
        message_status = 'error'
        logger.error(f"{settings.Messages.PARTNER_CODE_DELETE_ERROR}: {e}")
        db.session.rollback()

    return jsonify(
        {
            'message': message,
            'status': message_status,
            'htmlresponse': render_template('admin/a_user_control/partner_code_add_modal_body.html', **locals())
        }
    )


def h_telegram_set_group() -> Response:
    form_dict = request.form.to_dict()
    channel_id = form_dict.get("tg_channel_id")
    name = form_dict.get("tg_name")
    comment = form_dict.get("comment")

    try:
        new_telegram = Telegram(channel_id=channel_id, name=name, comment=comment)
        db.session.add(new_telegram)
        db.session.commit()
        flash(message=settings.Messages.TELEGRAM_SET_SUCCESS)
    except IntegrityError as e:
        db.session.rollback()
        message = f"{settings.Messages.TELEGRAM_SET_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)

        return redirect(url_for('admin_control.index'))

    return redirect(url_for('admin_control.index', expanded=settings.EXP_TELEGRAM))


def h_telegram_message_set(u_id: int, t_id: int) -> Response:
    message_status = 'error'
    form_dict = request.form.to_dict()
    send_admin_info = form_dict.get("send_admin_info")
    send_organization_name = form_dict.get("send_organization_name")
    send_organization_idn = form_dict.get("send_organization_idn")
    send_login_name = form_dict.get("send_login_name")
    send_email = form_dict.get("send_email")
    send_phone = form_dict.get("send_phone")
    send_client_code = form_dict.get("send_client_code")

    try:
        telegram_message = TelegramMessage.query.filter_by(id=t_id).first()
        telegram_message.send_admin_info = True if send_admin_info == 'true' else False
        telegram_message.send_organization_name = True if send_organization_name == 'true' else False
        telegram_message.send_organization_idn = True if send_organization_idn == 'true' else False
        telegram_message.send_login_name = True if send_login_name == 'true' else False
        telegram_message.send_email = True if send_email == 'true' else False
        telegram_message.send_phone = True if send_phone == 'true' else False
        telegram_message.send_client_code = True if send_client_code  == 'true' else False
        db.session.commit()
        message_status = 'success'
        message = settings.Messages.TELEGRAM_MPSET_SUCCESS

    except IntegrityError as e:
        db.session.rollback()
        message = f"{settings.Messages.TELEGRAM_MPSET_ERROR} {e}"
        logger.error(message)

    return jsonify({'message': message, 'type': message_status})


def h_telegram_group_bind() -> Response:
    form_dict = request.form.to_dict()
    t_id = form_dict.get("t_id")
    u_id = form_dict.get("u_id")

    try:
        user = User.filter(id=u_id)
        telegram = Telegram.filter(id=t_id)
        user.telegram.append(telegram)
        db.session.add(user)
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        message = f"{settings.Messages.TELEGRAM_BIND_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)

        return redirect(url_for('admin_control.index'))

    return redirect(url_for('admin_control.index', expanded=settings.EXP_TELEGRAM))


def h_delete_telegram_group(t_id: int) -> Response:

    telegram = Telegram.query.filter_by(id=t_id).first()

    if not telegram:
        message = f"{settings.Messages.TELEGRAM_DELETE_ERROR}"
        message_status = 'error'
        return jsonify({'message': message, 'status': message_status})
    if telegram.users:
        user = telegram.users[0]
        user.is_at2 = False
    telegram.users = []
    message = f"{settings.Messages.TELEGRAM_DELETE_SUCCESS}"
    message_status = 'success'
    db.session.delete(telegram)
    db.session.commit()
    return jsonify({'message': message, 'status': message_status})


def h_set_user_admin(u_id: int) -> Response:
    user = User.query.filter_by(id=u_id).first()
    if not user:
        flash(message=f"{settings.Messages.ACTIVATED_USER_ERROR}", category='error')
        return redirect(url_for('admin_control.index'))
    user.status = True
    db.session.commit()
    flash(message=f"{settings.Messages.ACTIVATED_ADMIN} {user.login_name}")
    return redirect(url_for('admin_control.index', expanded=settings.EXP_USERS))


def h_set_user(type_set: str, u_id: int) -> Response:

    user = User.query.filter_by(id=u_id).first()

    if not user:
        flash(message=f"{settings.Messages.ACTIVATED_USER_ERROR}", category='error')
        return redirect(url_for('admin_control.index'))
    if current_user.role != settings.SUPER_USER and current_user.id != user.admin_parent_id:
        flash(message=f"{settings.Messages.STRANGE_REQUESTS} {settings.Messages.ACTIVATED_USER_ND_ERROR}",
              category='error')
        return redirect(url_for('admin_control.admin', u_id=current_user.id))

    admin = User.query.filter_by(id=user.admin_parent_id).first()
    try:
        match type_set:
            case settings.ACTIVATE_USER:
                user.status = True
                user.client_code = request.form.get("client_code")[:30]
                flash(message=f"{settings.Messages.ACTIVATED_USER} {user.login_name}")
            case settings.ACTIVATE_IS_SEND_EXCEL:
                if admin.is_at2:
                    user.is_send_excel = True
                    flash(message=f"{settings.Messages.ACTIVATED_EXCEL_UPLOAD_USER} {user.login_name}")
                else:
                    flash(message=f"{settings.Messages.ACTIVATED_EXCEL_UPLOAD_ERROR}", category='error')

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.ACTIVATED_USER_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)

    if user.role == settings.ORD_USER:
        return redirect(url_for('admin_control.admin', u_id=user.admin_parent_id))
    else:
        return redirect(url_for('admin_control.index', expanded=settings.EXP_USERS))


def h_deactivate_user(type_set: str, u_id: int) -> Response:
    user = User.query.filter_by(id=u_id).first()
    if current_user.role != settings.SUPER_USER and current_user.id != user.admin_parent_id:
        flash(message=f"{settings.Messages.STRANGE_REQUESTS} {settings.Messages.DEACTIVATED_ND_USER_ERROR}",
              category='error')
        return redirect(url_for('admin_control.admin', u_id=current_user.id))
    try:
        match type_set:
            case settings.DEACTIVATE_USER:
                user.status = False
                flash(message=f"{settings.Messages.DEACTIVATED_USER} {user.login_name}")
            case settings.DEACTIVATE_IS_SEND_EXCEL:
                user.is_send_excel = False
                flash(message=f"{settings.Messages.DEACTIVATED_EXCEL_UPLOAD_USER} {user.login_name}")
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.DEACTIVATED_USER_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)

    return redirect(url_for('admin_control.admin', u_id=user.admin_parent_id))


def h_activate_all_admin_users(au_id: int) -> Response:
    status = 'error'
    if current_user.role != settings.SUPER_USER and current_user.id != au_id:
        flash(message=f"{settings.Messages.DELETE_USER_ERROR} {settings.Messages.DELETE_USER_ND_ERROR}",
              category='error')
        return redirect(url_for('admin_control.admin', u_id=current_user.id))
        message = f"{settings.Messages.DELETE_USER_ERROR} {settings.Messages.DELETE_USER_ND_ERROR}",
        return jsonify({'message': message, 'status': status})

    try:
        users = User.query.filter_by(admin_parent_id=au_id, status=False).all()
        if users:
            for u in users:
                u.status = True
            db.session.commit()

        message = settings.Messages.ACTIVATE_ALL_USERS_SUCCESS
        status = 'success'
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.ACTIVATE_ALL_USERS_ERROR} {e}"
        status = 'error'
        logger.error(message)

    return jsonify({'message': message, 'status': status})

def h_deactivate_user_admin(u_id: int) -> Response:
    user = User.query.filter_by(id=u_id).first()
    try:
        user.status = False
        db.session.commit()
        flash(message=f"{settings.Messages.DEACTIVATED_ADMIN} {user.login_name}")
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.DEACTIVATED_USER_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)

    return redirect(url_for('admin_control.index', expanded=settings.EXP_USERS))


def h_bck_set_user_price(u_id: int) -> Response:
    """
        process request from admin_control.index and admin_control.admin , result is connecting price to user
    :param u_id:
    :return:
    """
    def _make_user_block(user_id: int, login_name: str, price_code: str,
                         price_1: Decimal, price_2: Decimal, price_3: Decimal, price_4: Decimal, price_5: Decimal, price_6: Decimal,
                         price_7: Decimal, price_8: Decimal, price_9: Decimal, price_10: Decimal, price_11: Decimal, csrf: str,
                         price_at2: bool = False) -> str:
        text_badge = "bg-secondary" if price_at2 else "bg-warning text-black"
        return f'<span class="badge {text_badge}" style="cursor:pointer" ' \
               f'onclick = "perform_modal_prices(\'{user_id}\', \'{login_name}\', \'{price_code}\',' \
               f' \'{price_1}\', \'{price_2}\', \'{price_3}\',' \
               f' \'{price_4}\', \'{price_5}\', \'{price_6}\', \'{price_7}\', \'{price_8}\', \'{price_9}\', \'{price_10}\', \'{price_11}\', ' \
               f'\'{url_for("admin_control.bck_set_user_price", u_id=u_id)}?bck=1\', \'{csrf}\')">' \
               f'{price_code}</span>'

    status = settings.ERROR
    message = settings.Messages.USER_PRICE_TYPE_VALUE_ERROR
    user_block = None
    user = User.query.filter(User.id == u_id).with_entities(User.id, User.login_name, User.admin_parent_id, User.role, User.is_at2).first()

    try:
        if not user or (current_user.role != settings.SUPER_USER and user.admin_parent_id != current_user.id):
            message = settings.Messages.USER_PRICE_TYPE_ADMIN_ERROR

            raise ValueError
        p_id = request.form.get('price_id', '').replace('--', '')
        csrf = request.form.get('csrf_token', '').replace('--', '')

        if not p_id:
            # option receiving basic_prices
            basic_prices = settings.Prices.BASIC_PRICES
            user_block = _make_user_block(user_id=u_id, login_name=user.login_name, price_code=basic_prices[0],
                                          price_1=basic_prices[1], price_2=basic_prices[2], price_3=basic_prices[3],
                                          price_4=basic_prices[4], price_5=basic_prices[5], price_6=basic_prices[6],
                                          price_7=basic_prices[7], price_8=basic_prices[8], price_9=basic_prices[9],
                                          price_10=basic_prices[10], price_11=basic_prices[11], csrf=csrf)

            status = settings.SUCCESS
            message = settings.Messages.USER_PRICE_PLUG

            if user.role == settings.ORD_USER:
                db.session.execute(text(f"""UPDATE public.users SET price_id=NULL WHERE id=:u_id;""").bindparams(u_id=u_id))
            elif user.role in [settings.ADMIN_USER, settings.SUPER_USER, ]:
                db.session.execute(text(f"""UPDATE public.users
                                            SET price_id = NULL
                                            WHERE id IN (
                                                SELECT cl.id
                                                FROM public.users cl
                                                JOIN public.users admin ON admin.id = :u_id
                                                WHERE cl.admin_parent_id = :u_id
                                                  AND (
                                                      (cl.price_id = admin.price_id)
                                                      OR (cl.price_id IS NULL AND admin.price_id IS NULL)
                                                  )
                                            )
                                            OR id = :u_id;""").bindparams(u_id=u_id))
            else:
                raise ValueError
            db.session.commit()
            return jsonify(dict(status=status, message=message, user_block=user_block))

        # option receiving price from db
        price = Price.query.with_entities(Price.id, Price.price_code, Price.price_1, Price.price_2,
                                          Price.price_3, Price.price_4, Price.price_5, Price.price_6,
                                          Price.price_7, Price.price_8, Price.price_9, Price.price_10, Price.price_11,
                                          Price.price_at2) \
                           .filter(Price.id == p_id).first()

        if not price:
            message = f"{settings.Messages.USER_PRICE_TYPE_ERROR} нет такой цены!"
            raise ValueError

        user_block = _make_user_block(user_id=u_id, login_name=user.login_name, price_code=price.price_code,
                                      price_1=price.price_1, price_2=price.price_2, price_3=price.price_3,
                                      price_4=price.price_4, price_5=price.price_5, price_6=price.price_6,
                                      price_7=price.price_7, price_8=price.price_8, price_9=price.price_9,
                                      price_10=price.price_10, price_11=price.price_11, csrf=csrf,
                                      price_at2=price.price_at2)
        # db.session.execute(text(f"""UPDATE public.users SET price_id={p_id} WHERE id={u_id};"""))
        if user.role == settings.ORD_USER:
            db.session.execute(text(f"""UPDATE public.users SET price_id=:p_id WHERE id=:u_id;""").bindparams(u_id=u_id, p_id=p_id))
        elif user.role in [settings.ADMIN_USER, settings.SUPER_USER, ]:

            db.session.execute(text(f"""UPDATE public.users
                                        SET price_id = :p_id
                                        WHERE id IN (
                                                SELECT cl.id
                                                FROM public.users cl
                                                JOIN public.users admin ON admin.id = :u_id
                                                WHERE cl.admin_parent_id = :u_id
                                                  AND (
                                                      (cl.price_id = admin.price_id)
                                                      OR (cl.price_id IS NULL AND admin.price_id IS NULL)
                                                  )
                                            )
                                            OR id = :u_id;""").bindparams(
                u_id=u_id, p_id=p_id))
        else:
            raise ValueError
        db.session.commit()
        status = settings.SUCCESS
        message = settings.Messages.USER_PRICE_PLUG

    except ValueError:
        status = settings.ERROR
        logger.error(message)
        db.session.rollback()
        return jsonify(dict(status=status, message=message))
    except IntegrityError as e:
        db.session.rollback()
        message = f"{settings.Messages.USER_PRICE_TYPE_DUPLICATE_ERROR} {e}"
        logger.error(message)
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.USER_PRICE_TYPE_ERROR}"
        logger.error(f"{message} {e}")
    return jsonify(dict(status=status, message=message, user_block=user_block))


def h_set_process_type(u_id: int, p_type: str) -> Response:
    user = User.query.filter_by(id=u_id).first()
    try:
        if not user:
            raise Exception
        match p_type:
            case settings.OrderStage.ORDER_PROCESS_CRM:
                user.is_crm = True
                user.is_at2 = False
                user.trust_limit = 0
                helper_delete_tg(user=user)
                flash(message=f"{settings.Messages.USER_PROCESS_TYPE} {user.login_name}")

            case settings.OrderStage.ORDER_PROCESS_AT2:
                # user.is_crm = False
                user.is_crm = True
                user.is_at2 = True
                user.trust_limit = settings.TRUST_LIMIT_DEFAULT

                form_data = request.form.to_dict()
                t_id = form_data.get('tg_select')
                telegram = Telegram.query.get(t_id)
                if not telegram:
                    raise Exception

                telegram_message = TelegramMessage(send_admin_info=True)
                user.telegram_message.append(telegram_message)
                telegram.status = True
                user.telegram.append(telegram)

                # update tg for all users
                agent_users = [a for a in User.query.filter(User.admin_parent_id == user.id).all()]
                for u in agent_users:
                    u.telegram.append(telegram)

                flash(message=f"{settings.Messages.USER_PROCESS_TYPE} {user.login_name}")
            case _:  # not sure about this!  may be here should be logic for crm process

                user.is_crm = True
                user.is_at2 = False
                user.trust_limit = 0

                flash(message=f"{settings.Messages.USER_PROCESS_TYPE_ERROR}")

        # set all clients of admin process type
        db.session.execute(text("""UPDATE public.users
                                            SET is_crm=:is_crm, is_at2=:is_at2
                                          WHERE admin_parent_id=:user_id""")
                           .bindparams(is_crm=user.is_crm, is_at2=user.is_at2, user_id=user.id))

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.USER_PROCESS_TYPE_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)

    return redirect(url_for('admin_control.index', expanded=settings.EXP_USERS))


def h_delete_user_admin(u_id: int) -> Response:
    user = User.query.filter_by(id=u_id).first()
    if not user:
        flash(message=f"{settings.Messages.STRANGE_REQUESTS}", category='error')
        return redirect(url_for('admin_control.index', expanded=settings.EXP_USERS))
    if user.admin_group:
        flash(message=f"{settings.Messages.DELETE_USER_ERROR} у агента есть пользователи. Свяжитесь с администратором", category='error')
        return redirect(url_for('admin_control.index', expanded=settings.EXP_USERS))
    try:
        partner_codes = [p for p in user.partners]
        user.partners = []
        user.promos = []
        for p in partner_codes:
            db.session.delete(p)

        helper_delete_tg(user=user)
        user_id = user.id
        db.session.delete(user)
        db.session.commit()

        flash(message=f"{settings.Messages.DELETE_USER} {user.login_name} c id {user_id}")
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.DELETE_USER_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)

    return redirect(url_for('admin_control.index', expanded=settings.EXP_USERS))


def h_delete_user(u_id: int) -> Response:
    user = User.query.filter_by(id=u_id).first()
    admin_id = user.admin_parent_id
    # check for trickers
    if current_user.role != settings.SUPER_USER and current_user.id != admin_id:
        flash(message=f"{settings.Messages.DELETE_USER_ERROR} {settings.Messages.DELETE_USER_ND_ERROR}",
              category='error')
        return redirect(url_for('admin_control.admin', u_id=current_user.id))

    try:
        user.telegram = []
        user.partners = []
        user.promos = []
        tg_user = TgUser.query.filter_by(flask_user_id=user.id).first()
        db.session.delete(user)
        if tg_user:
            db.session.delete(tg_user)
        db.session.commit()
        flash(message=f"{settings.Messages.DELETE_USER} {user.login_name}")
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.DELETE_USER_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)

    return redirect(url_for('admin_control.admin', u_id=admin_id))


def h_create_link_new_password(u_id: int) -> str:
    user_info = User.query.filter_by(id=u_id).first()
    active_link = user_info.restore_link.filter_by(status=True).first()
    if active_link:

        return f"{request.host}{active_link.link}"
    time_now = datetime.now().strftime("%Y_%m_%d %H_%M_%S")
    new_link = url_for(
        'user_cp.create_new_password',
        r_link=url_encrypt(f"{user_info.id}__{time_now}"),
    )

    try:
        restore_link = RestoreLink(link=new_link)
        user_info.restore_link.append(restore_link)
        db.session.add(user_info)
        db.session.commit()

        return f"{request.host}{new_link}"
    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"{settings.Messages.GET_RESTORE_LINK_COMMON_ERROR} {e}")
        return f"Возникла ошибка"


def h_send_order() -> Response:
    form_dict = request.form.to_dict()
    order_idn_form = form_dict.get("inputOrderid")
    if not order_idn_form:
        flash(message=settings.Messages.NO_SUCH_ORDER)
        return redirect(url_for('admin_control.index'))
    order = Order.query.with_entities(Order.id, Order.category, Order.user_id, Order.order_idn).filter(Order.order_idn == order_idn_form).first()
    if not order:
        flash(message=settings.Messages.NO_SUCH_ORDER)
        return redirect(url_for('admin_control.index'))
    else:
        user = User.query.filter(User.id == order.user_id).first()

        if orders_process_send_order(
            o_id=order.id,
            user=user,
            order_comment='',
            order_idn=order.order_idn,
            su_exec_order_name=order_idn_form,
        ):

            flash(message=settings.Messages.ORDER_RESTORED_SENT)
        return redirect(url_for('admin_control.index'))


def h_download_agent_report(u_id: int) -> Response:

    agent = User.query.filter_by(id=u_id).first().login_name
    excel_object = process_admin_report(u_id=u_id, sheet_name=agent)

    if excel_object:
        return send_file(path_or_file=excel_object, download_name=f"Отчет по агенту {agent}.xlsx", as_attachment=True)
    else:
        flash(message=settings.Messages.DOWNLOAD_ADMIN_ERROR, category='error')
        return redirect(url_for('admin_control.index'))


def h_change_agent_fee(u_id: int) -> Response:
    a_fee_form = request.form.get("agent_fee_value", '0')
    a_fee = int(a_fee_form) if a_fee_form.isdigit() else None
    agent = User.query.filter_by(id=u_id).first()
    if agent and isinstance(a_fee, int) and settings.AGENT_FEE_MIN <= a_fee <= settings.AGENT_FEE_MAX:
        try:
            agent.agent_fee = a_fee
            flash(message=settings.Messages.CHANGE_AGENT_FEE_SUCCESS)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            message = f"{settings.Messages.CHANGE_AGENT_FEE_ERROR} {e}"
            flash(message=message, category='error')
            logger.error(message)

    else:
        flash(message=f"{settings.Messages.CHANGE_AGENT_FEE_ERROR} нет такого агента или введена некорректная ставка",
              category='error')
    return redirect(url_for('admin_control.index'))


def h_change_trust_limit(u_id: int) -> Response:

    trust_limit_form = request.form.get("agent_tl_value", '10000')
    trust_limit = int(trust_limit_form) if trust_limit_form.isdigit() else None
    # only for at2
    agent = User.query.filter_by(id=u_id, is_at2=True).first()
    if agent and isinstance(trust_limit, int) and settings.TRUST_LIMIT_MINIMUM <= trust_limit <= settings.TRUST_LIMIT_MAXIMUM:
        try:
            agent.trust_limit = trust_limit
            flash(message=settings.Messages.CHANGE_TRUST_LIMIT_SUCCESS)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(message=settings.Messages.CHANGE_TRUST_LIMIT_ERROR, category='error')
            message = f"{settings.Messages.CHANGE_TRUST_LIMIT_ERROR} {e}"
            logger.error(message)

    else:
        flash(message=f"{settings.Messages.CHANGE_AGENT_FEE_ERROR} нет такого агента или введена некорректная ставка",
              category='error')
    return redirect(url_for('admin_control.index'))


def h_su_user_search() -> Response:
    search_word = request.form.get('query')
    basic_prices = None
    if search_word:
        stmt_get_agent_id = f"CASE WHEN MAX(a.id) IS NOT NULL THEN MAX(a.id) ELSE u.id end"
        stmt_get_agent_name = f"CASE WHEN MAX(a.login_name) IS NOT NULL THEN MAX(a.login_name) ELSE u.login_name end"
        res = db.session.execute(text(
            # f"SELECT * FROM public.users "
            f"SELECT u.id as id, "
            f"u.login_name as login_name, "
            f"u.phone as phone, "
            f"u.balance as balance, "
            f"u.email as email, "
            f"u.role as role, "
            f"u.status as status, "
            f"{stmt_get_agent_id} as admin_id , "
            f"{stmt_get_agent_name} as admin_name , "
            f"max(pr.price_code) as price_code, "
            f"max(pr.price_1) as price_1, "
            f"max(pr.price_2) as price_2, "
            f"max(pr.price_3) as price_3, "
            f"max(pr.price_4) as price_4, "
            f"max(pr.price_5) as price_5, "
            f"max(pr.price_6) as price_6, "
            f"max(pr.price_7) as price_7, "
            f"max(pr.price_8) as price_8, "
            f"max(pr.price_9) as price_9, "
            f"max(pr.price_10) as price_10, "
            f"max(pr.price_11) as price_11, "
            f"bool_and(pr.price_at2) as price_at2, "
            f"u.role as role, "
            f"u.client_code as client_code, "
            f"u.created_at as created_at,"
            f"MAX(pc.code) as partners_code, "
            f"COUNT(os.id) as orders_count, "
            f"sum(os.marks_count) as total_marks_count, "
            f"MAX(os.created_at) as os_created_at "
            f"FROM public.users u "
            f"LEFT JOIN public.users a ON u.admin_parent_id = a.id "
            f"LEFT JOIN public.orders_stats as os on os.user_id=u.id "
            f"LEFT JOIN public.prices pr on pr.id=u.price_id "
            f"LEFT JOIN public.users_partners as up on up.user_id=u.id "
            f"LEFT JOIN public.partner_codes as pc on pc.id=up.partner_code_id "
            f"WHERE (LOWER(u.login_name) LIKE  '%' || LOWER(:search_word) || '%' "
            f"OR LOWER(u.email) LIKE  '%' || LOWER(:search_word) || '%'"
            f"OR LOWER(u.phone) LIKE  '%' || LOWER(:search_word) || '%') "
            f"GROUP BY u.id "
            f"ORDER BY u.id DESC "
            f"LIMIT {settings.PAGINATION_PER_PAGE}").bindparams(search_word=search_word))
        numrows = int(res.rowcount)
        clients = res.fetchall()[:settings.PAGINATION_PER_PAGE]
        basic_prices = settings.Prices.BASIC_PRICES

    else:
        numrows = 0
        clients = ''

    return jsonify({'htmlresponse': render_template('admin/user_search/su_user_search_response.html', clients=clients,
                                                    numrows=numrows,  basic_prices=basic_prices)})


def h_user_search(user_admin_id: int) -> Response:
    if current_user.role not in [settings.SUPER_USER, ] and current_user.id != user_admin_id:
        return Response('', 403)
    search_word = request.form.get('query')
    basic_prices = None
    if search_word:
        res = db.session.execute(text(
            # f"SELECT * FROM public.users "
            f"SELECT u.id as id, "
            f"u.login_name as login_name, "
            f"u.phone as phone, "
            f"u.balance as balance, "
            f"u.email as email, "
            f"u.status as status, "
            f"max(pr.price_code) as price_code, "
            f"max(pr.price_1) as price_1, "
            f"max(pr.price_2) as price_2, "
            f"max(pr.price_3) as price_3, "
            f"max(pr.price_4) as price_4, "
            f"max(pr.price_5) as price_5, "
            f"max(pr.price_6) as price_6, "
            f"max(pr.price_7) as price_7, "
            f"max(pr.price_8) as price_8, "
            f"max(pr.price_9) as price_9, "
            f"max(pr.price_10) as price_10, "
            f"max(pr.price_11) as price_11, "
            f"bool_and(pr.price_at2) as price_at2, "
            f"u.role as role, "
            f"u.client_code as client_code, "
            f"u.created_at as created_at,"
            f"MAX(pc.code) as partners_code, "
            f"COUNT(os.id) as orders_count, "
            f"sum(os.marks_count) as total_marks_count, "
            f"MAX(os.created_at) as os_created_at "
            f"FROM public.users u "
            f"LEFT JOIN public.orders_stats as os on os.user_id=u.id "
            f"LEFT JOIN public.prices pr on pr.id=u.price_id "
            f"LEFT JOIN public.users_partners as up on up.user_id=u.id "
            f"LEFT JOIN public.partner_codes as pc on pc.id=up.partner_code_id "
            f"WHERE u.admin_parent_id=:user_admin_id AND "
            f"(LOWER(u.login_name) LIKE  '%' || LOWER(:search_word) || '%' "
            f"OR LOWER(u.email) LIKE  '%' || LOWER(:search_word) || '%'"
            f"OR LOWER(u.phone) LIKE  '%' || LOWER(:search_word) || '%') "
            f"GROUP BY u.id "
            f"ORDER BY u.id DESC "
            f"LIMIT {settings.PAGINATION_PER_PAGE}").bindparams(user_admin_id=user_admin_id, search_word=search_word))
        numrows = int(res.rowcount)
        clients = res.fetchall()[:settings.PAGINATION_PER_PAGE]
        basic_prices = settings.Prices.BASIC_PRICES

    else:
        numrows = 0
        clients = ''

    return jsonify({'htmlresponse': render_template('admin/user_search/user_search_response.html', clients=clients,
                                                    numrows=numrows, admin_id=user_admin_id, basic_prices=basic_prices)})


def h_user_search_idn(user_admin_id: int) -> Response:
    if current_user.role not in [settings.SUPER_USER, ] and current_user.id != user_admin_id:
        return Response('', 403)
    search_idn = request.form.get('query', '').replace("--", "")
    basic_prices = None

    if search_idn:
        res = db.session.execute(text(
            f"SELECT DISTINCT "
            f"u.id as id, "
            f"u.login_name as login_name, "
            f"u.balance as balance, "
            f"u.phone as phone, "
            f"u.email as email, "
            f"u.status as status, "
            f"max(pr.price_code) as price_code, "
            f"max(pr.price_1) as price_1, "
            f"max(pr.price_2) as price_2, "
            f"max(pr.price_3) as price_3, "
            f"max(pr.price_4) as price_4, "
            f"max(pr.price_5) as price_5, "
            f"max(pr.price_6) as price_6, "
            f"max(pr.price_7) as price_7, "
            f"max(pr.price_8) as price_8, "
            f"max(pr.price_9) as price_9, "
            f"max(pr.price_10) as price_10, "
            f"max(pr.price_11) as price_11, "
            f"bool_and(pr.price_at2) as price_at2, "
            f"u.role as role, "
            f"u.created_at as created_at, "
            f"MAX(pc.code) as partners_code, "
            f"COUNT(os.id) as orders_count, "
            f"sum(os.marks_count) as total_marks_count, "
            f"MAX(os.created_at) as os_created_at "
            f"FROM public.users u "
            f"LEFT JOIN public.orders_stats as os on os.user_id=u.id AND os.company_idn LIKE '%' || '{search_idn}' || '%' "
            f"LEFT JOIN public.prices pr on pr.id=u.price_id "
            f"LEFT JOIN public.users_partners as up on up.user_id=u.id "
            f"LEFT JOIN public.partner_codes as pc on pc.id=up.partner_code_id "
            f"WHERE u.id in(SELECT pos.user_id FROM public.orders_stats pos "
            f"WHERE pos.company_idn LIKE '%' || :search_idn || '%') AND u.id in(SELECT au.id from public.users au where au.admin_parent_id=:user_admin_id)"
            f"GROUP BY u.id "
            f"ORDER BY u.id DESC "
            f"LIMIT {settings.PAGINATION_PER_PAGE}").bindparams(search_idn=search_idn, user_admin_id=user_admin_id))
        numrows = int(res.rowcount)
        clients = res.fetchall()
        basic_prices = settings.Prices.BASIC_PRICES
    else:

        numrows = 0
        clients = ''

    return jsonify({'htmlresponse': render_template('admin/user_search/user_search_response.html', clients=clients,
                                                    numrows=numrows, admin_id=user_admin_id, basic_prices=basic_prices)})


def h_cross_user_search() -> Response:
    search_idn = request.form.get('query')
    if search_idn and not search_idn.isdigit():
        search_idn = None
    basic_prices = None
    if search_idn:
        res = db.session.execute(text(
            f"SELECT "
            f"u.id as id, "
            f"u.login_name as login_name, "
            f"u.balance as balance, "
            f"u.email as email, "
            f"u.status as status, "
            f"u.role as role, "
            f"max(pr.price_code) as price_code, "
            f"max(pr.price_1) as price_1, "
            f"max(pr.price_2) as price_2, "
            f"max(pr.price_3) as price_3, "
            f"max(pr.price_4) as price_4, "
            f"max(pr.price_5) as price_5, "
            f"max(pr.price_6) as price_6, "
            f"max(pr.price_7) as price_7, "
            f"max(pr.price_8) as price_8, "
            f"max(pr.price_9) as price_9, "
            f"max(pr.price_10) as price_10, "
            f"max(pr.price_11) as price_11, "
            f"bool_and(pr.price_at2) as price_at2, "
            f"(SELECT a.login_name from public.users a WHERE ( a.id=u.admin_parent_id AND (a.role in('admin', 'superuser'))) OR (a.id=u.id AND (a.role in('admin', 'superuser')))) as admin, "
            f"COUNT(os.id) as orders_count, "
            f"MAX(os.created_at) as created_at "
            f"FROM public.users u "
            f"LEFT JOIN public.orders_stats as os on os.user_id=u.id AND os.company_idn LIKE '%' || '{search_idn}' || '%' "
            f"LEFT JOIN public.prices pr on pr.id=u.price_id "
            f"WHERE u.id in(SELECT pos.user_id FROM public.orders_stats pos "
            f"WHERE pos.company_idn LIKE '%' || '{search_idn}' || '%') "
            f"GROUP BY u.id "
            f"ORDER BY u.id DESC "
            f"LIMIT {settings.PAGINATION_PER_PAGE}"))
        numrows = int(res.rowcount)
        clients = res.fetchall()[:settings.PAGINATION_PER_PAGE]
        basic_prices = settings.Prices.BASIC_PRICES
    else:
        numrows = 0
        clients = ''

    return jsonify({'htmlresponse': render_template('admin/user_search/cross_user_search_response.html', clients=clients,
                                                    numrows=numrows, basic_prices=basic_prices)})


def h_users_orders_stats(admin_id=None):
    if current_user.role == settings.SUPER_USER and admin_id is None:
        return helper_get_orders_stats()
    elif current_user.role == settings.SUPER_USER and admin_id:
        return helper_get_orders_stats(admin_id=admin_id)
    else:
        if current_user.id != admin_id:
            return jsonify(dict(status='danger', message=settings.Messages.STRANGE_REQUESTS))
        else:
            return helper_get_orders_stats(admin_id=admin_id)


def h_users_orders_stats_rpt(admin_id=None):
    if current_user.role == settings.SUPER_USER and admin_id is None:
        return helper_get_orders_stats_rpt()
    elif current_user.role == settings.SUPER_USER and admin_id:
        return helper_get_orders_stats_rpt()
    else:
        if current_user.id != admin_id:
            return jsonify(dict(status='danger', message=settings.Messages.STRANGE_REQUESTS))
        else:
            return helper_get_orders_stats_rpt()


def h_client_orders_stats(admin_id: int, client_id: int) -> Response:
    if current_user.role == settings.SUPER_USER or (current_user.role == settings.ADMIN_USER and current_user.id == admin_id):
        client = (User.query.with_entities(User.id, User.login_name, User.admin_parent_id)
                  .filter(User.id == client_id).first())
        if not client or client.admin_parent_id != admin_id:
            return helper_strange_response()
        return helper_get_clients_os(admin_id=admin_id, client=client)

    return helper_strange_response()


def h_at2_new_orders() -> Response:
    admin_id = current_user.id
    pool = settings.OrderStage.POOL
    cancelled = settings.OrderStage.CANCELLED

    orders_list_raw = helper_get_new_orders_at2(admin_id=admin_id)

    bck = request.args.get('bck', 0, type=int)

    if not orders_list_raw:
        return render_template('admin/crm_specific/at2_orders.html', **locals()) if not bck \
            else jsonify(
            {'status': 'success', 'htmlresponse': render_template(f'admin/crm_specific/at2_orders_table.html',
                                                                  **locals())})
    link_filters = 'bck=1&'
    link = f'javascript:bck_get_orders(\'' + url_for(
        'admin_control.at2_new_orders') + f'?{link_filters}' + 'page={0}\');'
    page, per_page, \
        offset, pagination, \
        orders_list = helper_paginate_data(data=orders_list_raw, per_page=settings.PAGINATION_PER_PAGE, href=link,
                                          anchor="OrdersTable")
    return render_template('admin/crm_specific/at2_orders.html', **locals()) if not bck \
        else jsonify(
        {'status': 'success', 'htmlresponse': render_template(f'admin/crm_specific/at2_orders_table.html',
                                                              **locals())})


def h_at2_orders_process(o_id: int, change_stage: int) -> Response:
    admin_id = current_user.id
    status = settings.ERROR
    reload = False
    pool_stmt = ''

    if change_stage not in [settings.OrderStage.POOL, settings.OrderStage.CANCELLED]:
        message = f"{settings.Messages.AT2_ORDER_CHANGE_ERROR} - Указаны некорректные данные для изменения!"
        return jsonify(dict(status=status, message=message))

    # check for trickers
    order_check = helper_check_new_order_at2(admin_id=admin_id, o_id=o_id)
    if not order_check:
        message = f"{settings.Messages.AT2_ORDER_CHANGE_ERROR} - Нет такого заказа!"
        return jsonify(dict(status=status, message=message))

    # make check of agent balance
    if change_stage == settings.OrderStage.POOL:
        status_balance, message_balance = helper_get_at2_pending_balance(admin_id=current_user.id,
                                                                         price_id=current_user.price_id,
                                                                         balance=current_user.balance,
                                                                         trust_limit=current_user.trust_limit)
        dt_pool = datetime.now()
        pool_stmt = f", p_started='{dt_pool}'"
        if not status_balance:
            return jsonify(dict(status=status, message=message_balance))
    try:
        cancel_stmt = (", cc_created='{date}', comment_cancel='{auto_comment}'"
                       .format(date=str(datetime.now()), auto_comment=settings.Messages.AT2_ORDER_CANCEL_TEXT)) if change_stage == settings.OrderStage.CANCELLED else ""

        update_order_stmt = (text(f"""UPDATE public.orders SET stage=:change_stage{cancel_stmt}{pool_stmt} WHERE id=:o_id""")
                             .bindparams(o_id=o_id, change_stage=change_stage))

        db.session.execute(update_order_stmt)

        order_idn = order_check.order_idn

        # make refill on cancell
        if change_stage == settings.OrderStage.CANCELLED and order_check.payment:
            h_cancel_order_process_payment(order_idn=order_idn, user_id=order_check.user_id)
            reload = True
        db.session.commit()
        message = f"{settings.Messages.AT2_ORDER_CHANGE} {order_idn} {settings.OrderStage.STAGES[change_stage][1]}"
        status = settings.SUCCESS
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.AT2_ORDER_CHANGE_ERROR} {e}"
        logger.error(message)

    return jsonify(dict(status=status, message=message, reload=reload))


def h_users_activate_list():
    additional_stmt = ""
    user_stmt = f"""SELECT u.id as id,
                           u.login_name as login_name,
                           u.email as email,
                           u.phone as phone,
                           MAX(a.login_name) as agent_name,
                           u.created_at as created_at,
                           MAX(pc.code) as partner_code
                     FROM public.users u 
                     LEFT JOIN public.users a on a.id =u.admin_parent_id
                     LEFT JOIN public.users_partners up on up.user_id =u.id
                     LEFT JOIN public.partner_codes pc on pc.id = up.partner_code_id
                     WHERE u.status=False
                     GROUP BY u.id, u.created_at
                     ORDER BY u.created_at DESC
                            """

    user_full_list = db.session.execute(text(user_stmt)).fetchall()

    bck = request.args.get('bck', 0, type=int)

    if not user_full_list:
        return render_template('admin/user_activate/admin_user_activate.html', **locals()) if not bck \
            else jsonify({'status': 'success', 'htmlresponse': render_template(f'admin/user_activate/user_activate_table.html',
                          **locals())})
    link_filters = 'bck=1&'
    link = f'javascript:bck_get_users_activated(\'' + url_for(
        'admin_control.users_activate_list') + f'?{link_filters}' + 'page={0}\');'
    page, per_page, \
        offset, pagination, \
        users_list = helper_paginate_data(data=user_full_list, per_page=settings.PAGINATION_PER_PAGE, href=link, anchor="usersActivateTable")
    return render_template('admin/user_activate/admin_user_activate.html', **locals()) if not bck \
        else jsonify({'status': 'success', 'htmlresponse': render_template(f'admin/user_activate/user_activate_table.html',
                      **locals())})


def h_bck_user_delete(u_id: int) -> Response:
    user = User.query.get(u_id)
    status = 'danger'
    # check for trickers
    if not user:
        message = f"{settings.Messages.DELETE_USER_ERROR} Нет такого пользователя!"
        return jsonify(dict(status=status, message=message))
    try:
        user.telegram = []
        user.partners = []
        user.promos = []
        db.session.delete(user)
        db.session.commit()
        db.session.commit()

        message = f"{settings.Messages.DELETE_USER} {user.login_name}"
        status = 'success'
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.DELETE_USER_ERROR} {e}"
        logger.error(message)

    return jsonify(dict(status=status, message=message))


def h_bck_user_activate(u_id: int) -> Response:
    user = User.query.with_entities(User.id, User.login_name).filter(User.id == u_id).first()
    status = 'danger'
    # check for trickers
    if not user:
        message = f"{settings.Messages.ACTIVATED_USER_ERROR} Нет такого пользователя!"
        return jsonify(dict(status=status, message=message))
    try:
        client_code = request.form.get("client_code", '')[:30].strip()
        db.session.execute(
            text('UPDATE public.users SET status=True, client_code=:client_code WHERE id=:u_id').bindparams(
                    u_id=u_id, client_code=client_code))
        db.session.commit()

        message = f"{settings.Messages.ACTIVATED_USER} {user.login_name}"
        status = 'success'
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.ACTIVATED_USER_ERROR} {e}"
        logger.error(message)

    return jsonify(dict(status=status, message=message))


def helper_create_at2_admin(login_name: str, email: str, password: str, tg_id: str) -> Response:

    try:
        new_admin = User(admin_order_num=0, login_name=login_name, email=email, phone=settings.SU_PHONE,
                         is_crm=True, is_at2=True, is_send_excel=True,
                         password=generate_password_hash(password, method='sha256'),
                         role=settings.ADMIN_USER, client_code=settings.AU_CLIENT_CODE, status=True,
                         trust_limit=settings.TRUST_LIMIT_DEFAULT)

        # create new substance tm
        telegram_message = TelegramMessage(send_admin_info=True)
        new_admin.telegram_message.append(telegram_message)

        telegram = Telegram.query.get(tg_id)
        if telegram:

            telegram.status = True

            new_admin.telegram.append(telegram)

        db.session.add(new_admin)
        db.session.commit()
        flash(message=settings.Messages.ADMIN_TG_CREATE_SUCCESS)
        return redirect(url_for('admin_control.index', expanded=settings.EXP_USERS))
    except IntegrityError as e:
        db.session.rollback()
        message = f"{settings.Messages.ADMIN_CREATE_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)

        return redirect(url_for('admin_control.index'))


def h_bck_change_user_password(u_id: int) -> Response:
    status = 'danger'
    user = User.query.filter_by(id=u_id).first()
    if not user:
        message = f"{settings.Messages.NO_SUCH_USER}"
        return jsonify(dict(status=status, message=message))
    try:
        new_password = request.form.get('new_password', '').strip()
        if not new_password:
            message = f"{settings.Messages.NO_USER_PASSWORD}"
            return jsonify(dict(status=status, message=message))
        user.password = generate_password_hash(new_password, method='sha256')
        db.session.commit()
        message = f"{settings.Messages.USER_PASSWORD_CHANGE} {user.login_name}"
        status = 'success'
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.USER_PASSWORD_CHANGE_ERROR}"
        logger.error(message + str(e))

    return jsonify(dict(status=status, message=message))


def h_bck_save_call_result():
    u_id, comment, call_result = helper_get_reanimate_call_result()
    stmt = select(
        ReanimateStatus
    ).where(ReanimateStatus.user_id == u_id)
    try:
        rec = db.session.execute(stmt).scalar_one()
        rec.comment = comment
        rec.call_result = call_result
        rec.updated_at = datetime.now()
        db.session.commit()
    except NoResultFound:
        rec = ReanimateStatus(user_id=u_id, comment=comment, call_result=call_result)
        db.session.add(rec)
        db.session.commit()
    except Exception as err:
        logger.error(f'an error during save call result in reanimate interface\nError: {err}')
        return Response(status=400)
    # swap ReanimateStatus.id and ReanimateStatus.user_id for correct handling in template
    user = rec
    user.id = rec.user_id
    user.last_call_update = rec.updated_at.strftime('%d-%m-%Y %H:%M')
    reanimate_call_result = settings.REANIMATE_CALL_RESULT
    return jsonify({'htmlresponse': render_template(f'admin/ra/reanimate_comment.html', **locals())})


def h_bck_reanimate():
    """
       background update of users to reanimate(users that don't make orders for a while)
    :return:
    """

    # set manually type and status for render page case
    date_quantity, date_type, link_filters, sort_type = helper_get_filter_users()

    link = f'javascript:bck_get_users_reanimate(\'' + url_for(
        'admin_control.bck_control_reanimate') + f'?bck=1&{link_filters}' + 'page={0}\');'

    users = helper_get_users_reanimate(date_quantity=date_quantity, date_type=date_type, sort_type=sort_type)
    numrows = len(users)

    basic_prices = settings.Prices.BASIC_PRICES
    all_prices = Price.query.with_entities(Price.id, Price.price_code, Price.price_at2) \
        .order_by(desc(Price.created_at)).all()


    page, per_page, \
        offset, pagination, \
        users_list = helper_paginate_data(data=users, per_page=settings.PAGINATION_PER_PAGE, href=link)

    bck = request.args.get('bck', 0, type=int)
    basic_prices = settings.Prices.BASIC_PRICES
    date_range_types = settings.Users.FILTER_DATE_TYPES
    date_quant_max = settings.Users.FILTER_MAX_QUANTITY
    converted_date_type = settings.Users.FILTER_DATE_DICT.get(date_type)
    reanimate_call_result = settings.REANIMATE_CALL_RESULT
    return jsonify({'htmlresponse': render_template(f'admin/ra/user_reanimate_response.html', **locals())}) \
        if bck else render_template('admin/ra/main_reanimate.html', **locals())


def h_bck_su_control_reanimate_excel():
    # set manually type and status for render page case
    date_quantity, date_type, link_filters, sort_type = helper_get_filter_users(excel_report=True)

    link = f'javascript:bck_get_users_reanimate(\'' + url_for(
        'admin_control.bck_control_reanimate') + f'?bck=1&{link_filters}' + 'page={0}\');'

    users = helper_get_users_reanimate(date_quantity=date_quantity, date_type=date_type, sort_type=sort_type)

    users_processed = list(map(lambda x: (x.created_at, x.os_created_at, x.login_name, x.phone, x.email, x.partners_code), users))
    excel_filters = {
        'Временная единица': date_type,
        'Количество временных единиц': date_quantity,
    }

    excel = ExcelReport(
        data=users_processed,
        filters=excel_filters,
        columns_name=['дата регистрации', 'Дата крайнего заказа', 'Логин', 'Телефон', 'Email', 'Код партнера', ],
        sheet_name='Отчет реанимации пользователей',
        output_file_name=f'реанимация клиентов({datetime.today().strftime("%d.%m.%y %H-%M")})',
    )

    excel_io = excel.create_report()
    content = excel_io.getvalue()
    response = make_response(content)
    response.headers['data_file_name'] = parse.quote(excel.output_file_name)
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['data_status'] = 'success'

    return response


def h_bck_agent_reanimate(u_id: int):
    """
       background update of agent users transactions  write_off for agent commission counter
    :return:
    """
    bck = request.args.get('bck', 0, type=int)
    # check if current user is not a superuser and try to pass another u_id or
    # send request with bck equal 1
    if current_user.role != 'superuser' and current_user.id != u_id and not bck:
        flash(message=settings.Messages.STRANGE_REQUESTS, category='error')
        return redirect(url_for('admin_control.admin', u_id=current_user.id))

    elif current_user.role != 'superuser' and current_user.id != u_id and bck:
        return jsonify({'message': 'something went wrong'})

    if current_user.role == 'superuser' and u_id:
        agent = User.query.with_entities(User.login_name).filter(User.id == u_id).first()

    # set manually type and status for render page case
    date_quantity, date_type, link_filters, sort_type = helper_get_filter_users()

    link = f'javascript:bck_get_users_reanimate(\'' + url_for(
        'admin_control.bck_agent_control_reanimate', u_id=u_id) + f'?bck=1&{link_filters}' + 'page={0}\');'

    users = helper_get_users_reanimate(date_quantity=date_quantity, date_type=date_type, sort_type=sort_type, u_id=u_id)
    numrows = len(users)

    basic_prices = settings.Prices.BASIC_PRICES
    all_prices = Price.query.with_entities(Price.id, Price.price_code, Price.price_at2) \
        .order_by(desc(Price.created_at)).all()


    page, per_page, \
        offset, pagination, \
        users_list = helper_paginate_data(data=users, per_page=settings.PAGINATION_PER_PAGE, href=link)


    date_range_types = settings.Users.FILTER_DATE_TYPES
    date_quant_max = settings.Users.FILTER_MAX_QUANTITY
    converted_date_type = settings.Users.FILTER_DATE_DICT.get(date_type)
    reanimate_call_result = settings.REANIMATE_CALL_RESULT
    return jsonify({'htmlresponse': render_template(f'admin/ra/agent/user_reanimate_response.html', **locals())}) \
        if bck else render_template('admin/ra/agent/main_reanimate.html', **locals())


def helper_get_ar_orders_stat(ar_schema: AROrdersSchema, u_id: int) -> tuple:
    """
    Returns a tuple of orders quantity and marks quantity.

    :param ar_schema: AROrdersSchema instance containing the necessary parameters.
    :return: A tuple containing the orders count and marks count.
    """
    category_type_condition_stmt = "AND coalesce(sh.type, cl.type, l.type, p.type) = '{category_pos_type}' ".format(category_pos_type=ar_schema.category_pos_type) if ar_schema.category_pos_type != settings.ALL_CATEGORY_TYPES else ''
    category_pos_type_stmt = "max(coalesce(sh.type, cl.type, l.type, p.type))" if ar_schema.category_pos_type != settings.ALL_CATEGORY_TYPES else "\'Все типы\'"

    stmt = text(f"""
        SELECT max(o.category) as category,
               {category_pos_type_stmt} as category_pos_type, 
               COUNT(DISTINCT o.id) as orders_count,
               COUNT(coalesce(sh.id, cl.id, sk.id, l.id, p.id)) as pos_count, 
               SUM(coalesce(sh.box_quantity * sh_qs.quantity, cl.box_quantity * cl_qs.quantity, sk.box_quantity * sk_qs.quantity, l.box_quantity * l_qs.quantity, p.quantity)) as marks_count
        FROM public.orders o
        LEFT JOIN public.shoes sh ON o.id = sh.order_id
        LEFT JOIN public.shoes_quantity_sizes sh_qs ON sh.id = sh_qs.shoe_id 
        LEFT JOIN public.clothes cl ON o.id = cl.order_id
        LEFT JOIN public.cl_quantity_sizes cl_qs ON cl.id = cl_qs.cl_id
        LEFT JOIN public.socks sk ON o.id = sk.order_id
        LEFT JOIN public.socks_quantity_sizes sk_qs ON sk.id = sk_qs.socks_id
        LEFT JOIN public.linen l ON o.id = l.order_id
        LEFT JOIN public.linen_quantity_sizes l_qs ON l.id = l_qs.lin_id
        LEFT JOIN public.parfum p ON o.id = p.order_id 
        WHERE o.category=:category AND o.payment=True
        AND o.user_id in (SELECT u.id from public.users u where u.admin_parent_id=:u_id OR u.id=:u_id)
        {category_type_condition_stmt}
        AND o.sent_at >= :date_from
        AND o.sent_at <= :date_to
    """).bindparams(category=ar_schema.category,
                    date_from=ar_schema.date_from,
                    date_to=ar_schema.date_to + timedelta(days=1), u_id=u_id)

    return db.session.execute(stmt).fetchone()


def h_bck_ar_orders(u_id: int):
    bck = request.args.get('bck', 0, type=int)
    status = 0
    message = ''
    ac_types = ar_categories_types

    try:
        if current_user.role not in [settings.SUPER_USER, settings.MARKINERIS_ADMIN_USER] and current_user.id != u_id:
            return '', 400

        if not bck:
            admin = User.query.with_entities(User.login_name).filter(User.id == u_id).first()
        date_from_str = request.args.get('date_from', '', type=str)
        date_to_str = request.args.get('date_to', '', type=str)
        date_from = datetime.strptime(date_from_str, '%d.%m.%Y') \
            if date_from_str else datetime.now() - timedelta(days=settings.AR_ORDERS_DAYS_DEFAULT)
        date_to = datetime.strptime(date_to_str, '%d.%m.%Y') if date_to_str else datetime.now()

        data = {
            'date_from': date_from,
            'date_to': date_to,
            'category': request.args.get('category', settings.Clothes.CATEGORY),
            'category_pos_type': request.args.get('category_pos_type', settings.ALL_CATEGORY_TYPES)
        }
        ar_schema = AROrdersSchema(**data)
        res_data = helper_get_ar_orders_stat(ar_schema=ar_schema, u_id=u_id)
        status = 1
    except ValueError as ve:
        message = 'Некорректные данные в форме фильтр'
        logger.error(str(ve))
    except Exception as e:
        message = 'Возникло исключение'
        logger.error(str(e))

    return jsonify({'htmlresponse': render_template(f'admin/ar_orders/ar_info.html', **locals()),
                    'status': status, 'message': message}) \
        if bck else render_template('admin/ar_orders/ar_main.html', **locals())



def helper_create_crm_admin(login_name: str, email: str, password: str) -> Response:
    try:
        new_admin = User(admin_order_num=0, login_name=login_name, email=email, phone=settings.SU_PHONE, is_crm=True,
                         is_at2=False, password=generate_password_hash(password, method='sha256'),
                         role=settings.ADMIN_USER, client_code=settings.AU_CLIENT_CODE, status=True)

        db.session.add(new_admin)
        db.session.commit()
        flash(message=settings.Messages.ADMIN_CRM_CREATE_SUCCESS)
        return redirect(url_for('admin_control.index', expanded=settings.EXP_USERS))
    except IntegrityError as e:
        db.session.rollback()
        message = f"{settings.Messages.ADMIN_CREATE_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)

        return redirect(url_for('admin_control.index'))


def helper_delete_tg(user: User) -> None:

    telegram = user.telegram

    if telegram:
        telegram_ids = [tg.id for tg in telegram]

        # trying to avoid strange error
        telegram_ids_str = ','.join(map(str, telegram_ids))

        # Hard deleting from users_telegrams
        query = f"""
            DELETE FROM users_telegrams WHERE telegram_id IN ({telegram_ids_str})
        """
        db.session.execute(text(query))
        for tg in telegram:
            tg.status = False
            tg.users = []

    tm = user.telegram_message
    if tm:
        for message in tm:
            db.session.delete(message)


def util_get_agent_passwords():
    from data_migrations.utils import make_password
    from models import User
    emails = User.query.filter(User.role == 'admin', User.email.startswith('Agent')).with_entities(User.email, User.password).order_by(User.email).all()
    salt = settings.SALT.get_secret_value()
    for e in emails:
        print(f"{e.email}: {make_password(email=e.email, salt=salt)}")

