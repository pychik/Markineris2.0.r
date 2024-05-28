from datetime import datetime, timedelta
from decimal import Decimal
from os import listdir as o_list_dir
from os import remove as o_remove

from flask import render_template, url_for, request, Response, jsonify
from flask_login import current_user
from sqlalchemy import desc, text, create_engine, null
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from config import settings
from logger import logger
from models import Promo, Price, ServiceAccount, ServerParam, User, UserTransaction
from models import db
from utilities.support import helper_paginate_data, check_file_extension, get_file_extension, \
    helper_get_server_balance, helper_get_filters_transactions, \
    helper_update_pending_rf_transaction_status, helper_get_image_html, \
    helper_perform_ut_wo, helper_get_transaction_orders_detail


def h_su_control_finance():
    promos = Promo.query.with_entities(Promo.id, Promo.code, Promo.value, Promo.created_at).order_by(desc(Promo.created_at)).all()
    prices = Price.query.order_by(desc(Price.created_at)).all()

    account_type_db = ServerParam.query.with_entities(ServerParam.account_type).first()
    account_type = settings.ServiceAccounts.DEFAULT_QR_ACCOUNT_TYPE if not account_type_db else account_type_db.account_type
    service_accounts = ServiceAccount.query.order_by(desc(ServiceAccount.created_at)).all()

    # rf- refill , wo write off
    balance, pending_balance_rf = helper_get_server_balance()

    basic_prices = settings.Prices.BASIC_PRICES
    base_path = settings.DOWNLOAD_QA_BASIC
    sa_types = settings.ServiceAccounts.TYPES_DICT
    all_prices = Price.query.with_entities(Price.id, Price.price_code, Price.price_at2).order_by(
        desc(Price.created_at)).all()

    # paginated promo's
    link = 'javascript:get_promos_history(\'' + url_for('admin_control.su_bck_promo') + '?page={0}\');'
    page, per_page, \
        offset, pagination, \
        promo_list = helper_paginate_data(data=promos, href=link, per_page=settings.PAGINATION_PER_PROMOS)
    return render_template('admin/su_finance_control.html', **locals())


def h_su_bck_promo():

    promos = Promo.query.with_entities(Promo.id, Promo.code, Promo.value, Promo.created_at).order_by(
        desc(Promo.created_at)).all()
    link = 'javascript:get_promos_history(\'' + url_for('admin_control.su_bck_promo') + '?page={0}\');'
    page, per_page, \
        offset, pagination, \
        promo_list = helper_paginate_data(data=promos, href=link, per_page=settings.PAGINATION_PER_PROMOS)

    return jsonify({'htmlresponse': render_template(f'admin/promos_table.html', **locals())})


def h_su_add_promo():
    code = request.form.get('promo_code', '').replace('--', '')
    status = 'danger'

    try:
        value = int(request.form.get('promo_value', '').replace('--', ''))
        promo = Promo(code=code, value=value)
        db.session.add(promo)
        db.session.commit()
        message = f"{settings.Messages.PROMO_CREATE} {code} "
        status = 'success'
    except ValueError:
        db.session.rollback()
        message = f"{settings.Messages.PROMO_TYPE_ERROR}"
        logger.error(message)

    except IntegrityError as e:
        db.session.rollback()
        message = f"{settings.Messages.PROMO_DUPLICATE_ERROR} {code}" if "psycopg2.errors.UniqueViolation)" \
            in str(e) else f"{settings.Messages.PROMO_ERROR}{str(e)}"
        logger.error(message)

    return jsonify(dict(status=status, message=message))


def h_su_delete_promo(p_id: int) -> Response:
    promo = Promo.query.with_entities(Promo.id, Promo.code).filter(Promo.id == p_id).first()
    status = 'danger'
    # check for trickers
    if not promo:
        message = settings.Messages.DELETE_NE_PROMO
        return jsonify(dict(status=status, message=message))
    try:
        db.session.execute(text(f'DELETE FROM public.users_promos WHERE promo_id={p_id}'))
        db.session.execute(db.delete(Promo).filter_by(id=p_id))

        db.session.commit()

        message = f"{settings.Messages.DELETE_PROMO} {promo.code}"
        status = 'success'
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.DELETE_PROMO_ERROR} {e}"
        logger.error(message)

    return jsonify(dict(status=status, message=message))


def h_su_bck_prices():
    prices = Price.query.order_by(desc(Price.created_at)).all()
    basic_prices = settings.Prices.BASIC_PRICES
    all_prices = Price.query.with_entities(Price.id, Price.price_code, Price.price_at2).order_by(
        desc(Price.created_at)).all()
    base_path = settings.DOWNLOAD_DIR_SA_QR

    return jsonify({'htmlresponse': render_template(f'admin/prices_table.html', **locals())})


def h_su_add_prices():
    price_code = request.form.get('price_code', '').replace('--', '')
    # https://stackoverflow.com/questions/31859903/get-the-value-of-a-checkbox-in-flask
    price_at2 = request.form.get('price_at2') is not None

    status = 'danger'
    try:
        price_1 = Decimal(request.form.get('price_1').replace('--', ''))
        price_2 = Decimal(request.form.get('price_2').replace('--', ''))
        price_3 = Decimal(request.form.get('price_3').replace('--', ''))
        price_4 = Decimal(request.form.get('price_4').replace('--', ''))
        price_5 = Decimal(request.form.get('price_5').replace('--', ''))
        price = Price(price_code=price_code, price_at2=price_at2,
                      price_1=price_1, price_2=price_2, price_3=price_3, price_4=price_4, price_5=price_5)

        db.session.add(price)
        db.session.commit()
        message = f"{settings.Messages.PRICE_CREATE} {price_code} "
        status = 'success'

    except ValueError:
        db.session.rollback()
        message = f"{settings.Messages.PRICE_TYPE_ERROR}"
        logger.error(message)

    except IntegrityError as e:
        db.session.rollback()
        message = f"{settings.Messages.PRICE_DUPLICATE_ERROR} {price_code}" if "psycopg2.errors.UniqueViolation)" \
            in str(e) else f"{settings.Messages.PRICE_ERROR}{str(e)}"
        logger.error(message)

    return jsonify(dict(status=status, message=message))


def h_su_delete_prices(p_id: int) -> Response:

    price = Price.query.with_entities(Price.id, Price.price_code).filter(Price.id == p_id).first()
    price_replace_id = request.form.get('price_id', None, int)

    status = 'danger'
    # check for trickers
    if not price:
        message = settings.Messages.DELETE_NE_PRICE
        return jsonify(dict(status=status, message=message))

    # check for basic price
    if not price_replace_id:
        user_update_stmt = text(f"""UPDATE public.users set price_id=NULL WHERE price_id={p_id}""")
    else:
        # price_replace = Price.query.with_entities(Price.id).filter(Price.id == request.form.get('price_id', null(), int)).first()
        price_replace = Price.query.with_entities(Price.id).filter(Price.id == price_replace_id).first()

        replace_price_id = price_replace.id if price_replace else null()
        user_update_stmt = text(f"""UPDATE public.users set price_id={replace_price_id} WHERE price_id={p_id}""")

    try:

        db.session.execute(user_update_stmt)
        db.session.execute(db.delete(Price).filter_by(id=p_id))
        db.session.commit()

        message = f"{settings.Messages.DELETE_PRICE} {price.price_code}"
        status = 'success'
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.DELETE_PRICE_ERROR} {e}"
        logger.error(message)

    return jsonify(dict(status=status, message=message))


def h_su_bck_sa():
    base_path = settings.DOWNLOAD_QA_BASIC
    sa_types = settings.ServiceAccounts.TYPES_DICT
    service_accounts = ServiceAccount.query.order_by(desc(ServiceAccount.created_at)).all()
    return jsonify({'htmlresponse': render_template(f'admin/sa_table.html', **locals())})


def h_su_add_sa():

    status = 'danger'

    sa_quantity = ServiceAccount.query.count()

    # check quantity limit
    if sa_quantity >= settings.ServiceAccounts.QUANTITY_LIMIT:
        message = f'{settings.Messages.SA_LIMIT_ERROR} {sa_quantity}'
        return jsonify(dict(status=status, message=message))
    sa_name = request.form.get('sa_name', '').replace('--', '')
    sa_type = request.form.get('sa_type', '').replace('--', '')
    try:
        # check sa_type
        if sa_type not in settings.ServiceAccounts.TYPES_KEYS:
            raise ValueError

        sa_qr_path = None
        sa_reqs = None
        if sa_type == settings.ServiceAccounts.TYPES_KEYS[0]:
            # qr service_account
            sa_qr_file = request.files.get('sa_qr_file')
            # check file
            if sa_qr_file is None or sa_qr_file is False or check_file_extension(filename=sa_qr_file.filename,
                                                                                 extensions=settings.ALLOWED_IMG_EXTENSIONS) is False:
                message = settings.Messages.SA_TYPE_FILE_ERROR
                return jsonify(dict(status=status, message=message))
            sa_extension = get_file_extension(filename=sa_qr_file.filename)
            sa_qr_path = f'img_{sa_name}.{sa_extension}'
            # save file
            sa_qr_file.save(f"{settings.DOWNLOAD_DIR_SA_QR}{sa_qr_path}")
        else:
            # requisites service_account
            sa_reqs = request.form.get('sa_req', '').replace('--', '')

        # another trick check
        if not sa_reqs and not sa_qr_path:
            raise ValueError

        sa_new = ServiceAccount(sa_name=sa_name, sa_type=sa_type, sa_qr_path=sa_qr_path, sa_reqs=sa_reqs)

        db.session.add(sa_new)
        db.session.commit()
        message = f"{settings.Messages.SA_CREATE} {sa_name} {sa_type}"
        status = 'success'

    except ValueError:
        db.session.rollback()
        message = f"{settings.Messages.SA_TYPE_ERROR}"
        logger.error(message)

    except IntegrityError as e:
        db.session.rollback()
        message = f"{settings.Messages.SA_DUPLICATE_ERROR} {sa_name}" if "psycopg2.errors.UniqueViolation)" \
            in str(e) else f"{settings.Messages.SA_ERROR}{str(e)}"
        logger.error(message)

    return jsonify(dict(status=status, message=message))


def h_su_delete_sa(sa_id: int) -> Response:
    account = ServiceAccount.query.with_entities(
        ServiceAccount.id, ServiceAccount.sa_name, ServiceAccount.sa_type,
        ServiceAccount.sa_qr_path).filter(ServiceAccount.id == sa_id).first()
    status = 'danger'

    # check for trickers
    if not account:
        message = settings.Messages.DELETE_NE_SA
        return jsonify(dict(status=status, message=message))
    try:
        db.session.execute(db.delete(ServiceAccount).filter_by(id=sa_id))

        if account.sa_type == settings.ServiceAccounts.TYPES_KEYS[0] and account.sa_qr_path in o_list_dir(settings.DOWNLOAD_DIR_SA_QR):

            # sa is qr_type, removing image from service
            o_remove(path=f"{settings.DOWNLOAD_DIR_SA_QR}{account.sa_qr_path}")

        db.session.commit()
        message = f"{settings.Messages.DELETE_SA} {account.sa_name}"
        status = 'success'
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.DELETE_SA_ERROR}" \
                  f" { settings.Messages.DELETE_SA_UT_ERROR if 'psycopg2.errors.ForeignKeyViolation' in str(e) else e}"
        logger.error(message)

    return jsonify(dict(status=status, message=message))


def h_su_bck_change_sa_activity(sa_id: int) -> Response:
    account = ServiceAccount.query.filter(ServiceAccount.id == sa_id).first()
    status = 'danger'

    # check for trickers
    if not account:
        message = settings.Messages.CHANGE_NE_SA_ACTIVITY
        return jsonify(dict(status=status, message=message))
    try:
        # check if we got an account that is already in use with sa type
        current_account_use = ServiceAccount.query.filter(ServiceAccount.sa_type == account.sa_type,
                                                          ServiceAccount.current_use == True).first()
        account.current_use = False if current_account_use else True

        account.is_active = not account.is_active

        db.session.commit()
        message = settings.Messages.CHANGE_SA_ACTIVITY.format(status="Активирован" if account.is_active else "Не активен")
        status = 'success'
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.CHANGE_SA_ACTIVITY_ERROR} {e}"
        logger.error(message)

    return jsonify(dict(status=status, message=message))


def h_su_bck_change_sa_type(sa_type: str = 'qr_code') -> Response:

    status = 'danger'
    message = settings.Messages.SA_TYPE_CHANGE_ERROR

    # check for trickers
    if sa_type not in settings.ServiceAccounts.TYPES_KEYS:
        return jsonify(dict(status=status, message=message))

    change_block = f'<label>Работа по Qr коду</label><input class="form-check-input bg-warning border border-warning"' \
                   f' type="checkbox" role="switch" ' \
                   f'id="account_type_switch" name="account_type_switch" checked onclick="bck_change_account_type'\
                   f'(\'{url_for("admin_control.su_bck_change_sa_type", sa_type="requisites")}\', \'requisites\')">'\
                   if sa_type == 'qr_code'\
                   else f'<label>Работа по реквизитам</label><input class="form-check-input border border-warning"' \
                        f' type="checkbox" role="switch" id="account_type_switch" name="account_type_switch" ' \
                        f'onclick="bck_change_account_type' \
                        f'(\'{url_for("admin_control.su_bck_change_sa_type", sa_type="qr_code")}\', \'qr_code\')">'

    try:
        account_type_db = ServerParam.query.with_entities(ServerParam.account_type).first()
        if not account_type_db:
            new_sp = ServerParam(account_type=sa_type)
            db.session.add(new_sp)
        else:
            db.session.execute(text(f"UPDATE public.server_params SET account_type='{sa_type}'"))

        db.session.commit()
        message = f"{settings.Messages.SA_TYPE_CHANGE}"
        status = 'warning'

    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.SA_TYPE_CHANGE_ERROR} {e}"
        logger.error(message)

    return jsonify(dict(status=status, message=message, change_block=change_block))


def h_su_control_ut(user_ids: list = None):
    # PENDING transactions refill, WITH default DATE filter
    transaction_types = settings.Transactions.TRANSACTION_TYPES
    transaction_dict = settings.Transactions.TRANSACTIONS

    tr_type = transaction_types.get(1)
    tr_status = transaction_dict[settings.Transactions.PENDING]

    # default date range conditions
    date_to = datetime.now()
    date_from = date_to - timedelta(days=settings.Transactions.DEFAULT_DAYS_RANGE)

    transactions = UserTransaction.query.with_entities(UserTransaction.id, UserTransaction.amount,
                                                       UserTransaction.promo_info, UserTransaction.type,
                                                       UserTransaction.status,
                                                       UserTransaction.created_at, UserTransaction.user_id,
                                                       User.login_name)\
        .join(User, User.id == UserTransaction.user_id)\
        .filter(UserTransaction.status == settings.Transactions.PENDING, UserTransaction.type.is_(True),
                UserTransaction.created_at >= date_from)\
        .order_by(desc(UserTransaction.created_at)).all()

    sa_types = settings.ServiceAccounts.TYPES_DICT
    transaction_types = settings.Transactions.TRANSACTION_TYPES

    link_filters = f'tr_type=1&tr_status={settings.Transactions.PENDING}&'
    link = f'javascript:bck_get_transactions(\'' + url_for(
        'admin_control.su_bck_control_ut') + f'?bck=1{link_filters}' + 'page={0}\');'
    page, per_page, \
        offset, pagination, \
        transactions_list = helper_paginate_data(data=transactions, per_page=settings.PAGINATION_PER_PAGE, href=link)
    return render_template('admin/transactions/su_control_transactions.html', **locals())


def h_bck_control_ut():
    transaction_dict = settings.Transactions.TRANSACTIONS

    tr_type, tr_status, date_from, date_to,\
        link_filters, model_conditions, model_order_type = helper_get_filters_transactions()

    transactions = UserTransaction.query.with_entities(UserTransaction.id, UserTransaction.amount,
                                                       UserTransaction.promo_info, UserTransaction.type,
                                                       UserTransaction.status,
                                                       UserTransaction.created_at, UserTransaction.user_id, User.login_name) \
        .join(User, User.id == UserTransaction.user_id).filter(*model_conditions) \
        .order_by(model_order_type).all()

    link = f'javascript:bck_get_transactions(\'' + url_for('admin_control.su_bck_control_ut') + f'?bck=1{link_filters}' + 'page={0}\');'

    page, per_page, \
        offset, pagination, \
        transactions_list = helper_paginate_data(data=transactions, per_page=settings.PAGINATION_PER_PAGE, href=link)

    return jsonify({'htmlresponse': render_template(f'admin/transactions/su_transactions_table.html', **locals())})


def h_au_bck_control_ut():
    """
       background update of agent users transactions  write_off for agent commission counter
    :return:
    """
    transaction_types = settings.Transactions.TRANSACTION_TYPES
    transaction_dict = settings.Transactions.TRANSACTIONS

    user_ids = [uid.id for uid in User.query.filter(User.admin_parent_id == current_user.id).with_entities(User.id).all()]
    user_ids.append(current_user.id)

    is_at2 = current_user.is_at2

    transaction_dict = settings.Transactions.TRANSACTIONS

    # set manually type and status for render page case
    tr_type, tr_status, date_from, date_to, link_filters, model_conditions, model_order_type = \
        helper_get_filters_transactions(tr_type=settings.Transactions.TRANSACTION_WRITEOFF,
                                        tr_status=settings.Transactions.SUCCESS)

    transactions = UserTransaction.query.with_entities(UserTransaction.id, UserTransaction.amount,
                                                       UserTransaction.agent_fee, UserTransaction.promo_info,
                                                       UserTransaction.type, UserTransaction.status,
                                                       UserTransaction.created_at, UserTransaction.user_id,
                                                       User.login_name) \
                                  .join(User, User.id == UserTransaction.user_id) \
                                  .filter(*model_conditions, User.id.in_(user_ids), UserTransaction.agent_fee != None,) \
                                  .order_by(model_order_type).all()

    link = f'javascript:bck_get_transactions(\'' + url_for(
        'admin_control.au_bck_control_ut') + f'?bck=1&{link_filters}' + 'page={0}\');'

    page, per_page, \
        offset, pagination, \
        transactions_list = helper_paginate_data(data=transactions, per_page=settings.PAGINATION_PER_PAGE, href=link)

    bck = request.args.get('bck', 0, type=int)
    return jsonify({'htmlresponse': render_template(f'admin/au_transactions/au_transactions_table.html', **locals())}) \
        if bck else render_template('admin/au_transactions/au_control_transactions.html', **locals())


def h_su_transaction_detail(u_id: int, t_id: int):
    # background retrieving info
    transaction = UserTransaction.query.with_entities(UserTransaction.id, UserTransaction.type, UserTransaction.status,
                                                      UserTransaction.amount, UserTransaction.op_cost, UserTransaction.bill_path,
                                                      UserTransaction.user_id, UserTransaction.promo_info,
                                                      UserTransaction.wo_account_info,
                                                      UserTransaction.sa_id, UserTransaction.created_at, User.login_name, User.email, User.phone) \
        .join(User, User.id == UserTransaction.user_id)\
        .filter(UserTransaction.user_id == u_id, UserTransaction.id == t_id).first()

    transaction_dict = settings.Transactions.TRANSACTIONS
    sa_types = settings.ServiceAccounts.TYPES_DICT
    if transaction.type and transaction.status in [settings.Transactions.SUCCESS, settings.Transactions.PENDING,
                                                   settings.Transactions.CANCELLED]:
        transaction_image = helper_get_image_html(img_path=f"{settings.DOWNLOAD_DIR_BILLS}{transaction.bill_path}")
        service_account = ServiceAccount.query.filter(ServiceAccount.id == transaction.sa_id).first()
    # elif (not transaction.type or (transaction.type and transaction.op_cost)) and transaction.status == settings.Transactions.SUCCESS:
    else:
        order_prices_marks = helper_get_transaction_orders_detail(t_id=t_id)

        if order_prices_marks:
            total_marks = sum(list(map(lambda x: x.marks_count, order_prices_marks)))

        else:
            total_marks = 0

    return jsonify({'transaction_report': render_template(f'admin/transactions/su_transaction_report.html', **locals())})


def h_aus_transaction_detail(u_id: int, t_id: int):
    # background retrieving info
    user_ids = [uid.id for uid in User.query.filter(User.admin_parent_id == current_user.id)
                                            .with_entities(User.id).all()]
    user_ids.append(current_user.id)  # we check admin_info too
    if u_id not in user_ids:
        return jsonify(dict(status=0, message=settings.Messages.STRANGE_REQUESTS))

    transaction = UserTransaction.query.with_entities(UserTransaction.id, UserTransaction.type, UserTransaction.status,
                                                      UserTransaction.amount, UserTransaction.op_cost, UserTransaction.bill_path,
                                                      UserTransaction.user_id, UserTransaction.promo_info,
                                                      UserTransaction.wo_account_info,
                                                      UserTransaction.sa_id, UserTransaction.created_at)\
        .filter(UserTransaction.user_id == u_id, UserTransaction.id == t_id).first()

    transaction_dict = settings.Transactions.TRANSACTIONS
    sa_types = settings.ServiceAccounts.TYPES_DICT

    order_prices_marks = helper_get_transaction_orders_detail(t_id=t_id)

    if order_prices_marks:
        total_marks = sum(list(map(lambda x: x.marks_count, order_prices_marks)))

    else:
        total_marks = 0

    return jsonify({'transaction_report': render_template(f'admin/transactions/su_transaction_report.html', **locals()),
                    'status': 1})


def h_su_wo_transactions() -> Response:
    from settings.start import app
    app.config['MAINTENANCE_MODE'] = True

    # background update of transactions
    # 2 getting users with pending orders
    user_ids_stmt = f"""
                     SELECT DISTINCT o.user_id AS user_id FROM public.orders o 
                     WHERE o.payment !=True AND o.processed != True AND o.stage > {settings.OrderStage.NEW} AND o.stage != {settings.OrderStage.CANCELLED};
                      """
    user_ids = db.session.execute(text(user_ids_stmt)).fetchall()
    if user_ids:
        status, server_balance = helper_perform_ut_wo(user_ids=user_ids)
    else:
        status, server_balance = 0, 'No orders to write off'

    app.config['MAINTENANCE_MODE'] = False
    return jsonify(dict(status=status, server_balance=server_balance))


def h_su_pending_transaction_update(u_id: int, t_id: int,):

    status = 'danger'
    message = settings.Messages.SU_TRANSACTION_CHANGE_ERROR

    tr_type = request.form.get('tr_type', 0, int)
    tr_status = request.form.get('tr_status', 0, int)

    if tr_type not in [0, 1, ] and tr_status not in settings.Transactions.TRANSACTIONS.keys():
        jsonify(dict(status=status, message=f"{message} ошибка ввода"))

    # check for tricksters
    transaction_updated = UserTransaction.query.with_entities(UserTransaction.id, UserTransaction.amount)\
                                               .filter(UserTransaction.user_id == u_id,
                                                       UserTransaction.id == t_id).first()

    user = User.query.with_entities(User.id).filter(User.id == u_id).first()
    if not user or not transaction_updated:
        jsonify(dict(status=status, message=f"{message} нет такого пользователя или транзакции"))

    process_transaction = helper_update_pending_rf_transaction_status(u_id=u_id, t_id=t_id,
                                                                      amount=transaction_updated.amount,
                                                                      tr_type=tr_type, tr_status=tr_status)
    if process_transaction[0]:
        status = 'success'
        message = settings.Messages.SU_TRANSACTION_CHANGE
    else:
        message += ': ' + process_transaction[1]

    return jsonify(dict(status=status, message=message))


def _h_isolated_session():

    plain_engine = create_engine(settings.SQL_DATABASE_URL)

    with Session(bind=plain_engine) as session:
        session.connection(execution_options={"isolation_level": "SERIALIZABLE"})
        # making queries session
        ...
