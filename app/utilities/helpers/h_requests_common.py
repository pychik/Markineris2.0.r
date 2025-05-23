from typing import Union

from flask import flash, jsonify, redirect, render_template, request, Response, url_for
from flask_login import current_user

from config import settings
from logger import logger
from models import db, Telegram, Order
from utilities.check_idn import IdnGetter
from utilities.check_tnved import TnvedChecker
from utilities.support import check_file_extension, send_file_tg, \
    orders_list_common, helper_check_useroragent_balance, helper_check_uoabm, helper_check_user_order_in_archive


def h_get_company_data(u_id: int, from_category: str, idn: str) -> str:
    if u_id != current_user.id or from_category not in settings.CATEGORIES_PROCESS_NAMES:
        result_status = 0
        answer_list = []
    else:
        result_status, answer_list = IdnGetter.get_company(idn=idn)

    return f"{result_status};{';'.join(answer_list)}"


def h_process_idn_error(from_category: str, message: str) -> Response:
    if from_category not in settings.CATEGORIES_PROCESS_NAMES:
        flash(message=settings.Messages.STRANGE_REQUESTS, category='error')
        return redirect(url_for('main.enter'))
    if message == 'error_0':
        flash(message=settings.Messages.STRANGE_REQUESTS, category='error')
        return redirect(url_for('main.enter'))
    if message == 'error_1':
        flash(message=settings.Messages.AUTO_IDN_ERROR_CON, category='error')
        return redirect(url_for(f"{from_category}.index"))
    if message == 'error_2':
        flash(message=settings.Messages.AUTO_IDN_ERROR_DATA, category='error')
        redirect(url_for(f"{from_category}.index"))
        return redirect(url_for(f"{from_category}.index"))
    else:
        flash(message=settings.Messages.STRANGE_REQUESTS, category='error')
        return redirect(url_for('main.enter'))


def h_check_tnved_code_data(u_id: int, from_category: str, tnved_code: str) -> str:
    result_status = 0
    big_tnved_list_str = ''
    if u_id != current_user.id or from_category not in settings.CATEGORIES_PROCESS_NAMES :
        answer = settings.Messages.STRANGE_REQUESTS
    elif not tnved_code:
        answer = settings.Messages.TNVED_INPUT_ERROR_EMPTY
    else:
        tc = TnvedChecker(category=from_category, tnved_code=tnved_code)
        result_status, answer = tc.tnved_parse()
        big_tnved_list_str = ','.join(settings.Tnved.BIG_TNVED_DICT.get(from_category)[1])

    return f"{result_status};{answer};{big_tnved_list_str}"


def h_get_tg_user_data(tg_id: int) -> str:
    telegram_data = Telegram.query.filter_by(id=tg_id).first()
    result_status = 0
    if not telegram_data:
        answer = settings.Messages.TELEGRAM_REQUEST_ERROR
    else:
        result_status = 5
        answer = ','.join([u.login_name for u in telegram_data.users])
    return f"{result_status};{answer}"


def h_send_table() -> str:
    user = current_user
    send_table = True
    price_description = settings.PRICE_DESCRIPTION
    tnved_description = settings.TNVED_DESCRIPTION

    company_types = settings.COMPANY_TYPES
    edo_types = settings.EDO_TYPES
    tax_list = settings.TAX_LIST

    company_type = request.args.get("company_type")
    company_name = request.args.get("company_name")
    company_idn = request.args.get("company_idn")
    edo_type = request.args.get("edo_type")
    edo_id = request.args.get("edo_id")
    mark_type = request.args.get("mark_type")
    return render_template('upload/category_upper_part_send.html', **locals())


def h_send_table_order() -> Response:
    form_data_raw = request.form
    form_dict = form_data_raw.to_dict()
    company_type = form_dict.get("company_type")
    company_name = form_dict.get("company_name")
    company_idn = form_dict.get("company_idn")
    edo_type = form_dict.get("edo_type")
    edo_id = form_dict.get("edo_id")
    mark_type = form_dict.get("mark_type")

    table_file = request.files.get('table_upload')

    # print(not table_file, check_file_extension(filename=table_file.filename))
    if table_file is False or check_file_extension(filename=table_file.filename) is False:
        flash(message=settings.Messages.UPLOAD_FILE_EXTEXSION_ERROR, category='error')
        return redirect(url_for('requests_common.send_table', company_type=company_type, company_name=company_name,
                                    company_idn=company_idn, edo_type=edo_type, edo_id=edo_id, mark_type=mark_type))

    if not all([company_type, company_name, company_idn, edo_type, mark_type]):
        flash(message=f"{settings.Messages.SEND_FILE_EXTEXSION_ERROR}", category='error')
    else:
        try:
            user = current_user
            send_file_tg(user=user, company_idn=company_idn, company_type=company_type,
                         company_name=company_name, edo_type=edo_type, edo_id=edo_id,
                         mark_type=mark_type, table_file=table_file.read())
            return redirect(url_for('requests_common.send_table'))

        except Exception as e:
            message = f"{settings.Messages.SEND_FILE_EXTEXSION_ERROR} Ошибка: {e}"
            flash(message=message, category='error')
            logger.error(message)

    return redirect(url_for('requests_common.send_table', company_type=company_type, company_name=company_name,
                            company_idn=company_idn, edo_type=edo_type, edo_id=edo_id, mark_type=mark_type))


def h_change_order_org_param(o_id: int) -> Union[str, Response]:

    order = Order.query.filter_by(id=o_id, processed=False).filter(~Order.to_delete).first()
    if not order:
        flash(message=settings.Messages.STRANGE_REQUESTS, category='error')
        return redirect(url_for('main.enter'))
    else:

        price_description = settings.PRICE_DESCRIPTION

        category = order.category
        category_process_name = settings.CATEGORIES_DICT.get(category)

        company_types = settings.COMPANY_TYPES
        edo_types = settings.EDO_TYPES

        order, order_list, company_type, company_name, company_idn, \
            edo_type, edo_id, mark_type, trademark, orders_pos_count, pos_count, \
            total_price, price_exist, subcategory = orders_list_common(category=category, user=current_user,
                                                          o_id=o_id)

    return render_template('change_org_v2.html', **locals())


def h_change_order_org_param_form(o_id: int) -> Response:
    order = Order.query.filter_by(id=o_id, processed=False).filter(~Order.to_delete).first()
    if not order:
        flash(message=settings.Messages.STRANGE_REQUESTS, category='error')
        return redirect(url_for('main.enter'))

    company_idn = order.company_idn
    if company_idn in settings.ExceptionOrders.COMPANIES_IDNS:
        flash(message=settings.ExceptionOrders.COMPANY_IDN_ERROR.format(company_idn=company_idn), category='error')
        return redirect(url_for('main.enter'))

    form_dict = request.form.to_dict()
    category = form_dict.get("category_hidden")
    try:
        order.company_type = form_dict.get("company_type")
        order.company_name = form_dict.get("company_name")
        order.edo_type = form_dict.get("edo_type")
        order.edo_id = form_dict.get("edo_id")
        order.company_idn = form_dict.get("company_idn")
        order.mark_type = form_dict.get("mark_type_hidden"),

        db.session.commit()
        flash(message=settings.Messages.UPDATE_ORG_SUCCESS)
    except Exception as e:

        db.session.rollback()
        message = f"{settings.Messages.UPDATE_ORG_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)

    return redirect(url_for(category + '.index', o_id=o_id))


def h_cubaa():
    """ handler background: checks user balance and order in archieve"""

    category = request.form.get('category').replace('--', '')
    o_id = int(request.form.get('o_id').replace('--', ''))
    status_order, status_balance, answer_order, answer_balance = (0, 0,
                                                                  settings.Messages.STRANGE_REQUESTS,
                                                                  settings.Messages.STRANGE_REQUESTS)

    order_check = Order.query.with_entities(Order.id).filter(Order.user_id == current_user.id, ~Order.to_delete).first()
    if not order_check:
        return jsonify(dict(status_order=status_order, answer_orders=f"{answer_order}",
                            status_balance=status_balance, answer_balance=answer_balance))

    status_order, answer_order = helper_check_user_order_in_archive(category=category, o_id=o_id)

    status_balance, total_order_price, \
        agent_at2, answer_balance = helper_check_uoabm(user=current_user, o_id=o_id)

    return jsonify(dict(status_order=status_order, answer_orders=f"{answer_order}",
                        status_balance=status_balance, answer_balance=answer_balance,  agent_at2=agent_at2))


def h_get_dadata_token():

    return jsonify({"token": "eae07ba0f72cc349e91500f5a949eacf49a63051"})