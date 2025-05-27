from datetime import datetime
from logger import logger

from flask import Blueprint, flash, render_template, redirect, url_for, request, jsonify
from flask_login import current_user, login_required

from config import settings
from models import User, Order, ServerParam
from utilities.download import orders_download_common
from utilities.support import (user_activated, sumausmumu_required, susmumu_required, susmu_required,
                               aus_required, ausumsuu_required, suausmumu_required)

from .helpers import (helper_get_agent_orders, helper_get_manager_orders, helper_m_order_processed, helper_m_order_ps,
                      helper_attach_file, helper_download_file, helper_delete_order_file,
                      helper_cancel_order, helper_change_agent_stage, helpers_m_take_order, helper_change_manager,
                      helper_attach_of_link, helpers_move_orders_to_processed,
                      helper_search_crma_order, helper_search_crmm_order, helpers_ceps_order, helper_crm_preload,
                      helper_get_agent_stage_orders, helper_categories_counter,
                      helper_change_agent_stage_bck, helper_a_order_bp, helper_m_order_bp,
                      helpers_problem_order_response)
from .helpers_mo import h_all_new_multi_pool
crm_d = Blueprint('crm_d', __name__)


@crm_d.route('/agents', methods=["GET"])
@login_required
@user_activated
@aus_required
def agents():
    # attempt to decrease sql queries
    category = request.args.get('category')
    all_orders_no_limit = helper_get_agent_orders(user=current_user, category=category)

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
    categories_counter = helper_categories_counter(all_cards=all_orders_no_limit)
    return render_template('crm_mod_v1/crm_agent.html', **locals()) if not bck \
        else jsonify({'htmlresponse': render_template(f'crm_mod_v1/crma/crma_main_block.html', **locals()),
                      'status': 'success' if all_orders_no_limit else ''})


@crm_d.route('/update_agent_stage', methods=["POST"])
@login_required
@user_activated
@aus_required
def update_agent_stage():
    status = settings.ERROR
    message = settings.Messages.ORDER_CHANGE_STAGE_ERROR
    # attempt to decrease sql queries
    stage = request.form.get("stage", -1, int)
    order_id = request.form.get("order_id", 0, int)
    category = request.form.get("category", 'all')

    if not stage or stage not in settings.OrderStage.CHECK_TUPLE:
        mes = f"{message} Invalid stage: {stage}"
        logger.error(mes)
        return jsonify({'htmlresponse': None, 'status': status, 'message': mes})
    if not category or (category != 'all' and category not in settings.CATEGORIES_UPLOAD):
        mes = f"{message} Invalid category: {category}"
        logger.error(mes)
        return jsonify({'htmlresponse': None, 'status': status, 'message': mes})
    # check if we received order_id to change stage
    if order_id:
        o_status, o_message = helper_change_agent_stage_bck(o_id=order_id, stage=stage, user=current_user)
        if not o_status:
            return jsonify({'htmlresponse': None, 'status': status, 'message': o_message})
    update_orders = helper_get_agent_stage_orders(stage=stage, category=category, user=current_user)

    status = settings.SUCCESS
    message = settings.Messages.ORDER_CHANGE_STAGE_SUCCESS
    return jsonify({'htmlresponse': render_template('crm_mod_v1/crma/updated_stages/orders_{stage}.html'.format(stage=stage), **locals()),
                    'quantity': len(update_orders), 'status': status, 'message': message})


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
    return orders_download_common(user=user, o_id=o_id, flag_046=request.args.get("flag_046", False, bool))


@crm_d.route('/cancel_crm_order/<int:o_id>', methods=["POST"])
@login_required
@user_activated
@aus_required
def cancel_crm_order(o_id: int):
    cancel_comment = request.form.get("cancel_order_comment", '').replace("--", '').replace("#", '')
    return helper_cancel_order(user=current_user, o_id=o_id, cancel_comment=cancel_comment)


@crm_d.route('/set_problem_order/<int:o_id>/', methods=["POST"])
@login_required
@user_activated
@sumausmumu_required
def set_problem_order(o_id: int):
    user = current_user
    return helpers_problem_order_response(user=user, o_id=o_id)


@crm_d.route('/ceps/<int:o_id>/<int:ep>', methods=["POST"])
@login_required
@user_activated
def ceps(o_id: int, ep: int):
    executor = request.form.get('executor')
    # change external problem stage
    status = 'danger'
    if executor not in ['manager', 'agent']:
        message = settings.Messages.STRANGE_REQUESTS
        return jsonify({'status': status, 'message': message})
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

    return helpers_ceps_order(o_id=o_id, ep=ep, executor=executor)


@crm_d.route('/managers', methods=["GET"])
@login_required
@user_activated
@susmumu_required
def managers(filtered_manager_id: int = None):
    user = current_user

    category = request.args.get('category')
    filtered_manager_id = request.args.get('filtered_manager_id', None, int)
    all_orders_raw = helper_get_manager_orders(user=user, filtered_manager_id=filtered_manager_id, category=category)

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
    categories_counter = helper_categories_counter(all_cards=all_orders_raw)
    return render_template('crm_mod_v1/crm_manager.html', **locals()) if not bck \
        else jsonify({'htmlresponse': render_template(f'crm_mod_v1/crmm/crmm_main_block.html', **locals()),
                      'status': 'success' if all_orders_raw else ''})

@crm_d.route('/m_take_order/<int:o_id>', methods=["POST"])
@login_required
@user_activated
@susmumu_required
def m_take_order(o_id: int):
    user = current_user

    return helpers_m_take_order(user=user, o_id=o_id)


@crm_d.route('/m_order_processed/<int:o_id>/<int:manager_id>',  methods=["POST"])
@login_required
@user_activated
@susmumu_required
def m_order_processed(o_id: int, manager_id: int):
    """
        change stage of order Manager processed
    :param o_id:
    :param manager_id:
    :return:
    """
    user = current_user
    return helper_m_order_processed(user=user, o_id=o_id, manager_id=manager_id)


@crm_d.route('/m_order_ps/<int:o_id>/<int:manager_id>', methods=["POST"])
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

    return helper_m_order_ps(user=user, o_id=o_id, manager_id=manager_id)


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
@crm_d.route('/download_file/<int:manager_id>/<int:o_id>/<string:user_type>', methods=["POST"])
@login_required
@user_activated
@suausmumu_required
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


@crm_d.route('/m_order_manager_bp/<int:o_id>/<int:manager_id>', methods=["POST"])
@login_required
@user_activated
@susmu_required
def m_order_order_bp(o_id: int, manager_id: int):
    """
        change stage of order PROBLEM SOLVED or PROCESSED back to order PROCESSING by manager/ Only for SUPERMANAGER AND SUPERUSER
    :param o_id:
    :param manager_id:
    :return:
    """
    user = current_user
    return helper_m_order_bp(user=user, o_id=o_id, manager_id=manager_id)


@crm_d.route('/a_order_manager_bp/<int:o_id>/<int:manager_id>', methods=["POST"])
@login_required
@user_activated
@ausumsuu_required
def a_order_order_bp(o_id: int, manager_id: int):
    """
        change stage of order PROBLEM SOLVED or PROCESSED back to order PROCESSING by manager/ Only for SUPERMANAGER AND SUPERUSER
    :param o_id:
    :param manager_id:
    :return:
    """
    user = current_user
    return helper_a_order_bp(user=user, o_id=o_id, manager_id=manager_id)


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
