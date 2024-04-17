from datetime import datetime

from flask import flash, render_template, redirect, send_file, url_for, request, Response, jsonify
from flask_login import current_user
from sqlalchemy import asc, desc, func, text

from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from config import settings
from logger import logger
from models import db, Order, OrderStat, PartnerCode, RestoreLink, Telegram, TelegramMessage, User, users_partners, \
    Price, TgUser
from utilities.download import orders_process_send_order
from utilities.support import url_encrypt, helper_check_form, helper_update_order_note, \
      helper_paginate_data, helper_strange_response, sql_count
from utilities.admin.helpers import process_admin_report, helper_get_clients_os, helper_get_orders_stats


def h_index(expanded: str = None):
    # def sum_lists(*args):
    #     return list(map(sum, zip(*args)))

    if current_user.role != settings.SUPER_USER:
        return redirect(url_for('admin_control.admin', u_id=current_user.id))

    if expanded in [None, settings.EXP_USERS, settings.EXP_PARTNERS, settings.EXP_TELEGRAM]:
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
                                 pq.price_3 as price_3, pq.price_4 as price_4, pq.price_5 as price_5,
                                 pq.price_at2 as price_at2, tq.channel_id as tg_channel_id, tq.name as tg_name,
                                 tq.comment as tg_comment,
                                 count(u.id) as reg_clients,
                                 (select array[count(os.id), sum(os.rows_count), sum(os.marks_count)] from public.orders_stats os where os.user_id in (select uu.id from public.users uu where uu.admin_parent_id=au.id or uu.id=au.id) limit 1) as data_orders_array
                             FROM public.users au
                             LEFT JOIN public.users_telegrams ut on ut.user_id = au.id
                             LEFT JOIN public.telegram tq on ut.telegram_id = tq.id
                             LEFT JOIN public.prices pq on au.price_id = pq.id
                             LEFT JOIN public.users u on u.admin_parent_id = au.id
                             WHERE au.role in('{settings.ADMIN_USER}', '{settings.SUPER_USER}')
                             group by au.id, pq.price_code, pq.price_1, pq.price_2,pq.price_3, pq.price_4, pq.price_5, pq.price_at2, tg_channel_id, tg_name, tg_comment
                             order by au.id""")
        su_list = db.session.execute(users_stmt).fetchall()

        # previous way to get users with n+1 request and n2

        # prices_query = db.session.query(Price.id.label("price_id"), Price.price_code, Price.price_1, Price.price_2, Price.price_3,
        #                                 Price.price_4, Price.price_5, Price.price_at2) \
        #     .filter(User.price_id == Price.id) \
        #     .subquery()
        #
        # telegram_query = db.session.query(users_telegrams.c.user_id, Telegram.channel_id.label("tg_channel_id"),
        #                                   Telegram.name.label("tg_name"),
        #                                   Telegram.comment.label("tg_comment"))\
        #     .join(Telegram, Telegram.id == users_telegrams.c.telegram_id)\
        #     .subquery()
        #
        # super_user_admin_list = User.query.filter(User.role.in_([settings.ADMIN_USER, settings.SUPER_USER]))  \
        #                             .outerjoin(prices_query, User.price_id == prices_query.c.price_id) \
        #                             .outerjoin(telegram_query, User.id == telegram_query.c.user_id) \
        #     .with_entities(User.id, User.role, User.balance, User.login_name, User.email, User.client_code,
        #                    User.agent_fee, User.trust_limit, User.is_crm,
        #                    User.is_at2, User.status, User.phone,
        #                    User.created_at, prices_query.c.price_code, prices_query.c.price_1, prices_query.c.price_2,
        #                    prices_query.c.price_3, prices_query.c.price_4, prices_query.c.price_5,
        #                    prices_query.c.price_at2, telegram_query.c.tg_channel_id, telegram_query.c.tg_name,
        #                    telegram_query.c.tg_comment) \
        #     .group_by(User.id, prices_query.c.price_code, prices_query.c.price_1,
        #               prices_query.c.price_2, prices_query.c.price_3,
        #               prices_query.c.price_4, prices_query.c.price_5, prices_query.c.price_at2,
        #               telegram_query.c.tg_channel_id, telegram_query.c.tg_name, telegram_query.c.tg_comment) \
        #     .order_by(User.id).all()
        #
        # su_list = [u._asdict() for u in super_user_admin_list]
        #
        # orders_rows_marks = [o for o in OrderStat.query.with_entities(OrderStat.user_id, func.count(OrderStat.id),
        #                                                   func.sum(OrderStat.rows_count).label("rows_count"),
        #                                                   func.sum(OrderStat.marks_count).label("marks_count"), ).group_by(OrderStat.user_id).all()]
        # for u in su_list:
        #     agent_id = u.get('id')
        #     admin_users_ids = tuple((u[0] for u in User.query.with_entities(User.id)
        #                             .filter_by(admin_parent_id=agent_id).all())) + (agent_id,)
        #
        #     users_info_list = list(filter(lambda x: x.user_id in admin_users_ids, orders_rows_marks))
        #     u_orders_rows_marks = sum_lists(*users_info_list)
        #
        #     u["orders_count"] = u_orders_rows_marks[1] if u_orders_rows_marks else []
        #     u["rows_count"] = u_orders_rows_marks[2] if u_orders_rows_marks else []
        #     u["marks_count"] = u_orders_rows_marks[3] if u_orders_rows_marks else []
        #     u["count_order_rows_marks"] = u_orders_rows_marks[1:] if u_orders_rows_marks else []
        #     u["reg_clients"] = len(admin_users_ids) - 1

        ou_quantity = User.query.filter(User.role == settings.ORD_USER) \
            .order_by(User.id).count()

        telegram_list = Telegram.query.all()
        if current_user.role == settings.SUPER_USER:
            tg_group_list = Telegram.query.filter_by(status=False).all()

        markineris_url_coi = settings.MARKINERIS_CHECK_CROSS_OI_LINK
        markineris_secret = settings.MARKINERIS_SECRET

        basic_prices = settings.Prices.BASIC_PRICES
        all_prices = Price.query.with_entities(Price.id, Price.price_code, Price.price_at2).order_by(desc(Price.created_at)).all()
        return render_template('admin/admin_control.html', **locals())
    else:
        flash(message="Что-то странное ощущаю я. Это что, хитрый парсер ссылок?", category='error')
        return redirect(url_for('admin_control.index'))


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
        prices_query = db.session.query(Price.id.label("price_id"), Price.price_code, Price.price_1, Price.price_2, Price.price_3,
                                        Price.price_4, Price.price_5) \
            .filter(User.price_id == Price.id, Price.price_at2.isnot(True)) \
            .subquery()

        sort_arg = request.args.get("sort_type")
        order_type = desc(User.created_at) if sort_arg != 'orders' else asc(os_query.c.os_created_at)

        users_pagination = User.query\
            .outerjoin(os_query, User.id == os_query.c.user_id)\
            .outerjoin(partner_query, User.id == partner_query.c.user_id) \
            .outerjoin(prices_query, User.price_id == prices_query.c.price_id) \
            .with_entities(User.id, User.role, User.balance, User.login_name, User.email, User.client_code,
                           User.status, User.phone,
                           User.created_at, partner_query.c.code, os_query.c.orders_count, os_query.c.total_rows_count,
                           os_query.c.total_marks_count, os_query.c.os_created_at,
                           prices_query.c.price_code, prices_query.c.price_1, prices_query.c.price_2,
                           prices_query.c.price_3, prices_query.c.price_4, prices_query.c.price_5)\
            .filter(User.admin_parent_id == u_id).group_by(User.id, os_query.c.orders_count, os_query.c.total_rows_count,
                                                           os_query.c.total_marks_count, os_query.c.os_created_at,
                                                           partner_query.c.user_id, partner_query.c.code,
                                                           prices_query.c.price_code, prices_query.c.price_1,
                                                           prices_query.c.price_2, prices_query.c.price_3,
                                                           prices_query.c.price_4, prices_query.c.price_5)\
            .order_by(order_type).paginate(page=page, per_page=settings.PAGINATION_PER_PAGE)

        basic_prices = settings.Prices.BASIC_PRICES
        all_prices = Price.query.with_entities(Price.id, Price.price_code, Price.price_at2).filter(Price.price_at2.isnot(True)) \
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

        if admin_info.telegram_message:
            telegram_message = admin_info.telegram_message[0]

        return render_template('admin/admin_user_control.html', **locals())
    else:
        flash(message=settings.Messages.USER_NOT_EXIST, category='error')
        return redirect(url_for('main.enter'))


def h_set_order_notification(u_id: int):
    form_dict = request.form.to_dict()
    order_note = form_dict.get("order_note")
    if not helper_check_form(on=order_note) or not helper_update_order_note(on=order_note, u_id=u_id):
        flash(message=settings.Messages.FORM_CONTENT_ERROR, category='error')
    else:
        flash(message=settings.Messages.ORDER_NOTE_UPDATE_SUCCESS)
    return redirect(url_for('admin_control.admin', u_id=u_id))


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


def h_partner_code(u_id: int, auto: int = None):
    user = User.query.get(u_id)
    required_email = True  # if form_dict.get("required_email") else False
    required_phone = True  # if set_dict.get("required_phone") else False

    if auto == 1:
        name = user.login_name + '_' + str(len(user.partners)+1)
        code = name
        phone = settings.SU_PHONE
    elif auto is None:
        set_dict = request.form.to_dict()
        name = set_dict.get("name")
        code = set_dict.get("code")
        phone = set_dict.get("phone")

        if '__' in code:
            flash(message=f"{settings.Messages.PARTNER_CODE_ERROR} В партнер код нельзя ставить подряд __. "
                          f"Попробуйте придумать другой код", category='error')
            return redirect(url_for('admin_control.admin', u_id=u_id))
    else:
        flash(message=f"{settings.Messages.PARTNER_CODE_ERROR} В партнер код нельзя ставить подряд __. "
                      f"Попробуйте придумать другой код", category='error')
        return redirect(url_for('admin_control.admin', u_id=u_id))

    partner_code = PartnerCode(name=name, code=code, phone=phone,
                               required_phone=required_phone, required_email=required_email
                               )
    try:
        user.partners.append(partner_code)
        db.session.add(user)
        db.session.commit()
        flash(message=f"{settings.Messages.PARTNER_CODE_CREATE} {name} ")
    except IntegrityError as e:
        db.session.rollback()
        message = f"{settings.Messages.PARTNER_CODE_DUPLICATE_ERROR} {code}" if "psycopg2.errors.UniqueViolation)" \
                                                                                in str(e) \
            else f"{settings.Messages.PARTNER_CODE_ERROR} {e}"
        logger.error(message)
        flash(message=message, category='error')

    return redirect(url_for('admin_control.admin', u_id=u_id))


def h_delete_partner_code(u_id: int, p_id: int) -> Response:
    partner_code = PartnerCode.query.filter_by(id=p_id).first()
    if not partner_code:
        flash(message=f"{settings.Messages.STRANGE_REQUESTS}")
        return redirect(url_for('admin_control.index'))
    try:
        db.session.delete(partner_code)
        db.session.commit()
        flash(message=settings.Messages.PARTNER_CODE_DELETE_SUCCESS.format(partner_code=partner_code.code), category='success')
    except Exception as e:
        flash(message=settings.Messages.PARTNER_CODE_DELETE_ERROR, category='error')
        logger.error(f"{settings.Messages.PARTNER_CODE_DELETE_ERROR}: {e}")
        db.session.rollback()
    return redirect(url_for('admin_control.admin', u_id=u_id))


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
        telegram_message.send_admin_info = True if send_admin_info else False
        telegram_message.send_organization_name = True if send_organization_name else False
        telegram_message.send_organization_idn = True if send_organization_idn else False
        telegram_message.send_login_name = True if send_login_name else False
        telegram_message.send_email = True if send_email else False
        telegram_message.send_phone = True if send_phone else False
        telegram_message.send_client_code = True if send_client_code else False
        db.session.commit()
        flash(message=settings.Messages.TELEGRAM_MPSET_SUCCESS)
    except IntegrityError as e:
        db.session.rollback()
        message = f"{settings.Messages.TELEGRAM_MPSET_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)

        return redirect(url_for('admin_control.index'))

    return redirect(url_for('admin_control.admin', u_id=u_id))


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
        flash(message=f"{settings.Messages.TELEGRAM_DELETE_ERROR}", category='error')
        return redirect(url_for('admin_control.index'))
    if telegram.users:
        user = telegram.users[0]
        user.is_at2 = False
    telegram.users = []

    db.session.delete(telegram)
    db.session.commit()
    return redirect(url_for('admin_control.index', expanded=settings.EXP_TELEGRAM))


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
    if current_user.role != settings.SUPER_USER and current_user.id != au_id:
        flash(message=f"{settings.Messages.DELETE_USER_ERROR} {settings.Messages.DELETE_USER_ND_ERROR}",
              category='error')
        return redirect(url_for('admin_control.admin', u_id=current_user.id))
    try:
        users = User.query.filter_by(admin_parent_id=au_id, status=False).all()
        if users:
            for u in users:
                u.status = True
            db.session.commit()
        flash(message=settings.Messages.ACTIVATE_ALL_USERS_SUCCESS)
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.ACTIVATE_ALL_USERS_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)

    return redirect(url_for('admin_control.admin', u_id=au_id))


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
                         price_1: int, price_2: int, price_3: int, price_4: int, price_5: int, csrf: str, price_at2: bool = False) -> str:
        text_badge = "bg-secondary" if price_at2 else "bg-warning text-black"
        return f'<span class="badge {text_badge}" style="cursor:pointer" ' \
               f'onclick = "perform_modal_prices(\'{user_id}\', \'{login_name}\', \'{price_code}\',' \
               f' \'{price_1}\', \'{price_2}\', \'{price_3}\',' \
               f' \'{price_4}\', \'{price_5}\', ' \
               f'\'{url_for("admin_control.bck_set_user_price", u_id=u_id)}?bck=1\', \'{csrf}\')">' \
               f'{price_code}</span>'

    status = 'danger'
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
                                          price_4=basic_prices[4], price_5=basic_prices[5], csrf=csrf)

            status = 'success'
            message = settings.Messages.USER_PRICE_PLUG
            db.session.execute(text(f"""UPDATE public.users SET price_id=NULL WHERE id={u_id};"""))
            db.session.commit()
            return jsonify(dict(status=status, message=message, user_block=user_block))

        # option receiving price from db
        price = Price.query.with_entities(Price.id, Price.price_code, Price.price_1, Price.price_2,
                                          Price.price_3, Price.price_4, Price.price_5, Price.price_at2) \
                           .filter(Price.id == p_id).first()

        if not price:
            message = f"{settings.Messages.USER_PRICE_TYPE_ERROR} нет такой цены!"
            raise ValueError

        user_block = _make_user_block(user_id=u_id, login_name=user.login_name, price_code=price.price_code,
                                      price_1=price.price_1, price_2=price.price_2, price_3=price.price_3,
                                      price_4=price.price_4, price_5=price.price_5, csrf=csrf, price_at2=price.price_at2)
        db.session.execute(text(f"""UPDATE public.users SET price_id={p_id} WHERE id={u_id};"""))
        db.session.commit()
        status = 'success'
        message = settings.Messages.USER_PRICE_PLUG

    except ValueError:
        status = 'danger'
        logger.error(message)
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

                flash(message=f"{settings.Messages.USER_PROCESS_TYPE} {user.login_name}")
            case _:  # not sure about this!  may be here should be logic for crm process

                user.is_crm = True
                user.is_at2 = False
                user.trust_limit = 0

                flash(message=f"{settings.Messages.USER_PROCESS_TYPE_ERROR}")
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.USER_PROCESS_TYPE_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)

    return redirect(url_for('admin_control.index', expanded=settings.EXP_USERS))


def h_delete_user_admin(u_id: int) -> Response:
    user = User.query.filter_by(id=u_id).first()

    try:
        partner_codes = user.partners
        for p in partner_codes:
            db.session.delete(p)
        user.partners = []
        user.promos = []

        helper_delete_tg(user=user)

        db.session.delete(user)
        db.session.commit()
        flash(message=f"{settings.Messages.DELETE_USER} {user.login_name}")
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
    order = Order.query.with_entities(Order.id, Order.category, Order.user_id).filter(Order.order_idn == order_idn_form).first()
    if not order:
        flash(message=settings.Messages.NO_SUCH_ORDER)
        return redirect(url_for('admin_control.index'))
    else:
        user = User.query.filter(User.id == order.user_id).first()

        if orders_process_send_order(
            o_id=order.id,
            user=user,
            order_comment='',
            su_exec_order_name=order_idn_form,
            clothes_divider_flag=True if order.category == settings.Clothes.CATEGORY else False,
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


def h_user_search(user_admin_id: int) -> Response:
    if current_user.role not in [settings.SUPER_USER, ] and current_user.id != user_admin_id:
        return Response('', 403)
    search_word = request.form.get('query')

    if search_word:
        res = db.session.execute(text(
            # f"SELECT * FROM public.users "
            f"SELECT u.id as id, "
            f"u.login_name as login_name, "
            f"u.phone as phone, "
            f"u.balance as balance, "
            f"u.email as email, "
            f"u.status as status, "
            f"u.role as role, "
            f"u.client_code as client_code, "
            f"u.created_at as created_at,"
            f"MAX(pc.code) as partners_code, "
            f"COUNT(os.id) as orders_count, "
            f"sum(os.marks_count) as total_marks_count, "
            f"MAX(os.created_at) as os_created_at "
            f"FROM public.users u "
            f"LEFT JOIN public.orders_stats as os on os.user_id=u.id "
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
    else:
        numrows = 0
        clients = ''

    return jsonify({'htmlresponse': render_template('helpers/user_search_response.html', clients=clients,
                                                    numrows=numrows, admin_id=user_admin_id)})


def h_user_search_idn(user_admin_id: int) -> Response:
    if current_user.role not in [settings.SUPER_USER, ] and current_user.id != user_admin_id:
        return Response('', 403)
    search_idn = request.form.get('query', '').replace("--", "")

    if search_idn:
        res = db.session.execute(text(
            f"SELECT DISTINCT "
            f"u.id as id, "
            f"u.login_name as login_name, "
            f"u.balance as balance, "
            f"u.phone as phone, "
            f"u.email as email, "
            f"u.status as status, "
            f"u.role as role, "
            f"u.created_at as created_at, "
            f"MAX(pc.code) as partners_code, "
            f"COUNT(os.id) as orders_count, "
            f"sum(os.marks_count) as total_marks_count, "
            f"MAX(os.created_at) as os_created_at "
            f"FROM public.users u "
            f"LEFT JOIN public.orders_stats as os on os.user_id=u.id AND os.company_idn LIKE '%' || '{search_idn}' || '%' "
            f"LEFT JOIN public.users_partners as up on up.user_id=u.id "
            f"LEFT JOIN public.partner_codes as pc on pc.id=up.partner_code_id "
            f"WHERE u.id in(SELECT pos.user_id FROM public.orders_stats pos "
            f"WHERE pos.company_idn LIKE '%' || :search_idn || '%') AND u.id in(SELECT au.id from public.users au where au.admin_parent_id=:user_admin_id)"
            f"GROUP BY u.id "
            f"ORDER BY u.id DESC "
            f"LIMIT {settings.PAGINATION_PER_PAGE}").bindparams(search_idn=search_idn, user_admin_id=user_admin_id))
        numrows = int(res.rowcount)
        clients = res.fetchall()
    else:
        numrows = 0
        clients = ''

    return jsonify({'htmlresponse': render_template('helpers/user_search_response.html', clients=clients,
                                                    numrows=numrows, admin_id=user_admin_id)})


def h_cross_user_search() -> Response:
    search_idn = request.form.get('query')
    if search_idn and not search_idn.isdigit():
        search_idn = None

    if search_idn:
        res = db.session.execute(text(
            f"SELECT "
            f"u.id as id, "
            f"u.login_name as login_name, "
            f"u.email as email, "
            f"u.status as status, "
            f"u.role as role, "
            f"(SELECT a.login_name from public.users a WHERE ( a.id=u.admin_parent_id AND (a.role in('admin', 'superuser'))) OR (a.id=u.id AND (a.role in('admin', 'superuser')))) as admin, "
            f"COUNT(os.id) as orders_count, "
            f"MAX(os.created_at) as created_at "
            f"FROM public.users u "
            f"LEFT JOIN public.orders_stats as os on os.user_id=u.id AND os.company_idn LIKE '%' || '{search_idn}' || '%' "
            f"WHERE u.id in(SELECT pos.user_id FROM public.orders_stats pos "
            f"WHERE pos.company_idn LIKE '%' || '{search_idn}' || '%') "
            f"GROUP BY u.id "
            f"ORDER BY u.id DESC "
            f"LIMIT {settings.PAGINATION_PER_PAGE}"))
        numrows = int(res.rowcount)
        clients = res.fetchall()[:settings.PAGINATION_PER_PAGE]
    else:
        numrows = 0
        clients = ''

    return jsonify({'htmlresponse': render_template('helpers/cross_user_search_response.html', clients=clients,
                                                    numrows=numrows)})


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


def h_client_orders_stats(admin_id: int, client_id: int) -> Response:
    if current_user.role == settings.SUPER_USER or (current_user.role == settings.ADMIN_USER and current_user.id == admin_id):
        client = (User.query.with_entities(User.id, User.login_name, User.admin_parent_id)
                  .filter(User.id == client_id).first())
        if not client or client.admin_parent_id != admin_id:
            return helper_strange_response()
        return helper_get_clients_os(admin_id=admin_id, client=client)

    return helper_strange_response()


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
                     GROUP BY u.id
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
    tm = user.telegram_message
    if telegram:
        telegram[0].status = False
        telegram[0].users = []
    if tm:
        db.session.delete(tm[0])


def util_get_agent_passwords():
    from data_migrations.utils import make_password
    from models import User
    emails = User.query.filter(User.role == 'admin', User.email.startswith('Agent')).with_entities(User.email, User.password).order_by(User.email).all()
    salt = settings.SALT.get_secret_value()
    for e in emails:
        print(f"{e.email}: {make_password(email=e.email, salt=salt)}")

