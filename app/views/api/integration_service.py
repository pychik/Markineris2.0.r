from __future__ import annotations

from datetime import datetime, timedelta
from random import choice
from uuid import uuid4

from sqlalchemy.orm import lazyload, selectinload

from config import settings
from external_processors.config import EXTERNAL_PROCESSOR_CONFIG
from models import ExternalProcessor, Order, OrderProcessedLog, ProcessingCompany, User, UserProcessingCompany, db
from utilities.download import get_order_download_payload
from utilities.minio_service.services import get_s3_service

DELIVERY_UNCONFIRMED_STATUS = 'delivery_unconfirmed'
EXTERNAL_PROCESSING_SYSTEM_SOURCE = 'external_processor'
FINAL_RESULT_STATUSES = {'processed', 'failed', 'problem', 'error'}
RESULT_CALLBACK_ALLOWED_STAGES = (
    settings.OrderStage.MANAGER_START,
    settings.OrderStage.MANAGER_PROBLEM,
    settings.OrderStage.CRM_PROCESSED,
)


def _now() -> datetime:
    return datetime.now()


def _external_processing_order_filter(model=Order):
    return (
        model.is_moderation.is_(True),
        model.is_automated_crm.is_(True),
        model.to_delete.isnot(True),
    )


def _eligible_orders_query():
    return (
        db.session.query(Order)
        .options(lazyload('*'))
        .filter(Order.stage == settings.OrderStage.POOL)
        .filter(*_external_processing_order_filter(Order))
    )


def count_available_orders() -> int:
    return _eligible_orders_query().count()


def _claim_candidate_orders(batch_size: int) -> tuple[list[Order], bool]:
    candidate_orders = (
        _eligible_orders_query()
        .order_by(Order.crm_created_at.asc(), Order.id.asc())
        .with_for_update(skip_locked=True, of=Order)
        .limit(batch_size + 1)
        .all()
    )
    has_more = len(candidate_orders) > batch_size
    return candidate_orders[:batch_size], has_more


def _load_claim_users(orders: list[Order]) -> dict[int, User]:
    user_ids = {order.user_id for order in orders if order.user_id}
    if not user_ids:
        return {}

    rows = (
        db.session.query(User)
        .options(lazyload('*'), selectinload(User.partners))
        .filter(User.id.in_(user_ids))
        .all()
    )
    return {user.id: user for user in rows}


def _pick_processing_company_payload_map(orders: list[Order]) -> dict[int, dict]:
    user_ids = {order.user_id for order in orders if order.user_id}
    if not user_ids:
        return {}

    company_rows = (
        db.session.query(UserProcessingCompany.user_id, ProcessingCompany.title, ProcessingCompany.inn)
        .join(ProcessingCompany, UserProcessingCompany.company_id == ProcessingCompany.id)
        .filter(UserProcessingCompany.user_id.in_(user_ids))
        .filter(UserProcessingCompany.is_approved.is_(True))
        .filter(ProcessingCompany.is_active.is_(True))
        .order_by(UserProcessingCompany.user_id.asc(), UserProcessingCompany.slot.asc(), ProcessingCompany.id.asc())
        .all()
    )

    grouped_companies: dict[int, list[dict]] = {}
    for user_id, title, inn in company_rows:
        grouped_companies.setdefault(user_id, []).append({'title': title, 'inn': inn})

    return {
        user_id: choice(companies)
        for user_id, companies in grouped_companies.items()
        if companies
    }


def _mark_order_problem(
    order: Order,
    external_processor: ExternalProcessor | None,
    message: str,
    payload: dict | None = None,
    status: str = 'problem',
    event_type: str = 'result_failed',
    dispatch_token: str | None = None,
    object_key: str | None = None,
):
    order.status = status
    order.stage = settings.OrderStage.MANAGER_PROBLEM
    order.cp_created = _now()
    order.closed_at = None
    order.m_finished = None
    order.processed = False
    order.external_problem = True
    order.comment_problem = message[:230]
    order.stage_setter_name = external_processor.source_label if external_processor else EXTERNAL_PROCESSING_SYSTEM_SOURCE

    log_order_event(
        order=order,
        event_type=event_type,
        message=message,
        payload=payload,
        status=status,
        object_key=object_key,
        dispatch_token=dispatch_token,
        source=external_processor.source_label if external_processor else None,
    )


def _confirmation_timeout_map() -> dict[str, int]:
    default_timeout = EXTERNAL_PROCESSOR_CONFIG.confirmation_timeout_seconds
    rows = (
        db.session.query(ExternalProcessor.source_label, ExternalProcessor.confirmation_timeout_seconds)
        .all()
    )
    return {
        source_label: int(timeout_seconds or default_timeout)
        for source_label, timeout_seconds in rows
        if source_label
    }


def _resolve_confirmation_timeout_seconds(source_label: str | None, timeout_map: dict[str, int]) -> int:
    default_timeout = EXTERNAL_PROCESSOR_CONFIG.confirmation_timeout_seconds
    if not source_label:
        return default_timeout
    return int(timeout_map.get(source_label, default_timeout))


def _min_confirmation_timeout_seconds(timeout_map: dict[str, int]) -> int:
    default_timeout = EXTERNAL_PROCESSOR_CONFIG.confirmation_timeout_seconds
    candidate_values = [default_timeout]
    candidate_values.extend(timeout_map.values())
    return min(value for value in candidate_values if value and value > 0)


def requeue_expired_unconfirmed_orders(timeout_seconds: int | None = None) -> int:
    timeout_map = {} if timeout_seconds is not None else _confirmation_timeout_map()
    reference_timeout = int(timeout_seconds or _min_confirmation_timeout_seconds(timeout_map))
    current_dt = _now()
    expires_before = current_dt - timedelta(seconds=reference_timeout)
    expired_orders = (
        db.session.query(Order)
        .filter(Order.stage == settings.OrderStage.MANAGER_START)
        .filter(Order.status == DELIVERY_UNCONFIRMED_STATUS)
        .filter(Order.confirmed_at.is_(None))
        .filter(Order.sent_at.isnot(None))
        .filter(Order.sent_at < expires_before)
        .filter(*_external_processing_order_filter(Order))
        .with_for_update(skip_locked=True, of=Order)
        .all()
    )

    for order in expired_orders:
        ttl_seconds = int(timeout_seconds or _resolve_confirmation_timeout_seconds(order.stage_setter_name, timeout_map))
        if not order.sent_at or (current_dt - order.sent_at).total_seconds() < ttl_seconds:
            continue

        expired_dispatch_token = order.dispatch_token
        expired_object_key = order.object_key
        order.stage = settings.OrderStage.POOL
        order.status = None
        order.dispatch_token = None
        order.object_key = None
        order.confirmed_at = None
        order.sent_at = None
        order.p_started = current_dt
        order.m_started = None
        order.manager_id = None
        order.cp_created = None
        order.external_problem = False
        order.comment_problem = ''
        order.stage_setter_name = EXTERNAL_PROCESSING_SYSTEM_SOURCE

        log_order_event(
            order=order,
            event_type='claim_expired',
            message='Истекло подтверждение выдачи внешнему обработчику, заказ возвращен в пул',
            payload={'order_id': order.id},
            status='expired',
            object_key=expired_object_key,
            dispatch_token=expired_dispatch_token,
        )

    return len(expired_orders)


def mark_stale_processing_orders_as_problem(timeout_seconds: int | None = None) -> int:
    timeout_map = {} if timeout_seconds is not None else _confirmation_timeout_map()
    reference_timeout = int(timeout_seconds or _min_confirmation_timeout_seconds(timeout_map))
    current_dt = _now()
    expires_before = current_dt - timedelta(seconds=reference_timeout)
    stale_orders = (
        db.session.query(Order)
        .filter(Order.stage == settings.OrderStage.MANAGER_START)
        .filter(Order.confirmed_at.isnot(None))
        .filter(Order.confirmed_at < expires_before)
        .filter(*_external_processing_order_filter(Order))
        .with_for_update(skip_locked=True, of=Order)
        .all()
    )

    for order in stale_orders:
        ttl_seconds = int(timeout_seconds or _resolve_confirmation_timeout_seconds(order.stage_setter_name, timeout_map))
        if not order.confirmed_at or (current_dt - order.confirmed_at).total_seconds() < ttl_seconds:
            continue

        _mark_order_problem(
            order=order,
            external_processor=None,
            message='Истек таймаут ответа внешнего обработчика, заказ требует решения оператора CRM',
            payload={'order_id': order.id},
            event_type='processor_timeout',
            dispatch_token=order.dispatch_token,
            object_key=order.object_key,
        )

    return len(stale_orders)


def create_object_key(order_id: int, dispatch_token: str, external_processor: ExternalProcessor) -> str:
    prefix = (external_processor.minio_prefix or '').strip('/')
    if prefix:
        return f'{prefix}/{order_id}/{dispatch_token}/result.zip'
    return f'{order_id}/{dispatch_token}/result.zip'


def log_order_event(
    order: Order,
    event_type: str,
    message: str,
    payload: dict | None = None,
    status: str | None = None,
    object_key: str | None = None,
    dispatch_token: str | None = None,
    source: str | None = None,
):
    db.session.add(
        OrderProcessedLog(
            order_id=order.id,
            event_type=event_type,
            status=status or order.status,
            dispatch_token=dispatch_token or order.dispatch_token,
            stage=order.stage,
            message=message,
            object_key=object_key or order.object_key,
            source=source or EXTERNAL_PROCESSING_SYSTEM_SOURCE,
            payload=payload,
        )
    )


def _pick_processing_company_payload(order: Order) -> dict | None:
    if not order or not order.user_id:
        return None

    company_rows = (
        db.session.query(ProcessingCompany.title, ProcessingCompany.inn)
        .join(UserProcessingCompany, UserProcessingCompany.company_id == ProcessingCompany.id)
        .filter(UserProcessingCompany.user_id == order.user_id)
        .filter(UserProcessingCompany.is_approved.is_(True))
        .filter(ProcessingCompany.is_active.is_(True))
        .order_by(UserProcessingCompany.slot.asc(), ProcessingCompany.id.asc())
        .all()
    )
    if not company_rows:
        return None

    selected_company = choice(company_rows)
    return {
        'title': selected_company.title,
        'inn': selected_company.inn,
    }


def serialize_order_for_api(
    order: Order,
    source_file: dict,
    external_processor: ExternalProcessor,
    processing_company: dict | None = None,
) -> dict:
    payload = {
        'id': order.id,
        'dispatch_token': order.dispatch_token,
        'source_file': source_file,
        'upload': {
            'bucket': external_processor.minio_bucket_name,
            'object_key': order.object_key,
        },
    }
    if processing_company:
        payload['processing_company'] = processing_company
    return payload


def claim_new_orders(external_processor: ExternalProcessor) -> tuple[list[dict], bool]:
    batch_size = external_processor.batch_size
    now = _now()
    claimed_payload = []

    requeue_expired_unconfirmed_orders()
    mark_stale_processing_orders_as_problem()

    orders, has_more = _claim_candidate_orders(batch_size)
    claim_users = _load_claim_users(orders)
    processing_company_map = _pick_processing_company_payload_map(orders)

    for order in orders:
        source_file = get_order_download_payload(
            order.id,
            order=order,
            user=claim_users.get(order.user_id),
        )
        if not source_file:
            _mark_order_problem(
                order=order,
                external_processor=external_processor,
                message='Не удалось подготовить исходный файл для внешнего обработчика',
                payload={'order_id': order.id},
                event_type='claim_failed_missing_source',
                dispatch_token=order.dispatch_token,
                object_key=order.object_key,
            )
            continue

        dispatch_token = uuid4().hex
        object_key = create_object_key(order.id, dispatch_token, external_processor=external_processor)
        processing_company = processing_company_map.get(order.user_id)

        order.stage = settings.OrderStage.MANAGER_START
        order.status = DELIVERY_UNCONFIRMED_STATUS
        order.dispatch_token = dispatch_token
        order.object_key = object_key
        order.confirmed_at = None
        order.m_started = order.m_started or now
        order.sent_at = now
        order.stage_setter_name = external_processor.source_label

        log_order_event(
            order=order,
            event_type='claimed',
            message='Заказ выдан внешнему обработчику',
            payload={
                'order_id': order.id,
                'object_key': object_key,
                'processing_company': processing_company,
            },
            status=DELIVERY_UNCONFIRMED_STATUS,
            object_key=object_key,
            dispatch_token=dispatch_token,
            source=external_processor.source_label,
        )

        claimed_payload.append(
            serialize_order_for_api(
                order,
                source_file=source_file,
                external_processor=external_processor,
                processing_company=processing_company,
            )
        )

    db.session.commit()
    return claimed_payload, has_more


def _get_order_for_dispatch(
    order_id: int,
    dispatch_token: str,
    allowed_stages: tuple[int, ...] | None = None,
) -> Order | None:
    query = (
        db.session.query(Order)
        .filter(Order.id == order_id)
        .filter(Order.dispatch_token == dispatch_token)
        .filter(*_external_processing_order_filter(Order))
    )
    if allowed_stages:
        query = query.filter(Order.stage.in_(allowed_stages))
    return query.first()


def accept_orders(orders_payload: list[dict], external_processor: ExternalProcessor) -> tuple[list[int], list[dict]]:
    accepted = []
    rejected = []
    now = _now()

    for item in orders_payload:
        order_id = item.get('order_id')
        dispatch_token = (item.get('dispatch_token') or '').strip()
        status = (item.get('status') or '').strip()
        message = (item.get('message') or 'Заказ подтвержден внешним обработчиком').strip()

        if not order_id or not dispatch_token:
            rejected.append({'order_id': order_id, 'reason': 'order_id and dispatch_token are required'})
            continue

        if status != 'accepted':
            rejected.append({'order_id': order_id, 'reason': 'status must be accepted'})
            continue

        order = _get_order_for_dispatch(
            order_id=order_id,
            dispatch_token=dispatch_token,
            allowed_stages=(settings.OrderStage.MANAGER_START,),
        )
        if not order:
            rejected.append({'order_id': order_id, 'reason': 'invalid dispatch token'})
            continue

        if order.confirmed_at is None:
            order.confirmed_at = now
            order.status = status
            order.stage_setter_name = external_processor.source_label
            log_order_event(
                order=order,
                event_type='accepted',
                message=message,
                payload=item,
                status=status,
                dispatch_token=dispatch_token,
                source=external_processor.source_label,
            )

        accepted.append(order.id)

    db.session.commit()
    return accepted, rejected


def apply_status_update(order_id: int, body: dict, external_processor: ExternalProcessor) -> tuple[bool, str]:
    dispatch_token = (body.get('dispatch_token') or '').strip()
    status = (body.get('status') or '').strip()
    message = (body.get('message') or 'Статус обработки обновлен').strip()

    if not dispatch_token:
        return False, 'dispatch_token is required'
    if not status:
        return False, 'status is required'
    if status in FINAL_RESULT_STATUSES:
        return False, 'final statuses are not allowed in /status'

    order = _get_order_for_dispatch(
        order_id=order_id,
        dispatch_token=dispatch_token,
        allowed_stages=(settings.OrderStage.MANAGER_START,),
    )
    if not order:
        return False, 'invalid dispatch token'

    if order.confirmed_at is None:
        order.confirmed_at = _now()

    order.status = status
    order.stage_setter_name = external_processor.source_label
    log_order_event(
        order=order,
        event_type='status_updated',
        message=message,
        payload=body,
        status=status,
        dispatch_token=dispatch_token,
        source=external_processor.source_label,
    )
    db.session.commit()
    return True, status


def apply_result_update(order_id: int, body: dict, external_processor: ExternalProcessor) -> tuple[bool, str]:
    dispatch_token = (body.get('dispatch_token') or '').strip()
    status = (body.get('status') or '').strip()
    message = (body.get('message') or '').strip()
    object_key = (body.get('object_key') or '').strip() or None

    if not dispatch_token:
        return False, 'dispatch_token is required'
    if status not in FINAL_RESULT_STATUSES:
        return False, 'unsupported final status'

    order = _get_order_for_dispatch(
        order_id=order_id,
        dispatch_token=dispatch_token,
        allowed_stages=RESULT_CALLBACK_ALLOWED_STAGES,
    )
    if not order:
        return False, 'invalid dispatch token'

    if status == 'processed':
        if not object_key:
            _mark_order_problem(
                order=order,
                external_processor=external_processor,
                message='Внешний обработчик не передал object_key для финального результата',
                payload=body,
                event_type='result_invalid_payload',
                dispatch_token=dispatch_token,
            )
            db.session.commit()
            return True, 'problem'
        if object_key != order.object_key:
            _mark_order_problem(
                order=order,
                external_processor=external_processor,
                message='Внешний обработчик передал object_key, который не совпадает с ожидаемым',
                payload=body,
                event_type='result_invalid_object_key',
                dispatch_token=dispatch_token,
                object_key=object_key,
            )
            db.session.commit()
            return True, 'problem'
        if not get_s3_service().object_exists(
            object_name=object_key,
            bucket_name=external_processor.minio_bucket_name,
        ):
            _mark_order_problem(
                order=order,
                external_processor=external_processor,
                message='Финальный файл внешнего обработчика не найден в объектном хранилище',
                payload=body,
                event_type='result_missing_object',
                dispatch_token=dispatch_token,
                object_key=object_key,
            )
            db.session.commit()
            return True, 'problem'

        if order.stage == settings.OrderStage.CRM_PROCESSED and order.status == 'processed':
            return True, 'processed'

        order.status = status
        order.stage = settings.OrderStage.CRM_PROCESSED
        order.closed_at = _now()
        order.processed = True
        order.external_problem = False
        order.comment_problem = ''
        order.stage_setter_name = external_processor.source_label
        log_order_event(
            order=order,
            event_type='result_processed',
            message=message or 'Заказ успешно обработан внешним обработчиком',
            payload=body,
            status=status,
            object_key=object_key,
            dispatch_token=dispatch_token,
            source=external_processor.source_label,
        )
        db.session.commit()
        return True, status

    if order.stage == settings.OrderStage.MANAGER_PROBLEM and order.status == status:
        return True, status

    order.status = status
    order.stage = settings.OrderStage.MANAGER_PROBLEM
    order.cp_created = _now()
    order.external_problem = True
    order.comment_problem = message[:230] if message else order.comment_problem
    order.stage_setter_name = external_processor.source_label
    log_order_event(
        order=order,
        event_type='result_failed',
        message=message or 'Внешний обработчик завершил обработку с ошибкой',
        payload=body,
        status=status,
        dispatch_token=dispatch_token,
        source=external_processor.source_label,
    )
    db.session.commit()
    return True, status