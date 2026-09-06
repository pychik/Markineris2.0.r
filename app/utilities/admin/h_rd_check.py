import uuid
from functools import wraps

from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from rq import Queue

from config import settings
from fsa.circuit_breaker import STATE_CLOSED
from fsa.client import get_fsa_circuit_breaker
from fsa.constants import DOC_TYPE_CERTIFICATE, DOC_TYPE_DECLARATION
from fsa.job_store import RdCheckJobStore
from fsa.tasks import check_rd_task
from redis_queue.connection import conn
from tezaurus.runtime_catalogs import get_all_countries, get_clothes_all_tnved, get_clothes_tnved_types
from utilities.categories_data.subcategories_data import ClothesSubcategories

DOC_TYPE_OPTIONS = (
    (DOC_TYPE_DECLARATION, settings.RD_TYPES[0]),
    (DOC_TYPE_CERTIFICATE, settings.RD_TYPES[1]),
)

# демо ограничен категориями "одежда" (базовая подкатегория) и "обувь", как в реальных шагах оформления заказа
CLOTHES_SUBCATEGORY = ClothesSubcategories.common.value

# доступ к демо: суперпользователь либо тестовый аккаунт для показа руководству
# (тот же список, что и на плитке "Тестирование РД" на странице выбора категории)
RD_CHECK_ALLOWED_EMAILS = {"test_cosmetics@markineris.com"}


def rd_check_access_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.status is True and (
            current_user.role == settings.SUPER_USER or current_user.email in RD_CHECK_ALLOWED_EMAILS
        ):
            return func(*args, **kwargs)
        flash(message=settings.Messages.SUPERUSER_REQUIRED, category='error')
        return redirect(url_for('main.enter'))

    return wrapper


def h_rd_check_main():
    return render_template(
        'admin/rd_check/main.html',
        doc_type_options=DOC_TYPE_OPTIONS,
        subcategory=CLOTHES_SUBCATEGORY,
        category_process_name=settings.Clothes.CATEGORY_PROCESS,
        types=get_clothes_tnved_types(CLOTHES_SUBCATEGORY),
        clothes_all_tnved=get_clothes_all_tnved(CLOTHES_SUBCATEGORY),
        countries=get_all_countries(),
        shoes_types=settings.Shoes.TYPES,
        shoes_genders=settings.Shoes.GENDERS,
        shoes_materials_top=settings.Shoes.MATERIALS_UP_LINEN,
        shoe_tnved=settings.Shoes.TNVED_CODE,
        shoe_al=settings.Shoes.SHOE_AL,
        shoe_ot=settings.Shoes.SHOE_OT,
        shoe_nl=settings.Shoes.SHOE_NL,
    )


def h_rd_check_submit():
    doc_type = (request.form.get('doc_type') or '').strip()
    number = (request.form.get('number') or '').strip()
    product_type = (request.form.get('type') or '').strip()
    gender = (request.form.get('gender') or '').strip()
    tnved_code = (request.form.get('tnved_code') or '').strip()
    country = (request.form.get('country') or '').strip()

    valid_doc_types = {key for key, _ in DOC_TYPE_OPTIONS}
    if doc_type not in valid_doc_types or not number:
        return jsonify(status='error', message='Укажите тип документа и номер РД'), 400

    if not product_type or not gender or not tnved_code or not country:
        return jsonify(status='error', message='Укажите вид товара, пол, ТНВЭД и страну перед проверкой РД'), 400

    request_id = uuid.uuid4().hex
    job_store = RdCheckJobStore()
    job_store.create(
        request_id=request_id,
        doc_type=doc_type,
        number=number,
        product_type=product_type,
        gender=gender,
        tnved_code=tnved_code,
        country=country,
    )
    check_rd_task.delay(
        request_id=request_id,
        doc_type=doc_type,
        number=number,
        tnved_code=tnved_code,
        country=country,
    )

    return jsonify(status='success', request_id=request_id), 200


def h_rd_check_status(request_id: str):
    job_store = RdCheckJobStore()
    data = job_store.get(request_id)

    if not data:
        return jsonify(status='error', message='Запрос не найден или устарел'), 404

    return jsonify(data), 200


def h_rd_check_health():
    breaker = get_fsa_circuit_breaker()
    breaker_state = breaker.get_state()

    queue = Queue(settings.RD_CHECK_QUEUE_NAME, connection=conn)

    return jsonify(
        circuit_state=breaker_state['state'],
        circuit_failures=breaker_state['failures'],
        is_healthy=breaker_state['state'] == STATE_CLOSED,
        queue_length=queue.count,
    ), 200
