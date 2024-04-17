from flask import Blueprint, flash, render_template, redirect, url_for
from flask_login import login_required, current_user

from config import settings
from utilities.helpers.h_user_cp import h_user_control_panel, h_user_personal_account, h_change_user_password, \
    h_get_restore_link, h_create_new_password, h_change_user_password_na, h_pa_refill, h_update_transactions_history, \
    h_transaction_detail, h_agent_wo, h_order_book_detail, h_tg_verify_detail
from utilities.support import user_activated, bck_aus_required
from utilities.tg_verify.service import h_tg_markineris_verify, h_tg_markineris_stop_verify

user_cp = Blueprint('user_cp', __name__)


@user_cp.route('/<int:u_id>', methods=['GET'])
@login_required
@user_activated
def user_control_panel(u_id: int):
    """Page for changing password when user is authorised"""
    return h_user_control_panel(u_id=u_id)


@user_cp.route('/change_user_password/<int:u_id>', methods=['POST'])
@login_required
@user_activated
def change_user_password(u_id: int):
    """
        Changes user password with user control panel form
    """
    return h_change_user_password(u_id=u_id)


@user_cp.route('/restore_page', methods=['GET'])
def restore_page():
    """
        Page for email input to receive change password link
    """
    if current_user.is_authenticated:
        flash(message=settings.Messages.SECONDARY_SIGN_UP_ERROR, category='error')
        return redirect(url_for('main.enter'))
    return render_template('user_control/user_email_password_restore.html')


@user_cp.route('personal_account/<int:u_id>', defaults={'stage': None}, methods=['GET'])
@login_required
@user_activated
def personal_account(u_id: int, stage: int = None):
    """
    user personal account page
    :param u_id:
    :param stage:
    :return:
    """
    return h_user_personal_account(u_id=u_id, stage=stage)


@user_cp.route('update_transactions_history/<int:u_id>', methods=['GET'])
@login_required
@user_activated
def bck_update_transactions(u_id: int):
    """
    update user transaction table
    :param u_id:
    :return:
    """
    return h_update_transactions_history(u_id=u_id)


@user_cp.route('transaction_detail/<int:u_id>/<int:t_id>', methods=['GET'])
@login_required
@user_activated
def bck_transaction_detail(u_id: int, t_id: int):
    """
    user trabsaction detail
    :param u_id:
    :param t_id:
    :return:
    """
    return h_transaction_detail(u_id=u_id, t_id=t_id)


@user_cp.route('pa_refill/<int:u_id>', methods=['POST'])
@login_required
@user_activated
def pa_refill(u_id: int):
    """
    personal account refill
    :param u_id:
    :return:
    """
    return h_pa_refill(u_id=u_id)


@user_cp.route('order_book_detail/<int:u_id>', methods=['GET'])
@login_required
@user_activated
def bck_order_book_detail(u_id: int):
    """
    Returns modal window with info about all active orders
    :param u_id:
    :return:
    """
    return h_order_book_detail(u_id=u_id)


@user_cp.route('agent_wo/<int:u_id>', methods=['POST'])
@login_required
@user_activated
@bck_aus_required
def agent_wo(u_id: int):
    """
    request for write off transaction for agent balance
    :param u_id:
    :return:
    """
    return h_agent_wo(u_id=u_id)


# @user_cp.route('order_write_off_check/<int:o_id>', methods=['POST'])
# @login_required
# @user_activated
# def order_write_off_check(o_id: int):
#     return h_order_write_off_check(o_id=o_id)


@user_cp.route('/get_restore_link', methods=['POST'])
def get_restore_link():
    """
        Get restore link if user has email and send it with email
        Post request from forgotten password page

    :return:
    """
    return h_get_restore_link()


@user_cp.route('/create_new_password/<r_link>', methods=['GET'])
def create_new_password(r_link: str):
    """
        Page for changing password via link received
    """
    return h_create_new_password(r_link=r_link)


@user_cp.route('/change_user_password_na', methods=['POST'])
def change_user_password_na():
    """
        Change user password via email link received
    """
    return h_change_user_password_na()


@user_cp.route('tg_verify_detail/<int:u_id>', methods=['GET'])
@login_required
@user_activated
def bck_tg_verify_detail(u_id: int):
    """
    Returns modal window with info about user tg verification
    :param u_id:
    :return:
    """
    return h_tg_verify_detail(u_id=u_id)


@user_cp.route('/tg_markineris_verify', methods=["POST"])
@login_required
@user_activated
def bck_tg_markineris_verify():
    return h_tg_markineris_verify()


@user_cp.route('/tg_markineris_stop_verify', methods=["POST"])
@login_required
@user_activated
def bck_tg_markineris_stop_verify():
    return h_tg_markineris_stop_verify()

