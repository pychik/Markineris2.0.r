"""Подготовка заказа через Тезаурус: подбор РД и выбор компании-обработчика.

Здесь собрано всё, что нужно превалидации заказа:

- вытащить из позиций критерии в том виде, в каком их ждёт /rd/match;
- разложить ответ обратно по позициям;
- определить происхождение заказа и взять компанию.

Порядок вызовов важен: сначала РД, и только если подобрались все позиции -
компания. Ручка выбора компании меняет состояние на стороне Тезауруса,
лишний вызов перекашивает очередь раздачи.
"""
from __future__ import annotations

from typing import Any, Iterable

from config import settings
from logger import logger
from models import Order

from .api_client import TezaurusApiClient, TezaurusApiError, TezaurusConfigurationError

# Связи Order -> позиции по категориям
POSITION_RELATIONS = ('shoes', 'clothes', 'socks', 'linen', 'parfum', 'cosmetics')

ORIGIN_RF = 'рф'
ORIGIN_IMPORT = 'импорт'


def _tnved_prefix(tnved_code: str | None) -> str:
    digits = ''.join(ch for ch in (tnved_code or '') if ch.isdigit())
    return digits[:4]


def _is_children(position: Any) -> bool | None:
    """True - детский, False - взрослый, None - признак к категории неприменим.

    У парфюма признака возраста нет вовсе, и False там означал бы «взрослый»,
    что неверно.
    """
    if hasattr(position, 'for_children'):
        return bool(position.for_children)

    customer_age = getattr(position, 'customer_age', None)
    if customer_age:
        value = str(customer_age).strip().upper()
        if value == 'ДЕТСКИЙ':
            return True
        if value == 'ВЗРОСЛЫЙ':
            return False
        return None

    gender = getattr(position, 'gender', None)
    if gender:
        return gender in settings.RZ_GENDERS_RD_LIST

    return None


def _materials(position: Any) -> dict[str, str] | None:
    """Материалы обуви - единого поля состава у неё нет."""
    top = getattr(position, 'material_top', None)
    if top is None and not hasattr(position, 'material_lining'):
        return None
    materials = {
        'top': top or '',
        'lining': getattr(position, 'material_lining', None) or '',
        'bottom': getattr(position, 'material_bottom', None) or '',
    }
    return materials if any(materials.values()) else None


def build_position_payload(position: Any) -> dict[str, Any]:
    """Критерии одной позиции в формате /rd/match."""
    return {
        'position_id': position.id,
        'product_type': (getattr(position, 'type', None) or '').strip(),
        'tnved_code': (getattr(position, 'tnved_code', None) or '').strip(),
        'tnved_prefix': _tnved_prefix(getattr(position, 'tnved_code', None)),
        'country': (getattr(position, 'country', None) or '').strip().upper(),
        'is_children': _is_children(position),
        'gender': getattr(position, 'gender', None) or getattr(position, 'customer_age', None),
        'content': getattr(position, 'content', None),
        'materials': _materials(position),
    }


def iter_order_positions(order: Order) -> Iterable[Any]:
    for relation in POSITION_RELATIONS:
        for position in getattr(order, relation, None) or ():
            yield position


def position_has_rd(position: Any) -> bool:
    """РД считается указанной, если есть номер и дата окончания действия."""
    return bool(getattr(position, 'rd_name', None) and getattr(position, 'rd_date_to', None))


def collect_positions_without_rd(order: Order) -> list[Any]:
    """Позиции, которым нужен подбор. Указанные клиентом РД не трогаем."""
    return [p for p in iter_order_positions(order) if not position_has_rd(p)]


def resolve_order_origin(order: Order) -> str:
    """Происхождение заказа для выбора компании.

    Компания выбирается на заказ, а страна лежит на позиции, и заказ может быть
    смешанным - выгрузка не зря делится на «ВВЕЗЕН» и «РФ_ВНУТР». Берём импорт,
    если импортная хотя бы одна позиция: компания, работающая с импортом,
    проведёт и российский товар, обратное неверно.
    """
    countries = {
        (getattr(p, 'country', None) or '').strip().upper()
        for p in iter_order_positions(order)
    }
    countries.discard('')
    if not countries:
        return ORIGIN_RF
    return ORIGIN_RF if countries <= set(settings.COUNTRIES_INNER) else ORIGIN_IMPORT


def apply_rd_results(positions: list[Any], results: list[dict]) -> tuple[int, list[str]]:
    """Записать подобранные РД в позиции.

    Возвращает число проставленных и причины отказов. Найденные документы
    записываются даже когда заказ уходит в проблему: оператору останется
    разобраться только с теми позициями, где РД не нашлась.
    """
    by_id = {r.get('position_id'): r for r in results if isinstance(r, dict)}
    applied = 0
    problems: list[str] = []

    for position in positions:
        result = by_id.get(position.id)
        if result is None:
            problems.append(f'{position.type or position.id}: Тезаурус не вернул результат по позиции')
            continue

        if not result.get('found'):
            problems.append(f'{position.type or position.id}: {result.get("reason") or "РД не подобрана"}')
            continue

        rd = result.get('rd') or {}
        position.rd_type = rd.get('rd_type')
        position.rd_name = rd.get('rd_name')
        position.rd_date = rd.get('rd_date')
        position.rd_date_to = rd.get('rd_date_to')
        applied += 1

    return applied, problems


def match_order_rd(order: Order) -> tuple[bool, str]:
    """Подобрать и проставить РД по всем позициям заказа без документа.

    Возвращает (все ли позиции укомплектованы, сообщение для истории заказа).
    """
    positions = collect_positions_without_rd(order)
    if not positions:
        return True, 'РД указана клиентом по всем позициям, подбор не требовался'

    payload = [build_position_payload(p) for p in positions]
    client = TezaurusApiClient()
    response = client.match_rd(order_id=order.id, positions=payload, category=order.category)

    results = response.get('results') or []
    applied, problems = apply_rd_results(positions, results)

    if response.get('has_problem') or problems:
        total = response.get('positions_total', len(positions))
        not_found = response.get('positions_not_found', len(problems))
        detail = '; '.join(problems[:5])
        if len(problems) > 5:
            detail += f'; и ещё {len(problems) - 5}'
        return False, f'РД не подобраны для {not_found} из {total} позиций. {detail}'

    return True, f'РД подобраны Тезаурусом для {applied} позиций'


def select_company_for_order(order: Order) -> dict[str, Any] | None:
    """Взять компанию-обработчика под заказ.

    Вызывать строго один раз и только после успешного подбора РД: ручка сдвигает
    очередь раздачи, и лишний вызов перекашивает распределение между компаниями.
    """
    origin = resolve_order_origin(order)
    client = TezaurusApiClient()
    company = client.select_processing_company(category=order.category, origin=origin)
    if company is None:
        logger.warning(
            'Тезаурус не нашёл компанию: order_id=%s category=%s origin=%s',
            order.id, order.category, origin,
        )
    return company


__all__ = [
    'TezaurusApiError',
    'TezaurusConfigurationError',
    'build_position_payload',
    'collect_positions_without_rd',
    'match_order_rd',
    'resolve_order_origin',
    'select_company_for_order',
]
