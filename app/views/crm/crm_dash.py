from datetime import datetime
from logger import logger

from flask import Blueprint, flash, render_template, redirect, url_for, request, jsonify
from flask_login import current_user, login_required

from config import settings
from models import User, Order, ServerParam
from utilities.download import orders_download_common
from utilities.support import (user_activated, su_required, sumausmumu_required, susmumu_required, susmu_required,
                               aus_required)

from .helpers import (helper_get_agent_orders, helper_get_manager_orders, helper_m_order_processed, helper_m_order_ps,
                      helper_attach_file, helper_download_file, helper_delete_order_file, helpers_problem_order,
                      helper_cancel_order, helper_change_agent_stage, helpers_m_take_order, helper_change_manager,
                      helper_attach_of_link, helper_m_order_bp, helpers_move_orders_to_processed,
                      helper_search_crma_order, helper_search_crmm_order, helpers_ceps_order, helper_crm_preload,
                      helper_auto_problem_cancel_order, helper_get_agent_stage_orders)
from .helpers_mo import h_all_new_multi_pool
crm_d = Blueprint('crm_d', __name__)


@crm_d.route('/agents', methods=["GET"])
@login_required
@user_activated
@aus_required
def agents():
    # attempt to decrease sql queries
    all_orders_no_limit = helper_get_agent_orders(user=current_user)

    if all_orders_no_limit:

        cancelled_orders = list(filter(lambda x: x.stage == settings.OrderStage.CANCELLED, all_orders_no_limit))
        crm_processed_orders = list(filter(lambda x: x.stage == settings.OrderStage.CRM_PROCESSED, all_orders_no_limit))

        new_orders = list(filter(lambda x: x.stage == settings.OrderStage.NEW, all_orders_no_limit))
        pool_orders = list(filter(lambda x: x.stage == settings.OrderStage.POOL, all_orders_no_limit))

        m_start_orders = list(filter(lambda x: x.stage == settings.OrderStage.MANAGER_START, all_orders_no_limit))
        m_edo_orders = list(filter(lambda x: x.stage == settings.OrderStage.MANAGER_EDO, all_orders_no_limit))
        m_processed_orders = list(filter(lambda x: x.stage == settings.OrderStage.MANAGER_PROCESSED, all_orders_no_limit))
        m_problem_orders = list(filter(lambda x: x.stage == settings.OrderStage.MANAGER_PROBLEM, all_orders_no_limit))
        m_solved_orders = list(filter(lambda x: x.stage == settings.OrderStage.MANAGER_SOLVED, all_orders_no_limit))

        sent_orders = list(filter(lambda x: x.stage == settings.OrderStage.SENT, all_orders_no_limit))

        ps_limit_qry = ServerParam.query.get(1)
        problem_order_time_limit = ps_limit_qry.crm_manager_ps_limit if ps_limit_qry and ps_limit_qry.crm_manager_ps_limit\
            else settings.OrderStage.DEFAULT_PS_LIMIT
        cur_time = datetime.now()
        of_max_size = settings.OrderStage.MAX_ORDER_FILE_SIZE

        managers_list = list(map(lambda x: [x.id, x.login_name, ],
                                 User.query.with_entities(User.id, User.login_name).filter(
                                     User.role in [settings.MANAGER_USER, settings.SUPER_MANAGER]).all()))
        search_order_url = url_for('crm_d.search_crma_order')
        # using bck upload flag as 1
    bck = request.args.get('bck', 0, int)
    return render_template('crm/crm_agent.html', **locals()) if not bck \
        else jsonify({'htmlresponse': render_template(f'crm/crma/crma_main_block.html', **locals())})


@crm_d.route('/update_agent_stage', methods=["POST"])
@login_required
@user_activated
@aus_required
def update_agent_stage():
    # attempt to decrease sql queries
    stage = int(request.form.get("stage"))
    if not stage or stage not in [settings.OrderStage.SENT, settings.OrderStage.CANCELLED,
                                  settings.OrderStage.CRM_PROCESSED]:
        logger.error(f"Invalid stage: {stage}")
        return jsonify({'htmlresponse': None})

    update_orders = helper_get_agent_stage_orders(stage=stage, user=current_user)
    # using bck upload flag as 1
    return jsonify({'htmlresponse': render_template('crm/crma/updated_stages/orders_{stage}.html'.format(stage=stage), **locals())})


@crm_d.route('/change_stage/<int:o_id>/<int:stage>', methods=["POST"])
@login_required
@user_activated
@aus_required
def change_agent_stage(o_id: int, stage: int):
    return helper_change_agent_stage(o_id=o_id, stage=stage, user=current_user)


@crm_d.route('/all_new_multi_pool', methods=["POST"])
@login_required
@user_activated
@aus_required
def all_new_multi_pool():
    return h_all_new_multi_pool()


@crm_d.route('/download_order/<int:o_id>', methods=["POST"])
@login_required
@user_activated
@sumausmumu_required
def download_order(o_id: int):
    order_id = Order.query.filter_by(id=o_id).with_entities(Order.id).first()
    if not order_id:
        flash(message=settings.Messages.EMPTY_ORDER, category='error')
        return redirect(url_for('crm_d.agents'))

    u_id = Order.query.filter_by(id=o_id).with_entities(Order.user_id).scalar_subquery()
    user = User.query.filter_by(id=u_id).first()
    return orders_download_common(user=user, o_id=o_id)


@crm_d.route('/cancel_crm_order/<int:o_id>', methods=["POST"])
@login_required
@user_activated
@aus_required
def cancel_crm_order(o_id: int):
    cancel_comment = request.form.get("cancel_order_comment", '').replace("--", '').replace("#", '')
    return helper_cancel_order(user=current_user, o_id=o_id, cancel_comment=cancel_comment)


@crm_d.route('/set_problem_order/<int:o_id>/', defaults={'user_type': None}, methods=["POST"])
@crm_d.route('/set_problem_order/<int:o_id>/<string:user_type>', methods=["POST"])
@login_required
@user_activated
@sumausmumu_required
def set_problem_order(o_id: int, user_type: str = None):
    # setting redirect route
    user_type = 'managers' if not user_type else 'agents'

    problem_comment = request.form.get("problem_order_comment", '').replace("--", '').replace("#", '')
    problem_order = Order.query.get(o_id)
    if not o_id or not problem_order:
        flash(message=settings.Messages.EMPTY_ORDER, category='error')
        return redirect(url_for(f'crm_d.{user_type}'))

    helpers_problem_order(problem_order=problem_order, problem_comment=problem_comment)

    return redirect(url_for(f'crm_d.{user_type}'))


@crm_d.route('/ceps/<int:o_id>/<int:ep>', methods=["POST"])
@login_required
@user_activated
def ceps(o_id: int, ep: int):

    # change external problem stage
    status = 'danger'
    if ep not in [0, 1]:
        message = settings.Messages.SUPER_MOD_REQUIRED
        return jsonify({'status': status, 'message': message})
    if ep == 0:
        if current_user.role not in [settings.SUPER_USER, settings.ADMIN_USER]:
            message = settings.Messages.SUPERADMIN_MADMIN_USER_REQUIRED
            return jsonify({'status': status, 'message': message})

    if ep == 1:
        if current_user.role not in [settings.SUPER_USER, settings.SUPER_MANAGER, settings.MANAGER_USER]:
            message = settings.Messages.CRM_MANAGER_USER_REQUIRED
            return jsonify({'status': status, 'message': message})

    return helpers_ceps_order(o_id=o_id, ep=ep)


@crm_d.route('/managers', defaults={'filtered_manager_id': None}, methods=["GET"])
@crm_d.route('/managers/<int:filtered_manager_id>', methods=["GET"])
@login_required
@user_activated
@susmumu_required
def managers(filtered_manager_id: int = None):

    user = current_user

    # pool_orders = helper_get_manager_orders(user=user, pool=True)
    all_orders_raw = helper_get_manager_orders(user=user, filtered_manager_id=filtered_manager_id)

    pool_orders = list(filter(lambda x: x.stage == settings.OrderStage.POOL, all_orders_raw))
    m_start_orders = list(filter(lambda x: x.stage == settings.OrderStage.MANAGER_START, all_orders_raw))
    m_edo_orders = list(filter(lambda x: x.stage == settings.OrderStage.MANAGER_EDO, all_orders_raw))
    m_processed_orders = list(filter(lambda x: x.stage == settings.OrderStage.MANAGER_PROCESSED, all_orders_raw))
    m_problem_orders = list(filter(lambda x: x.stage == settings.OrderStage.MANAGER_PROBLEM, all_orders_raw))
    m_solved_orders = list(filter(lambda x: x.stage == settings.OrderStage.MANAGER_SOLVED, all_orders_raw))

    ps_limit_qry = ServerParam.query.get(1)
    problem_order_time_limit = ps_limit_qry.crm_manager_ps_limit if ps_limit_qry and ps_limit_qry.crm_manager_ps_limit \
        else settings.OrderStage.DEFAULT_PS_LIMIT
    cur_time = datetime.now()
    of_max_size = settings.OrderStage.MAX_ORDER_FILE_SIZE

    managers_list = list(map(lambda x: (x.id, x.login_name,),
                             User.query.with_entities(User.id, User.login_name).filter(
                                 (User.role == settings.MANAGER_USER) | (User.role == settings.SUPER_MANAGER)).all()))
    search_order_url = url_for('crm_d.search_crmm_order')

    bck = request.args.get('bck', 0, int)
    return render_template('crm/crm_manager.html', **locals()) if not bck \
        else jsonify({'htmlresponse': render_template(f'crm/crmm/crmm_main_block.html', **locals())})


@crm_d.route('/m_take_order/<int:o_id>', methods=["POST"])
@login_required
@user_activated
@susmumu_required
def m_take_order(o_id: int):
    user = current_user

    return helpers_m_take_order(user=user, o_id=o_id)


@crm_d.route('/m_order_processed/<int:o_id>/<int:manager_id>', defaults={'f_manager_id': None}, methods=["POST"])
@crm_d.route('/m_order_processed/<int:o_id>/<int:manager_id>/<int:f_manager_id>', methods=["POST"])
@login_required
@user_activated
@susmumu_required
def m_order_processed(o_id: int, manager_id: int, f_manager_id: int = None):
    """
        change stage of order Manager processed
    :param o_id:
    :param manager_id:
    :param f_manager_id:
    :return:
    """
    user = current_user
    return helper_m_order_processed(user=user, o_id=o_id, manager_id=manager_id, f_manager_id=f_manager_id)


@crm_d.route('/m_order_ps/<int:o_id>/<int:manager_id>', defaults={'f_manager_id': None}, methods=["POST"])
@crm_d.route('/m_order_ps/<int:o_id>/<int:manager_id>/<int:f_manager_id>', methods=["POST"])
@login_required
@user_activated
@susmumu_required
def m_order_ps(o_id: int, manager_id: int, f_manager_id: int = None):
    """
        change stage of order manager problem solved
    :param o_id:
    :param manager_id:
    :param f_manager_id:
    :return:
    """
    user = current_user

    return helper_m_order_ps(user=user, o_id=o_id, manager_id=manager_id, f_manager_id=f_manager_id)


@crm_d.route('/attach_file/<string:manager>/<int:manager_id>/<int:o_id>', methods=["POST"])
@login_required
@user_activated
@susmumu_required
def attach_file(manager: str, manager_id: int, o_id: int):
    return helper_attach_file(manager=manager, manager_id=manager_id, o_id=o_id)


@crm_d.route('/attach_of_link/<string:manager>/<int:manager_id>/<int:o_id>', methods=["POST"])
@login_required
@user_activated
@susmumu_required
def attach_of_link(manager: str, manager_id: int, o_id: int):
    return helper_attach_of_link(manager=manager, manager_id=manager_id, o_id=o_id)


@crm_d.route('/download_file/<int:manager_id>/<int:o_id>/', defaults={'user_type': None}, methods=["POST"])
@crm_d.route('/download_file/<int:manager_id>/<int:o_id><string:user_type>', methods=["POST"])
@login_required
@user_activated
@susmumu_required
def download_file(manager_id: int, o_id: int, user_type: str = None):
    user_type = 'managers' if not user_type else 'agents'
    return helper_download_file(manager_id=manager_id, o_id=o_id, user_type=user_type)


@crm_d.route('/crm_preload/<int:o_id>', methods=["GET"])
@login_required
@user_activated
@aus_required
def crm_preload(o_id: int):
    return helper_crm_preload(o_id=o_id)


@crm_d.route('/delete_order_file/<int:manager_id>/<int:o_id>', methods=["POST"])
@login_required
@user_activated
@sumausmumu_required
def delete_order_file(manager_id: int, o_id: int):
    return helper_delete_order_file(manager_id=manager_id, o_id=o_id)


@crm_d.route('/change_manager/<int:manager_id>/<int:o_id>', methods=["POST"])
@login_required
@user_activated
@susmu_required
def change_order_manager(manager_id: int, o_id: int):

    return helper_change_manager(manager_id=manager_id, o_id=o_id)


@crm_d.route('/m_order_manager_bp/<int:o_id>/<int:manager_id>', defaults={'f_manager_id': None}, methods=["POST"])
@crm_d.route('/m_order_manager_bp/<int:o_id>/<int:manager_id>/<int:f_manager_id>', methods=["POST"])
@login_required
@user_activated
@susmu_required
def m_order_order_bp(o_id: int, manager_id: int, f_manager_id: int = None):
    """
        change stage of order PROBLEM SOLVED or PROCESSED back to order PROCESSING by manager/ Only for SUPERMANAGER AND SUPERUSER
    :param o_id:
    :param manager_id:
    :param f_manager_id:
    :return:
    """
    user = current_user
    return helper_m_order_bp(user=user, o_id=o_id, manager_id=manager_id, f_manager_id=f_manager_id)


@crm_d.route('/move from sent_orders', methods=["POST"])
@login_required
@user_activated
@aus_required
def move_from_sent_orders():
    """
        change stage for all orders in SENT that are stucked for more than 5 days in daily tasks
    :return:
    """
    return helpers_move_orders_to_processed()


# @crm_d.route('/move from problem_orders', methods=["POST"])
# @login_required
# @user_activated
# @aus_required
# def move_from_problem_orders():
#     """
#         change stage for all orders in MANAGER_PROBLEM that are stucked for more than 24hour and 30 minutes
#     :return:
#     """
#     return helper_auto_problem_cancel_order()

# todo
# @crm_d.route('/move from sent_orders', methods=["POST"])
# @login_required
# @user_activated
# @su_required
# def bck_change_orders_stage():
#     """
#         change stage for all orders from specified stage to another specified in post data
#     :return:
#     """
#     return helpers_bck_change_orders_stage()

@crm_d.route('/search_crma_order', methods=['POST'])
@login_required
@aus_required
def search_crma_order():

    return helper_search_crma_order()


@crm_d.route('/search_crmm_order', methods=['POST'])
@login_required
@user_activated
@susmumu_required
def search_crmm_order():

    return helper_search_crmm_order()
