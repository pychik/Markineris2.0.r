"""Assign the conductor of an ordinary GTIN order; keep UPD edits separate."""
from flask import current_app, jsonify, render_template, request
from flask_login import current_user
from sqlalchemy.orm import lazyload, selectinload

from config import settings
from models import Order, db
from utilities.gtin_orders import company_options
from utilities.order_log import append_order_log
from utilities.order_processing_info import split_processing_company_label
from .helpers import _get_order_desc_row, _can_view_order_desc


def _can_access_gtin_order(user, order_id):
    return _can_view_order_desc(_get_order_desc_row(order_id), user)


def reassign_gtin_company(order, company_key, positions):
    """Update all explicit GTIN metadata atomically; the caller commits and logs."""
    options = {option['value']: option['label'] for option in company_options()}
    if company_key not in options:
        raise ValueError('Выберите проводящую компанию из списка.')
    if not order.is_gtin_order or order.is_moderation:
        raise ValueError('Смена компании доступна только для обычного GTIN-заказа.')
    if company_key == order.processing_company_key:
        return False
    for position in positions:
        if position.gtin:
            position.gtin_company_key = company_key
        for size in getattr(position, 'sizes_quantities', ()):
            if size.gtin:
                size.gtin_company_key = company_key
    order.processing_company_key = company_key
    order.processing_company_label = options[company_key]
    order.upd_number = None
    order.processing_info = ''
    return True


def h_gtin_company(order_id):
    if current_user.role not in (settings.MANAGER_USER, settings.SUPER_MANAGER, settings.SUPER_USER):
        return jsonify(status='error', message='Нет доступа к смене GTIN-компании.'), 403

    query = Order.query.options(lazyload('*')).filter(Order.id == order_id)
    if request.method == 'POST':
        query = query.with_for_update(of=Order)
    order = query.first()
    if order is None or order.to_delete:
        return jsonify(status='error', message='Заказ не найден.'), 404
    if not _can_access_gtin_order(current_user, order_id):
        return jsonify(status='error', message='Нет доступа к этому заказу.'), 403
    if not order.is_gtin_order or order.is_moderation:
        return jsonify(status='error', message='Смена компании доступна только для обычного GTIN-заказа.'), 400

    if request.method == 'GET':
        response = jsonify(status='success', html=render_template(
            'crm_mod_v1/helpers/modals/modal_gtin_company.html', order=order,
            companies=company_options()))
        response.headers['Cache-Control'] = 'no-store'
        return response

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(status='error', message='Некорректные данные запроса.'), 400
    if data.get('expected_company') != (order.processing_company_key or ''):
        return jsonify(status='error', message='Компания заказа уже изменилась. Закройте окно и откройте его заново.'), 409
    company_key = str(data.get('company') or '').strip()
    if company_key not in {option['value'] for option in company_options()}:
        return jsonify(status='error', message='Выберите проводящую компанию из списка.'), 400

    try:
        changed = False
        upd_reset = False
        previous_label = order.processing_company_label or order.processing_company_key or 'не указана'
        if company_key != order.processing_company_key:
            relation_name = settings.CATEGORIES_DICT.get(order.category)
            if not relation_name:
                return jsonify(status='error', message='Неизвестная категория заказа.'), 400
            model = getattr(Order, relation_name).property.mapper.class_
            positions_query = db.session.query(model).options(lazyload('*')).filter(model.order_id == order.id)
            if hasattr(model, 'sizes_quantities'):
                positions_query = positions_query.options(selectinload(model.sizes_quantities))
            upd_reset = bool(order.upd_number or order.processing_info)
            changed = reassign_gtin_company(order, company_key, positions_query.all())
            if changed:
                action = f'изменил GTIN-компанию: {previous_label} → {order.processing_company_label}'
                append_order_log(order.id, action + ('; УПД сброшен' if upd_reset else ''))
            db.session.commit()
        title, inn = split_processing_company_label(order.processing_company_label)
        return jsonify(
            status='success', message='Компания GTIN-заказа сохранена.' + (' УПД сброшен.' if upd_reset else ''),
            order_id=order.id, company_key=order.processing_company_key,
            company_label=order.processing_company_label, company_title=title, company_inn=inn,
            upd_number=order.upd_number or '', processing_info=order.processing_info or '',
            changed=changed, upd_reset=upd_reset,
        )
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Failed to change GTIN company for order %s', order_id)
        return jsonify(status='error', message='Не удалось сохранить компанию. Повторите попытку.'), 500
