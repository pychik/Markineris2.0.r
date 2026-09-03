from functools import wraps

from flask import Blueprint, jsonify, request
from flask_login import current_user
from pydantic import ValidationError

from config import settings
from external_processors.schemas import (
    ExternalProcessorCreateSchema,
    ExternalProcessorUpdateSchema,
)
from external_processors.service import (
    create_external_processor,
    delete_external_processor,
    get_external_processor,
    list_external_processors,
    serialize_external_processor,
    update_external_processor,
)
from logger import logger

external_processors_admin = Blueprint('external_processors_admin', __name__)


def _admin_required_json(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'status': 'error', 'message': 'Требуется аутентификация'}), 401
        if current_user.status is True and current_user.role == settings.SUPER_USER:
            return func(*args, **kwargs)
        return jsonify({'status': 'error', 'message': 'Недостаточно прав'}), 403

    return wrapper


def _not_found_response():
    return jsonify({'status': 'error', 'message': 'Внешний обработчик не найден'}), 404


@external_processors_admin.get('/external_processors')
@_admin_required_json
def external_processors_list():
    processors = [serialize_external_processor(item) for item in list_external_processors()]
    return jsonify({'status': 'ok', 'data': {'items': processors}})


@external_processors_admin.get('/external_processors/<int:external_processor_id>')
@_admin_required_json
def external_processors_detail(external_processor_id: int):
    processor = get_external_processor(external_processor_id)
    if processor is None:
        return _not_found_response()
    return jsonify({'status': 'ok', 'data': serialize_external_processor(processor, include_secret=True)})


@external_processors_admin.post('/external_processors')
@_admin_required_json
def external_processors_create():
    payload = request.get_json(silent=True) or {}
    try:
        data = ExternalProcessorCreateSchema(**payload).model_dump(exclude_unset=True)
        processor = create_external_processor(data)
    except ValidationError as exc:
        return jsonify({'status': 'error', 'message': 'Некорректные данные', 'errors': exc.errors()}), 400
    except ValueError as exc:
        return jsonify({'status': 'error', 'message': str(exc)}), 409
    except Exception:
        logger.exception('Ошибка создания внешнего обработчика')
        return jsonify({'status': 'error', 'message': 'Не удалось создать внешнего обработчика'}), 500

    return jsonify({'status': 'ok', 'data': serialize_external_processor(processor, include_secret=True)}), 201


@external_processors_admin.put('/external_processors/<int:external_processor_id>')
@_admin_required_json
def external_processors_update(external_processor_id: int):
    processor = get_external_processor(external_processor_id)
    if processor is None:
        return _not_found_response()

    payload = request.get_json(silent=True) or {}
    try:
        data = ExternalProcessorUpdateSchema(**payload).model_dump(exclude_unset=True)
        processor = update_external_processor(processor, data)
    except ValidationError as exc:
        return jsonify({'status': 'error', 'message': 'Некорректные данные', 'errors': exc.errors()}), 400
    except ValueError as exc:
        return jsonify({'status': 'error', 'message': str(exc)}), 409
    except Exception:
        logger.exception('Ошибка обновления внешнего обработчика')
        return jsonify({'status': 'error', 'message': 'Не удалось обновить внешнего обработчика'}), 500

    return jsonify({'status': 'ok', 'data': serialize_external_processor(processor, include_secret=True)})


@external_processors_admin.delete('/external_processors/<int:external_processor_id>')
@_admin_required_json
def external_processors_delete(external_processor_id: int):
    processor = get_external_processor(external_processor_id)
    if processor is None:
        return _not_found_response()

    try:
        delete_external_processor(processor)
    except Exception:
        logger.exception('Ошибка удаления внешнего обработчика')
        return jsonify({'status': 'error', 'message': 'Не удалось удалить внешнего обработчика'}), 500

    return jsonify({'status': 'ok', 'message': 'Внешний обработчик удален'})
