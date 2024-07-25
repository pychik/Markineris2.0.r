import urllib
from datetime import datetime, timedelta
from decimal import Decimal
from os import listdir as o_list_dir
from os import remove as o_remove

from flask import render_template, url_for, request, Response, jsonify, make_response
from flask_login import current_user
from sqlalchemy import desc, text, create_engine, null, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from config import settings
from logger import logger
from models import Promo, Price, ServiceAccount, ServerParam, User, UserTransaction, TgUser
from models import db
from utilities.admin.excel_report import ExcelReportProcessor, ExcelReport
from utilities.support import helper_paginate_data, check_file_extension, get_file_extension, \
    helper_get_server_balance, helper_get_filters_transactions, \
    helper_update_pending_rf_transaction_status, helper_get_image_html, \
    helper_perform_ut_wo_mod, helper_get_transaction_orders_detail, helper_get_stmt_for_fin_order_report, \
    helper_get_filter_fin_order_report, helper_get_stmt_for_fin_promo_history, helper_get_filter_fin_promo_history,\
    helper_get_transactions, helper_get_user_at2_opt2
from utilities.telegram import NotificationTgUser
from utilities.tg_verify.service import send_tg_message_with_transaction_updated_status


def h_su_control_finance():
    stat_date = datetime.today() - timedelta(days=1)
    stat_stmt = text("""WITH mark_count as (SELECT os.transaction_id, sum(os.marks_count) as total_marks from public.orders_stats os GROUP BY os.transaction_id)
    SELECT 
        round(coalesce(sum(ut.amount), 0), 2) as amount, 
        coalesce(sum(mc.total_marks), 0) as marks_cnt, 
        round(case when coalesce(sum(mc.total_marks), 0) = 0 then 0 else coalesce(sum(amount), 0) / coalesce(sum(mc.total_marks), 0) end, 2) as avg_price
    FROM public.user_transactions ut
    JOIN mark_count mc on ut.id = mc.transaction_id
    WHERE
        ut.op_cost is not null and ut.type=False
        and ut.created_at >= DATE_TRUNC('DAY', NOW()::timestamp);
        """)
    stat = db.session.execute(stat_stmt).first()

    promos = Promo.query.with_entities(Promo.id, Promo.code, Promo.value, Promo.created_at).order_by(desc(Promo.created_at)).all()
    prices = Price.query.order_by(desc(Price.created_at)).all()

    account_type_db = ServerParam.query.with_entities(ServerParam.account_type).first()
    account_type = settings.ServiceAccounts.DEFAULT_QR_ACCOUNT_TYPE if not account_type_db else account_type_db.account_type
    service_accounts = ServiceAccount.query.order_by(desc(ServiceAccount.created_at)).all()

    # rf- refill , wo write off
    balance, pending_balance_rf, summ_at1, summ_at2, summ_client = helper_get_server_balance()

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
    roles = (settings.SUPER_USER, settings.ADMIN_USER)
    transaction_types = settings.Transactions.TRANSACTION_TYPES
    transaction_dict = settings.Transactions.TRANSACTIONS

    tr_type = transaction_types.get(1)

    tr_status = transaction_dict[settings.Transactions.PENDING]

    # default date range conditions
    date_to = datetime.now()
    date_from = date_to - timedelta(days=settings.Transactions.DEFAULT_DAYS_RANGE)
    users_filter = User.query.with_entities(User.id, User.login_name).filter(User.role.in_(roles)).all()

    transactions = [t for t in UserTransaction.query.with_entities(UserTransaction.id, UserTransaction.amount,
                                                       UserTransaction.promo_info, UserTransaction.type,
                                                       UserTransaction.status,
                                                       UserTransaction.created_at, UserTransaction.user_id,
                                                       User.login_name, User.email)\
        .join(User, User.id == UserTransaction.user_id) \
        .filter(UserTransaction.status == settings.Transactions.PENDING, UserTransaction.type.is_(True),
                UserTransaction.created_at >= date_from) \
        .order_by(desc(UserTransaction.created_at)).all()]

    sa_types = settings.ServiceAccounts.TYPES_DICT
    transaction_types = settings.Transactions.TRANSACTION_TYPES

    transaction_summ = sum(t.amount for t in transactions)

    link_filters = f'tr_type=1&tr_status={settings.Transactions.PENDING}&'
    link = f'javascript:bck_get_transactions(\'' + url_for(
        'admin_control.su_bck_control_ut') + f'?bck=1&{link_filters}' + 'page={0}\');'
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

    link = f'javascript:bck_get_transactions(\'' + url_for('admin_control.su_bck_control_ut') + f'?bck=1&{link_filters}' + 'page={0}\');'

    transaction_summ = sum(t.amount for t in transactions)

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
                                  .filter(*model_conditions, User.id.in_(user_ids), UserTransaction.agent_fee.isnot(None),) \
                                  .order_by(model_order_type).all()

    link = f'javascript:bck_get_transactions(\'' + url_for(
        'admin_control.au_bck_control_ut') + f'?bck=1&{link_filters}' + 'page={0}\');'

    page, per_page, \
        offset, pagination, \
        transactions_list = helper_paginate_data(data=transactions, per_page=settings.PAGINATION_PER_PAGE, href=link)

    bck = request.args.get('bck', 0, type=int)
    return jsonify({'htmlresponse': render_template(f'admin/au_transactions/au_transactions_table.html', **locals())}) \
        if bck else render_template('admin/au_transactions/au_control_transactions.html', **locals())


def h_bck_ut_excel_report() -> Response:
    """
    fetching a blob report of transactions
    :return:
    """
    tr_type, tr_status, date_from, date_to, \
        link_filters, model_conditions, model_order_type = helper_get_filters_transactions(report=True)

    transactions = [t for t in UserTransaction.query.with_entities(UserTransaction.id, UserTransaction.amount,
                                                                   UserTransaction.promo_info, UserTransaction.type,
                                                                   UserTransaction.status,
                                                                   UserTransaction.wo_account_info,
                                                                   UserTransaction.created_at, UserTransaction.user_id,
                                                                   User.login_name, User.email)
            .join(User, User.id == UserTransaction.user_id).filter(*model_conditions)
            .order_by(model_order_type).all()]

    transaction_summ = sum(t.amount for t in transactions)

    name_start = settings.Transactions.TRANSACTIONS_TYPES_LATIN1.get(tr_type)
    date_range = f"{date_from} - {date_to}".replace(' 00:00:00', '')
    excel_proc = ExcelReportProcessor(transactions=transactions, transaction_summ=transaction_summ, tr_type=tr_type,
                                      tr_status=tr_status, date_range=date_range)

    excel_io = excel_proc.get_excel_report()

    response = make_response(excel_io.getvalue())
    response.headers['data_file_name'] = "{name_start} {date_range}.xlsx".format(name_start=name_start,
                                                                                 date_range=date_range)
    response.headers['Content-type'] = 'text/plain'

    # response.headers['Content-Type'] = 'application/octet-stream'
    response.headers['data_status'] = 'success'

    return response


def h_fin_promo_history():
    date_from = datetime.today() - timedelta(days=7)
    date_to = datetime.today()
    promo_stmt = select(Promo.code)
    promo_codes = db.session.execute(promo_stmt).all()
    promo_hist_stmt = helper_get_stmt_for_fin_promo_history()
    promo_codes_history = db.session.execute(promo_hist_stmt).all()

    link = ''
    page, per_page, \
        offset, pagination, \
        promo_codes_history = helper_paginate_data(data=promo_codes_history, per_page=settings.PAGINATION_PER_PAGE, href=link)
    return render_template('admin/fin_promo_history/main.html', **locals())


def h_bck_fin_promo_history():
    date_from, date_to, promo_code, sort_type = helper_get_filter_fin_promo_history()
    stmt = helper_get_stmt_for_fin_promo_history(
        date_from=date_from,
        date_to=date_to,
        sort_type=sort_type,
        promo_code=promo_code,
    )
    promo_codes_history = db.session.execute(stmt, ).fetchall()
    link = f'javascript:bck_get_fin_promo_history(\'' + url_for(
        'admin_control.su_bck_fin_promo_history') + f'?bck=1' + '&page={0}\');'
    page, per_page, \
        offset, pagination, \
        promo_codes_history = helper_paginate_data(data=promo_codes_history, per_page=settings.PAGINATION_PER_PAGE, href=link)
    return jsonify({'htmlresponse': render_template(f'admin/fin_promo_history/table.html', **locals())})


def h_bck_fin_promo_history_excel():
    date_from, date_to, promo_code, sort_type = helper_get_filter_fin_promo_history(report=True)
    stmt = helper_get_stmt_for_fin_promo_history(
        date_from=date_from,
        date_to=date_to,
        sort_type=sort_type,
        promo_code=promo_code,
    )
    promo_codes_history = db.session.execute(stmt, ).fetchall()

    excel_filters = {
        'дата начала': date_from,
        'дата окончания': (datetime.strptime(date_to, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d'),
    }
    if promo_code:
        excel_filters['промокод'] = promo_code
    report_name = f'история промокодов({datetime.today().strftime("%d.%m.%y %H-%M")})'

    excel = ExcelReport(
        data=promo_codes_history,
        filters=excel_filters,
        columns_name=['дата активации', 'e-mail пользователя', 'логин агента', 'промокод',],
        sheet_name='История промокодов',
        output_file_name=report_name,
    )

    excel_io = excel.create_report()
    content = excel_io.getvalue()
    response = make_response(content)
    response.headers['data_file_name'] = urllib.parse.quote(excel.output_file_name)
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['data_status'] = 'success'

    return response


def h_su_control_specific_ut(u_id: int):

    # default date range conditions
    url_date_to_raw = datetime.now()
    url_date_to = url_date_to_raw.strftime('%d.%m.%Y')
    url_date_from = (url_date_to_raw - timedelta(days=settings.Transactions.DEFAULT_DAYS_RANGE)).strftime('%d.%m.%Y')
    date_to = url_date_to_raw.strftime('%Y-%m-%d')
    date_from = (url_date_to_raw - timedelta(days=settings.Transactions.DEFAULT_DAYS_RANGE)).strftime('%Y-%m-%d')

    is_at2, agent_id, agent_email, client_email, client_balance = helper_get_user_at2_opt2(u_id=u_id)

    pa_detalize_list, sum_fill, sum_spend = helper_get_transactions(u_id=u_id, date_from=date_from, date_to=date_to, sort_type='desc')
    link = f'javascript:get_transaction_history(\'' + url_for(f'user_cp.bck_update_transactions',
                                                              u_id=u_id) + '?page={0}\');'

    transaction_dict = settings.Transactions.TRANSACTIONS

    link_filters = ''
    link = f'javascript:bck_get_transactions_specific_user(\'' + url_for(
        'admin_control.su_bck_control_specific_ut', u_id=u_id) + f'?bck=1&{link_filters}' + 'page={0}\');'
    page, per_page, \
        offset, pagination, \
        transactions_list = helper_paginate_data(data=pa_detalize_list, per_page=settings.PAGINATION_PER_PAGE, href=link)
    return render_template('admin/ur_transactions/ur_transactions_history.html', **locals())


def h_bck_control_specific_ut(u_id: int):
    # default date range conditions
    url_date_from = request.args.get('date_from', '', type=str)
    url_date_to = request.args.get('date_to', '', type=str)
    date_from = datetime.strptime(url_date_from, '%d.%m.%Y').strftime('%Y-%m-%d') if url_date_from\
        else settings.Transactions.DEFAULT_DATE_FROM
    date_to = (datetime.strptime(url_date_to, '%d.%m.%Y') + timedelta(days=1)).strftime(
        '%Y-%m-%d') if url_date_to else datetime.now().strftime('%Y-%m-%d')

    sort_type = request.args.get('sort_type', 'desc', str)

    is_at2, agent_id, agent_email, client_email, client_balance = helper_get_user_at2_opt2(u_id=u_id)

    pa_detalize_list, sum_fill, sum_spend = helper_get_transactions(u_id=u_id, date_from=date_from,
                                                                    date_to=date_to, sort_type=sort_type)

    transaction_dict = settings.Transactions.TRANSACTIONS

    link = f'javascript:bck_get_transactions_specific_user(\'' + url_for(
        'admin_control.su_bck_control_specific_ut', u_id=u_id) + f'?bck=1&' + 'page={0}\');'
    page, per_page, \
        offset, pagination, \
        transactions_list = helper_paginate_data(data=pa_detalize_list, per_page=settings.PAGINATION_PER_PAGE,
                                                 href=link)
    return jsonify({'htmlresponse': render_template('admin/ur_transactions/ur_transactions_table.html', **locals())})


def h_su_fin_order_report():
    date_from = datetime.now() - timedelta(settings.ORDERS_REPORT_TIMEDELTA)
    date_to = datetime.now()
    stmt = helper_get_stmt_for_fin_order_report()
    orders = db.session.execute(stmt, ).fetchall()
    link = f'javascript:bck_get_fin_order_report(\'' + url_for(
        'admin_control.su_bck_fin_order_report') + f'?bck=1' + '&page={0}\');'
    page, per_page, \
        offset, pagination, \
        orders_list = helper_paginate_data(data=orders, per_page=settings.PAGINATION_PER_PAGE, href=link)
    return render_template('admin/fin_order_report/su_order_report.html', **locals())


def h_bck_fin_order_report():
    date_from, date_to, sort_type, order_type, payment_status = helper_get_filter_fin_order_report()
    stmt = helper_get_stmt_for_fin_order_report(
        date_from=date_from,
        date_to=date_to,
        sort_type=sort_type,
        order_type=order_type,
        payment_status=payment_status,
    )
    orders = db.session.execute(stmt,).fetchall()
    link = f'javascript:bck_get_fin_order_report(\'' + url_for(
        'admin_control.su_bck_fin_order_report') + f'?bck=1' + '&page={0}\');'
    page, per_page, \
        offset, pagination, \
        orders_list = helper_paginate_data(data=orders, per_page=settings.PAGINATION_PER_PAGE, href=link)
    return jsonify({'htmlresponse': render_template(f'admin/fin_order_report/su_order_table.html', **locals())})


def h_bck_fin_order_report_excel():
    date_from, date_to, sort_type, order_type, payment_status = helper_get_filter_fin_order_report(report=True)
    stmt = helper_get_stmt_for_fin_order_report(
        order_type=order_type,
        sort_type=sort_type,
        date_from=date_from,
        date_to=date_to,
        payment_status=payment_status
    )
    orders = db.session.execute(stmt).fetchall()
    # convert payment_status and order_type to readable filter
    order_type = 'отменен' if order_type == (settings.OrderStage.CANCELLED,) else 'отправлен'

    if payment_status == (True,):
        payment_status = 'оплачен'
    elif payment_status == (False,):
        payment_status = 'ожидает оплаты'
    else:
        payment_status = 'оплачен или ожидает оплаты'

    excel_filters = {
        'дата начала': date_from,
        'дата окончания': (datetime.strptime(date_to, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d'),
        'статус заказа': order_type,
    }

    if order_type == 'отправлен':
        excel_filters['статус платежа'] = payment_status

    if order_type == 'отменен':
        report_name = f'отмененные заказы({datetime.today().strftime("%d.%m.%y %H-%M")})'
    else:
        report_name = f'отправленные заказы({datetime.today().strftime("%d.%m.%y %H-%M")})'
    excel = ExcelReport(
        data=orders,
        filters=excel_filters,
        columns_name=['дата', 'номер заказа', 'компания', 'тел. номер клиента', 'агент', 'КМ', 'КС', 'Чего', 'Цена за марку',],
        sheet_name='Отчет по заказам',
        output_file_name=report_name,
    )

    excel_io = excel.create_report()
    content = excel_io.getvalue()
    response = make_response(content)
    response.headers['data_file_name'] = urllib.parse.quote(excel.output_file_name)
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['data_status'] = 'success'

    return response


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
                     WHERE o.payment !=True AND o.processed != True AND o.stage >= {settings.OrderStage.NEW} AND o.stage != {settings.OrderStage.CANCELLED}  AND o.to_delete != True;
                      """
    user_ids = db.session.execute(text(user_ids_stmt)).fetchall()
    if user_ids:
        status, server_balance = helper_perform_ut_wo_mod(user_ids=user_ids)
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
    if user:
        send_tg_message_with_transaction_updated_status(user.id, t_id)

    return jsonify(dict(status=status, message=message))


def _h_isolated_session():

    plain_engine = create_engine(settings.SQL_DATABASE_URL)

    with Session(bind=plain_engine) as session:
        session.connection(execution_options={"isolation_level": "SERIALIZABLE"})
        # making queries session
        ...
