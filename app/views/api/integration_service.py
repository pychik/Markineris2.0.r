from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import lazyload, selectinload

from config import settings
from external_processors.config import EXTERNAL_PROCESSOR_CONFIG
from logger import logger
from markupsafe import escape
from models import ExternalProcessor, Order, OrderProcessedLog, User, db
from utilities.download import get_order_download_payload
from utilities.minio_service.services import get_s3_service
from views.crm.schema import format_upd_company, pick_upd_company

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
        model.is_automated_crm.is_(True),
        model.to_delete.isnot(True),
    )


def _eligible_orders_query():
    return (
        db.session.query(Order)
        .options(lazyload('*'))
        .filter(Order.stage == settings.OrderStage.POOL)
        # без пройденной превалидации заказ не выдаётся: у него может не быть РД
        # и не закреплена компания обработки
        .filter(Order.prevalidated_at.isnot(None))
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


# Честный Знак присылает очень объёмные тексты ошибок (десятки тысяч знаков).
# В базе держим только хвост: полезное - в конце сообщения, начало это шапка.
PROBLEM_COMMENT_LIMIT = 500


def problem_comment_tail(message: str | None) -> str:
    """Хвост сообщения об ошибке - именно он несёт причину."""
    text_value = (message or '').strip()
    if len(text_value) <= PROBLEM_COMMENT_LIMIT:
        return text_value
    return text_value[-PROBLEM_COMMENT_LIMIT:]


def ensure_upd_company(order: Order) -> None:
    """Закрепить за заказом компанию, от которой он проводится и от которой придёт УПД.

    Ставится один раз. При повторной выдаче после таймаута компания не меняется -
    иначе УПД пришёл бы от другого юрлица, чем то, под которым шла модерация.
    """
    if order.upd_company_inn or order.upd_company_name:
        return
    company = pick_upd_company(category=order.category, order_id=order.id)
    order.upd_company_name = company.display_name
    order.upd_company_inn = company.inn


# Номер УПД приходит извне и кладётся в String(100): длиннее - StringDataRightTruncation
# и потеря всего финального результата, поэтому проверяем до записи.
UPD_NUMBER_MAX_LENGTH = 100


def build_processing_info(order: Order) -> str:
    """Строка для карточки заказа - формат тот же, что набирает оператор руками.

    Значения экранируются: строка рендерится в шаблонах через `| safe`, а номер УПД
    приходит от внешнего сервиса, то есть из-за границы доверия.
    """
    company = escape(format_upd_company(order.upd_company_name, order.upd_company_inn))
    upd_number = escape((order.upd_number or '').strip())
    if company and upd_number:
        return f'{company} <br> УПД: {upd_number}'
    return str(company) or (f'УПД: {upd_number}' if upd_number else '')


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
    order.comment_problem = problem_comment_tail(message)
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


# Два независимых таймаута: сколько ждём accept и сколько ждём финальный result.
CONFIRMATION_TIMEOUT = 'confirmation'
PROCESSING_TIMEOUT = 'processing'

_TIMEOUT_COLUMNS = {
    CONFIRMATION_TIMEOUT: (
        ExternalProcessor.confirmation_timeout_seconds,
        EXTERNAL_PROCESSOR_CONFIG.confirmation_timeout_seconds,
    ),
    PROCESSING_TIMEOUT: (
        ExternalProcessor.processing_timeout_seconds,
        EXTERNAL_PROCESSOR_CONFIG.processing_timeout_seconds,
    ),
}


def _timeout_map(kind: str) -> dict[str, int]:
    column, default_timeout = _TIMEOUT_COLUMNS[kind]
    rows = db.session.query(ExternalProcessor.source_label, column).all()
    return {
        source_label: int(timeout_seconds or default_timeout)
        for source_label, timeout_seconds in rows
        if source_label
    }


def _resolve_timeout_seconds(kind: str, source_label: str | None, timeout_map: dict[str, int]) -> int:
    default_timeout = _TIMEOUT_COLUMNS[kind][1]
    if not source_label:
        return default_timeout
    return int(timeout_map.get(source_label, default_timeout))


def _min_timeout_seconds(kind: str, timeout_map: dict[str, int]) -> int:
    candidate_values = [_TIMEOUT_COLUMNS[kind][1]]
    candidate_values.extend(timeout_map.values())
    return min(value for value in candidate_values if value and value > 0)


def requeue_expired_unconfirmed_orders(timeout_seconds: int | None = None) -> int:
    timeout_map = {} if timeout_seconds is not None else _timeout_map(CONFIRMATION_TIMEOUT)
    reference_timeout = int(timeout_seconds or _min_timeout_seconds(CONFIRMATION_TIMEOUT, timeout_map))
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

    requeued_count = 0
    for order in expired_orders:
        ttl_seconds = int(
            timeout_seconds
            or _resolve_timeout_seconds(CONFIRMATION_TIMEOUT, order.stage_setter_name, timeout_map)
        )
        if not order.sent_at or (current_dt - order.sent_at).total_seconds() < ttl_seconds:
            continue

        requeued_count += 1
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

    # без commit изменения теряются: из планировщика эту функцию никто не коммитит
    if requeued_count:
        db.session.commit()
    else:
        db.session.rollback()
    return requeued_count


def mark_stale_processing_orders_as_problem(timeout_seconds: int | None = None) -> int:
    timeout_map = {} if timeout_seconds is not None else _timeout_map(PROCESSING_TIMEOUT)
    reference_timeout = int(timeout_seconds or _min_timeout_seconds(PROCESSING_TIMEOUT, timeout_map))
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

    stale_count = 0
    for order in stale_orders:
        ttl_seconds = int(
            timeout_seconds
            or _resolve_timeout_seconds(PROCESSING_TIMEOUT, order.stage_setter_name, timeout_map)
        )
        if not order.confirmed_at or (current_dt - order.confirmed_at).total_seconds() < ttl_seconds:
            continue

        stale_count += 1
        # запоминаем, какому обработчику заказ был выдан: по этой метке он потом
        # получит его в /orders/problems и только он
        owner_label = order.stage_setter_name
        _mark_order_problem(
            order=order,
            external_processor=None,
            message='Истек таймаут обработки, заказ снят с внешнего обработчика и требует решения оператора CRM',
            payload={'order_id': order.id, 'processing_timeout_seconds': ttl_seconds},
            event_type='processor_timeout',
            dispatch_token=order.dispatch_token,
            object_key=order.object_key,
        )
        # заказ подлежит уведомлению внешнего обработчика через GET /orders/problems
        order.problem_notified_at = current_dt
        order.problem_ack_at = None
        if owner_label:
            order.stage_setter_name = owner_label

    if stale_count:
        db.session.commit()
    else:
        db.session.rollback()
    return stale_count


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


def serialize_order_for_api(
    order: Order,
    source_file: dict,
    external_processor: ExternalProcessor,
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
    if order.upd_company_name:
        payload['processing_company'] = {
            'title': order.upd_company_name,
            'inn': order.upd_company_inn or '',
        }
    return payload


def claim_new_orders(external_processor: ExternalProcessor) -> tuple[list[dict], bool]:
    batch_size = external_processor.batch_size
    now = _now()
    claimed_payload = []

    requeue_expired_unconfirmed_orders()
    mark_stale_processing_orders_as_problem()

    orders, has_more = _claim_candidate_orders(batch_size)
    claim_users = _load_claim_users(orders)

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

        order.stage = settings.OrderStage.MANAGER_START
        order.status = DELIVERY_UNCONFIRMED_STATUS
        order.dispatch_token = dispatch_token
        order.object_key = object_key
        order.confirmed_at = None
        order.m_started = order.m_started or now
        order.sent_at = now
        order.stage_setter_name = external_processor.source_label
        order.problem_notified_at = None
        order.problem_ack_at = None

        log_order_event(
            order=order,
            event_type='claimed',
            message='Заказ выдан внешнему обработчику',
            payload={
                'order_id': order.id,
                'object_key': object_key,
                'processing_company': {
                    'title': order.upd_company_name,
                    'inn': order.upd_company_inn,
                },
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

    def reject(order_id, reason: str):
        rejected.append({'order_id': order_id, 'reason': reason})
        logger.warning(
            'Отклонено подтверждение заказа: order_id=%s reason=%s source=%s',
            order_id, reason, external_processor.source_label,
        )

    for item in orders_payload:
        order_id = item.get('order_id')
        dispatch_token = (item.get('dispatch_token') or '').strip()
        status = (item.get('status') or '').strip()
        message = (item.get('message') or 'Заказ подтвержден внешним обработчиком').strip()

        if not order_id or not dispatch_token:
            reject(order_id, 'order_id and dispatch_token are required')
            continue

        if status != 'accepted':
            reject(order_id, 'status must be accepted')
            continue

        order = _get_order_for_dispatch(
            order_id=order_id,
            dispatch_token=dispatch_token,
            allowed_stages=(settings.OrderStage.MANAGER_START,),
        )
        if not order:
            reject(order_id, 'invalid dispatch token')
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
    upd_number = (body.get('upd_number') or '').strip() or None

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
        if upd_number and len(upd_number) > UPD_NUMBER_MAX_LENGTH:
            _mark_order_problem(
                order=order,
                external_processor=external_processor,
                message=f'Номер УПД длиннее допустимых {UPD_NUMBER_MAX_LENGTH} символов',
                payload=body,
                event_type='result_invalid_upd_number',
                dispatch_token=dispatch_token,
                object_key=object_key,
            )
            db.session.commit()
            return True, 'problem'
        if not upd_number:
            _mark_order_problem(
                order=order,
                external_processor=external_processor,
                message='Внешний обработчик не передал номер УПД для финального результата',
                payload=body,
                event_type='result_missing_upd_number',
                dispatch_token=dispatch_token,
                object_key=object_key,
            )
            db.session.commit()
            return True, 'problem'
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
        order.upd_number = upd_number
        order.processing_info = build_processing_info(order)
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
    order.comment_problem = problem_comment_tail(message) if message else order.comment_problem
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

def list_timeout_problem_orders(external_processor: ExternalProcessor, limit: int | None = None) -> list[dict]:
    """Заказы, снятые с обработчика по таймауту и ещё не подтверждённые им.

    Push в сторону LiteMark невозможен - их контур закрыт снаружи, поэтому обмен построен
    на опросе: они забирают список здесь и подтверждают через /orders/{id}/problem-ack.
    """
    batch_size = int(limit or external_processor.batch_size)
    orders = (
        db.session.query(Order)
        .options(lazyload('*'))
        .filter(Order.stage == settings.OrderStage.MANAGER_PROBLEM)
        .filter(Order.problem_notified_at.isnot(None))
        .filter(Order.problem_ack_at.is_(None))
        .filter(Order.dispatch_token.isnot(None))
        # только свои заказы: иначе второй обработчик увидит чужие dispatch-токены
        .filter(Order.stage_setter_name == external_processor.source_label)
        .filter(*_external_processing_order_filter(Order))
        .order_by(Order.problem_notified_at.asc(), Order.id.asc())
        .limit(batch_size)
        .all()
    )

    if orders:
        logger.warning(
            'Проблемные заказы отданы обработчику %s: %s',
            external_processor.source_label,
            [order.id for order in orders],
        )

    return [
        {
            'id': order.id,
            'dispatch_token': order.dispatch_token,
            'reason': 'processing_timeout',
            'message': order.comment_problem or 'Истек таймаут обработки, заказ снят с внешнего обработчика',
            'happened_at': order.problem_notified_at.isoformat() if order.problem_notified_at else None,
        }
        for order in orders
    ]


def acknowledge_problem_order(order_id: int, body: dict, external_processor: ExternalProcessor) -> tuple[bool, str]:
    """Обработчик подтвердил, что снял заказ с обработки и больше по нему ничего не пришлёт."""
    dispatch_token = (body.get('dispatch_token') or '').strip()
    message = (body.get('message') or 'Внешний обработчик подтвердил снятие заказа').strip()

    if not dispatch_token:
        return False, 'dispatch_token is required'

    order = (
        db.session.query(Order)
        .filter(Order.id == order_id)
        .filter(Order.dispatch_token == dispatch_token)
        .filter(Order.problem_notified_at.isnot(None))
        .filter(Order.stage_setter_name == external_processor.source_label)
        .filter(*_external_processing_order_filter(Order))
        .first()
    )
    if not order:
        return False, 'invalid dispatch token'

    if order.problem_ack_at is None:
        order.problem_ack_at = _now()
        log_order_event(
            order=order,
            event_type='problem_ack',
            message=message,
            payload=body,
            dispatch_token=dispatch_token,
            source=external_processor.source_label,
        )
        db.session.commit()

    return True, 'acknowledged'


def _order_positions_without_rd(order: Order) -> int:
    """Сколько позиций заказа осталось без разрешительной документации."""
    missing = 0
    for category_attr in ('shoes', 'clothes', 'socks', 'linen', 'parfum', 'cosmetics'):
        for position in getattr(order, category_attr, None) or ():
            if not getattr(position, 'rd_name', None) and not getattr(position, 'rd_date', None):
                missing += 1
    return missing


def prevalidate_order(order: Order) -> tuple[bool, str]:
    """Подготовить заказ к выдаче: закрепить компанию и добить недостающую РД.

    Возвращает (готов, сообщение). Заказ без отметки превалидации в выдачу не попадает.
    """
    ensure_upd_company(order)

    missing_rd = _order_positions_without_rd(order)
    if missing_rd:
        # ponytail: подбор РД через Тезаурус ещё не подключён - у них нет такого метода,
        # см. docs/litemark-todo.md, пункт 2. Пока фиксируем факт и пропускаем заказ дальше:
        # блокировать выдачу до появления подбора значит остановить весь поток.
        # Когда метод появится - здесь вызов подбора, а при неудаче return False.
        return True, f'РД отсутствует у позиций: {missing_rd}. Автоподбор пока не подключен'

    return True, 'Превалидация пройдена'


def prevalidate_pending_orders(limit: int = 100) -> int:
    """Прогнать превалидацию по заказам, которые её ещё не проходили."""
    orders = (
        db.session.query(Order)
        .filter(Order.stage == settings.OrderStage.POOL)
        .filter(Order.prevalidated_at.is_(None))
        .filter(*_external_processing_order_filter(Order))
        .order_by(Order.crm_created_at.asc(), Order.id.asc())
        .limit(limit)
        .all()
    )
    if not orders:
        return 0

    prepared = 0
    for order in orders:
        try:
            is_ready, message = prevalidate_order(order)
        except Exception:
            logger.exception('Ошибка превалидации заказа order_id=%s', order.id)
            db.session.rollback()
            continue

        if not is_ready:
            _mark_order_problem(
                order=order,
                external_processor=None,
                message=message,
                payload={'order_id': order.id},
                event_type='prevalidation_failed',
            )
            db.session.commit()
            continue

        order.prevalidated_at = _now()
        prepared += 1
        log_order_event(
            order=order,
            event_type='prevalidated',
            message=message,
            payload={
                'order_id': order.id,
                'upd_company': order.upd_company_name,
                'upd_company_inn': order.upd_company_inn,
            },
        )
        db.session.commit()

    return prepared
