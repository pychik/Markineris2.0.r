from datetime import datetime

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from config import settings
from utilities.support import su_sm_required, user_activated

from .service import (
    AUTOMATED_ALLOWED_STAGES,
    AUTOMATED_DEFAULT_PER_PAGE,
    attach_automated_file_response,
    attach_automated_link_response,
    build_automated_board_context,
    build_automated_column_context,
    cancel_order,
    can_access_automated_order,
    can_manage_automated_order_file,
    delete_automated_file_response,
    download_order_file_response,
    get_automated_chat_messages_response,
    get_automated_order_access_data,
    get_automated_order_details_response,
    get_automated_order_info,
    get_automated_order_logs_response,
    get_automated_order_technical_info_response,
    get_automated_processing_order_info_response,
    get_automated_weekly_counters,
    log_automated_file_access_denied,
    mark_automated_chat_read_response,
    mark_problem,
    move_automated_order_to_stage,
    move_problem_to_work,
    normalize_automated_per_page,
    process_order,
    send_automated_chat_message_response,
    take_order,
    update_automated_processing_order_info_response,
)


crm_automated = Blueprint('crm_automated', __name__)


@crm_automated.route('/orders', methods=['GET'])
@login_required
@user_activated
@su_sm_required
def orders():
    category = request.args.get('category')
    filtered_manager_id = request.args.get('filtered_manager_id', None, int)
    per_page = normalize_automated_per_page(request.args.get('per_page', AUTOMATED_DEFAULT_PER_PAGE, int))
    weekly_counters = get_automated_weekly_counters(filtered_manager_id=filtered_manager_id)
    order_stage = settings.OrderStage
    oper_orders_string = ''
    hide_secondary_crm_links = True
    context = build_automated_board_context(
        user=current_user,
        filtered_manager_id=filtered_manager_id,
        category=category,
        per_page=per_page,
    )

    bck = request.args.get('bck', 0, int)
    if not bck:
        return render_template(
            'crm_automated_v1/main.html',
            weekly_counters=weekly_counters,
            order_stage=order_stage,
            oper_orders_string=oper_orders_string,
            hide_secondary_crm_links=hide_secondary_crm_links,
            **context,
        )

    return jsonify({
        'htmlresponse': render_template('crm_automated_v1/main_block.html', order_stage=order_stage, **context),
        'weekly_counters': weekly_counters,
        'status': settings.SUCCESS,
    })


@crm_automated.route('/orders/column', methods=['GET'])
@login_required
@user_activated
@su_sm_required
def orders_column():
    stage = request.args.get('stage', type=int)
    page = max(request.args.get('page', 1, int) or 1, 1)
    per_page = normalize_automated_per_page(request.args.get('per_page', AUTOMATED_DEFAULT_PER_PAGE, int))
    category = request.args.get('category')
    filtered_manager_id = request.args.get('filtered_manager_id', None, int)

    if stage not in AUTOMATED_ALLOWED_STAGES:
        return jsonify({'status': settings.ERROR, 'message': f'Недопустимая стадия: {stage}'}), 400

    column = build_automated_column_context(
        user=current_user,
        stage=stage,
        filtered_manager_id=filtered_manager_id,
        category=category,
        page=page,
        per_page=per_page,
    )
    if not column:
        return jsonify({'status': settings.ERROR, 'message': 'Колонка не найдена'}), 404

    return jsonify({
        'htmlresponse': render_template('crm_automated_v1/column_items.html', orders=column.items, order_stage=settings.OrderStage),
        'status': settings.SUCCESS,
        'quantity': column.total_count,
        'page': column.page,
        'per_page': column.per_page,
        'next_page': column.next_page,
        'has_more': column.has_more,
        'column_id': column.column_id,
        'stage': column.stage,
    })


@crm_automated.route('/orders/search', methods=['POST'])
@login_required
@user_activated
@su_sm_required
def search_order():
    search_order_idn = request.form.get('search_order_idn', '')
    if not search_order_idn:
        message = settings.Messages.CRM_SEARCH_ORDER_ERROR.format(comment='Введен пустой заказ!')
        return jsonify({'status': settings.ERROR, 'message': message})

    order_info = get_automated_order_info(search_order_idn=search_order_idn, viewer_user_id=current_user.id)
    if not order_info:
        message = settings.Messages.CRM_SEARCH_ORDER_ERROR.format(comment='Либо заказ отсутствует, либо не относится к автоматизированным заказам!')
        return jsonify({'status': settings.ERROR, 'message': message})

    htmlresponse = render_template('crm_automated_v1/search_result.html', n=order_info, cur_time=datetime.now(), order_stage=settings.OrderStage)
    return jsonify({'htmlresponse': htmlresponse, 'status': settings.SUCCESS})


@crm_automated.route('/orders/<int:o_id>/take', methods=['POST'])
@login_required
@user_activated
@su_sm_required
def take(o_id: int):
    status, message = take_order(current_user, o_id)
    return jsonify({'status': settings.SUCCESS if status else settings.ERROR, 'message': message})


@crm_automated.route('/orders/<int:o_id>/problem', methods=['POST'])
@login_required
@user_activated
@su_sm_required
def to_problem(o_id: int):
    problem_comment = request.form.get('problem_order_comment', '').replace('--', '').replace('#', '')
    status, message = mark_problem(current_user, o_id, problem_comment)
    return jsonify({'status': settings.SUCCESS if status else settings.ERROR, 'message': message})


@crm_automated.route('/orders/<int:o_id>/process', methods=['POST'])
@login_required
@user_activated
@su_sm_required
def process(o_id: int):
    status, message = process_order(current_user, o_id)
    return jsonify({'status': settings.SUCCESS if status else settings.ERROR, 'message': message})


@crm_automated.route('/orders/<int:o_id>/back-to-work', methods=['POST'])
@login_required
@user_activated
@su_sm_required
def back_to_work(o_id: int):
    status, message = move_problem_to_work(current_user, o_id)
    return jsonify({'status': settings.SUCCESS if status else settings.ERROR, 'message': message})


@crm_automated.route('/orders/<int:o_id>/cancel', methods=['POST'])
@login_required
@user_activated
@su_sm_required
def cancel(o_id: int):
    cancel_comment = request.form.get('cancel_order_comment', '').replace('--', '').replace('#', '')
    status, message = cancel_order(current_user, o_id, cancel_comment)
    return jsonify({'status': settings.SUCCESS if status else settings.ERROR, 'message': message})


@crm_automated.route('/orders/<int:o_id>/move-stage', methods=['POST'])
@login_required
@user_activated
@su_sm_required
def move_stage(o_id: int):
    target_stage = request.form.get('target_stage', type=int)
    stage_comment = (request.form.get('stage_comment') or '').replace('--', '').replace('#', '')
    status, message = move_automated_order_to_stage(current_user, o_id, target_stage, stage_comment)
    return jsonify({'status': settings.SUCCESS if status else settings.ERROR, 'message': message})


@crm_automated.route('/orders/<int:o_id>/files/attach', methods=['POST'])
@login_required
@user_activated
@su_sm_required
def attach_file(o_id: int):
    order = get_automated_order_access_data(o_id)
    if not can_manage_automated_order_file(order, current_user):
        log_automated_file_access_denied('attach_file', o_id, order, current_user)
        return jsonify({'status': settings.ERROR, 'message': 'Прикреплять файл можно только на стадии проблемы'})
    return attach_automated_file_response(o_id=o_id, manager_name=current_user.login_name)


@crm_automated.route('/orders/<int:o_id>/files/attach-link', methods=['POST'])
@login_required
@user_activated
@su_sm_required
def attach_link(o_id: int):
    order = get_automated_order_access_data(o_id)
    if not can_manage_automated_order_file(order, current_user):
        log_automated_file_access_denied('attach_link', o_id, order, current_user)
        return jsonify({'status': settings.ERROR, 'message': 'Прикреплять файл можно только на стадии проблемы'})
    return attach_automated_link_response(o_id=o_id)


@crm_automated.route('/orders/<int:o_id>/files/delete', methods=['POST'])
@login_required
@user_activated
@su_sm_required
def delete_file(o_id: int):
    order = get_automated_order_access_data(o_id)
    if not can_manage_automated_order_file(order, current_user):
        log_automated_file_access_denied('delete_file', o_id, order, current_user)
        return jsonify({'status': settings.ERROR, 'message': 'Удалять файл можно только на стадии проблемы'})
    return delete_automated_file_response(o_id=o_id)


@crm_automated.route('/orders/<int:o_id>/files/download', methods=['POST'])
@login_required
@user_activated
@su_sm_required
def download_file(o_id: int):
    return download_order_file_response(o_id)


@crm_automated.route('/orders/<int:o_id>/chat/messages', methods=['GET'])
@login_required
@user_activated
@su_sm_required
def order_chat_get_messages(o_id: int):
    return get_automated_chat_messages_response(o_id)


@crm_automated.route('/orders/<int:o_id>/chat/send', methods=['POST'])
@login_required
@user_activated
@su_sm_required
def order_chat_send(o_id: int):
    return send_automated_chat_message_response(o_id)


@crm_automated.route('/orders/<int:o_id>/chat/read', methods=['POST'])
@login_required
@user_activated
@su_sm_required
def order_chat_mark_read(o_id: int):
    return mark_automated_chat_read_response(o_id)


@crm_automated.route('/order/details', methods=['GET'])
@login_required
@user_activated
@su_sm_required
def order_details():
    return get_automated_order_details_response()


@crm_automated.route('/orders/<int:o_id>/logs', methods=['GET'])
@login_required
@user_activated
@su_sm_required
def order_logs(o_id: int):
    return get_automated_order_logs_response(o_id)


@crm_automated.route('/orders/<int:o_id>/technical-info', methods=['GET'])
@login_required
@user_activated
@su_sm_required
def order_technical_info(o_id: int):
    return get_automated_order_technical_info_response(o_id)


@crm_automated.route('/get_processing_order_info', methods=['GET'])
@login_required
@user_activated
@su_sm_required
def get_processing_order_info():
    return get_automated_processing_order_info_response()


@crm_automated.route('/update_processing_order_info', methods=['POST'])
@login_required
@user_activated
@su_sm_required
def update_processing_order_info():
    return update_automated_processing_order_info_response()