import json
import urllib
from decimal import Decimal
from datetime import date, timedelta, datetime

from flask import Blueprint, flash, render_template, redirect, url_for, request, make_response, jsonify
from flask_login import current_user, login_required
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from config import settings
from logger import logger
from models import User, Order, db
from utilities.admin.excel_report import ExcelReport
from utilities.support import (user_activated, su_required, susmu_required, susmumu_required, manager_exist_check,
                               helper_get_filter_avg_order_time_processing_report,
                               helper_get_stmt_avg_order_time_processing_report,
                               helper_get_stmt_operator_category_orders_report,
                               helper_get_stmt_daily_operator_category_orders_report,
                               helper_get_stmt_full_operator_metrics_report,
                               helper_paginate_data, sumsuu_required, moderator_exist_check, sql_count,
                               CRM_OPERATOR_REPORT_CATEGORY_COLUMNS,
                               DAILY_OPERATOR_ACTIVITY_REPORT_MAX_MONTHS,
                               FULL_OPERATOR_METRICS_REPORT_MAX_MONTHS)
from views.crm.helpers import (helper_clean_oco, check_manager_orders, helper_change_manager_limit, helper_get_limits,
                               helper_change_auto_order_pool, helper_change_auto_order_sent)

# crm user order control
crm_uoc = Blueprint('crm_uoc', __name__)


def _operator_report_manager_name(manager_id: int) -> str | None:
    if not manager_id:
        return None
    return User.query.with_entities(User.login_name).filter_by(id=manager_id).scalar()


def _operator_reports_filters(date_from: str, date_to: str, manager_id: int) -> dict:
    manager_name = _operator_report_manager_name(manager_id)
    filters = {
        'Дата C': date_from,
        'Дата По': (datetime.strptime(date_to, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d'),
    }
    if manager_name:
        filters['Оператор'] = manager_name
    return filters


def _crm_report_file_response(content: bytes, file_name: str, content_type: str):
    response = make_response(content)
    response.headers['data_file_name'] = urllib.parse.quote(file_name)
    response.headers['Content-Type'] = content_type
    response.headers['data_status'] = 'success'
    return response


def _crm_report_json_default(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def _crm_stage_name(stage: int) -> str:
    try:
        return settings.OrderStage.STAGES[stage][1]
    except Exception:
        return ''


def _crm_report_rows_to_dicts(records):
    result = []
    for rec in records:
        row = dict(rec._mapping)
        row['stage_name'] = _crm_stage_name(row.get('stage'))
        result.append(row)
    return result


def _xlsx_report_response(records, filters: dict, columns_name: list[str], output_file_name: str):
    excel = ExcelReport(
        data=records,
        filters=filters,
        columns_name=columns_name,
        output_file_name=output_file_name,
    )
    excel_io = excel.create_report()
    return _crm_report_file_response(
        content=excel_io.getvalue(),
        file_name=excel.output_file_name,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


@crm_uoc.route('/', methods=["GET"])
@login_required
@user_activated
@susmumu_required
def index():
    user = current_user
    workers_list = [w for w in User.query.filter(User.role.in_([settings.SUPER_MANAGER, settings.MANAGER_USER,
                                                                settings.MARKINERIS_ADMIN_USER]))
    .with_entities(User.id, User.status, User.role, User.login_name, User.email).order_by(User.id).all()]

    managers_list = list(filter(lambda x: x.role in [settings.SUPER_MANAGER, settings.MANAGER_USER], workers_list))
    moderators_list = list(filter(lambda x: x.role in [settings.MARKINERIS_ADMIN_USER], workers_list))

    dt_co = date.today() - timedelta(days=settings.OrderStage.DAYS_CONTENT)
    cancelled_orders = Order.query.with_entities(Order.id) \
        .filter(Order.stage == settings.OrderStage.CANCELLED, Order.cc_created < dt_co).count()

    # if managers_list:
    #     new_manager_name = managers_list[-1].login_name.split('_')[0] + '_' + str(
    #         int(managers_list[-1].login_name.split('_')[1]) + 1)
    if moderators_list:
        new_moderator_name = moderators_list[-1].login_name.split('_')[0] + '_' + str(
            int(moderators_list[-1].login_name.split('_')[1]) + 1)

    crm_defaults = helper_get_limits()
    limits_defaults = settings.OrderStage.PS_DICT
    return render_template('crm_mod_v1/crm_uoc.html', **locals())


@crm_uoc.route('/create_manager/', methods=['POST'])
@login_required
@user_activated
@susmu_required
def create_manager():

    form_dict = request.form.to_dict()
    login_name = 'manager_' + form_dict.get("manager_login_name", '1')
    password = form_dict.get("manager_password")

    try:
        new_manager = User(admin_order_num=0, login_name=login_name, phone=settings.SU_PHONE,
                           email=login_name + settings.MANAGER_EMAIL_POSTFIX,
                           is_crm=True, is_send_excel=True,
                           password=generate_password_hash(password, method='sha256'),
                           role=settings.MANAGER_USER, client_code=settings.MU_PARTNER, status=True)

        db.session.add(new_manager)
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        message = f"{settings.Messages.MANAGER_CREATE_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)

        return redirect(url_for('crm_uoc.index'))

    return redirect(url_for('crm_uoc.index'))


@crm_uoc.route('/delete_manager/<int:u_id>', methods=['POST'])
@login_required
@susmu_required
@manager_exist_check
def delete_manager(u_id: int):
    user = User.query.filter_by(id=u_id).first()
    order_count = check_manager_orders(u_id=u_id)
    if order_count != 0:
        flash(message=f'{settings.Messages.DELETE_USER_ERROR} {settings.Messages.DELETE_MANAGER_ERROR} {order_count}',
              category='error')
        return redirect(url_for('crm_uoc.index'))

    try:
        user.telegram = []
        db.session.delete(user)
        db.session.commit()
        flash(message=f"{settings.Messages.DELETE_USER} {user.login_name}")
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.DELETE_USER_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)

    return redirect(url_for('crm_uoc.index'))


@crm_uoc.route('/activate_manager/<int:u_id>', methods=['POST'])
@login_required
@susmu_required
def activate_manager(u_id: int):
    user = User.query.filter_by(id=u_id).first()
    if not user:
        flash(message=f"{settings.Messages.ACTIVATED_USER_ERROR}", category='error')
        return redirect(url_for('main.index'))
    try:
        user.status = True
        db.session.commit()

        flash(message=f"{settings.Messages.ACTIVATED_USER} {user.login_name}")
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.ACTIVATED_USER_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)

    return redirect(url_for('crm_uoc.index'))


@crm_uoc.route('/set_supermanager/<int:u_id>', methods=['POST'])
@login_required
@su_required
def set_supermanager(u_id: int):
    user = User.query.filter_by(id=u_id).first()
    if not user:
        flash(message=f"{settings.Messages.NO_SUCH_USER}", category='error')
        return redirect(url_for('main.index'))
    try:
        user.role = settings.SUPER_MANAGER
        db.session.commit()

        flash(message=f"{settings.Messages.SUPERMANAGER_SET} {user.login_name}")
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.SUPERMANAGER_SET_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)

    return redirect(url_for('crm_uoc.index'))


@crm_uoc.route('/set_manager/<int:u_id>', methods=['POST'])
@login_required
@su_required
def set_manager(u_id: int):
    user = User.query.filter_by(id=u_id).first()
    if not user:
        flash(message=f"{settings.Messages.NO_SUCH_USER}", category='error')
        return redirect(url_for('main.index'))
    try:
        user.role = settings.MANAGER_USER
        db.session.commit()

        flash(message=f"{settings.Messages.MANAGER_SET} {user.login_name}")
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.MANAGER_SET_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)

    return redirect(url_for('crm_uoc.index'))


@crm_uoc.route('/deactivate_manager/<int:u_id>', methods=['POST'])
@login_required
@susmu_required
@manager_exist_check
def deactivate_manager(u_id: int):

    user = User.query.filter_by(id=u_id).first()
    try:
        user.status = False
        db.session.commit()
        flash(message=f"{settings.Messages.DEACTIVATED_USER} {user.login_name}")

    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.DEACTIVATED_USER_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)

    return redirect(url_for('crm_uoc.index'))


# clean old cancelled orders
@crm_uoc.route('/clean_oco', methods=['POST'])
@login_required
@su_required
def clean_oco():
    return helper_clean_oco()


@crm_uoc.route('/change_manager_limit/<string:limit_param>', methods=['POST'])
@login_required
@su_required
def change_manager_limit(limit_param: str):
    return helper_change_manager_limit(limit_param=limit_param)


@crm_uoc.route('/change_auto_order_pool', methods=['POST'])
@login_required
@su_required
def change_auto_order_pool():
    return helper_change_auto_order_pool()


@crm_uoc.route('/change_auto_order_sent', methods=['POST'])
@login_required
@su_required
def change_auto_order_sent():
    return helper_change_auto_order_sent()


@crm_uoc.route('/avg_order_processing_time_report', methods=['GET'])
@login_required
@sumsuu_required
def avg_order_processing_time_rpt():
    date_from = datetime.now() - timedelta(settings.ORDERS_REPORT_TIMEDELTA)
    date_to = datetime.now()
    category_columns = CRM_OPERATOR_REPORT_CATEGORY_COLUMNS
    managers = db.session.execute(
        text('select distinct id, login_name from users where id in (select manager_id from orders where manager_id is not null) order by login_name')).fetchall()
    stmt = helper_get_stmt_avg_order_time_processing_report()
    records = db.session.execute(stmt, ).fetchall()
    link = f"javascript:bck_crm_operator_report('avg_processing', '" + url_for(
        'crm_uoc.bck_avg_order_processing_time_rpt') + f"?bck=1&page={{0}}');"
    page, per_page, \
        offset, pagination, \
        records_list = helper_paginate_data(data=records, per_page=settings.PAGINATION_PER_PAGE, href=link)
    return render_template('crm_mod_v1/reports/avg_order_processing_time/main.html', **locals())


@crm_uoc.route('/bck_avg_order_processing_time_report', methods=['GET'])
@login_required
@sumsuu_required
def bck_avg_order_processing_time_rpt():
    try:
        date_from, date_to, manager_id = helper_get_filter_avg_order_time_processing_report()
    except ValueError as exc:
        return jsonify({'status': 'error', 'message': str(exc)}), 400

    stmt = helper_get_stmt_avg_order_time_processing_report(
        date_from=date_from,
        date_to=date_to,
        manager_id=manager_id,
    )
    records = db.session.execute(stmt).fetchall()
    link = f'javascript:bck_avg_order_processing_time_rpt(\'' + url_for(
        'crm_uoc.bck_avg_order_processing_time_rpt') + f'?bck=1' + '&page={0}\');'
    page, per_page, \
        offset, pagination, \
        records_list = helper_paginate_data(data=records, per_page=settings.PAGINATION_PER_PAGE, href=link, css_framework='foundation')
    return jsonify(
        {
            'htmlresponse': render_template(f'crm_mod_v1/reports/avg_order_processing_time/table.html', **locals())
        }
    )


@crm_uoc.route('/bck_operator_category_orders_report', methods=['GET'])
@login_required
@sumsuu_required
def bck_operator_category_orders_rpt():
    try:
        date_from, date_to, manager_id = helper_get_filter_avg_order_time_processing_report()
    except ValueError as exc:
        return jsonify({'status': 'error', 'message': str(exc)}), 400

    stmt = helper_get_stmt_operator_category_orders_report(
        date_from=date_from,
        date_to=date_to,
        manager_id=manager_id,
    )
    records = db.session.execute(stmt).fetchall()
    category_columns = CRM_OPERATOR_REPORT_CATEGORY_COLUMNS
    link = f"javascript:bck_crm_operator_report('operator_category', '" + url_for(
        'crm_uoc.bck_operator_category_orders_rpt') + f"?bck=1&page={{0}}');"
    page, per_page, \
        offset, pagination, \
        records_list = helper_paginate_data(data=records, per_page=settings.PAGINATION_PER_PAGE, href=link, css_framework='foundation')
    return jsonify(
        {
            'htmlresponse': render_template(f'crm_mod_v1/reports/avg_order_processing_time/operator_category_table.html', **locals())
        }
    )


@crm_uoc.route('/bck_daily_operator_category_orders_report', methods=['GET'])
@login_required
@sumsuu_required
def bck_daily_operator_category_orders_rpt():
    try:
        date_from, date_to, manager_id = helper_get_filter_avg_order_time_processing_report(
            max_months=DAILY_OPERATOR_ACTIVITY_REPORT_MAX_MONTHS,
        )
    except ValueError as exc:
        return jsonify({'status': 'error', 'message': str(exc)}), 400

    stmt = helper_get_stmt_daily_operator_category_orders_report(
        date_from=date_from,
        date_to=date_to,
        manager_id=manager_id,
    )
    records = db.session.execute(stmt).fetchall()
    category_columns = CRM_OPERATOR_REPORT_CATEGORY_COLUMNS
    manager_name = _operator_report_manager_name(manager_id)
    link = f"javascript:bck_crm_operator_report('daily_category', '" + url_for(
        'crm_uoc.bck_daily_operator_category_orders_rpt') + f"?bck=1&page={{0}}');"
    page, per_page, \
        offset, pagination, \
        records_list = helper_paginate_data(data=records, per_page=settings.PAGINATION_PER_PAGE, href=link, css_framework='foundation')
    return jsonify(
        {
            'htmlresponse': render_template(f'crm_mod_v1/reports/avg_order_processing_time/daily_category_table.html', **locals())
        }
    )


@crm_uoc.route('/avg_order_processing_time_report_excel', methods=['POST'])
@login_required
@sumsuu_required
def avg_order_processing_time_rpt_excel():
    try:
        date_from, date_to, manager_id = helper_get_filter_avg_order_time_processing_report(report=True)
    except ValueError as exc:
        return jsonify({'status': 'error', 'message': str(exc)}), 400

    stmt = helper_get_stmt_avg_order_time_processing_report(
        date_from=date_from,
        date_to=date_to,
        manager_id=manager_id,
    )
    records = db.session.execute(stmt).fetchall()
    filters = _operator_reports_filters(date_from, date_to, manager_id)
    output_file_name = f'Отчет среднему времени обработки заказов от {datetime.now().strftime("%d.%m.%Y")}'

    excel = ExcelReport(
        data=records,
        filters=filters,
        columns_name=[
            'login',
            'Кол-во заказов',
            'Кол-во строк',
            'Кол-во марок',
            'За 1 день',
            'За 2 дня',
            'За 3 дня',
            'За 4 дня',
            'Более 4 дней',
            'Среднее время выполнения заказа(мин)',
            'Среднее время выполнения заказа(часов)',
        ],
        output_file_name=output_file_name,
        condition_format={10: [{
            'type': 'cell',
            'criteria': '>',
            'value': 5,
            'format': {'bg_color': 'red'}
        }]}
    )

    excel_io = excel.create_report()
    return _crm_report_file_response(
        content=excel_io.getvalue(),
        file_name=excel.output_file_name,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


@crm_uoc.route('/operator_category_orders_report_excel', methods=['POST'])
@login_required
@sumsuu_required
def operator_category_orders_rpt_excel():
    try:
        date_from, date_to, manager_id = helper_get_filter_avg_order_time_processing_report(report=True)
    except ValueError as exc:
        return jsonify({'status': 'error', 'message': str(exc)}), 400

    stmt = helper_get_stmt_operator_category_orders_report(
        date_from=date_from,
        date_to=date_to,
        manager_id=manager_id,
    )
    records = db.session.execute(stmt).fetchall()
    columns_name = ['Оператор', 'Всего заказов'] + [column[2] for column in CRM_OPERATOR_REPORT_CATEGORY_COLUMNS]
    output_file_name = f'Отчет по заказам операторов по категориям от {datetime.now().strftime("%d.%m.%Y")}'
    return _xlsx_report_response(
        records=records,
        filters=_operator_reports_filters(date_from, date_to, manager_id),
        columns_name=columns_name,
        output_file_name=output_file_name,
    )


@crm_uoc.route('/daily_operator_category_orders_report_excel', methods=['POST'])
@login_required
@sumsuu_required
def daily_operator_category_orders_rpt_excel():
    try:
        date_from, date_to, manager_id = helper_get_filter_avg_order_time_processing_report(
            report=True,
            max_months=DAILY_OPERATOR_ACTIVITY_REPORT_MAX_MONTHS,
        )
    except ValueError as exc:
        return jsonify({'status': 'error', 'message': str(exc)}), 400

    stmt = helper_get_stmt_daily_operator_category_orders_report(
        date_from=date_from,
        date_to=date_to,
        manager_id=manager_id,
    )
    records = db.session.execute(stmt).fetchall()
    columns_name = ['Дата', 'Всего заказов'] + [column[2] for column in CRM_OPERATOR_REPORT_CATEGORY_COLUMNS]
    output_file_name = f'Отчет по взятым заказам по дням от {datetime.now().strftime("%d.%m.%Y")}'
    return _xlsx_report_response(
        records=records,
        filters=_operator_reports_filters(date_from, date_to, manager_id),
        columns_name=columns_name,
        output_file_name=output_file_name,
    )


@crm_uoc.route('/full_operator_metrics_report_file', methods=['POST'])
@login_required
@sumsuu_required
def full_operator_metrics_rpt_file():
    try:
        date_from, date_to, manager_id = helper_get_filter_avg_order_time_processing_report(
            report=True,
            max_months=FULL_OPERATOR_METRICS_REPORT_MAX_MONTHS,
        )
    except ValueError as exc:
        return jsonify({'status': 'error', 'message': str(exc)}), 400

    stmt = helper_get_stmt_full_operator_metrics_report(
        date_from=date_from,
        date_to=date_to,
        manager_id=manager_id,
    )
    records = db.session.execute(stmt).fetchall()
    payload = {
        'generated_at': datetime.now(),
        'filters': _operator_reports_filters(date_from, date_to, manager_id),
        'criteria': {
            'date_field_for_period': 'm_finished',
            'included_orders': 'orders with m_started >= date_from, m_finished < date_to + 1 day, m_finished is not null, stage is not cancelled',
            'daily_report_date_field': 'm_started',
        },
        'data': _crm_report_rows_to_dicts(records),
    }
    content = json.dumps(payload, ensure_ascii=False, default=_crm_report_json_default, indent=2).encode('utf-8')
    output_file_name = f'Полные метрики заказов операторов от {datetime.now().strftime("%d.%m.%Y")}.txt'
    return _crm_report_file_response(
        content=content,
        file_name=output_file_name,
        content_type='text/plain; charset=utf-8',
    )


@crm_uoc.route('/create_moderator/', methods=['POST'])
@login_required
@user_activated
@su_required
def create_moderator():

    form_dict = request.form.to_dict()
    login_name = form_dict.get("moderator_login_name")
    password = form_dict.get("moderator_password")
    if not login_name or not login_name.startswith('moderator_') or not password or len(password) < 6:
        flash(message=settings.Messages.STRANGE_REQUESTS, category='error')
        return redirect(url_for('crm_uoc.index'))

    try:
        new_moderator = User(admin_order_num=0, login_name=login_name, phone=settings.SU_PHONE,
                             email=login_name + settings.MANAGER_EMAIL_POSTFIX,
                             is_crm=False, is_send_excel=False, is_at2=False,
                             password=generate_password_hash(password, method='sha256'),
                             role=settings.MARKINERIS_ADMIN_USER, client_code=settings.MM_PARTNER, status=True)

        db.session.add(new_moderator)
        db.session.commit()
        flash(message=f"{settings.Messages.MODERATOR_CREATE_SUCCESS} {login_name + settings.MANAGER_EMAIL_POSTFIX}")
    except IntegrityError as e:
        db.session.rollback()
        message = f"{settings.Messages.MODERATOR_CREATE_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)

        return redirect(url_for('crm_uoc.index'))

    return redirect(url_for('crm_uoc.index'))


@crm_uoc.route('/delete_moderator/<int:u_id>', methods=['POST'])
@login_required
@su_required
@moderator_exist_check
def delete_moderator(u_id: int):
    # user = User.query.filter_by(id=u_id).first()

    try:
        removed_user = db.session.execute(text("DELETE FROM public.users WHERE id=:u_id returning public.users.login_name").bindparams(u_id=u_id)).fetchone().login_name
        # user.telegram = []
        # db.session.delete(user)
        db.session.commit()
        flash(message=f"{settings.Messages.DELETE_USER} {removed_user}")
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.DELETE_USER_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)

    return redirect(url_for('crm_uoc.index'))


@crm_uoc.route('/activate_moderator/<int:u_id>', methods=['POST'])
@login_required
@su_required
@moderator_exist_check
def activate_moderator(u_id: int):
    user = User.query.filter_by(id=u_id).first()

    try:
        user.status = True
        db.session.commit()

        flash(message=f"{settings.Messages.ACTIVATED_USER} {user.login_name}")
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.ACTIVATED_USER_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)

    return redirect(url_for('crm_uoc.index'))


@crm_uoc.route('/deactivate_moderator/<int:u_id>', methods=['POST'])
@login_required
@su_required
@moderator_exist_check
def deactivate_moderator(u_id: int):

    user = User.query.filter_by(id=u_id).first()
    try:
        user.status = False
        db.session.commit()
        flash(message=f"{settings.Messages.DEACTIVATED_USER} {user.login_name}")

    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.DEACTIVATED_USER_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)

    return redirect(url_for('crm_uoc.index'))
