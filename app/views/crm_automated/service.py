from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Optional

from flask import jsonify, render_template, request
from flask_login import current_user
from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased, joinedload, load_only
from werkzeug.utils import secure_filename

from config import settings
from logger import logger
from models import (
    Order,
    OrderChatRead,
    OrderMessage,
    OrderFile,
    OrderProcessedLog,
    ProcessingCompany,
    ServerParam,
    User,
    UserProcessingCompany,
    db,
)
from utilities.exceptions import EmptyFileToUploadError
from utilities.helpers.h_tg_notify import helper_send_user_order_tg_notify
from utilities.minio_service.services import download_file_from_minio, get_s3_service
from utilities.pdf_processor import helper_check_attached_file
from utilities.sql_categories_aggregations import SQLQueryCategoriesAll
from utilities.telegram import MarkinerisInform
from utilities.support import is_automated_crm_order
from ..crm.crm_support import h_cancel_order_process_payment
from ..crm.helpers import check_order_file, helper_create_filename, of_delete_remove


AUTOMATED_ALLOWED_STAGES = (
    settings.OrderStage.POOL,
    settings.OrderStage.MANAGER_START,
    settings.OrderStage.MANAGER_PROBLEM,
    settings.OrderStage.CANCELLED,
    settings.OrderStage.CRM_PROCESSED,
)
AUTOMATED_MOVE_TARGET_STAGES = (
    settings.OrderStage.POOL,
    settings.OrderStage.MANAGER_PROBLEM,
    settings.OrderStage.CANCELLED,
    settings.OrderStage.CRM_PROCESSED,
)
AUTOMATED_WORK_STAGES = (
    settings.OrderStage.POOL,
    settings.OrderStage.MANAGER_START,
    settings.OrderStage.MANAGER_PROBLEM,
)
AUTOMATED_ALLOWED_ROLES = {
    settings.SUPER_USER,
    settings.SUPER_MANAGER,
}
AUTOMATED_CATEGORIES = ('одежда', 'обувь', 'белье', 'парфюм', 'носки и прочее')
AUTOMATED_EXTERNAL_CONFIRMATION_OVERDUE_SECONDS = 60 * 60
AUTOMATED_ORDER_FILTER_SQL = "o.is_moderation IS TRUE AND o.is_automated_crm IS TRUE"
AUTOMATED_PER_PAGE_OPTIONS = (25, 50, 100, 200)
AUTOMATED_DEFAULT_PER_PAGE = 50
AUTOMATED_ALLOWED_STAGES_SQL = ','.join(map(str, AUTOMATED_ALLOWED_STAGES))
AUTOMATED_BOARD_COLUMNS = (
    {'stage': settings.OrderStage.POOL, 'column_id': 'pool_ordersMainDiv', 'title': 'Пул'},
    {'stage': settings.OrderStage.MANAGER_START, 'column_id': 'm_start_ordersMainDiv', 'title': 'В обработке'},
    {'stage': settings.OrderStage.MANAGER_PROBLEM, 'column_id': 'm_problem_ordersMainDiv', 'title': 'Проблема в заказе'},
    {'stage': settings.OrderStage.CRM_PROCESSED, 'column_id': 'crm_processed_ordersMainDiv', 'title': 'Обработано'},
    {'stage': settings.OrderStage.CANCELLED, 'column_id': 'cancelled_ordersMainDiv', 'title': 'Отменено'},
)


def _is_automated_order(is_moderation: Optional[bool], is_automated_crm: Optional[bool]) -> bool:
    return is_automated_crm_order(is_moderation, is_automated_crm)


def _automated_order_expr(model=Order):
    return model.is_moderation.is_(True), model.is_automated_crm.is_(True)


def normalize_automated_per_page(per_page: Optional[int]) -> int:
    try:
        value = int(per_page or AUTOMATED_DEFAULT_PER_PAGE)
    except (TypeError, ValueError):
        return AUTOMATED_DEFAULT_PER_PAGE
    return value if value in AUTOMATED_PER_PAGE_OPTIONS else AUTOMATED_DEFAULT_PER_PAGE


def _get_automated_pagination_meta(total_count: int, page: int = 1, per_page: int = AUTOMATED_DEFAULT_PER_PAGE) -> dict:
    safe_page = max(int(page or 1), 1)
    safe_per_page = normalize_automated_per_page(per_page)
    offset = (safe_page - 1) * safe_per_page
    next_offset = offset + safe_per_page
    has_more = next_offset < total_count

    return {
        'page': safe_page,
        'per_page': safe_per_page,
        'total_count': total_count,
        'has_more': has_more,
        'next_page': safe_page + 1 if has_more else safe_page,
        'offset': offset,
        'limit': safe_per_page,
    }


def get_automated_board_column(stage: int):
    for column in AUTOMATED_BOARD_COLUMNS:
        if column['stage'] == stage:
            return column
    return None


def build_automated_column_context(
    user: User,
    stage: int,
    filtered_manager_id: int = None,
    category: str = None,
    page: int = 1,
    per_page: int = AUTOMATED_DEFAULT_PER_PAGE,
):
    column = get_automated_board_column(stage)
    if not column:
        return None

    paginated = get_automated_orders_page(
        viewer_user_id=user.id,
        filtered_manager_id=filtered_manager_id,
        category=category,
        stage=stage,
        page=page,
        per_page=per_page,
    )
    return SimpleNamespace(**column, **paginated)


def _is_external_confirmation_overdue(stage, status, sent_at, confirmed_at, now: Optional[datetime] = None) -> bool:
    if stage != settings.OrderStage.MANAGER_START:
        return False
    if status != 'delivery_unconfirmed':
        return False
    if not sent_at or confirmed_at:
        return False

    current_dt = now or datetime.now()
    return (current_dt - sent_at).total_seconds() >= AUTOMATED_EXTERNAL_CONFIRMATION_OVERDUE_SECONDS


def _build_external_status_meta(status, sent_at, confirmed_at, stage=None, now: Optional[datetime] = None) -> dict:
    current_dt = now or datetime.now()
    overdue = _is_external_confirmation_overdue(stage, status, sent_at, confirmed_at, current_dt)

    if confirmed_at or status == 'accepted':
        detail = f'Подтвержден внешним сервисом: {confirmed_at.strftime("%d-%m-%Y %H:%M:%S")}' if confirmed_at else 'Заказ подтвержден внешним сервисом'
        return {
            'label': 'Подтвержден внешним сервисом',
            'short_label': '✓',
            'tone': 'success',
            'blink': False,
            'tooltip': detail,
            'detail': detail,
            'visible': True,
        }

    if status == 'delivery_unconfirmed' or (sent_at and not confirmed_at):
        sent_text = sent_at.strftime('%d-%m-%Y %H:%M:%S') if sent_at else None
        if overdue:
            detail = (
                f'Заказ отправлен во внешний сервис {sent_text} и более часа не получено подтверждение о принятии в работу'
                if sent_text else
                'Заказ был отправлен во внешний сервис и более часа не получено подтверждение о принятии в работу'
            )
            return {
                'label': 'Нет подтверждения более часа',
                'short_label': '!',
                'tone': 'danger',
                'blink': True,
                'tooltip': detail,
                'detail': detail,
                'visible': True,
            }

        detail = (
            f'Заказ отправлен во внешний сервис {sent_text}, подтверждение о принятии в работу пока не получено'
            if sent_text else
            'Заказ отправлен во внешний сервис, подтверждение о принятии в работу пока не получено'
        )
        return {
            'label': 'Ожидает подтверждения',
            'short_label': '!',
            'tone': 'warning',
            'blink': True,
            'tooltip': detail,
            'detail': detail,
            'visible': True,
        }

    if status:
        return {
            'label': 'Есть внешний статус',
            'short_label': '!',
            'tone': 'info',
            'blink': False,
            'tooltip': 'Внешний сервис вернул служебный статус, проверьте техническую информацию заказа',
            'detail': 'Внешний сервис вернул служебный статус, проверьте техническую информацию заказа',
            'visible': True,
        }

    return {
        'label': 'Нет внешнего статуса',
        'short_label': 'Нет статуса',
        'tone': 'muted',
        'blink': False,
        'tooltip': 'Заказ еще не отправлялся во внешний сервис',
        'detail': 'Заказ еще не отправлялся во внешний сервис',
        'visible': False,
    }


def _automation_unread_map(order_ids: list[int], user_id: int) -> dict[int, int]:
    if not order_ids or not user_id:
        return {}

    q = (
        db.session.query(OrderMessage.order_id, func.count(OrderMessage.id))
        .outerjoin(
            OrderChatRead,
            (OrderChatRead.order_id == OrderMessage.order_id) & (OrderChatRead.user_id == user_id),
        )
        .filter(OrderMessage.order_id.in_(order_ids))
        .filter(OrderMessage.id > func.coalesce(OrderChatRead.last_read_message_id, 0))
        .group_by(OrderMessage.order_id)
    )

    rows = q.all()
    result = {oid: 0 for oid in order_ids}
    for oid, cnt in rows:
        result[int(oid)] = int(cnt or 0)
    return result


def _attach_order_chat_unread(rows, viewer_user_id: Optional[int]):
    if not rows or not viewer_user_id:
        wrapped_rows = rows
        if rows and hasattr(rows[0], '__dict__'):
            for row in wrapped_rows:
                setattr(
                    row,
                    'external_confirmation_overdue',
                    _is_external_confirmation_overdue(
                        getattr(row, 'stage', None),
                        getattr(row, 'status', None),
                        getattr(row, 'sent_at', None),
                        getattr(row, 'confirmed_at', None),
                    ),
                )
        return wrapped_rows

    order_ids = []
    for row in rows:
        rid = getattr(row, 'id', None)
        if rid:
            order_ids.append(int(rid))

    if not order_ids:
        return rows

    unread_map = _automation_unread_map(order_ids, int(viewer_user_id))
    wrapped = []
    for row in rows:
        data = dict(row._mapping) if hasattr(row, '_mapping') else dict(getattr(row, '__dict__', {}))
        data.pop('_sa_instance_state', None)
        data['unread_chat_count'] = int(unread_map.get(int(data.get('id', 0) or 0), 0))
        data['external_confirmation_overdue'] = _is_external_confirmation_overdue(
            data.get('stage'),
            data.get('status'),
            data.get('sent_at'),
            data.get('confirmed_at'),
        )
        data['external_status_meta'] = _build_external_status_meta(
            data.get('status'),
            data.get('sent_at'),
            data.get('confirmed_at'),
            data.get('stage'),
        )
        wrapped.append(SimpleNamespace(**data))
    return wrapped


def get_automated_weekly_counters(filtered_manager_id: int | None = None) -> dict:
    today = datetime.today().date()
    monday = today - timedelta(days=today.weekday())

    manager_filter_sql = 'AND manager_id = :manager_id' if filtered_manager_id is not None else ''
    manager_params = {'manager_id': filtered_manager_id} if filtered_manager_id is not None else {}

    processed = db.session.execute(text(f"""
        SELECT COUNT(*)
        FROM public.orders
        WHERE stage = :crm_processed
          AND is_moderation IS TRUE
          AND is_automated_crm IS TRUE
          AND closed_at::date BETWEEN :start_date AND :end_date
          {manager_filter_sql}
    """), {
        'crm_processed': settings.OrderStage.CRM_PROCESSED,
        'start_date': monday,
        'end_date': today,
        **manager_params,
    }).scalar() or 0

    cancelled = db.session.execute(text(f"""
        SELECT COUNT(*)
        FROM public.orders
        WHERE stage = :cancelled
          AND is_moderation IS TRUE
          AND is_automated_crm IS TRUE
          AND cc_created::date BETWEEN :start_date AND :end_date
          {manager_filter_sql}
    """), {
        'cancelled': settings.OrderStage.CANCELLED,
        'start_date': monday,
        'end_date': today,
        **manager_params,
    }).scalar() or 0

    problem = db.session.execute(text(f"""
        SELECT COUNT(*)
        FROM public.orders
        WHERE stage = :problem_stage
          AND is_moderation IS TRUE
          AND is_automated_crm IS TRUE
          AND cp_created::date BETWEEN :start_date AND :end_date
          {manager_filter_sql}
    """), {
        'problem_stage': settings.OrderStage.MANAGER_PROBLEM,
        'start_date': monday,
        'end_date': today,
        **manager_params,
    }).scalar() or 0

    return {
        'processed': int(processed),
        'cancelled': int(cancelled),
        'problem': int(problem),
        'range': f"{monday.strftime('%d.%m.%Y')}-{today.strftime('%d.%m.%Y')}",
    }


def get_order_processed_logs(order_id: int) -> list[OrderProcessedLog]:
    return (
        OrderProcessedLog.query
        .filter(OrderProcessedLog.order_id == order_id)
        .order_by(OrderProcessedLog.created_at.desc(), OrderProcessedLog.id.desc())
        .all()
    )


def get_automated_managers_list() -> list[tuple[int, str]]:
    return list(map(
        lambda x: (x.id, x.login_name),
        User.query.with_entities(User.id, User.login_name)
        .filter((User.role == settings.SUPER_USER) | (User.role == settings.SUPER_MANAGER))
        .order_by(User.login_name.asc())
        .all(),
    ))


def _build_automated_orders_where_sql(
    filtered_manager_id: int = None,
    category: str = None,
    stage: int = None,
) -> tuple[str, dict]:
    where_clauses = [
        AUTOMATED_ORDER_FILTER_SQL,
        'o.to_delete IS NOT TRUE',
        f'o.stage IN ({AUTOMATED_ALLOWED_STAGES_SQL})',
    ]
    params = {}

    if category in settings.CATEGORIES_UPLOAD:
        where_clauses.append('o.category = :category')
        params['category'] = category

    if stage in AUTOMATED_ALLOWED_STAGES:
        where_clauses.append('o.stage = :stage')
        params['stage'] = stage

    if filtered_manager_id:
        where_clauses.append('(o.stage = :pool_stage OR o.manager_id = :filtered_manager_id)')
        params['pool_stage'] = settings.OrderStage.POOL
        params['filtered_manager_id'] = filtered_manager_id

    return '\n          AND '.join(where_clauses), params


def _get_automated_orders_select_stmt(where_sql: str, include_limit_offset: bool = False):
    limit_offset_sql = ''
    if include_limit_offset:
        limit_offset_sql = """
        LIMIT :limit
        OFFSET :offset
        """

    return text(f"""
        SELECT
            u.is_at2 as is_at2,
            o.id as id,
            o.manager_id as manager_id,
            o.stage as stage,
            o.payment as payment,
            o.order_idn as order_idn,
            o.category as category,
            o.company_type as company_type,
            o.company_name as company_name,
            o.company_idn as company_idn,
            o.external_problem as external_problem,
            o.edo_type as edo_type,
            o.mark_type as mark_type,
            o.user_comment as user_comment,
            o.has_new_tnveds as has_new_tnveds,
            o.to_delete as to_delete,
            o.processing_info as processing_info,
            o.is_moderation as is_moderation,
            o.is_automated_crm as is_automated_crm,
            o.stage_setter_name as stage_setter_name,
            o.comment_problem as comment_problem,
            o.comment_cancel as comment_cancel,
            o.cp_created as cp_created,
            o.cc_created as cc_created,
            o.crm_created_at as crm_created_at,
            o.p_started as p_started,
            o.m_started as m_started,
            o.m_finished as m_finished,
            o.sent_at as sent_at,
            o.closed_at as closed_at,
            o.status as status,
            o.dispatch_token as dispatch_token,
            o.object_key as object_key,
            o.confirmed_at as confirmed_at,
            MAX(ofa.order_file) as order_file,
            MAX(ofa.order_file_link) as order_file_link,
            MAX(managers.login_name) as manager,
            COUNT(o.id) as row_count,
            {SQLQueryCategoriesAll.get_stmt(field='subcategory')} as subcategory,
            {SQLQueryCategoriesAll.get_stmt(field='declar_doc')} as declar_doc,
            {SQLQueryCategoriesAll.get_stmt(field='marks_count')} as pos_count
        FROM public.users u
        JOIN public.orders o ON o.user_id = u.id
        LEFT JOIN LATERAL (
            SELECT
                MAX(orf.origin_name) AS order_file,
                MAX(orf.file_link) AS order_file_link
            FROM public.order_files orf
            WHERE orf.order_id = o.id
        ) ofa ON TRUE
        LEFT JOIN public.users managers ON o.manager_id = managers.id
        {SQLQueryCategoriesAll.get_joins()}
        WHERE {where_sql}
        GROUP BY u.id, o.id
        ORDER BY o.p_started ASC NULLS LAST, o.crm_created_at ASC, o.id ASC
        {limit_offset_sql}
    """)


def _fetch_automated_order_rows(
    viewer_user_id: int,
    filtered_manager_id: int = None,
    category: str = None,
    stage: int = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
):
    where_sql, params = _build_automated_orders_where_sql(
        filtered_manager_id=filtered_manager_id,
        category=category,
        stage=stage,
    )
    include_limit_offset = limit is not None and offset is not None
    stmt = _get_automated_orders_select_stmt(where_sql, include_limit_offset=include_limit_offset)
    if include_limit_offset:
        params.update({'limit': int(limit), 'offset': int(offset)})

    rows = db.session.execute(stmt, params).fetchall()
    return _attach_order_chat_unread(rows, viewer_user_id)


def get_automated_orders_count(filtered_manager_id: int = None, category: str = None, stage: int = None) -> int:
    where_sql, params = _build_automated_orders_where_sql(
        filtered_manager_id=filtered_manager_id,
        category=category,
        stage=stage,
    )
    stmt = text(f"""
        SELECT COUNT(*)
        FROM public.orders o
        WHERE {where_sql}
    """)
    return int(db.session.execute(stmt, params).scalar() or 0)


def get_automated_stage_counts(filtered_manager_id: int = None, category: str = None) -> dict[int, int]:
    where_sql, params = _build_automated_orders_where_sql(
        filtered_manager_id=filtered_manager_id,
        category=category,
    )
    stmt = text(f"""
        SELECT o.stage AS stage, COUNT(*) AS total_count
        FROM public.orders o
        WHERE {where_sql}
        GROUP BY o.stage
    """)

    counts = {stage_value: 0 for stage_value in AUTOMATED_ALLOWED_STAGES}
    rows = db.session.execute(stmt, params).fetchall()
    for row in rows:
        counts[int(row.stage)] = int(row.total_count or 0)
    return counts


def get_automated_orders_page(
    viewer_user_id: int,
    filtered_manager_id: int = None,
    category: str = None,
    stage: int = None,
    page: int = 1,
    per_page: int = AUTOMATED_DEFAULT_PER_PAGE,
    total_count: Optional[int] = None,
):
    resolved_total_count = int(total_count) if total_count is not None else get_automated_orders_count(
        filtered_manager_id=filtered_manager_id,
        category=category,
        stage=stage,
    )
    pagination = _get_automated_pagination_meta(resolved_total_count, page=page, per_page=per_page)
    items = []
    if resolved_total_count:
        items = _fetch_automated_order_rows(
            viewer_user_id=viewer_user_id,
            filtered_manager_id=filtered_manager_id,
            category=category,
            stage=stage,
            limit=pagination['limit'],
            offset=pagination['offset'],
        )

    return {
        'items': items,
        'page': pagination['page'],
        'per_page': pagination['per_page'],
        'total_count': pagination['total_count'],
        'has_more': pagination['has_more'],
        'next_page': pagination['next_page'],
    }


def get_automated_categories_counter(all_cards: list | tuple) -> dict:
    categories_counter = {'all': len(all_cards)}
    for cat in AUTOMATED_CATEGORIES:
        categories_counter[cat] = sum(1 for card in all_cards if card.category == cat)
    return categories_counter


def get_automated_categories_counter_by_filters(filtered_manager_id: int = None, category: str = None) -> dict:
    where_sql, params = _build_automated_orders_where_sql(
        filtered_manager_id=filtered_manager_id,
        category=category,
    )
    stmt = text(f"""
        SELECT o.category AS category, COUNT(*) AS total_count
        FROM public.orders o
        WHERE {where_sql}
        GROUP BY o.category
    """)

    categories_counter = {'all': 0}
    for cat in AUTOMATED_CATEGORIES:
        categories_counter[cat] = 0

    rows = db.session.execute(stmt, params).fetchall()
    for row in rows:
        total_count = int(row.total_count or 0)
        categories_counter['all'] += total_count
        if row.category in categories_counter:
            categories_counter[row.category] = total_count

    return categories_counter


def build_automated_board_context(
    user: User,
    filtered_manager_id: int = None,
    category: str = None,
    per_page: int = AUTOMATED_DEFAULT_PER_PAGE,
) -> dict:
    ps_limit_qry = ServerParam.query.get(1)
    safe_per_page = normalize_automated_per_page(per_page)
    stage_counts = get_automated_stage_counts(filtered_manager_id=filtered_manager_id, category=category)

    board_columns = []
    for column in AUTOMATED_BOARD_COLUMNS:
        paginated = get_automated_orders_page(
            viewer_user_id=user.id,
            filtered_manager_id=filtered_manager_id,
            category=category,
            stage=column['stage'],
            page=1,
            per_page=safe_per_page,
            total_count=stage_counts.get(column['stage'], 0),
        )
        board_columns.append(SimpleNamespace(**column, **paginated))

    return {
        'all_orders_raw': (),
        'board_columns': board_columns,
        'filtered_manager_id': filtered_manager_id,
        'categories_counter': get_automated_categories_counter_by_filters(filtered_manager_id=filtered_manager_id, category=category),
        'managers_list': get_automated_managers_list(),
        'of_max_size': settings.OrderStage.MAX_ORDER_FILE_SIZE,
        'cur_time': datetime.now(),
        'problem_order_time_limit': ps_limit_qry.crm_manager_ps_limit if ps_limit_qry and ps_limit_qry.crm_manager_ps_limit else settings.OrderStage.DEFAULT_PS_LIMIT,
        'automated_per_page': safe_per_page,
        'automated_per_page_options': AUTOMATED_PER_PAGE_OPTIONS,
    }


def get_automated_order_info(search_order_idn: str, viewer_user_id: int):
    stmt = text(f"""
        SELECT
            o.id as id,
            o.manager_id as manager_id,
            o.stage as stage,
            o.payment as payment,
            o.order_idn as order_idn,
            o.category as category,
            o.crm_created_at as crm_created_at,
            o.company_type as company_type,
            o.company_name as company_name,
            o.company_idn as company_idn,
            o.external_problem as external_problem,
            o.edo_type as edo_type,
            o.mark_type as mark_type,
            o.user_comment as user_comment,
            o.has_new_tnveds as has_new_tnveds,
            o.to_delete as to_delete,
            o.processing_info as processing_info,
            o.is_moderation as is_moderation,
            o.is_automated_crm as is_automated_crm,
            o.stage_setter_name as stage_setter_name,
            o.comment_problem as comment_problem,
            o.comment_cancel as comment_cancel,
            o.cp_created as cp_created,
            o.cc_created as cc_created,
            o.p_started as p_started,
            o.m_started as m_started,
            o.m_finished as m_finished,
            o.sent_at as sent_at,
            o.closed_at as closed_at,
            o.status as status,
            o.confirmed_at as confirmed_at,
            MAX(orf.origin_name) as order_file,
            MAX(orf.file_link) as order_file_link,
            MAX(managers.login_name) as manager,
            COUNT(o.id) as row_count,
            {SQLQueryCategoriesAll.get_stmt(field='subcategory')} as subcategory,
            {SQLQueryCategoriesAll.get_stmt(field='declar_doc')} as declar_doc,
            {SQLQueryCategoriesAll.get_stmt(field='marks_count')} as pos_count
        FROM public.users u
        JOIN public.orders o ON o.user_id = u.id
        LEFT JOIN public.order_files orf ON o.id = orf.order_id
        LEFT JOIN public.users managers ON o.manager_id = managers.id
        {SQLQueryCategoriesAll.get_joins()}
        WHERE o.order_idn = :search_order_idn
          AND {AUTOMATED_ORDER_FILTER_SQL}
          AND o.to_delete IS NOT True
          AND o.stage IN ({','.join(map(str, AUTOMATED_ALLOWED_STAGES))})
        GROUP BY o.id
    """).bindparams(search_order_idn=search_order_idn)
    row = db.session.execute(stmt).fetchone()
    if not row:
        return None
    return _attach_order_chat_unread([row], viewer_user_id)[0]


def get_automated_order_access_data(o_id: int):
    return (
        db.session.query(Order.id, Order.stage, Order.manager_id, Order.is_moderation, Order.is_automated_crm, Order.to_delete)
        .filter(Order.id == o_id)
        .first()
    )


def get_automated_order_manager_id(o_id: int) -> Optional[int]:
    order = get_automated_order_access_data(o_id)
    if not order:
        return None
    return order.manager_id


def can_access_automated_order(order_row, user: User) -> bool:
    return bool(
        order_row
        and not order_row.to_delete
        and _is_automated_order(order_row.is_moderation, getattr(order_row, 'is_automated_crm', None))
        and user.role in AUTOMATED_ALLOWED_ROLES
    )


def can_manage_automated_order_file(order_row, user: User) -> bool:
    return bool(
        can_access_automated_order(order_row, user)
        and order_row.stage == settings.OrderStage.MANAGER_PROBLEM
    )


def log_automated_file_access_denied(action: str, o_id: int, order_row, user: User):
    logger.warning(
        'Automated CRM file action denied: action=%s order_id=%s order_exists=%s stage=%s manager_id=%s user_id=%s role=%s',
        action,
        o_id,
        bool(order_row),
        getattr(order_row, 'stage', None),
        getattr(order_row, 'manager_id', None),
        getattr(user, 'id', None),
        getattr(user, 'role', None),
    )


def _get_automated_order_for_file(o_id: int) -> Optional[Order]:
    order = db.session.get(Order, o_id)
    if not order or order.to_delete or not _is_automated_order(order.is_moderation, order.is_automated_crm):
        return None
    return order


def attach_automated_file_response(o_id: int, manager_name: str):
    order = _get_automated_order_for_file(o_id)
    if not order:
        logger.warning('Automated CRM attach file failed: order not found order_id=%s', o_id)
        return jsonify({'status': settings.ERROR, 'message': settings.Messages.ORDER_ATTACH_FILE_ABS_ERROR})

    file = request.files.get('order_file', '')
    check, check_file_message = helper_check_attached_file(order_file=file, order_idn=order.order_idn)
    if not check:
        logger.warning('Automated CRM attach file validation failed: order_id=%s order_idn=%s message=%s', o_id, order.order_idn, check_file_message)
        return jsonify({'status': settings.ERROR, 'message': check_file_message})

    s3_service = get_s3_service()
    existing_file = order.order_zip_file
    existing_system_name = existing_file.file_system_name if existing_file else None

    filename = secure_filename(filename=file.filename)
    origin, fs_name = helper_create_filename(order_idn=order.order_idn, manager_name=manager_name, filename=filename)
    if not fs_name:
        logger.warning('Automated CRM attach file failed: filename generation failed order_id=%s order_idn=%s filename=%s', o_id, order.order_idn, filename)
        return jsonify({'status': settings.ERROR, 'message': settings.Messages.CRM_FILENAME_ERROR})

    try:
        s3_service.upload_file(
            file_data=file.stream,
            object_name=fs_name,
            bucket_name=settings.MINIO_CRM_BUCKET_NAME,
        )
    except EmptyFileToUploadError:
        message = f'{settings.Messages.ORDER_ATTACH_FILE_ERROR} Переданный файл пуст'
        logger.warning('Automated CRM attach file failed: empty file order_id=%s order_idn=%s', o_id, order.order_idn)
        return jsonify({'status': settings.ERROR, 'message': message})
    except Exception:
        logger.exception('Automated CRM attach file upload failed: order_id=%s order_idn=%s', o_id, order.order_idn)
        return jsonify({'status': settings.ERROR, 'message': settings.Messages.ORDER_ATTACH_FILE_ERROR})

    try:
        if existing_file:
            existing_file.origin_name = origin
            existing_file.file_system_name = fs_name
            existing_file.file_link = ''
        else:
            db.session.add(OrderFile(origin_name=origin, file_system_name=fs_name, file_link='', order_id=o_id))
        db.session.commit()
        logger.info('Automated CRM attach file success: order_id=%s order_idn=%s file=%s', o_id, order.order_idn, fs_name)
    except Exception:
        db.session.rollback()
        try:
            if s3_service.object_exists(fs_name, settings.MINIO_CRM_BUCKET_NAME):
                s3_service.remove_object(object_name=fs_name, bucket_name=settings.MINIO_CRM_BUCKET_NAME)
        except Exception:
            logger.exception('Automated CRM attach file cleanup failed: order_id=%s order_idn=%s object=%s', o_id, order.order_idn, fs_name)
        logger.exception('Automated CRM attach file DB save failed: order_id=%s order_idn=%s', o_id, order.order_idn)
        return jsonify({'status': settings.ERROR, 'message': settings.Messages.ORDER_ATTACH_FILE_ERROR})

    if existing_system_name and existing_system_name != fs_name:
        try:
            if s3_service.object_exists(existing_system_name, settings.MINIO_CRM_BUCKET_NAME):
                s3_service.remove_object(object_name=existing_system_name, bucket_name=settings.MINIO_CRM_BUCKET_NAME)
        except Exception:
            logger.exception('Automated CRM attach file old object cleanup failed: order_id=%s object=%s', o_id, existing_system_name)

    return jsonify({'status': settings.SUCCESS, 'message': settings.Messages.ORDER_ATTACH_FILE.format(order_idn=order.order_idn)})


def attach_automated_link_response(o_id: int):
    order = _get_automated_order_for_file(o_id)
    if not order:
        logger.warning('Automated CRM attach link failed: order not found order_id=%s', o_id)
        return jsonify({'status': settings.ERROR, 'message': settings.Messages.ORDER_ATTACH_FILE_LINK_ABS_ERROR})

    file_link = request.form.get('of_link', '').replace('--', '')
    s3_service = get_s3_service()
    existing_file = order.order_zip_file
    existing_system_name = existing_file.file_system_name if existing_file else None

    try:
        if existing_file:
            existing_file.origin_name = ''
            existing_file.file_system_name = ''
            existing_file.file_link = file_link
        else:
            db.session.add(OrderFile(origin_name='', file_system_name='', file_link=file_link, order_id=o_id))
        db.session.commit()
        logger.info('Automated CRM attach link success: order_id=%s order_idn=%s', o_id, order.order_idn)
    except Exception:
        db.session.rollback()
        logger.exception('Automated CRM attach link DB save failed: order_id=%s order_idn=%s', o_id, order.order_idn)
        return jsonify({'status': settings.ERROR, 'message': settings.Messages.ORDER_ATTACH_FILE_LINK_ERROR})

    if existing_system_name:
        try:
            if s3_service.object_exists(existing_system_name, settings.MINIO_CRM_BUCKET_NAME):
                s3_service.remove_object(object_name=existing_system_name, bucket_name=settings.MINIO_CRM_BUCKET_NAME)
        except Exception:
            logger.exception('Automated CRM attach link old object cleanup failed: order_id=%s object=%s', o_id, existing_system_name)

    return jsonify({'status': settings.SUCCESS, 'message': settings.Messages.ORDER_ATTACH_FILE_LINK.format(order_idn=order.order_idn)})


def delete_automated_file_response(o_id: int):
    order = _get_automated_order_for_file(o_id)
    if not order or not order.order_zip_file:
        logger.warning('Automated CRM delete file failed: file/order not found order_id=%s', o_id)
        return jsonify({'status': settings.ERROR, 'message': settings.Messages.ORDER_DELETE_FILE_ABS_ERROR})

    existing_file = order.order_zip_file
    existing_system_name = existing_file.file_system_name

    try:
        s3_service = get_s3_service()
        if existing_system_name and s3_service.object_exists(existing_system_name, settings.MINIO_CRM_BUCKET_NAME):
            s3_service.remove_object(object_name=existing_system_name, bucket_name=settings.MINIO_CRM_BUCKET_NAME)
    except Exception:
        logger.exception('Automated CRM delete file failed during storage removal: order_id=%s object=%s', o_id, existing_system_name)
        return jsonify({'status': settings.ERROR, 'message': 'Ошибка при удалении файла из хранилища, попробуйте позже.'})

    try:
        db.session.delete(existing_file)
        db.session.commit()
        logger.info('Automated CRM delete file success: order_id=%s order_idn=%s', o_id, order.order_idn)
        return jsonify({'status': settings.SUCCESS, 'message': settings.Messages.ORDER_DELETE_FILE.format(order_idn=order.order_idn)})
    except Exception:
        db.session.rollback()
        logger.exception('Automated CRM delete file DB delete failed: order_id=%s order_idn=%s', o_id, order.order_idn)
        return jsonify({'status': settings.ERROR, 'message': settings.Messages.ORDER_DELETE_FILE_ERROR})


def move_automated_order_to_stage(user: User, o_id: int, target_stage: int, stage_comment: str = '') -> tuple[bool, str]:
    if target_stage not in AUTOMATED_MOVE_TARGET_STAGES:
        return False, f'{settings.Messages.ORDER_CHANGE_STAGE_ERROR} Invalid stage: {target_stage}'

    order = _load_order_for_action(o_id)
    if not order:
        return False, settings.Messages.STRANGE_REQUESTS

    previous_stage = order.stage
    now = datetime.now()

    if previous_stage == target_stage:
        return True, settings.Messages.ORDER_CHANGE_STAGE_SUCCESS

    if previous_stage == settings.OrderStage.CANCELLED:
        return False, 'Из отмененных заказов больше нельзя менять стадию'

    if target_stage == settings.OrderStage.CANCELLED and previous_stage != settings.OrderStage.MANAGER_PROBLEM:
        return False, 'В отмену можно переводить только со стадии проблемы'

    if target_stage == settings.OrderStage.CRM_PROCESSED:
        if not order.order_zip_file or (not order.order_zip_file.file_system_name and not order.order_zip_file.file_link):
            return False, 'В обработано нельзя перевести заказ без прикрепленного файла'

    try:
        if target_stage == settings.OrderStage.CANCELLED and previous_stage != settings.OrderStage.CANCELLED and order.payment:
            h_cancel_order_process_payment(order_idn=order.order_idn, user_id=order.user_id)
            order.payment = False

        order.stage = target_stage
        order.stage_setter_name = user.login_name

        if target_stage == settings.OrderStage.POOL:
            order.manager_id = None
            order.p_started = now
            order.m_started = None
            order.m_finished = None
            order.cp_created = None
            order.cc_created = None
            order.closed_at = None
            order.comment_problem = ''
            order.comment_cancel = ''
            order.external_problem = False
            order.processed = False
            order.status = None
            order.dispatch_token = None
            order.object_key = None
            order.confirmed_at = None
            order.sent_at = None
        elif target_stage == settings.OrderStage.MANAGER_PROBLEM:
            order.manager_id = order.manager_id or user.id
            order.external_problem = True
            order.comment_problem = stage_comment or order.comment_problem
            order.cp_created = now
            order.cc_created = None
            order.closed_at = None
            order.processed = False
            order.m_finished = None
        elif target_stage == settings.OrderStage.CRM_PROCESSED:
            order.manager_id = order.manager_id or user.id
            order.external_problem = False
            order.cp_created = None
            order.cc_created = None
            order.closed_at = now
            order.m_finished = now
            order.processed = True
        elif target_stage == settings.OrderStage.CANCELLED:
            order.comment_cancel = stage_comment or order.comment_cancel or 'Стадия изменена оператором automated CRM'
            order.cc_created = now
            order.external_problem = False
            order.cp_created = None
            order.closed_at = None
            order.m_finished = None
            order.processed = False

        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception(
            'Automated CRM move stage failed: order_id=%s order_idn=%s from_stage=%s to_stage=%s user_id=%s',
            o_id,
            getattr(order, 'order_idn', None),
            previous_stage,
            target_stage,
            user.id,
        )
        return False, settings.Messages.ORDER_CHANGE_STAGE_ERROR

    if target_stage in settings.OrderStage.M_ORDER_MSG_DICT:
        helper_send_user_order_tg_notify(user_id=order.user_id, order_idn=order.order_idn, order_stage=target_stage)

    logger.info(
        'Automated CRM move stage success: order_id=%s order_idn=%s from_stage=%s to_stage=%s user_id=%s',
        o_id,
        order.order_idn,
        previous_stage,
        target_stage,
        user.id,
    )
    return True, settings.Messages.ORDER_CHANGE_STAGE_SUCCESS


def get_automated_chat_messages_response(o_id: int):
    order = get_automated_order_access_data(o_id)
    if not can_access_automated_order(order, current_user):
        return jsonify({'status': 'error', 'message': 'Нет доступа'}), 403

    msgs = (
        OrderMessage.query
        .options(joinedload(OrderMessage.author).load_only(User.id, User.login_name))
        .filter(OrderMessage.order_id == o_id)
        .order_by(OrderMessage.created_at.asc(), OrderMessage.id.asc())
        .all()
    )

    payload = []
    for msg in msgs:
        payload.append({
            'id': msg.id,
            'text': msg.text,
            'created_at': msg.created_at.isoformat() if msg.created_at else None,
            'author_id': msg.author_id,
            'author_login': msg.author.login_name if msg.author else '',
        })

    read_row = OrderChatRead.query.filter_by(order_id=o_id, user_id=current_user.id).first()
    last_read_id = read_row.last_read_message_id if read_row else 0
    unread_count = sum(1 for msg in msgs if (msg.id or 0) > last_read_id)

    return jsonify({
        'status': 'success',
        'order_id': o_id,
        'unread_count': unread_count,
        'messages': payload,
    })


def send_automated_chat_message_response(o_id: int):
    order = get_automated_order_access_data(o_id)
    if not can_access_automated_order(order, current_user):
        return jsonify({'status': 'error', 'message': 'Нет доступа'}), 403

    text_value = (current_user and (current_user.role in AUTOMATED_ALLOWED_ROLES)) and (request.form.get('text') or '').strip()
    if not text_value:
        return jsonify({'status': 'error', 'message': 'Пустое сообщение'}), 400
    if len(text_value) > 300:
        return jsonify({'status': 'error', 'message': 'Сообщение слишком длинное (макс 300)'}), 400

    try:
        msg = OrderMessage(order_id=o_id, text=text_value, author_id=current_user.id)
        db.session.add(msg)
        db.session.commit()
        return jsonify({'status': 'success', 'message_id': msg.id})
    except Exception:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'Ошибка отправки'}), 500


def mark_automated_chat_read_response(o_id: int):
    order = get_automated_order_access_data(o_id)
    if not can_access_automated_order(order, current_user):
        return jsonify({'status': 'error', 'message': 'Нет доступа'}), 403

    last_id = request.form.get('last_id', type=int)
    if not last_id:
        return jsonify({'status': 'error', 'message': 'last_id required'}), 400

    try:
        row = OrderChatRead.query.filter_by(order_id=o_id, user_id=current_user.id).first()
        if not row:
            row = OrderChatRead(order_id=o_id, user_id=current_user.id, last_read_message_id=last_id)
            db.session.add(row)
            db.session.commit()
            return jsonify({'status': 'success'})

        current_last = row.last_read_message_id or 0
        if last_id <= current_last:
            return jsonify({'status': 'success'})

        row.last_read_message_id = last_id
        row.last_read_at = datetime.now()
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'Ошибка'}), 500


def get_automated_processing_order_info_response():
    order_id = request.args.get('order_id', type=int)
    if not order_id:
        return jsonify({'status': 'danger', 'message': 'Ошибка- не указан номер заказа!'})

    order_info = (
        Order.query.with_entities(Order.processing_info, Order.order_idn, Order.user_id, Order.is_moderation, Order.is_automated_crm)
        .filter(Order.id == order_id, *_automated_order_expr(Order))
        .first()
    )
    if not order_info:
        return jsonify({'status': 'danger', 'message': 'Ошибка- заказ не найден, обратитесь к администратору.'})

    companies_operators = []
    rows = (
        UserProcessingCompany.query
        .join(ProcessingCompany, UserProcessingCompany.company_id == ProcessingCompany.id)
        .options(joinedload(UserProcessingCompany.company))
        .filter(UserProcessingCompany.user_id == order_info.user_id)
        .filter(UserProcessingCompany.is_approved.is_(True))
        .filter(ProcessingCompany.is_active.is_(True))
        .order_by(UserProcessingCompany.slot.asc())
        .all()
    )
    for row in rows:
        company = row.company
        if not company:
            continue
        companies_operators.append({
            'value': f'u:{company.id}',
            'label': f'{company.title} ({company.inn})',
        })

    if not companies_operators:
        message = 'Данные по организации не установлены'
        htmlresponse = render_template('crm_mod_v1/helpers/modals/modal_order_process_info.html', **locals())
        return jsonify({'status': 'danger', 'htmlresponse': htmlresponse})

    htmlresponse = render_template('crm_mod_v1/helpers/modals/modal_order_process_info.html', **locals())
    return jsonify({'status': 'success', 'htmlresponse': htmlresponse})


def update_automated_processing_order_info_response():
    data = request.get_json() or {}
    order_id = data.get('order_id')
    company_value = data.get('company')
    upd_number = data.get('upd_number')

    if not all([order_id, company_value, upd_number]):
        return jsonify({'status': 'error', 'message': 'Все поля обязательны к заполнению'}), 400

    order = db.session.get(Order, order_id)
    if not order or not _is_automated_order(order.is_moderation, order.is_automated_crm):
        return jsonify({'status': 'error', 'message': 'Заказ не найден'}), 404

    try:
        kind, raw = company_value.split(':', 1)
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Некорректная компания'}), 400

    if kind != 'u':
        return jsonify({'status': 'error', 'message': 'Некорректный тип компании для этого заказа'}), 400

    try:
        company_id = int(raw)
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Некорректная компания'}), 400

    company = (
        db.session.query(ProcessingCompany)
        .join(UserProcessingCompany, UserProcessingCompany.company_id == ProcessingCompany.id)
        .filter(UserProcessingCompany.user_id == order.user_id, ProcessingCompany.id == company_id)
        .filter(UserProcessingCompany.is_approved.is_(True))
        .filter(ProcessingCompany.is_active.is_(True))
        .first()
    )
    if not company:
        return jsonify({'status': 'error', 'message': 'Ошибка ввода компании (за владельцем заказа не закреплены)'}), 404

    try:
        order.processing_info = f'{company.title} ({company.inn}) <br> УПД: {upd_number}'
        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': f'Информация по заказу № {order.order_idn} обновлена',
            'order_idn': order.order_idn,
            'processing_info': order.processing_info,
        }), 200
    except Exception as exc:
        db.session.rollback()
        logger.exception('Ошибка обновления информации по организации проводящей заказ: ')
        return jsonify({'status': 'error', 'message': f'Ошибка при обновлении: {exc}'}), 500


def _get_order_desc_row(order_id: int):
    Agent = aliased(User)
    Manager = aliased(User)

    return (
        db.session.query(
            Order.id,
            Order.user_id,
            Order.manager_id,
            Order.stage,
            Order.to_delete,
            Order.order_idn,
            Order.category,
            Order.company_type,
            Order.company_name,
            Order.company_idn,
            Order.edo_type,
            Order.mark_type,
            Order.user_comment,
            Order.is_moderation,
            Order.is_automated_crm,
            Order.processing_info,
            Order.comment_problem,
            Order.comment_cancel,
            Order.status,
            Order.dispatch_token,
            Order.object_key,
            Order.confirmed_at,
            Order.sent_at,
            Order.crm_created_at,
            Order.p_started,
            Order.m_started,
            Order.cp_created,
            Order.cc_created,
            Order.closed_at,
            Order.stage_setter_name,

            User.client_code,
            User.login_name,
            User.phone,
            User.email,
            User.is_at2,
            User.admin_parent_id,

            db.case(
                (Agent.login_name.isnot(None), Agent.login_name),
                else_=User.login_name,
            ).label('agent_name'),
            Manager.login_name.label('manager_login'),
            Manager.role.label('manager_role'),
        )
        .join(User, User.id == Order.user_id)
        .outerjoin(Agent, User.admin_parent_id == Agent.id)
        .outerjoin(Manager, Order.manager_id == Manager.id)
        .filter(Order.id == order_id, *_automated_order_expr(Order))
        .first()
    )


def _get_user_companies_for_user(user_id: int):
    rows = (
        UserProcessingCompany.query
        .options(joinedload(UserProcessingCompany.company))
        .filter(UserProcessingCompany.user_id == user_id)
        .order_by(UserProcessingCompany.slot.asc())
        .all()
    )
    out = []
    for row in rows:
        company = row.company
        out.append({
            'slot': row.slot,
            'is_approved': bool(row.is_approved),
            'assigned_at': row.assigned_at,
            'title': company.title if company else '',
            'inn': company.inn if company else '',
            'is_active': bool(company.is_active) if company else True,
        })
    return out


def get_automated_order_details_response():
    src = (request.args.get('src') or '').strip()
    order_id = request.args.get('order_id', type=int)
    if not order_id:
        return jsonify(status='error', message='order_id required'), 400

    order_row = _get_order_desc_row(order_id)
    if not can_access_automated_order(order_row, current_user):
        return jsonify(status='error', message='Access denied'), 403

    user_companies = _get_user_companies_for_user(order_row.user_id)
    external_status_meta = _build_external_status_meta(
        getattr(order_row, 'status', None),
        getattr(order_row, 'sent_at', None),
        getattr(order_row, 'confirmed_at', None),
        getattr(order_row, 'stage', None),
    )
    html = render_template(
        'crm_automated_v1/order_description.html',
        src=src,
        n=order_row,
        user_companies=user_companies,
        external_status_meta=external_status_meta,
    )
    return jsonify(status='success', html=html)


def get_automated_order_logs_response(o_id: int):
    order_row = _get_order_desc_row(o_id)
    if not can_access_automated_order(order_row, current_user):
        return jsonify(status='error', message='Access denied'), 403

    processed_logs = get_order_processed_logs(o_id)
    html = render_template(
        'crm_automated_v1/order_logs.html',
        n=order_row,
        processed_logs=processed_logs,
    )
    return jsonify(status='success', html=html, title=f'Логи заказа {order_row.order_idn}')


def get_automated_order_technical_info_response(o_id: int):
    order_row = _get_order_desc_row(o_id)
    if not can_access_automated_order(order_row, current_user):
        return jsonify(status='error', message='Access denied'), 403

    external_status_meta = _build_external_status_meta(
        getattr(order_row, 'status', None),
        getattr(order_row, 'sent_at', None),
        getattr(order_row, 'confirmed_at', None),
        getattr(order_row, 'stage', None),
    )

    html = render_template(
        'crm_automated_v1/order_technical_info.html',
        n=order_row,
        external_status_meta=external_status_meta,
    )
    return jsonify(status='success', html=html, title=f'Техническая информация заказа {order_row.order_idn}')


def _load_order_for_action(o_id: int) -> Optional[Order]:
    order = db.session.get(Order, o_id)
    if not order or order.to_delete or not _is_automated_order(order.is_moderation, order.is_automated_crm):
        return None
    return order


def take_order(user: User, o_id: int) -> tuple[bool, str]:
    order = _load_order_for_action(o_id)
    if not order or order.stage != settings.OrderStage.POOL:
        return False, settings.Messages.ORDER_MANAGER_TAKE_ABS_ERROR

    try:
        order.manager_id = user.id
        order.stage = settings.OrderStage.MANAGER_START
        order.m_started = datetime.now()
        order.stage_setter_name = user.login_name
        db.session.commit()
        return True, settings.Messages.ORDER_MANAGER_TAKE
    except IntegrityError:
        db.session.rollback()
        logger.error(settings.Messages.ORDER_MANAGER_TAKE_ERROR)
        return False, settings.Messages.ORDER_MANAGER_TAKE_ERROR


def mark_problem(user: User, o_id: int, problem_comment: str) -> tuple[bool, str]:
    order = _load_order_for_action(o_id)
    if not order or order.stage not in (settings.OrderStage.MANAGER_START, settings.OrderStage.MANAGER_PROBLEM):
        return False, settings.Messages.EMPTY_ORDER

    try:
        order.stage = settings.OrderStage.MANAGER_PROBLEM
        order.external_problem = True
        order.comment_problem = problem_comment
        order.cp_created = datetime.now()
        order.m_finished = None
        order.stage_setter_name = user.login_name
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        logger.error(settings.Messages.ORDER_PROBLEM_ERROR)
        return False, settings.Messages.ORDER_PROBLEM_ERROR

    helper_send_user_order_tg_notify(user_id=order.user_id, order_idn=order.order_idn, order_stage=settings.OrderStage.MANAGER_PROBLEM)
    MarkinerisInform.send_message_tg.delay(order_idn=order.order_idn, problem_order_flag=True)
    return True, settings.Messages.ORDER_PROBLEM.format(order_idn=order.order_idn)


def move_problem_to_work(user: User, o_id: int) -> tuple[bool, str]:
    order = _load_order_for_action(o_id)
    if not order or order.stage != settings.OrderStage.MANAGER_PROBLEM:
        return False, settings.Messages.ORDER_MANAGER_PS_ABS_ERROR

    try:
        order.stage = settings.OrderStage.MANAGER_START
        order.external_problem = False
        order.cp_created = None
        order.m_finished = None
        order.stage_setter_name = user.login_name
        db.session.commit()
        helper_send_user_order_tg_notify(user_id=order.user_id, order_idn=order.order_idn, order_stage=settings.OrderStage.MANAGER_START)
        return True, settings.Messages.ORDER_MANAGER_BP.format(order_idn=order.order_idn)
    except IntegrityError:
        db.session.rollback()
        logger.error(settings.Messages.ORDER_MANAGER_BP_ERROR)
        return False, settings.Messages.ORDER_MANAGER_BP_ERROR


def process_order(user: User, o_id: int) -> tuple[bool, str]:
    order = _load_order_for_action(o_id)
    if not order or order.stage not in (settings.OrderStage.MANAGER_START, settings.OrderStage.MANAGER_PROBLEM):
        return False, settings.Messages.ORDER_MANAGER_PROCESSED_ABS_ERROR
    if not order.order_zip_file or (not order.order_zip_file.file_system_name and not order.order_zip_file.file_link):
        return False, settings.Messages.ORDER_MANAGER_PROCESSED_ABS_FILE_ERROR
    if order.order_zip_file.file_system_name:
        check_status, check_message = check_order_file(order_file_name=order.order_zip_file.file_system_name, o_id=o_id)
        if not check_status:
            return False, check_message
    if not order.processing_info:
        return False, settings.Messages.ORDER_MANAGER_PROCESSED_ABS_PROCESSING_INFO

    try:
        now = datetime.now()
        order.stage = settings.OrderStage.CRM_PROCESSED
        order.processed = True
        order.external_problem = False
        order.closed_at = now
        order.m_finished = now
        order.stage_setter_name = user.login_name
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        logger.error(settings.Messages.ORDER_MANAGER_PROCESSED_ERROR)
        return False, settings.Messages.ORDER_MANAGER_PROCESSED_ERROR

    helper_send_user_order_tg_notify(user_id=order.user_id, order_idn=order.order_idn, order_stage=settings.OrderStage.CRM_PROCESSED)
    return True, settings.Messages.ORDER_STAGE_CHANGE


def cancel_order(user: User, o_id: int, cancel_comment: str) -> tuple[bool, str]:
    stmt_get_agent = "SELECT a.admin_parent_id FROM public.users a WHERE a.id  = (SELECT o.user_id FROM public.orders o WHERE o.id=:o_id LIMIT 1)"
    order_stmt = text(f"""
        SELECT o.id as id,
               o.user_id as user_id,
               o.order_idn as order_idn,
             o.stage as stage,
               o.payment as payment,
               o.transaction_id as transaction_id,
               ({stmt_get_agent}) as agent_id,
               orf.id as of_id,
               orf.file_system_name as file_system_name
        FROM public.orders o
        LEFT JOIN public.order_files orf ON o.id=orf.order_id
        WHERE o.id=:o_id AND o.to_delete IS NOT True AND o.is_moderation IS TRUE AND o.is_automated_crm IS TRUE;
    """).bindparams(o_id=o_id)
    order_info = db.session.execute(order_stmt).fetchone()
    if not order_info or user.role not in AUTOMATED_ALLOWED_ROLES:
        return False, settings.Messages.STRANGE_REQUESTS
    if order_info.stage != settings.OrderStage.MANAGER_PROBLEM:
        return False, 'В отмену можно переводить только со стадии проблемы'

    of_delete_remove(order_info=order_info, o_id=o_id)

    dt_agent = datetime.now()
    order_query = text(f"""
        UPDATE public.orders
        SET payment=False,
            stage={settings.OrderStage.CANCELLED},
            comment_cancel=:cancel_comment,
            cc_created=:dt_agent,
            external_problem=False,
            processed=False,
            closed_at=NULL,
            m_finished=NULL,
            stage_setter_name=:stage_setter_name
        WHERE id=:o_id
    """).bindparams(o_id=o_id, cancel_comment=cancel_comment, dt_agent=dt_agent, stage_setter_name=user.login_name)

    try:
        db.session.execute(order_query)
        if order_info.payment:
            h_cancel_order_process_payment(order_idn=order_info.order_idn, user_id=order_info.user_id)
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        logger.error(f'{settings.Messages.ORDER_CANCEL_ERROR} {exc}')
        return False, settings.Messages.ORDER_CANCEL_ERROR
    except Exception as exc:
        db.session.rollback()
        logger.error(str(exc))
        return False, settings.Messages.ORDER_CANCEL_ERROR

    helper_send_user_order_tg_notify(user_id=order_info.user_id, order_idn=order_info.order_idn, order_stage=settings.OrderStage.CANCELLED)
    return True, settings.Messages.ORDER_CANCEL.format(order_idn=order_info.order_idn)


def download_order_file_response(o_id: int):
    order = _load_order_for_action(o_id)
    if not order or not order.order_zip_file:
        return jsonify({'status': 'error', 'message': settings.Messages.ORDER_DOWNLOAD_FILE_ABS_ERROR}), 404

    origin_name = order.order_zip_file.origin_name
    file_system_name = order.order_zip_file.file_system_name
    if not file_system_name:
        return jsonify({'status': 'error', 'message': settings.Messages.ORDER_DOWNLOAD_FILE_ABS_ERROR}), 404

    check_status, check_message = check_order_file(order_file_name=file_system_name, o_id=o_id)
    if not check_status:
        return jsonify({'status': 'error', 'message': check_message}), 404

    return download_file_from_minio(
        object_name=file_system_name,
        bucket_name=settings.MINIO_CRM_BUCKET_NAME,
        download_name=origin_name,
    )