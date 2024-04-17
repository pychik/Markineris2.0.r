from flask import Blueprint, send_file
from flask_login import login_required

from config import settings

from utilities.helpers.h_requests_common import h_get_company_data, h_process_idn_error, h_check_tnved_code_data, \
    h_get_tg_user_data, h_send_table, h_send_table_order, h_change_order_org_param, h_change_order_org_param_form, \
    h_cubaa
from utilities.support import user_activated, user_is_send_check, helper_check_user_order_in_archive, su_required

requests_common = Blueprint('requests_common', __name__)


@requests_common.route('get_company_data/<int:u_id>/<from_category>/<idn>')
@login_required
@user_activated
def get_company_data(u_id: int, from_category: str, idn: str):
    return h_get_company_data(u_id=u_id, from_category=from_category, idn=idn)


@requests_common.route('process_idn_error/<from_category>/<message>')
@login_required
@user_activated
def process_idn_error(from_category: str, message: str):
    return h_process_idn_error(from_category=from_category, message=message)


@requests_common.route('/download/<path:filename>', methods=['GET'])
@login_required
@user_activated
def download_file(filename: str):
    path = f"{settings.DOWNLOAD_DIR}/{filename}"
    return send_file(path_or_file=path, as_attachment=True)


@requests_common.route('check_tnved_code_data/<int:u_id>/<from_category>/', defaults={'tnved_code': None})
@requests_common.route('check_tnved_code_data/<int:u_id>/<from_category>/<tnved_code>')
@login_required
@user_activated
def check_tnved_code_data(u_id: int, from_category: str, tnved_code: str):
    return h_check_tnved_code_data(u_id=u_id, from_category=from_category, tnved_code=tnved_code)


@requests_common.route('get_tg_user_data/<int:tg_id>/', methods=['GET'])
@login_required
@user_activated
def get_tg_user_data(tg_id: int):
    return h_get_tg_user_data(tg_id=tg_id)


@requests_common.route('/send_table', methods=['GET'])
@login_required
@user_activated
@user_is_send_check
def send_table():
    return h_send_table()


@requests_common.route('/send_table_order', methods=['POST'])
@login_required
@user_activated
@user_is_send_check
def send_table_order():
    return h_send_table_order()


@requests_common.route('/change_order_org_param/<int:o_id>', methods=['GET'])
@login_required
@user_activated
def change_order_org_param(o_id: int):
    return h_change_order_org_param(o_id=o_id)


@requests_common.route('/change_order_org_param_form/<int:o_id>', methods=['POST'])
@login_required
@user_activated
def change_order_org_param_form(o_id: int):
    return h_change_order_org_param_form(o_id=o_id)


@requests_common.route('check_user_order/<string:category>/<int:o_id>/', methods=['GET'])
@login_required
@user_activated
def check_user_order_in_archive(category: str, o_id: int):
    """
    Checks string AGG types and trademark of user orders
    """
    result_status, answer = helper_check_user_order_in_archive(category=category, o_id=o_id)

    return f"{result_status};{answer}"


@requests_common.route('cubaa', methods=['POST'])
@login_required
@user_activated
def cubaa():
    """
    Checks user balance and duplicates of order in db
    cubaa - check_user_balance_and_archieve
    """

    return h_cubaa()
