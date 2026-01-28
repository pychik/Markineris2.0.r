import urllib
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal, InvalidOperation
from flask import flash, redirect, render_template, url_for, request, Response, jsonify, make_response
from flask_login import current_user
from sqlalchemy import case, desc, text, create_engine, null, select, or_, not_, exists
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from config import settings
from logger import logger
from models import (
    db,
    Promo,
    Price,
    ServiceAccount,
    ServerParam,
    User,
    UserTransaction,
    Bonus,
    TransactionStatuses,
    TransactionTypes,
    TransactionOperations
)
from utilities.admin.excel_report import ExcelReportProcessor, ExcelReport, ExcelReportWithSheets
from utilities.exceptions import UserNotFoundError, NegativeBalanceError, BalanceUpdateError
from utilities.minio_service.services import get_s3_service
from utilities.support import (
    helper_paginate_data,
    check_file_extension,
    get_file_extension,
    helper_get_server_balance,
    helper_get_filters_transactions,
    helper_update_pending_rf_transaction_status,
    helper_get_image_html,
    helper_perform_ut_wo_mod,
    helper_get_transaction_orders_detail,
    helper_get_stmt_for_fin_order_report,
    helper_get_filter_fin_order_report,
    helper_get_stmt_for_fin_promo_history,
    helper_get_filter_fin_promo_history,
    helper_get_filter_fin_bonus_history,
    helper_get_stmt_for_fin_bonus_history,
    helper_get_transactions,
    helper_get_user_at2_opt2,
    helper_get_promo_on_cancel_transaction,
    TransactionFilters,
    create_bill_path, helper_paginate_sql_with_window,
)
from utilities.tg_verify.service import send_tg_message_with_transaction_updated_status
from validators.admin_control import UpdateBalanceSchema


class NotFoundBonusCode(Exception):
    """ Бонус код не найден. """


def h_su_control_finance():
    def _get_stats_refill():
        # НОВОЕ: суммы за сегодняшний день по нужным статусам/типам
        today_tx_stmt = text("""
                SELECT
                    COALESCE(SUM(CASE
                        WHEN ut.transaction_type = :refill_type
                         AND ut.type = TRUE
                         AND ut.status = :st_success
                         AND ut.created_at >= DATE_TRUNC('day', NOW()::timestamp)
                        THEN ut.amount ELSE 0 END
                    ), 0) AS refill_success_sum,

                    COALESCE(SUM(CASE
                        WHEN ut.transaction_type = :refill_type
                         AND ut.type = TRUE
                         AND ut.status = :st_pending
                         AND ut.created_at >= DATE_TRUNC('day', NOW()::timestamp)
                        THEN ut.amount ELSE 0 END
                    ), 0) AS refill_pending_sum,

                    COALESCE(SUM(CASE
                        WHEN ut.transaction_type = :refill_type
                         AND ut.type = TRUE
                         AND ut.status = :st_cancelled
                         AND ut.created_at >= DATE_TRUNC('day', NOW()::timestamp)
                        THEN ut.amount ELSE 0 END
                    ), 0) AS refill_cancelled_sum,

                    COALESCE(SUM(CASE
                        WHEN ut.transaction_type = :promo_type
                         AND ut.status = :st_success
                         AND ut.created_at >= DATE_TRUNC('day', NOW()::timestamp)
                        THEN ut.amount ELSE 0 END
                    ), 0) AS promo_success_sum
                FROM public.user_transactions ut
            """)

        today_tx = db.session.execute(
            today_tx_stmt,
            {
                "refill_type": TransactionTypes.refill_balance.value,
                "promo_type": TransactionTypes.promo.value,
                "st_success": TransactionStatuses.success.value,
                "st_pending": TransactionStatuses.pending.value,
                "st_cancelled": TransactionStatuses.cancelled.value,
            }
        ).first()

        return today_tx

    today_date = datetime.today()
    stat_date = today_date - timedelta(days=1)

    stat_paid_stmt = text("""WITH mark_count as (SELECT os.transaction_id, count(os.id) as total_orders, sum(os.marks_count) as total_marks from public.orders_stats os GROUP BY os.transaction_id)
                            SELECT 
                                coalesce(sum(mc.total_orders), 0) as total_orders,
                                round(coalesce(sum(ut.amount), 0), 2) as amount, 
                                coalesce(sum(mc.total_marks), 0) as marks_cnt, 
                                round(case when coalesce(sum(mc.total_marks), 0) = 0 then 0 else coalesce(sum(amount), 0) / coalesce(sum(mc.total_marks), 0) end, 2) as avg_price
                            FROM public.user_transactions ut
                            JOIN mark_count mc on ut.id = mc.transaction_id
                            WHERE
                                ut.op_cost is not null and ut.type=False
                                and ut.created_at >= DATE_TRUNC('DAY', NOW()::timestamp);
                            """)

    stat_proc_stmt = text("""WITH filtered_orders AS (
                        SELECT 
                            o.transaction_id AS transaction_id, 
                            COUNT(o.id) AS orders_proc 
                        FROM public.orders o 
                        WHERE o.stage >= 8 
                          AND o.stage != 9 
                          AND o.sent_at >= DATE_TRUNC('DAY', NOW() - INTERVAL '1 DAY')  -- Выполненные заказы за вчера
                          AND o.sent_at < DATE_TRUNC('DAY', NOW())  -- До начала текущего дня
                        GROUP BY o.transaction_id
                    )
                    SELECT 
                        COALESCE(SUM(fo.orders_proc), 0) AS total_orders_proc
                    FROM filtered_orders fo;
                    """)
    stat_paid = db.session.execute(stat_paid_stmt).first()
    stat_proc = db.session.execute(stat_proc_stmt).first()

    today_tx = _get_stats_refill()
    refill_success_sum = today_tx.refill_success_sum
    refill_pending_sum = today_tx.refill_pending_sum
    refill_cancelled_sum = today_tx.refill_cancelled_sum
    promo_success_sum = today_tx.promo_success_sum

    promos = Promo.query.with_entities(Promo.id, Promo.code, Promo.value, Promo.created_at, Promo.updated_at).filter(
        or_(Promo.is_archived == False, Promo.is_archived == None)).order_by(desc(Promo.created_at)).all()
    bonuses = Bonus.query.with_entities(Bonus.id, Bonus.code, Bonus.value, Bonus.created_at, Bonus.updated_at).filter(
        or_(Bonus.is_archived == False, Bonus.is_archived == None)).order_by(desc(Bonus.created_at)).all()
    prices = Price.query.order_by(desc(Price.created_at)).all()

    account_type_db = ServerParam.query.with_entities(ServerParam.account_type).first()
    account_type = settings.ServiceAccounts.DEFAULT_QR_ACCOUNT_TYPE if not account_type_db else account_type_db.account_type
    service_accounts = ServiceAccount.query.filter(
        not_(ServiceAccount.is_archived.is_(True))).order_by(desc(ServiceAccount.created_at)).all()

    # rf- refill , wo write off
    balance, pending_balance_rf, summ_at1, summ_at2, summ_client = helper_get_server_balance()

    basic_prices = settings.Prices.BASIC_PRICES
    base_path = settings.DOWNLOAD_QA_BASIC
    sa_types = settings.ServiceAccounts.TYPES_DICT
    all_prices = Price.query.with_entities(Price.id, Price.price_code, Price.price_at2).order_by(
        desc(Price.created_at)).all()

    # paginated promo's
    link_promos = 'javascript:get_promos_history(\'' + url_for('admin_control.su_bck_promo') + '?page={0}\');'
    page, per_page, \
        offset, pagination, \
        promo_list = helper_paginate_data(data=promos, href=link_promos, per_page=settings.PAGINATION_PER_PROMOS)

    link_bonuses = 'javascript:get_bonuses_history(\'' + url_for('admin_control.su_bck_bonus') + '?page={0}\');'
    page, per_page, \
        offset, pagination, \
        bonuses_list = helper_paginate_data(data=bonuses, href=link_bonuses, per_page=settings.PAGINATION_PER_PROMOS)

    link_sa = 'javascript:get_sa_history(\'' + url_for('admin_control.su_bck_sa') + '?page={0}\');'
    page, per_page, \
        offset, pagination, \
        sa_list = helper_paginate_data(data=service_accounts, href=link_sa, per_page=settings.PAGINATION_PER_PROMOS)

    return render_template('admin/finance/su_finance_control.html', **locals())


def h_su_bck_promo(show_archived: bool = False):
    show_archived = request.args.get('show_archived', default=False, type=lambda v: v.lower() == 'true')
    if show_archived:
        filter_by = True
    else:
        filter_by = not_(Promo.is_archived.is_(True))

    promos = Promo.query.with_entities(Promo.id, Promo.code, Promo.value, Promo.created_at, Promo.is_archived, Promo.updated_at).filter(filter_by).order_by(
        desc(Promo.created_at)).all()

    link = 'javascript:get_promos_history(\'' + url_for('admin_control.su_bck_promo') + '?page={0}\');'
    page, per_page, \
        offset, pagination, \
        promo_list = helper_paginate_data(data=promos, href=link, per_page=settings.PAGINATION_PER_PROMOS)

    return jsonify({'htmlresponse': render_template(f'admin/finance/promos_table.html', **locals())})


def h_su_add_promo():
    code = request.form.get('promo_code', '').replace('--', '').strip()
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
    promo_stmt = select(Promo).filter(Promo.id == p_id)
    promo = db.session.execute(promo_stmt).scalar_one_or_none()
    status = 'danger'
    # check for trickers
    if not promo:
        message = settings.Messages.DELETE_NE_PROMO
        return jsonify(dict(status=status, message=message))
    try:
        promo.is_archived = True
        db.session.commit()

        message = f"{settings.Messages.DELETE_PROMO} {promo.code}"
        status = 'success'
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.DELETE_PROMO_ERROR} {e}"
        logger.error(message)

    return jsonify(dict(status=status, message=message))


def h_su_bck_bonus(show_archived: bool = False):
    show_archived = request.args.get('show_archived', default=False, type=lambda v: v.lower() == 'true')
    if show_archived:
        filter_by = True
    else:
        filter_by = not_(Bonus.is_archived.is_(True))

    bonuses = Bonus.query.with_entities(Bonus.id, Bonus.code, Bonus.value, Bonus.created_at, Bonus.is_archived,
                                       Bonus.updated_at).filter(filter_by).order_by(
        desc(Bonus.created_at)).all()

    link_bonuses = 'javascript:get_bonuses_history(\'' + url_for('admin_control.su_bck_bonus') + '?page={0}\');'
    page, per_page, \
        offset, pagination, \
        bonuses_list = helper_paginate_data(data=bonuses, href=link_bonuses, per_page=settings.PAGINATION_PER_PROMOS)

    return jsonify({'htmlresponse': render_template(f'admin/finance/bonuses_table.html', **locals())})


def h_su_add_bonus():
    code = request.form.get('bonus_code', '').replace('--', '')
    status = settings.ERROR
    try:
        value = int(request.form.get('bonus_value', '').replace('--', ''))
        bonus = Bonus(code=code, value=value)
        db.session.add(bonus)
        db.session.commit()
        message = f"{settings.Messages.BONUS_CREATE} {code} "
        status = settings.SUCCESS
    except ValueError as ve:
        db.session.rollback()
        message = f"{settings.Messages.BONUS_TYPE_ERROR}"
        logger.error(message + ' ' + str(ve))

    except IntegrityError as e:
        db.session.rollback()
        message = f"{settings.Messages.BONUS_DUPLICATE_ERROR} {code}" if "psycopg2.errors.UniqueViolation)" \
            in str(e) else f"{settings.Messages.BONUS_ERROR}{str(e)}"
        logger.error(message)

    return jsonify(dict(status=status, message=message))


def h_su_delete_bonus(b_id: int) -> Response:

    bonus_stmt = select(Bonus).filter(Bonus.id == b_id)
    bonus = db.session.execute(bonus_stmt).scalar_one_or_none()
    status = 'danger'
    # check for trickers
    if not bonus:
        message = settings.Messages.DELETE_NE_BONUS
        return jsonify(dict(status=status, message=message))
    try:
        bonus.is_archived = True
        # promo.updated_at = datetime.now()
        db.session.commit()

        message = f"{settings.Messages.DELETE_BONUS} {bonus.code}"
        status = settings.SUCCESS
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.DELETE_BONUS_ERROR} {e}"
        logger.error(message)

    return jsonify(dict(status=status, message=message))


def h_su_bck_prices():
    prices = Price.query.order_by(desc(Price.created_at)).all()
    basic_prices = settings.Prices.BASIC_PRICES
    all_prices = Price.query.with_entities(Price.id, Price.price_code, Price.price_at2).order_by(
        desc(Price.created_at)).all()
    base_path = settings.DOWNLOAD_DIR_SA_QR

    return jsonify({'htmlresponse': render_template(f'admin/finance/prices_table.html', **locals())})


def h_su_bck_specific_price(p_id):
    status = settings.ERROR
    basic_prices = settings.Prices.BASIC_PRICES
    price = Price.query.filter(Price.id == p_id).first()
    if price:
        status = settings.SUCCESS
    base_path = settings.DOWNLOAD_DIR_SA_QR

    return jsonify({'status': status, 'htmlresponse': render_template(f'admin/finance/edit_prices_modal.html', **locals())})


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
        price_6 = Decimal(request.form.get('price_6').replace('--', ''))
        price_7 = Decimal(request.form.get('price_7').replace('--', ''))
        price_8 = Decimal(request.form.get('price_8').replace('--', ''))
        price_9 = Decimal(request.form.get('price_9').replace('--', ''))
        price_10 = Decimal(request.form.get('price_10').replace('--', ''))
        price_11 = Decimal(request.form.get('price_11').replace('--', ''))
        price = Price(price_code=price_code, price_at2=price_at2,
                      price_1=price_1, price_2=price_2, price_3=price_3, price_4=price_4, price_5=price_5,
                      price_6=price_6, price_7=price_7, price_8=price_8, price_9=price_9, price_10=price_10,
                      price_11=price_11)

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
        user_update_stmt = text("""UPDATE public.users set price_id=NULL WHERE price_id=:p_id""").bindparams(p_id=p_id)
    else:
        # price_replace = Price.query.with_entities(Price.id).filter(Price.id == request.form.get('price_id', null(), int)).first()
        price_replace = Price.query.with_entities(Price.id).filter(Price.id == price_replace_id).first()

        replace_price_id = price_replace.id if price_replace else null()
        user_update_stmt = text(
            """UPDATE public.users set price_id=:replace_price_id WHERE price_id=:p_id""").bindparams(
            replace_price_id=replace_price_id,
            p_id=p_id
        )

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


def h_su_edit_price(p_id: int) -> Response:

    def _check_price_values(price_1: Decimal, price_2: Decimal, price_3: Decimal, price_4: Decimal, price_5: Decimal,
                            price_6: Decimal, price_7: Decimal, price_8: Decimal, price_9: Decimal, price_10: Decimal,
                            price_11: Decimal) -> bool:
        return (1 <= price_1 <= 2 * settings.Prices.F_LTE_100 and 1 <= price_2 <= 2 * settings.Prices.F_100_500
                and 1 <= price_3 <= 2 * settings.Prices.F_500_1K and 1 <= price_4 <= 2 * settings.Prices.F_1K_3K
                and 1 <= price_5 <= 2 * settings.Prices.F_3K_5K and 1 <= price_6 <= 2 * settings.Prices.F_5K_10K
                and 1 <= price_7 <= 2 * settings.Prices.F_10K_20K and 1 <= price_8 <= 2 * settings.Prices.F_20K_35K
                and 1 <= price_9 <= 2 * settings.Prices.F_35K_50K and 1 <= price_10 <= 2 * settings.Prices.F_50K_100K
                and 1 <= price_11 <= 2 * settings.Prices.F_100K)

    status = settings.ERROR
    try:
        p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11 = tuple(Decimal(request.form.get(f'price_{i}', '1')) for i in range(1, 12))

        if not _check_price_values(price_1=p1, price_2=p2, price_3=p3, price_4=p4, price_5=p5, price_6=p6, price_7=p7,
                                   price_8=p8, price_9=p9, price_10=p10, price_11=p11):
            raise InvalidOperation
    except InvalidOperation as ie:
        message = settings.Messages.EDIT_PRICE_ERROR
        logger.error(message + str(ie))
        return jsonify(dict(status=status, message=message))

    price = Price.query.filter(Price.id == p_id).first()

    status = settings.ERROR
    # check for trickers
    if not price:
        message = settings.Messages.DELETE_NE_PRICE
        return jsonify(dict(status=status, message=message))

    try:
        price.price_1 = p1
        price.price_2 = p2
        price.price_3 = p3
        price.price_4 = p4
        price.price_5 = p5
        price.price_6 = p6
        price.price_7 = p7
        price.price_8 = p8
        price.price_9 = p9
        price.price_10 = p10
        price.price_11 = p11

        db.session.commit()

        status = settings.SUCCESS
        message = settings.Messages.EDIT_PRICE.format(price_code=price.price_code)
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.DELETE_PRICE_ERROR} {e}"
        logger.error(message)

    return jsonify(dict(status=status, message=message))


def h_su_bck_sa(show_archived: bool = False):
    show_archived = request.args.get('show_archived', default=False, type=lambda v: v.lower() == 'true')

    if show_archived:
        filter_by = ServiceAccount.is_archived.is_(True)
    else:
        filter_by = not_(ServiceAccount.is_archived.is_(True))

    service_accounts = ServiceAccount.query.filter(filter_by).order_by(desc(ServiceAccount.created_at)).all()

    link_sa = 'javascript:get_sa_history(\'' + url_for('admin_control.su_bck_sa') + '?page={0}\');'
    page, per_page, \
        offset, pagination, \
        sa_list = helper_paginate_data(data=service_accounts, href=link_sa, per_page=settings.PAGINATION_PER_PROMOS)

    base_path = settings.DOWNLOAD_QA_BASIC
    sa_types = settings.ServiceAccounts.TYPES_DICT

    return jsonify({'htmlresponse': render_template(f'admin/finance/sa_table.html', **locals())})


def h_su_add_sa():
    status = settings.ERROR

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
        outer_payment_reqs = None

        if sa_type == settings.ServiceAccounts.TYPES_KEYS[0]:  # qr_code
            # QR service_account
            sa_qr_file = request.files.get('sa_qr_file')
            # check file
            if sa_qr_file is None or sa_qr_file is False or check_file_extension(filename=sa_qr_file.filename,
                                                                                 extensions=settings.ALLOWED_IMG_EXTENSIONS) is False:
                message = settings.Messages.SA_TYPE_FILE_ERROR
                return jsonify(dict(status=status, message=message))
            sa_extension = get_file_extension(filename=sa_qr_file.filename)
            sa_qr_path = f'img_{sa_name}.{sa_extension}'
            # save file
            try:
                s3_service = get_s3_service()
                s3_service.upload_file(
                    object_name=f"{settings.DOWNLOAD_QA_BASIC}{sa_qr_path}",
                    bucket_name="static",
                    file_data=sa_qr_file.stream,
                )
            except Exception as e:
                logger.exception("Ошибка сохранении qr кода в s3")
                message = settings.Messages.SA_TYPE_FILE_ERROR
                return jsonify(dict(status=status, message=message))
        elif sa_type == settings.ServiceAccounts.TYPES_KEYS[1]:  # requisites
            # Requisites service_account
            sa_reqs = request.form.get('sa_req', '').replace('--', '')
        elif sa_type == 'external_payment':  # external_payment
            # External payment service_account
            outer_payment_reqs = request.form.get('outer_payment_req', '').replace('--', '')

        # Validation for required fields based on type
        if sa_type == 'qr_code' and not sa_qr_path:
            raise ValueError
        if sa_type == 'requisites' and not sa_reqs:
            raise ValueError
        if sa_type == 'external_payment' and not outer_payment_reqs:
            raise ValueError

        # Create a new service account entry
        sa_new = ServiceAccount(
            sa_name=sa_name,
            sa_type=sa_type,
            sa_qr_path=sa_qr_path,
            sa_reqs=sa_reqs or outer_payment_reqs
        )

        db.session.add(sa_new)
        db.session.commit()
        message = f"{settings.Messages.SA_CREATE} {sa_name} {sa_type}"
        status = settings.SUCCESS

    except ValueError:
        db.session.rollback()
        message = f"{settings.Messages.SA_TYPE_ERROR}"
        logger.error(message)

    except IntegrityError as e:
        db.session.rollback()
        message = f"{settings.Messages.SA_DUPLICATE_ERROR} {sa_name}" if "psycopg2.errors.UniqueViolation)" in str(e) \
            else f"{settings.Messages.SA_ERROR}{str(e)}"
        logger.error(message)

    return jsonify(dict(status=status, message=message))


def h_su_delete_sa(sa_id: int) -> Response:
    account = ServiceAccount.query.filter(
        ServiceAccount.id == sa_id
    ).first()
    status = 'danger'

    # check for trickers
    if not account:
        message = settings.Messages.DELETE_NE_SA
        return jsonify(dict(status=status, message=message))
    try:
        transactions = db.session.query(exists().where(UserTransaction.sa_id == account.id)).scalar()
        if transactions:
            account.is_archived = True
            account.is_active = False
            account.archived_at = datetime.now()
        else:
            s3_service = get_s3_service()
            try:
                qr_codes = s3_service.list_objects(bucket_name="static", prefix=f"{settings.DOWNLOAD_QA_BASIC}")
            except Exception:
                logger.exception("Ошибка при получении qr кодов из s3")
                qr_codes = []

            db.session.execute(db.delete(ServiceAccount).filter_by(id=sa_id))

            qr_code_key = f"{settings.DOWNLOAD_QA_BASIC}{account.sa_qr_path}"
            if account.sa_type == settings.ServiceAccounts.TYPES_KEYS[0] and qr_code_key in qr_codes:

                try:
                    s3_service.remove_object(object_name=qr_code_key, bucket_name="static")
                except Exception:
                    logger.exception("Ошибка при удалении qr кода из s3 хранилища")

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
    date_to = datetime.now()
    transaction_filters = helper_get_filters_transactions(transaction_type=TransactionTypes.refill_balance.value,
                                                          tr_status=TransactionStatuses.success.value
                                                          if request.args.get("service_account")
                                                          else TransactionStatuses.pending.value,
                                                          operation_type=TransactionOperations.refill.value)
    roles = (settings.SUPER_USER, settings.ADMIN_USER)
    transaction_types = settings.Transactions.TRANSACTION_TYPES
    operation_types = settings.Transactions.TRANSACTION_OPERATION_TYPES
    transaction_statuses = settings.Transactions.TRANSACTIONS
    # transaction_filters = TransactionFilters(
    #     status=TransactionStatuses.pending.value,
    #     transaction_type=TransactionTypes.refill_balance.value,
    #     operation_type=settings.Transactions.TRANSACTION_REFILL,
    #     date_from=date_to - timedelta(days=settings.Transactions.DEFAULT_DAYS_RANGE),
    #     date_to=date_to,
    # )

    users_filter = User.query.with_entities(User.id, User.login_name).filter(User.role.in_(roles)).all()
    transactions = UserTransaction.query.with_entities(
        UserTransaction.id,
        UserTransaction.amount,
        UserTransaction.promo_info,
        UserTransaction.type,
        UserTransaction.status,
        UserTransaction.created_at,
        UserTransaction.user_id,
        UserTransaction.transaction_type,
        UserTransaction.sa_id,
        User.login_name,
        User.email,
        ServiceAccount.sa_type,
        ServiceAccount.sa_name,
    ).join(
        User, User.id == UserTransaction.user_id,
    ).outerjoin(
        ServiceAccount, ServiceAccount.id == UserTransaction.sa_id,
    ).filter(
        UserTransaction.status == transaction_filters.status,
        UserTransaction.transaction_type == TransactionTypes.refill_balance.value,
        UserTransaction.type == bool(settings.Transactions.TRANSACTION_REFILL),
        UserTransaction.created_at >= transaction_filters.date_from,
        ServiceAccount.id == transaction_filters.service_account if transaction_filters.service_account else True,
    ).order_by(
        desc(UserTransaction.created_at),
    ).all()

    transaction_summ = sum(t.amount for t in transactions)

    sa_types = settings.ServiceAccounts.TYPES_DICT
    service_accounts = ServiceAccount.query.with_entities(
        ServiceAccount.id,
        ServiceAccount.sa_name,
    ).filter(
        ServiceAccount.is_archived.isnot(True),
    ).all()

    link_filters = transaction_filters.link_filters
    link = f'javascript:bck_get_transactions(\'' + url_for(
        'admin_control.su_bck_control_ut') + f'?bck=1&{link_filters}' + 'page={0}\');'

    page, per_page, offset, pagination, transactions_list = helper_paginate_data(
        data=transactions,
        per_page=settings.PAGINATION_PER_PAGE,
        href=link,
    )

    return render_template('admin/transactions/su_control_transactions.html', **locals())


def h_bck_control_ut():
    transaction_statuses = settings.Transactions.TRANSACTIONS
    transaction_types = settings.Transactions.TRANSACTION_TYPES
    operation_types = settings.Transactions.TRANSACTION_OPERATION_TYPES
    transaction_filters = helper_get_filters_transactions()

    transactions = UserTransaction.query.with_entities(
        UserTransaction.id,
        UserTransaction.amount,
        UserTransaction.promo_info,
        UserTransaction.transaction_type,
        UserTransaction.type,
        UserTransaction.status,
        UserTransaction.created_at,
        UserTransaction.user_id,
        UserTransaction.sa_id,
        User.login_name,
        User.email,
        ServiceAccount.sa_type,
        ServiceAccount.sa_name,
    ).join(
        User, User.id == UserTransaction.user_id,
    ).outerjoin(
        ServiceAccount, ServiceAccount.id == UserTransaction.sa_id,
    ).filter(
        *transaction_filters.model_conditions,
    ).order_by(
        transaction_filters.model_order_type,
    ).all()

    transaction_summ = sum(t.amount for t in transactions)
    service_accounts = ServiceAccount.query.with_entities(
        ServiceAccount.id,
        ServiceAccount.sa_name,
    ).filter(
        ServiceAccount.is_archived.isnot(True),
    ).all()

    link = (
            f'javascript:bck_get_transactions(\''
            + url_for('admin_control.su_bck_control_ut')
            + f'?bck=1&{transaction_filters.link_filters}'
            + 'page={0}\');'
    )

    page, per_page, \
        offset, pagination, \
        transactions_list = helper_paginate_data(data=transactions, per_page=settings.PAGINATION_PER_PAGE, href=link)

    return jsonify({
        'htmlresponse': render_template(f'admin/transactions/su_transactions_table.html', **locals()),
    })


def h_au_bck_control_ut():
    """
       background update of agent users transactions  write_off for agent commission counter
    :return:
    """
    transaction_types = settings.Transactions.TRANSACTION_TYPES
    transaction_statuses = settings.Transactions.TRANSACTIONS
    operation_types = settings.Transactions.TRANSACTION_OPERATION_TYPES

    user_ids = [uid.id for uid in User.query.filter(User.admin_parent_id == current_user.id).with_entities(User.id).all()]
    user_ids.append(current_user.id)

    is_at2 = current_user.is_at2

    # set manually type and status for render page case
    transaction_filters = helper_get_filters_transactions(
        tr_status=TransactionStatuses.success.value,
        current_user_id=current_user.id,
    )

    transactions = UserTransaction.query.with_entities(
        UserTransaction.id,
        UserTransaction.amount,
        case(
            (UserTransaction.transaction_type == TransactionTypes.agent_commission_cancel.value, 0),
            else_=UserTransaction.agent_fee
        ).label("agent_fee"),
        UserTransaction.promo_info,
        UserTransaction.type,
        UserTransaction.status,
        UserTransaction.created_at,
        UserTransaction.user_id,
        UserTransaction.transaction_type,
        UserTransaction.sa_id,
        User.login_name,
    ).join(
        User, User.id == UserTransaction.user_id,
    ).filter(
        UserTransaction.transaction_type.in_([
                TransactionTypes.order_payment.value,
                TransactionTypes.users_order_payment.value,
                TransactionTypes.agent_commission_cancel.value,
        ]),
        User.id.in_(user_ids),
        UserTransaction.agent_fee.is_not(None),
        *transaction_filters.model_conditions,
    ).order_by(
        transaction_filters.model_order_type,
    ).all()

    link = f'javascript:bck_get_transactions(\'' + url_for(
        'admin_control.au_bck_control_ut') + f'?bck=1&{transaction_filters.link_filters}' + 'page={0}\');'

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
    transaction_filters = helper_get_filters_transactions(report=True)

    transactions = UserTransaction.query.with_entities(
        UserTransaction.id,
        UserTransaction.amount,
        UserTransaction.promo_info,
        UserTransaction.transaction_type,
        UserTransaction.type,
        UserTransaction.status,
        UserTransaction.wo_account_info,
        UserTransaction.created_at,
        UserTransaction.user_id,
        UserTransaction.sa_id,
        User.login_name,
        User.email,
        ServiceAccount.sa_type,
        ServiceAccount.sa_name,
    ).join(
        User, User.id == UserTransaction.user_id,
    ).outerjoin(
        ServiceAccount, ServiceAccount.id == UserTransaction.sa_id,
    ).filter(
        *transaction_filters.model_conditions,
    ).order_by(
        transaction_filters.model_order_type,
    ).all()

    transaction_summ = sum(t.amount for t in transactions)

    name_start = (
        f"{settings.Transactions.TRANSACTIONS_OPERATION_TRANSLATE.get(transaction_filters.operation_type, 'All')}_"
        f"{settings.Transactions.TRANSACTIONS_STATUS_TRANSLATE.get(transaction_filters.status)}"
    )
    date_range = f"{transaction_filters.date_from.strftime('%d.%m.%Y')} - {transaction_filters.date_to.strftime('%d.%m.%Y')}".replace(' 00:00:00', '')
    excel_proc = ExcelReportProcessor(
        transactions=transactions,
        transaction_summ=transaction_summ,
        tr_status=settings.Transactions.TRANSACTIONS[transaction_filters.status],
        date_range=date_range,
    )

    excel_io = excel_proc.get_excel_report()

    response = make_response(excel_io.getvalue())
    response.headers['data_file_name'] = "{name_start} {date_range}.xlsx".format(name_start=name_start,
                                                                                 date_range=date_range)
    response.headers['Content-type'] = 'text/plain'

    # response.headers['Content-Type'] = 'application/octet-stream'
    response.headers['data_status'] = 'success'

    return response


def h_fin_codes_history(bonus_flag: bool = False):
    date_from = datetime.today() - timedelta(settings.PROMO_HISTORY_TIMEDELTA)
    date_to = datetime.today()
    if bonus_flag:
        bonus_stmt = select(Bonus.code)
        bonus_codes = db.session.execute(bonus_stmt).all()
        bonus_hist_stmt = helper_get_stmt_for_fin_bonus_history()
        bonus_codes_history = db.session.execute(bonus_hist_stmt).all()

        link = f'javascript:bck_get_fin_codes_history(\'' + url_for(
            'admin_control.su_bck_fin_bonus_history') + f'?bck=1' + '&page={0}\', \'bonus_codes_select\');'
        page, per_page, \
            offset, pagination, \
            bonus_codes_history = helper_paginate_data(data=bonus_codes_history, per_page=settings.PAGINATION_PER_PAGE,
                                                       href=link)
        return render_template('admin/finance/fin_bonus_history/main.html', **locals())
    else:
        promo_stmt = select(Promo.code)
        promo_codes = db.session.execute(promo_stmt).all()
        promo_hist_stmt = helper_get_stmt_for_fin_promo_history()
        promo_codes_history = db.session.execute(promo_hist_stmt).all()

        link = f'javascript:bck_get_fin_codes_history(\'' + url_for(
            'admin_control.su_bck_fin_promo_history') + f'?bck=1' + '&page={0}\', \'promo_codes_select\');'
        page, per_page, \
            offset, pagination, \
            promo_codes_history = helper_paginate_data(data=promo_codes_history, per_page=settings.PAGINATION_PER_PAGE, href=link)
        return render_template('admin/finance/fin_promo_history/main.html', **locals())


def h_bck_fin_codes_history(bonus_flag: bool = False):
    if bonus_flag:
        date_from, date_to, bonus_code, sort_type = helper_get_filter_fin_bonus_history()
        stmt = helper_get_stmt_for_fin_bonus_history(
            date_from=date_from,
            date_to=date_to,
            sort_type=sort_type,
            bonus_code=bonus_code,
        )
        bonus_codes_history = db.session.execute(stmt, ).fetchall()
        link = f'javascript:bck_get_fin_codes_history(\'' + url_for(
            'admin_control.su_bck_fin_bonus_history') + f'?bck=1' + '&page={0}\', \'bonus_codes_select\');'
        page, per_page, \
            offset, pagination, \
            bonus_codes_history = helper_paginate_data(data=bonus_codes_history, per_page=settings.PAGINATION_PER_PAGE,
                                                       href=link)
        return jsonify({'htmlresponse': render_template(f'admin/finance/fin_bonus_history/table.html', **locals())})
    else:
        date_from, date_to, promo_code, sort_type = helper_get_filter_fin_promo_history()
        stmt = helper_get_stmt_for_fin_promo_history(
            date_from=date_from,
            date_to=date_to,
            sort_type=sort_type,
            promo_code=promo_code,
        )
        promo_codes_history = db.session.execute(stmt, ).fetchall()
        link = f'javascript:bck_get_fin_codes_history(\'' + url_for(
            'admin_control.su_bck_fin_promo_history') + f'?bck=1' + '&page={0}\', \'promo_codes_select\');'
        page, per_page, \
            offset, pagination, \
            promo_codes_history = helper_paginate_data(data=promo_codes_history, per_page=settings.PAGINATION_PER_PAGE, href=link)
        return jsonify({'htmlresponse': render_template(f'admin/finance/fin_promo_history/table.html', **locals())})


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
        columns_name=['дата активации', 'e-mail пользователя', 'логин агента', 'промокод', 'добавочное значение, руб'],
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


def h_bck_fin_bonus_history_excel():
    date_from, date_to, bonus_code, sort_type = helper_get_filter_fin_bonus_history(report=True)
    stmt = helper_get_stmt_for_fin_bonus_history(
        date_from=date_from,
        date_to=date_to,
        sort_type=sort_type,
        bonus_code=bonus_code,
    )
    bonus_codes_history = db.session.execute(stmt, ).fetchall()

    excel_filters = {
        'дата начала': date_from,
        'дата окончания': (datetime.strptime(date_to, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d'),
    }
    if bonus_code:
        excel_filters['бонускод'] = bonus_code
    report_name = f'история бонускодов({datetime.today().strftime("%d.%m.%y %H-%M")})'

    excel = ExcelReport(
        data=bonus_codes_history,
        filters=excel_filters,
        columns_name=['дата активации', 'e-mail пользователя', 'логин агента', 'бонускод', 'добавочное значение, руб'],
        sheet_name='История бонускодов',
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
    url_date_to_raw = datetime.now() + timedelta(1)
    url_date_to = url_date_to_raw.strftime('%d.%m.%Y')
    url_date_from = (url_date_to_raw - timedelta(days=settings.Transactions.DEFAULT_DAYS_RANGE)).strftime('%d.%m.%Y')
    date_to = url_date_to_raw.strftime('%Y-%m-%d')
    date_from = (url_date_to_raw - timedelta(days=settings.Transactions.DEFAULT_DAYS_RANGE)).strftime('%Y-%m-%d')

    user_info = helper_get_user_at2_opt2(u_id=u_id)
    if not user_info:
        flash(message=settings.Messages.STRANGE_REQUESTS, category='error')
        return redirect(url_for('main.index'))

    is_at2, agent_id, agent_email, client_email, client_balance = user_info

    pa_detalize_list, sum_fill, sum_spend = helper_get_transactions(u_id=u_id, date_from=date_from, date_to=date_to, sort_type='desc')
    link = f'javascript:get_transaction_history(\'' + url_for(f'user_cp.bck_update_transactions',
                                                              u_id=u_id) + '?page={0}\');'

    transaction_statuses = settings.Transactions.TRANSACTIONS
    transaction_types = settings.Transactions.TRANSACTION_TYPES

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

    sort_type = 'desc' if request.args.get('sort_type', 'desc', str).lower() == 'desc' else 'asc'
    transaction_types = settings.Transactions.TRANSACTION_TYPES
    transaction_statuses = settings.Transactions.TRANSACTIONS

    user_info = helper_get_user_at2_opt2(u_id=u_id)
    if not user_info:
        return jsonify({'htmlresponse': render_template('admin/ur_transactions/ur_transactions_table.html', **locals()),
                        'status': 'error', 'message': settings.Messages.STRANGE_REQUESTS})
    is_at2, agent_id, agent_email, client_email, client_balance = user_info

    pa_detalize_list, sum_fill, sum_spend = helper_get_transactions(u_id=u_id, date_from=date_from,
                                                                    date_to=date_to, sort_type=sort_type)

    transaction_dict = settings.Transactions.TRANSACTIONS

    link = f'javascript:bck_get_transactions_specific_user(\'' + url_for(
        'admin_control.su_bck_control_specific_ut', u_id=u_id) + f'?bck=1&' + 'page={0}\');'
    page, per_page, \
        offset, pagination, \
        transactions_list = helper_paginate_data(data=pa_detalize_list, per_page=settings.PAGINATION_PER_PAGE,
                                               href=link)

    return jsonify({'htmlresponse': render_template('admin/ur_transactions/ur_transactions_table.html', **locals()),
                    'status': settings.SUCCESS})


def h_su_fin_order_report():
    date_from = datetime.now() - timedelta(settings.ORDERS_REPORT_TIMEDELTA)
    date_to = datetime.now()
    stmt = helper_get_stmt_for_fin_order_report()

    link = f'javascript:bck_get_fin_order_report(\'' + url_for(
        'admin_control.su_bck_fin_order_report') + f'?bck=1' + '&page={0}\');'
    page, per_page, offset, pagination, orders_list = helper_paginate_sql_with_window(
        stmt,
        per_page=settings.PAGINATION_PER_PAGE,
        href=link,
    )
    return render_template('admin/finance/fin_order_report/su_order_report.html', **locals())


def h_bck_fin_order_report():
    date_from, date_to, sort_type, order_type, payment_status = helper_get_filter_fin_order_report()
    stmt = helper_get_stmt_for_fin_order_report(
        date_from=date_from,
        date_to=date_to,
        sort_type=sort_type,
        order_type=order_type,
        payment_status=payment_status,
    )

    link = f'javascript:bck_get_fin_order_report(\'' + url_for(
        'admin_control.su_bck_fin_order_report') + f'?bck=1' + '&page={0}\');'
    page, per_page, offset, pagination, orders_list = helper_paginate_sql_with_window(
        stmt,
        per_page=settings.PAGINATION_PER_PAGE,
        href=link,
    )
    return jsonify({'htmlresponse': render_template(f'admin/finance/fin_order_report/su_order_table.html', **locals())})


def h_su_fin_marks_count_report() -> Response:
    date_till = datetime.now().replace(day=1)
    date_from = date_till - relativedelta(months=3)

    stmt = text("""SELECT
                        ROW_NUMBER() OVER (
                            PARTITION BY
                                ORDER_MOUNTH
                            ORDER BY
                                MARKS_COUNT DESC
                        ) as "ROW NUMBER",
                        T.*
                    FROM
                        (
                            SELECT
                                DATE_TRUNC('month', OS.CREATED_AT) AS ORDER_MOUNTH,
                                U.LOGIN_NAME AS USER_LOGIN,
                                U.EMAIL AS USER_EMAIL,
                                U_AGENT.LOGIN_NAME AS USER_AGENT,
                                -- OS.COMPANY_TYPE AS COMPANY_TYPE,
                                SUM(OS.MARKS_COUNT) AS MARKS_COUNT
                            FROM
                                ORDERS_STATS OS
                                JOIN USER_TRANSACTIONS UT ON UT.ID = OS.TRANSACTION_ID
                                JOIN USERS U ON U.ID = OS.USER_ID
                                LEFT JOIN USERS U_AGENT ON U_AGENT.ID = U.ADMIN_PARENT_ID
                            WHERE
                                OS.OP_COST IS NOT NULL
                                AND OS.CREATED_AT >= :date_from
                                AND OS.CREATED_AT < :date_till
                            GROUP BY
                                DATE_TRUNC('month', OS.CREATED_AT),
                                U.LOGIN_NAME, U.EMAIL,
                                U_AGENT.LOGIN_NAME
                                -- COMPANY_TYPE
                            ORDER BY
                                USER_LOGIN, USER_EMAIL,
                                ORDER_MOUNTH
                        ) T
                        """).bindparams(date_from=date_from.strftime('%Y.%m.%d'), date_till=date_till.strftime('%Y.%m.%d'))
    report_data = db.session.execute(stmt).mappings().all()
    data_by_sheet: dict[str, list] = {}
    for rec in report_data:
        order_month = rec['order_mounth'].strftime('%m-%Y')

        if order_month in data_by_sheet:
            data_by_sheet[order_month].append((rec['ROW NUMBER'], rec['user_login'], rec['user_email'],
                                               rec['user_agent'], rec['marks_count']))
        else:
            data_by_sheet[order_month] = [(rec['ROW NUMBER'], rec['user_login'], rec['user_email'],
                                           rec['user_agent'], rec['marks_count'])]

    output_file_name = f'Отчет по количеству марок от {datetime.now().strftime("%d.%m.%Y")}.xlsx'

    excel = ExcelReportWithSheets(
        report_data=data_by_sheet,
        columns_name=['row number', 'user login', 'user_email', 'agent', 'marks quantity', ],
        output_file_name=output_file_name,
    )

    excel_io = excel.create_report()
    content = excel_io.getvalue()
    response = make_response(content)
    response.headers['data_file_name'] = urllib.parse.quote(excel.output_file_name)
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['data_status'] = 'success'
    return response


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
    transaction = UserTransaction.query.with_entities(
        UserTransaction.id,
        UserTransaction.type,
        UserTransaction.status,
        UserTransaction.amount,
        UserTransaction.op_cost,
        UserTransaction.bill_path,
        UserTransaction.user_id,
        UserTransaction.promo_info,
        UserTransaction.wo_account_info,
        UserTransaction.cancel_comment,
        UserTransaction.transaction_type,
        UserTransaction.sa_id,
        UserTransaction.created_at,
        UserTransaction.is_bonus,
        User.login_name,
        User.email,
        User.phone,
    ).join(
        User, User.id == UserTransaction.user_id,
    ).filter(
        UserTransaction.user_id == u_id,
        UserTransaction.id == t_id,
    ).first()

    transaction_statuses = settings.Transactions.TRANSACTIONS
    transaction_types = settings.Transactions.TRANSACTION_TYPES
    transaction_type_enum = TransactionTypes
    sa_types = settings.ServiceAccounts.TYPES_DICT

    if transaction.type and transaction.status in [TransactionStatuses.success.value, TransactionStatuses.pending.value,
                                                   TransactionStatuses.cancelled.value]:
        if not transaction.is_bonus and check_file_extension(transaction.bill_path, settings.ALLOWED_BILL_EXTENSIONS):
            transaction_image = helper_get_image_html(img_path=transaction.bill_path)
        service_account = ServiceAccount.query.filter(ServiceAccount.id == transaction.sa_id).first()

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

    transaction = UserTransaction.query.with_entities(
        UserTransaction.id,
        UserTransaction.type,
        UserTransaction.status,
        UserTransaction.amount,
        UserTransaction.op_cost,
        UserTransaction.bill_path,
        UserTransaction.user_id,
        UserTransaction.promo_info,
        UserTransaction.wo_account_info,
        UserTransaction.cancel_comment,
        UserTransaction.transaction_type,
        UserTransaction.sa_id,
        UserTransaction.created_at,
        UserTransaction.is_bonus,
        User.login_name,
        User.email,
        User.phone,
    ).join(
        User, User.id == UserTransaction.user_id,
    ).filter(
        UserTransaction.user_id == u_id,
        UserTransaction.id == t_id,
    ).first()

    transaction_statuses = settings.Transactions.TRANSACTIONS
    transaction_types = settings.Transactions.TRANSACTION_TYPES
    transaction_type_enum = TransactionTypes
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

    operation_type = request.form.get('operation_type', 0, int)
    tr_status = request.form.get('tr_status', 0, int)

    if operation_type not in [0, 1, ] and tr_status not in settings.Transactions.TRANSACTIONS.keys():
        return jsonify(dict(status=status, message=f"{message} ошибка ввода"))

    # check for tricksters
    transaction_updated = UserTransaction.query.with_entities(UserTransaction.id,
                                                              UserTransaction.amount,
                                                              UserTransaction.promo_info,
                                                              UserTransaction.status) \
        .filter(UserTransaction.user_id == u_id,
                UserTransaction.id == t_id,
                UserTransaction.status == TransactionStatuses.pending.value).first()
    user = User.query.with_entities(User.id).filter(User.id == u_id).first()

    if not user or not transaction_updated:
        return jsonify(dict(status=status, message=f"{message} нет такого пользователя или транзакции"))

    # remove cancelled transaction promo used
    if operation_type == 1 and tr_status == TransactionStatuses.cancelled.value and transaction_updated.promo_info:
        helper_get_promo_on_cancel_transaction(u_id=user.id, promo_info=transaction_updated.promo_info)

    process_transaction = helper_update_pending_rf_transaction_status(u_id=u_id, t_id=t_id,
                                                                      amount=transaction_updated.amount,
                                                                      operation_type=operation_type, tr_status=tr_status)
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


def h_get_list_of_bonus_code() -> Response:
    try:
        return jsonify(
            [bonus.to_dict() for bonus in Bonus.query.filter(
                or_(Bonus.is_archived.is_(False), Bonus.is_archived.is_(None)),
            )]
        )
    except Exception:
        logger.exception('Ошибка при получении списка бонус кодов')
        return jsonify([])


def h_get_detail_of_bonus_code(bonus_code_id: int) -> Bonus | None:
    try:
        bonus_code = Bonus.query.filter(
            Bonus.id == bonus_code_id,
            or_(Bonus.is_archived.is_(False), Bonus.is_archived.is_(None)),
        ).first()
        if not bonus_code:
            raise NotFoundBonusCode
        return jsonify(bonus_code.to_dict())
    except NotFoundBonusCode:
        return jsonify({"result": False, "message": "Not found"})
    except Exception:
        logger.exception('Ошибка при получении деталей бонус кода по ID')
        return jsonify({"result": False, "message": "Failed"})


def h_delete_bonus_code(bonus_code_id: int) -> bool:
    try:
        bonus_code = Bonus.query.filter_by(id=bonus_code_id).first()
        if not bonus_code:
            raise NotFoundBonusCode

        bonus_code.is_archived = True
        db.session.commit()
    except NotFoundBonusCode:
        return jsonify({"result": False, "message": "Not found"})
    except Exception:
        db.session.rollback()
        logger.exception('Ошибка при попытке удалить бонус код по ID')
        return jsonify({"result": False, "message": "Deletion failed"})

    return jsonify({"result": True, "message": "Success deleted"})


def update_user_balance(user_id: int, data: UpdateBalanceSchema):
    user = User.query.filter(User.id == user_id).first()

    if user is None:
        raise UserNotFoundError()

    update_sum = data.amount if data.operation_type else -data.amount

    if user.role == settings.ORD_USER:
        if user.balance + update_sum < 0:
            raise NegativeBalanceError()
    # промо-коррекция возможна только при пополнении
    is_promo_corr = bool(data.is_promo_correction) and bool(data.operation_type)

    # разрешаем промо-коррекцию только модераторам/админам (настройте роли как у вас принято)
    if is_promo_corr and current_user.role not in ['superuser', 'admin', 'moderator']:
        is_promo_corr = False
    try:
        server_params = ServerParam.query.first()
        if is_promo_corr:
            comment = (
                f'<b>{current_user.login_name}</b> добавил на баланс через промокод '
                f'<b>{settings.Transactions.PROMO_CORRECTION_CODE}</b> {data.amount} руб.'
            )
            tx_type = TransactionTypes.promo.value
        else:
            comment = (
                f'<b>{current_user.login_name}</b> {"добавил на баланс" if data.operation_type else "списал с баланса"} '
                f'{data.amount}</b> руб.'
            )
            tx_type = TransactionTypes.technical.value

        if data.comment:
            comment += f'<br><b>Комментарий оператора:</b> {data.comment}'

        new_transaction = UserTransaction(
            type=data.operation_type,
            amount=data.amount,
            status=TransactionStatuses.success.value,
            transaction_type=tx_type,
            promo_info=comment,
            user_id=user.id,
            agent_fee=0,
            sa_id=None,
            bill_path=create_bill_path(filename=f"{current_user.login_name}.{user.login_name}.update_balance"),
        )

        user.balance += update_sum
        server_params.balance += update_sum

        db.session.add(new_transaction)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Ошибка при обновлении баланса пользователя")
        raise BalanceUpdateError()
