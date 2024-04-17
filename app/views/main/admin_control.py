from flask import Blueprint, jsonify, request
from flask_login import login_required

from config import settings
from data_migrations.instance import etl_service
from data_migrations.utils import make_password
from models import User
from utilities.admin.h_admin_control import h_index, h_admin, h_set_order_notification, h_create_admin, \
    h_partner_code, h_delete_partner_code, h_telegram_set_group, h_telegram_message_set, h_telegram_group_bind, \
    h_delete_telegram_group, h_set_user_admin, h_set_user, h_deactivate_user, h_activate_all_admin_users, \
    h_deactivate_user_admin, h_set_process_type, h_delete_user_admin, h_delete_user, h_create_link_new_password, \
    h_send_order, h_download_agent_report, h_user_search, h_user_search_idn, h_cross_user_search, h_bck_set_user_price, \
    h_change_agent_fee, h_change_trust_limit, h_users_orders_stats, h_users_activate_list, h_bck_user_delete, \
    h_bck_user_activate, h_client_orders_stats
from utilities.admin.h_finance_control import h_su_control_finance, h_su_bck_promo, h_su_add_promo, h_su_delete_promo, \
    h_su_bck_prices, h_su_add_prices, h_su_delete_prices, h_su_bck_sa, h_su_add_sa, h_su_delete_sa, \
    h_su_bck_change_sa_type, h_su_control_ut, h_su_transaction_detail, h_bck_control_ut, h_au_bck_control_ut, \
    h_su_pending_transaction_update, h_su_wo_transactions, h_aus_transaction_detail
from utilities.support import au_required, aus_required, bck_aus_required, bck_su_required, su_required, \
                               user_exist_check

admin_control = Blueprint('admin_control', __name__)


@admin_control.route('/', defaults={'expanded': None})
@admin_control.route('/<expanded>/')
@login_required
@aus_required
def index(expanded: str = None):
    return h_index(expanded=expanded)


@admin_control.route('/admin/<int:u_id>/', methods=["GET", ])
@login_required
@au_required
def admin(u_id: int):
    return h_admin(u_id=u_id)


@admin_control.route('/set_order_notification/<int:u_id>/', methods=["POST"])
@login_required
@au_required
def set_order_notification(u_id: int):
    return h_set_order_notification(u_id=u_id)


@admin_control.route('/create_admin/', methods=['POST'])
@login_required
@su_required
def create_admin():
    return h_create_admin()


@admin_control.route('/<int:u_id>/set_partner_code', defaults={'auto': None}, methods=['POST'])
@admin_control.route('/<int:u_id>/set_partner_code/<int:auto>', methods=['POST'])
@login_required
@au_required
def partner_code(u_id: int, auto: int = None):
    return h_partner_code(u_id=u_id, auto=auto)


@admin_control.route('/delete_partner_code/<int:u_id>/<p_id>', methods=['POST'])
@login_required
@au_required
def delete_partner_code(u_id: int, p_id: int):
    return h_delete_partner_code(u_id=u_id, p_id=p_id)


@admin_control.route('/telegram_set_group/', methods=['POST'])
@login_required
@su_required
def telegram_set_group():
    return h_telegram_set_group()


@admin_control.route('/telegram_message_set/<int:u_id>/<int:t_id>', methods=['POST'])
@login_required
@au_required
def telegram_message_set(u_id: int, t_id: int):
    return h_telegram_message_set(u_id=u_id, t_id=t_id)


@admin_control.route('/telegram_group_bind/', methods=['POST'])
@login_required
@su_required
def telegram_group_bind():
    return h_telegram_group_bind()


@admin_control.route('/delete_telegram_group/<int:t_id>', methods=['POST'])
@login_required
@su_required
def delete_telegram_group(t_id: int):
    return h_delete_telegram_group(t_id=t_id)


@admin_control.route('/set_user_admin/<int:u_id>', methods=['POST'])
@login_required
@su_required
def set_user_admin(u_id: int):
    return h_set_user_admin(u_id=u_id)


@admin_control.route('/set_user/<type_set>/<int:u_id>', methods=['POST'])
@login_required
@aus_required
def set_user(type_set: str, u_id: int):
    return h_set_user(type_set=type_set, u_id=u_id)


@admin_control.route('/deactivate_user/<type_set>/<int:u_id>', methods=['POST'])
@login_required
@aus_required
@user_exist_check
def deactivate_user(type_set: str, u_id: int):
    return h_deactivate_user(type_set=type_set, u_id=u_id)


@admin_control.route('/activate_all_admin_users/<int:au_id>', methods=['POST'])
@login_required
@aus_required
def activate_all_admin_users(au_id: int):
    return h_activate_all_admin_users(au_id=au_id)


@admin_control.route('/deactivate_user_admin/<int:u_id>', methods=['POST'])
@login_required
@su_required
@user_exist_check
def deactivate_user_admin(u_id: int):
    return h_deactivate_user_admin(u_id=u_id)


@admin_control.route('/bck_set_user_price/<int:u_id>', methods=['POST'])
@login_required
@bck_aus_required
def bck_set_user_price(u_id: int):
    return h_bck_set_user_price(u_id=u_id)


@admin_control.route('/set_process_type/<int:u_id>/<string:p_type>', methods=['POST'])
@login_required
@su_required
@user_exist_check
def set_process_type(u_id: int, p_type: str):
    return h_set_process_type(u_id=u_id, p_type=p_type)


@admin_control.route('/delete_user_admin/<int:u_id>', methods=['POST'])
@login_required
@su_required
@user_exist_check
def delete_user_admin(u_id: int):
    return h_delete_user_admin(u_id=u_id)


@admin_control.route('/delete_user/<int:u_id>', methods=['POST'])
@login_required
@aus_required
@user_exist_check
def delete_user(u_id: int):
    return h_delete_user(u_id=u_id)


@admin_control.route('/create_link_new_password/<int:u_id>', methods=['GET'])
@login_required
@aus_required
@user_exist_check
def create_link_new_password(u_id: int):
    """
        creates link for user new password and returns it to admin with js processing function
    :param u_id:
    :return:
    """
    return h_create_link_new_password(u_id=u_id)


@admin_control.route('/send_order', methods=['POST'])
@login_required
@su_required
def send_order():
    return h_send_order()


@admin_control.route('/download_agent_report/<int:u_id>', methods=['GET'])
@login_required
@su_required
def download_agent_report(u_id: int):
    return h_download_agent_report(u_id=u_id)


@admin_control.route('/change_agent_fee/<int:u_id>', methods=['POST'])
@login_required
@su_required
def change_agent_fee(u_id: int):
    """
        changes agent fee
    :param u_id:
    :return:
    """
    return h_change_agent_fee(u_id=u_id)


@admin_control.route('/change_trust_limit/<int:u_id>', methods=['POST'])
@login_required
@su_required
def change_trust_limit(u_id: int):
    """
        changes agent type 2 trust limit
    :param u_id:
    :return:
    """
    return h_change_trust_limit(u_id=u_id)


@admin_control.route('/user_search/<int:user_admin_id>', methods=["POST"])
@login_required
@aus_required
def user_search(user_admin_id: int):
    return h_user_search(user_admin_id=user_admin_id)


@admin_control.route('/user_search_idn/<int:user_admin_id>', methods=["POST"])
@login_required
@aus_required
def user_search_idn(user_admin_id: int):
    return h_user_search_idn(user_admin_id=user_admin_id)


@admin_control.route('/cross_user_search/', methods=["POST"])
@login_required
@su_required
def cross_user_search():
    return h_cross_user_search()


@admin_control.route('/su_control_finance', methods=['GET', ])
@login_required
@su_required
def su_control_finance():
    return h_su_control_finance()


@admin_control.route('/su_bck_promo', methods=['GET', ])
@login_required
@su_required
def su_bck_promo():
    return h_su_bck_promo()


@admin_control.route('/su_add_promo', methods=['POST', ])
@login_required
@su_required
def su_add_promo():
    return h_su_add_promo()


@admin_control.route('/su_delete_promo/<int:p_id>', methods=['POST', ])
@login_required
@su_required
def su_delete_promo(p_id: int):
    return h_su_delete_promo(p_id=p_id)


@admin_control.route('/su_bck_prices', methods=['GET', ])
@login_required
@su_required
def su_bck_prices():
    return h_su_bck_prices()


@admin_control.route('/su_add_prices', methods=['POST', ])
@login_required
@su_required
def su_add_prices():
    return h_su_add_prices()


@admin_control.route('/su_delete_prices/<int:p_id>', methods=['POST', ])
@login_required
@su_required
def su_delete_prices(p_id: int):
    return h_su_delete_prices(p_id=p_id)


@admin_control.route('/su_bck_sa', methods=['GET', ])
@login_required
@su_required
def su_bck_sa():
    """
        background update current service accounts
    :return:
    """
    return h_su_bck_sa()


@admin_control.route('/su_add_sa', methods=['POST', ])
@login_required
@su_required
def su_add_sa():
    """
        background add new service account
    :return:
    """
    return h_su_add_sa()


@admin_control.route('/su_delete_sa/<int:sa_id>', methods=['POST', ])
@login_required
@su_required
def su_delete_sa(sa_id: int):
    """
        background delete service acc
    :param sa_id:
    :return:
    """
    return h_su_delete_sa(sa_id=sa_id)


@admin_control.route('/change_sa_type/<string:sa_type>', methods=['POST', ])
@login_required
@su_required
def su_bck_change_sa_type(sa_type: str):
    """
        background change service account type qr_code | requisites
    :param:
    :return:
    """
    return h_su_bck_change_sa_type(sa_type=sa_type)


@admin_control.route('/su_control_ut', methods=['GET', ])
@login_required
@su_required
def su_control_ut():
    """
        page of all user transactions to control
    :return:
    """
    return h_su_control_ut()


@admin_control.route('/su_bck_control_ut', methods=['GET', ])
@login_required
@su_required
def su_bck_control_ut():
    """
        background update filtered user transactions to control
    :return:
    """
    return h_bck_control_ut()


@admin_control.route('/au_bck_control_ut', methods=['GET', ])
@login_required
@bck_aus_required
def au_bck_control_ut():
    """
        background update filtered agent user transactions to control agent fee
    :return:
    """
    return h_au_bck_control_ut()


@admin_control.route('su_transaction_detail/<int:u_id>/<int:t_id>', methods=['GET', ])
@login_required
@su_required
def bck_su_transaction_detail(u_id: int, t_id: int):
    """
        transaction info for modal window
    :param u_id:
    :param t_id:
    :return:
    """
    return h_su_transaction_detail(u_id=u_id, t_id=t_id)


@admin_control.route('aus_transaction_detail/<int:u_id>/<int:t_id>', methods=['GET', ])
@login_required
@bck_aus_required
def bck_aus_transaction_detail(u_id: int, t_id: int):
    """
        transaction info for modal window
    :param u_id:
    :param t_id:
    :return:
    """
    return h_aus_transaction_detail(u_id=u_id, t_id=t_id)


@admin_control.route('su_pending_transaction_update/<int:u_id>/<int:t_id>', methods=['POST', ])
@login_required
@su_required
def bck_su_pending_transaction_update(u_id: int, t_id: int):
    """
        super user background update pending transactions
    :param u_id:
    :param t_id:
    :return:
    """
    return h_su_pending_transaction_update(u_id=u_id, t_id=t_id)


@admin_control.route('bck_wo_transactions', methods=['POST', ])
@login_required
@su_required
def bck_su_bck_wo_transactions():
    """
        super user background perform orders in transactions
    :param u_id:
    :param t_id:
    :return:
    """
    return h_su_wo_transactions()


@admin_control.route('etl_upload_data', methods=['POST', ])
@login_required
@su_required
def etl_process_upload():
    """
        Makes request and returns json object of updated and inserted users form original markiners
    :return:
    """
    data = etl_service.start_etl_process()
    status = 'warning'

    # check for new data
    if data.get('users', {'inserted': 0}).get('inserted') > 0:
        status = 'success'

    users_total = User.query.filter(User.role == 'ordinary_user').count()
    agents_total = User.query.filter(User.role == 'admin').count()
    data['users_total'] = users_total
    data['agents_total'] = agents_total
    return jsonify(dict(status=status, info=data)), 200


@admin_control.route('su_agent_info', methods=['POST', ])
@login_required
@su_required
def su_agent_info():
    """
        makes request for passwords for auto extracted agents from partner codes markineris 1
    :return:
    """
    password = None
    data = request.form
    agent_email = data.get("agent_email")
    if agent_email:
        password = make_password(agent_email, settings.SALT.get_secret_value())

    return jsonify(dict(password=password)), 200


@admin_control.route('/users_orders_stats/', defaults={'admin_id': None}, methods=['GET', ])
@admin_control.route('/users_orders_stats/<int:admin_id>/', methods=['GET', ])
@login_required
@bck_aus_required
def users_orders_stats(admin_id: int = None):
    """
        gets all orders of agent clients for admin and all orders for super
    :return:
    """
    return h_users_orders_stats(admin_id=admin_id)


@admin_control.route('/client_orders_stats/<int:admin_id>/<int:client_id>', methods=['GET', ])
@login_required
@bck_aus_required
def client_orders_stats(admin_id: int, client_id: int):
    """
        gets all orders of specific client
    :return:
    """
    return h_client_orders_stats(admin_id=admin_id, client_id=client_id)


@admin_control.route('/users_activate_list', methods=["GET", ])
@login_required
@bck_su_required
def users_activate_list():
    return h_users_activate_list()


@admin_control.route('/bck_user_delete/<int:u_id>', methods=["POST", ])
@login_required
@bck_su_required
def bck_user_delete(u_id: int):
    return h_bck_user_delete(u_id=u_id)


@admin_control.route('/bck_user_activate/<int:u_id>', methods=["POST", ])
@login_required
@bck_su_required
def bck_user_activate(u_id: int):
    return h_bck_user_activate(u_id=u_id)
