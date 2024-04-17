from datetime import datetime
from typing import Union
from uuid import uuid4

from flask import flash, jsonify, render_template, redirect, url_for, request, Response
from flask_login import current_user
from sqlalchemy import text, desc
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash

from config import settings
from logger import logger
from models import db, Order, User, RestoreLink, Price, ServiceAccount, UserTransaction, TgUser
from utilities.mailer import MailSender
from utilities.support import url_encrypt, url_decrypt, check_email, check_user_messages, \
    helper_get_order_notification, helper_get_current_sa, \
    helper_check_promo, check_file_extension, get_file_extension, \
    helper_paginate_data, helper_get_transactions, helper_refill_transaction, \
    helper_agent_wo_transaction, helper_get_image_html, helper_get_transaction_orders_detail, helper_get_user_at2
from utilities.saving_uts import get_rows_marks
from utilities.google_settings.google_tables import GoogleProcess
from utilities.google_settings.schema import PromoRow
from utilities.telegram import WriteOffBalance, RefillBalance


def h_user_control_panel(u_id: int) -> Union[Response, str]:

    user_info = User.query.with_entities(User.id, User.admin_parent_id).filter_by(id=u_id).first()
    if u_id != current_user.id or not user_info:
        flash(message=f"{settings.Messages.CHANGE_PASSWORD_ERROR} Вы не можете корректировать чужую учетную запись!",
              category='error')
        return redirect(url_for('user_cp.user_control_panel', u_id=current_user.id))

    admin_id = user_info.admin_parent_id
    order_notification, admin_name, crm = helper_get_order_notification(admin_id=admin_id if admin_id else user_info.id)
    return render_template('user_control/user_control_panel.html', **locals())


def h_change_user_password(u_id: int) -> Response:
    user_info = User.query.with_entities(User.id, User.password, User.login_name).filter_by(id=u_id).first()
    if u_id != current_user.id or not user_info:
        flash(message=f"{settings.Messages.CHANGE_PASSWORD_ERROR} Вы не можете корректировать чужой пароль!",
              category='error')
        return redirect(url_for('user_cp.user_control_panel', u_id=current_user.id))

    form_dict = request.form.to_dict()
    previous_password = form_dict.get('previous_password')

    new_password = generate_password_hash(form_dict.get('new_password'), method='sha256')

    if not check_password_hash(user_info.password, previous_password):
        flash(message=f"{settings.Messages.CHANGE_PASSWORD_ERROR} Введенный старый пароль {previous_password} не"
                      f" корректен!", category='error')
    else:
        try:
            stmt = f"""
                    UPDATE public.users SET password='{new_password}' WHERE id={u_id}; 
                    """
            db.session.execute(text(stmt))
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            message = f"{settings.Messages.CHANGE_PASSWORD_ERROR}{e}"
            flash(message=message, category='error')
            logger.error(message)

            return redirect(url_for('user_cp.user_control_panel', u_id=u_id))

        flash(
            message=f"Пользователь {user_info.login_name} {settings.Messages.CHANGE_PASSWORD_SUCCESS}"
        )
    return redirect(url_for('user_cp.user_control_panel', u_id=u_id))


def h_get_restore_link() -> Response:
    if current_user.is_authenticated and current_user.role in [settings.ADMIN_USER, settings.SUPER_USER]:
        flash(message=f"{settings.Messages.GET_RESTORE_LINK_ADMINS_ERROR}", category='error')
        return redirect(url_for('user_cp.user_control_panel', u_id=current_user.id))
    if current_user.is_authenticated and current_user.role == settings.ORD_USER:
        flash(message=f"{settings.Messages.GET_RESTORE_LINK_USERS_ERROR}", category='error')
        return redirect(url_for('user_cp.user_control_panel', u_id=current_user.id))

    user_email = request.form.get("user_email")
    if not check_email(email=user_email):
        flash(message=settings.Messages.GET_RESTORE_LINK_EMAIL_DUPLICATE_ERROR, category='error')
        return redirect(url_for('auth.login'))

    user_info = User.query.filter_by(email=user_email).first()
    if not user_info:
        flash(message=f"{settings.Messages.GET_RESTORE_LINK_EMAIL_ERROR}", category='error')
        return redirect(url_for('auth.login'))
    if user_info and user_info.role in [settings.ADMIN_USER, settings.SUPER_USER]:
        flash(message=f"{settings.Messages.GET_RESTORE_LINK_ADMINS_ERROR}", category='error')
        return redirect(url_for('auth.login'))

    else:
        time_now = datetime.now().strftime("%Y_%m_%d %H_%M_%S")
        active_link = user_info.restore_link.filter_by(status=True).first()
        if active_link:
            new_link = f"{active_link.link}"
        else:
            new_link = url_for(
                'user_cp.create_new_password',
                r_link=url_encrypt(f"{user_info.id}__{time_now}")
            )

        try:
            message = f"<h4>{settings.Mail.RESTORE_LINK_TEXT}</h4>" \
                      f"<h4><a href=\"{request.host}{new_link}\">ссылке!</a></h4>"
            if not check_user_messages(user_info=user_info, message=message):
                return redirect(url_for('auth.login'))

            ms = MailSender(user_login_name=user_info.login_name, email=user_info.email,
                            subject=settings.Mail.RESTORE_LINK_SUBJECT, message=message)
            ms.send_email()
            if not active_link:
                restore_link = RestoreLink(link=new_link)
                user_info.restore_link.append(restore_link)
                db.session.add(user_info)
                db.session.commit()

        except IntegrityError as e:
            db.session.rollback()
            message = f"{settings.Messages.GET_RESTORE_LINK_COMMON_ERROR}{e}"
            flash(message=message, category='error')
            logger.error(message)

            return redirect(url_for('auth.login'))

        flash(message=f"На ваш email {user_email} {settings.Messages.GET_RESTORE_LINK_SUCCESS}")
        return redirect(url_for('auth.login'))


def h_user_personal_account(u_id: int, stage: int = None) -> Union[Response, str]:
    user_info = User.query.with_entities(User.id, User.role, User.admin_parent_id, User.price_id, User.balance, User.pending_balance_rf).filter_by(id=u_id).first()
    if u_id != current_user.id or not user_info:
        flash(message=f"{settings.Messages.USER_CP_ERROR} Вы не можете корректировать чужой пароль!",
              category='error')
        return redirect(url_for('user_cp.user_control_panel', u_id=current_user.id))

    agent_info = User.query.filter(User.id == current_user.admin_parent_id) \
        .with_entities(User.is_at2, User.login_name).first()

    basic_prices = settings.Prices.BASIC_PRICES
    user_prices = Price.query.filter_by(id=user_info.price_id).first()

    # current service account
    cur_sa = helper_get_current_sa()

    return render_template('user_control/personal_account.html', **locals())


def h_update_transactions_history(u_id: int):
    # background update of transactions
    if current_user.id != u_id:
        return jsonify(
            {'htmlresponse': settings.Messages.STRANGE_REQUESTS})

    is_at2 = helper_get_user_at2(user=current_user)

    pa_detalize_list, sum_fill, sum_spend = helper_get_transactions(u_id=u_id)
    link = f'javascript:get_transaction_history(\'' + url_for(f'user_cp.bck_update_transactions', u_id=u_id) + '?page={0}\');'
    page, per_page, offset, pagination, transactions_list = \
        helper_paginate_data(data=pa_detalize_list, href=link, per_page=settings.PAGINATION_PER_PROMOS,
                             anchor='transactions_table_info')
    transaction_dict = settings.Transactions.TRANSACTIONS

    return jsonify({'htmlresponse': render_template(f'user_control/transactions/transactions_history.html', **locals())})


def h_transaction_detail(u_id: int, t_id: int):
    # background transaction detail getter
    # user_info = User.query.with_entities(User.admin_parent_id, User.role, User.is_at2).filter(User.id == u_id).first()
    # if current_user.role == settings.ORD_USER:
    #     agent_info = User.query.with_entities(User.is_at2).filter(User.id == current_user.admin_parent_id).first()
    #     is_at2 = agent_info.is_at2 if agent_info else False  # not sure
    # else:
    #     is_at2 = current_user.is_at2
    is_at2 = helper_get_user_at2(user=current_user)

    transaction = UserTransaction.query.with_entities(UserTransaction.id, UserTransaction.type, UserTransaction.status,
                                                      UserTransaction.amount, UserTransaction.op_cost,
                                                      UserTransaction.bill_path, UserTransaction.promo_info,
                                                      UserTransaction.wo_account_info, UserTransaction.sa_id,
                                                      UserTransaction.created_at) \
        .filter(UserTransaction.user_id == u_id, UserTransaction.id == t_id).first()

    transaction_dict = settings.Transactions.TRANSACTIONS
    sa_types = settings.ServiceAccounts.TYPES_DICT
    if not transaction:
        return '', 404
    if transaction.type:
        transaction_image = helper_get_image_html(img_path=f"{settings.DOWNLOAD_DIR_BILLS}{transaction.bill_path}")
        service_account = ServiceAccount.query.filter(ServiceAccount.id == transaction.sa_id).first()
    else:
        order_prices_marks = helper_get_transaction_orders_detail(t_id=t_id)

        if order_prices_marks:
            total_marks = sum(list(map(lambda x: x.marks_count, order_prices_marks)))

        else:
            total_marks = 0
    return jsonify({'transaction_report': render_template(f'user_control/transactions/transaction_report.html', **locals())})


def h_order_book_detail(u_id: int):
    categories: dict = {"обувь": 'shoes',
                        "одежда": 'clothes',
                        "белье": 'linen',
                        "парфюм": 'parfum', }

    active_orders_raw = (current_user.orders.filter_by(processed=False, to_delete=False,
                                                       stage=settings.OrderStage.CREATING)
                         .with_entities(Order.id, Order.order_idn, Order.category, Order.company_type,
                                        Order.company_name, Order.company_idn, Order.to_delete,
                                        Order.created_at, Order.stage, Order.closed_at)
                         .group_by(Order.category, Order.id).order_by(desc(Order.created_at)).all())
    active_orders = []
    for el in categories.keys():
        active_orders.append((el, list(filter(lambda x: x.category == el, active_orders_raw))))

    return jsonify({'ob_report': render_template(f'user_control/order_book/ob_modal.html', **locals())})


def h_tg_verify_detail(u_id: int):
    tg_user = TgUser.query.filter(TgUser.flask_user_id == u_id).first()
    is_at2 = current_user.is_at2
    bot_link = settings.TELEGRAMM_USER_NOTIFY_LINK
    return jsonify({'tg_verify_report': render_template(f'user_control/tg_notifier/tg_notify_modal.html', **locals())})


# like big methods
def h_pa_refill(u_id: int):
    status = 'danger'

    # all neccessary checks
    if u_id != current_user.id:
        message = settings.Messages.STRANGE_REQUESTS
        return jsonify(dict(status=status, message=message))

    agent_info = User.query.filter(User.id == current_user.admin_parent_id)\
        .with_entities(User.is_at2, User.login_name).first()
    if agent_info and agent_info.is_at2:
        message = f"{settings.Messages.USER_TRANSACTION_AGENT_ERROR} {agent_info.login_name}"
        return jsonify(dict(status=status, message=message))

    cur_sa = helper_get_current_sa()
    if not cur_sa:
        message = settings.Messages.STRANGE_REQUESTS
        return jsonify(dict(status=status, message=message))

    promo_code = request.form.get('promo_code', '').replace('--', '')

    amount_add = 0
    if promo_code:
        promo_success, amount_add, message = helper_check_promo(user=current_user, promo_code=promo_code)
        if not promo_success:
            return jsonify(dict(status=status, message=message))

    try:

        bill_file = request.files.get('bill_file')
        # check file
        if bill_file is None or bill_file is False or check_file_extension(filename=bill_file.filename,
                                                                           extensions=settings.ALLOWED_IMG_EXTENSIONS) is False:
            message = settings.Messages.UT_TYPE_FILE_ERROR
            return jsonify(dict(status=status, message=message))

        bill_extension = get_file_extension(filename=bill_file.filename)

        uuid_prefix = str(uuid4())[:8]
        bill_path = f'{uuid_prefix}_{current_user.login_name}.{bill_extension}'
        # save file
        bill_file.save(f"{settings.DOWNLOAD_DIR_BILLS}{bill_path}")

        # make this variables to avoid current_user reload after update sessions

        username = current_user.login_name
        email = current_user.email
        phone = current_user.phone

        amount_orig = int(request.form.get('bill_summ', '').replace('--', ''))
        amount = amount_orig + amount_add
        promo_info = f'{promo_code}: {amount_orig} + {amount_add}' if promo_code else ''
        if helper_refill_transaction(amount=amount, status=settings.Transactions.PENDING, promo_info=promo_info,
                                     user_id=current_user.id, sa_id=cur_sa.id, bill_path=bill_path):

            # send message to admin TG
            RefillBalance.send_messages_refill_balance.delay(
                username=username,
                email=email,
                phone=phone,
                amount=amount,
                promo_code=promo_code,
                amount_add=amount_add,
            )

            # send promo_info to google tables
            if promo_code:
                date_time = datetime.now().strftime("%d.%m.%Y %H:%M")
                GoogleProcess.send_promo_data(data_packet=PromoRow(date_value=date_time, login_name=username,
                                                                   service_account=cur_sa.sa_name, promo_code=promo_code,
                                                                   promo_summ=amount_add))

            message = f"{settings.Messages.USER_TRANSACTION_CREATE}"
            status = 'success'

            return jsonify(dict(status=status, message=message, pending_amount=amount))
        else:
            raise IntegrityError
    except ValueError as ve:
        db.session.rollback()
        message = f"{settings.Messages.USER_TRANSACTION_ERROR} ошибка ввода данных"
        logger.error(ve)

    except IntegrityError as e:
        db.session.rollback()
        message = f"{settings.Messages.USER_TRANSACTION_ERROR} {e}"
        logger.error(message)

    return jsonify(dict(status=status, message=message))


def h_agent_wo(u_id: int):
    status = 'danger'
    if u_id != current_user.id:
        message = settings.Messages.STRANGE_REQUESTS
        return jsonify(dict(status=status, message=message))

    try:

        # make this variables to avoid current_user reload after update sessions
        username = current_user.login_name
        email = current_user.email
        phone = current_user.phone
        uuid_prefix = str(uuid4())[:8]
        bill_path = f'{uuid_prefix}_{current_user.login_name}_write_off_patch'
        amount = int(request.form.get('wo_summ', '').replace('--', ''))
        wo_account_info = request.form.get('wo_account_info', '').replace('--', '')
        check = helper_agent_wo_transaction(amount=amount, status=settings.Transactions.PENDING,
                                       user_id=current_user.id, bill_path=bill_path, wo_account_info=wo_account_info)
        if check[0]:

            # send message to admin TG
            WriteOffBalance.send_messages_wo_balance.delay(
                username=username,
                email=email,
                phone=phone,
                amount=amount,
                wo_account_info=wo_account_info,
            )

            message = f"{settings.Messages.USER_TRANSACTION_CREATE}"
            status = 'success'
            return jsonify(dict(status=status, message=message, pending_amount=amount))
        else:
            return jsonify(dict(status=status, message=check[1]))
    except ValueError:
        db.session.rollback()
        message = f"{settings.Messages.USER_TRANSACTION_ERROR} ошибка ввода данных"
        logger.error(message)

    except IntegrityError as e:
        db.session.rollback()
        message = f"{settings.Messages.USER_TRANSACTION_ERROR} {e}"
        logger.error(message)

    return jsonify(dict(status=status, message=message))


def h_create_new_password(r_link: str) -> Union[Response, str]:
    if current_user.is_authenticated:
        flash(message=settings.Messages.SECONDARY_SIGN_UP_ERROR)
        return redirect(url_for('main.enter'))

    info_list = url_decrypt(r_link).split('__')
    datetime_current = datetime.now()
    user_id, datetime_obj = int(info_list[0]), datetime.strptime(info_list[1], "%Y_%m_%d %H_%M_%S")
    user = User.query.get(user_id)
    if not user:
        flash(message=settings.Messages.RESTORE_LINK_ABSENT_USER, category="warning")
        return redirect(url_for('main.index'))
    compare_link = url_for('user_cp.create_new_password', r_link=r_link)
    if (datetime_current-datetime_obj).total_seconds() > settings.Mail.EXPIRATION_RESTORE_LINK:
        user_link = user.restore_link.filter_by(link=compare_link).first()
        if not user_link:
            flash(message=settings.Messages.RESTORE_LINK_ABSENT, category="warning")
            return redirect(url_for('auth.login'))
        try:
            db.session.delete(user_link)
            db.session.commit()
            flash(message=settings.Messages.RESTORE_LINK_EXPIRED, category="warning")

            return redirect(url_for('auth.login'))
        except IntegrityError as e:
            db.session.rollback()
            message = f"{settings.Messages.CHANGE_PASSWORD_ERROR}{(e)}"
            flash(message=message, category='error')
            logger.error(message)

            return redirect(url_for('auth.login'))
    else:

        user_link_raw = user.restore_link.filter_by(link=compare_link).first()
        if not user_link_raw:
            flash(message=f"{settings.Messages.WRONG_RESTORE_LINK}", category='error')
            return redirect(url_for('auth.login'))
        else:
            user_link = user_link_raw.link

    return render_template('user_control/user_create_new_password.html', **locals())


def h_change_user_password_na() -> Response:
    if current_user.is_authenticated:
        flash(message=settings.Messages.SECONDARY_SIGN_UP_ERROR, category='error')
        return redirect(url_for('main.enter'))
    form_dict = request.form.to_dict()
    restore_link = form_dict.get("restore_link")
    user_info = User.query.get(form_dict.get("user_id"))

    if not user_info:
        flash(message=f"{settings.Messages.CHANGE_PASSWORD_STRANGE_ACTIONS}", category='error')
        return redirect(url_for('auth.login'))

    check_user_link = user_info.restore_link.filter_by(link=restore_link).first()
    if not check_user_link or restore_link != check_user_link.link:
        flash(message=f"{settings.Messages.CHANGE_PASSWORD_STRANGE_ACTIONS} {settings.Messages.WRONG_RESTORE_LINK}", category='error')
        return redirect(url_for('auth.login'))
    if not check_user_link.status:
        flash(message=settings.Messages.RESTORE_LINK_EXPIRED, category='error')
        return redirect(url_for('auth.login'))

    new_password = generate_password_hash(form_dict.get('new_password'), method='sha256')

    try:
        user_info.password = new_password
        user_link_processed = user_info.restore_link.filter_by(link=restore_link).first()
        user_info.restore_link = []
        db.session.delete(user_link_processed)

        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        message = f"{settings.Messages.CHANGE_PASSWORD_ERROR}{e}"
        flash(message=message, category='error')
        logger.error(message)

        return redirect(url_for('user_cp.user_control_panel', u_id=user_info.id))

    flash(message=f"Пользователь {user_info.login_name} {settings.Messages.CHANGE_PASSWORD_SUCCESS}")
    return redirect(url_for('user_cp.user_control_panel', u_id=user_info.id))


def helper_get_summ_marks(u_id: int) -> int:

    orders = Order.query.with_entities(Order.category, Order.id).filter(Order.stage > 0,
                                                                        Order.payment == False,
                                                                        Order.user_id == u_id).all()

    return sum(tuple(map(lambda x: get_rows_marks(o_id=x.id, category=x.category)[1], orders)))


def h_order_write_off_check(o_id: int, service_flag: bool = True) -> bool:
    balance = current_user.balance
    prices = current_user.prices
    summary_marks = helper_get_summ_marks(o_id)
    ...

