import hashlib
import hmac
from time import time

from flask import jsonify, request
from redis import Redis
from redis.exceptions import RedisError

from config import settings
from external_processors.service import allowed_ips_as_list
from external_processors.service import (
    get_active_external_processor_by_key_id,
    has_active_external_processors,
)
from logger import logger

from . import api
from .integration_service import (
    accept_orders,
    apply_result_update,
    apply_status_update,
    claim_new_orders,
)

MAX_REQUEST_RATE_LIMIT = 50


def _json_response(payload: dict, status_code: int = 200, headers: dict | None = None):
    response = jsonify(payload)
    response.status_code = status_code
    if headers:
        for key, value in headers.items():
            response.headers[key] = value
    return response


def _error(message: str, code: str, status_code: int):
    return _json_response({'status': 'error', 'message': message, 'code': code}, status_code)


def _nonce_storage() -> Redis:
    return Redis.from_url(settings.REDIS_CONN)


def _rate_limit_key(key_id: str) -> str:
    return f'external-processing:ratelimit:{key_id}:{int(time()) // 60}'


def _check_rate_limit(nonce_storage: Redis, key_id: str):
    rate_limit_key = _rate_limit_key(key_id)
    current_requests = nonce_storage.incr(rate_limit_key)
    if current_requests == 1:
        nonce_storage.expire(rate_limit_key, 60)

    if current_requests > MAX_REQUEST_RATE_LIMIT:
        return _error('Rate limit exceeded', 'rate_limited', 429)

    return None


def _remote_ip() -> str:
    return request.remote_addr or ''


def _sha256_signature(shared_secret: str, timestamp: str, nonce: str) -> str:
    signature_bytes = b'\n'.join([
        shared_secret.encode('utf-8'),
        timestamp.encode('utf-8'),
        nonce.encode('utf-8'),
    ])
    return hashlib.sha256(signature_bytes).hexdigest()


def _resolve_processor_request():
    key_id = (request.headers.get('X-Integration-Key-Id') or '').strip()
    timestamp = (request.headers.get('X-Integration-Timestamp') or '').strip()
    nonce = (request.headers.get('X-Integration-Nonce') or '').strip()
    signature = (request.headers.get('X-Integration-Signature') or '').strip()

    if not all([key_id, timestamp, nonce, signature]):
        return None, _error('Missing authentication headers', 'missing_headers', 401)

    try:
        processor = get_active_external_processor_by_key_id(key_id)
        if processor is None:
            if not has_active_external_processors():
                return None, _error('Integration auth is not configured', 'integration_not_configured', 500)
            return None, _error('Unknown key id', 'unknown_key_id', 403)
    except Exception:
        logger.exception('Ошибка разрешения внешнего обработчика для webhook-а')
        return None, _error('Integration auth is temporarily unavailable', 'integration_temporarily_unavailable', 503)

    try:
        timestamp_value = int(timestamp)
    except ValueError:
        return None, _error('Invalid timestamp', 'invalid_timestamp', 400)

    if abs(int(time()) - timestamp_value) > processor.ttl_seconds:
        return None, _error('Expired timestamp', 'expired_timestamp', 401)

    allowed_ips = allowed_ips_as_list(processor.allowed_ips)
    if allowed_ips and _remote_ip() not in allowed_ips:
        return None, _error('IP is not allowed', 'ip_not_allowed', 403)

    expected_signature = _sha256_signature(
        shared_secret=processor.shared_secret,
        timestamp=timestamp,
        nonce=nonce,
    )

    if not hmac.compare_digest(expected_signature, signature):
        return None, _error('Invalid signature', 'invalid_signature', 401)

    try:
        nonce_storage = _nonce_storage()
        nonce_key = f'external-processing:nonce:{key_id}:{nonce}'
        if not nonce_storage.set(nonce_key, '1', ex=processor.nonce_ttl_seconds, nx=True):
            return None, _error('Replay nonce', 'replay_nonce', 409)

        rate_limit_error = _check_rate_limit(nonce_storage, key_id)
        if rate_limit_error:
            return None, rate_limit_error
    except RedisError:
        logger.exception('Ошибка Redis при проверке nonce/rate limit внешнего обработчика')
        return None, _error('Integration auth is temporarily unavailable', 'integration_temporarily_unavailable', 503)

    return processor, None


@api.get('/webhook/orders')
def api_claim_orders():
    processor, auth_error = _resolve_processor_request()
    if auth_error:
        return auth_error

    try:
        orders, has_more = claim_new_orders(external_processor=processor)
        headers = {
            'X-Orders-Returned': str(len(orders)),
            'X-Orders-Limit-Applied': str(processor.batch_size),
            'X-Orders-Has-More': 'true' if has_more else 'false',
        }
        if not has_more:
            headers['X-Orders-Remaining'] = '0'
        return _json_response(
            {
                'status': 'ok',
                'message': 'Orders claimed successfully',
                'data': {'orders': orders},
            },
            headers=headers,
        )
    except Exception:
        logger.exception('Ошибка выдачи заказов для внешнего обработчика')
        return _error('Failed to claim orders', 'claim_failed', 500)


@api.post('/webhook/orders/accept')
def api_accept_orders():
    processor, auth_error = _resolve_processor_request()
    if auth_error:
        return auth_error

    body = request.get_json(silent=True) or {}
    orders_payload = body.get('orders')
    if not isinstance(orders_payload, list):
        return _error('orders list is required', 'invalid_payload', 400)

    try:
        accepted, rejected = accept_orders(orders_payload, external_processor=processor)
        return _json_response(
            {
                'status': 'ok',
                'message': 'Orders accepted successfully',
                'data': {
                    'accepted': accepted,
                    'rejected': rejected,
                },
            }
        )
    except Exception:
        logger.exception('Ошибка подтверждения заказов внешним обработчиком')
        return _error('Failed to accept orders', 'accept_failed', 500)


@api.post('/webhook/orders/<int:order_id>/status')
def api_update_order_status(order_id: int):
    processor, auth_error = _resolve_processor_request()
    if auth_error:
        return auth_error

    body = request.get_json(silent=True) or {}
    try:
        success, result = apply_status_update(order_id=order_id, body=body, external_processor=processor)
        if not success:
            code = 'invalid_dispatch_token' if result == 'invalid dispatch token' else 'invalid_payload'
            status_code = 404 if code == 'invalid_dispatch_token' else 400
            return _error(result, code, status_code)

        return _json_response(
            {
                'status': 'ok',
                'message': 'Status updated',
                'data': {'order_id': order_id, 'status': result},
            }
        )
    except Exception:
        logger.exception('Ошибка обновления промежуточного статуса внешнего обработчика')
        return _error('Failed to update status', 'status_update_failed', 500)


@api.post('/webhook/orders/<int:order_id>/result')
def api_update_order_result(order_id: int):
    processor, auth_error = _resolve_processor_request()
    if auth_error:
        return auth_error

    body = request.get_json(silent=True) or {}
    try:
        success, result = apply_result_update(order_id=order_id, body=body, external_processor=processor)
        if not success:
            code_map = {
                'invalid dispatch token': ('invalid_dispatch_token', 404),
                'object key mismatch': ('object_key_mismatch', 400),
                'uploaded object not found': ('uploaded_object_not_found', 400),
                'unsupported final status': ('unsupported_status', 400),
                'object_key is required for processed result': ('invalid_payload', 400),
                'dispatch_token is required': ('invalid_payload', 400),
            }
            code, status_code = code_map.get(result, ('invalid_payload', 400))
            return _error(result, code, status_code)

        return _json_response(
            {
                'status': 'ok',
                'message': 'Result accepted',
                'data': {'order_id': order_id, 'status': result},
            }
        )
    except Exception:
        logger.exception('Ошибка обработки финального результата внешнего обработчика')
        return _error('Failed to accept result', 'result_update_failed', 500)