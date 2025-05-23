from flask import jsonify, render_template, request

from models import (
    AggrOrder, ClothesQuantitySize, Order, SocksQuantitySize,
    AggrClothesSize, AggrSocksSize
)
from settings.start import db


class AggrOrderService:
    def __init__(self, order):
        self.order = order

    def get_all(self) -> list[AggrOrder]:
        return self.order.aggr_orders

    def delete(self, aggr_order: AggrOrder) -> bool:
        if aggr_order not in self.order.aggr_orders:
            return False
        db.session.delete(aggr_order)
        db.session.commit()
        return True

    def create(self, category: str, items: list[tuple[int, int]], name: str = None, note: str = "", count: int = 1) -> (
            AggrOrder):

        """
        Создание нового набора.
        items: список кортежей (id, quantity)
        """
        if category not in ['clothes', 'socks']:
            raise ValueError('Категория может быть только "clothes" или "socks"')

        category_names = {
            'clothes': 'Одежда',
            'socks': 'Носки и прочее'
        }

        aggr = AggrOrder(
            order=self.order,
            category=category,
            name=name or f"Набор {category_names[category]} #{len(self.order.aggr_orders) + 1}",
            note=note,
            quantity = count
        )

        self._add_items_to_aggr(aggr, items)

        db.session.add(aggr)
        db.session.commit()
        return aggr

    def add_items(self, aggr_order: AggrOrder, items: list[tuple[int, int]]):
        """
        Добавление позиций в существующий набор
        """
        if aggr_order.order_id != self.order.id:
            raise ValueError("Набор не принадлежит текущему заказу")
        self._add_items_to_aggr(aggr_order, items)
        db.session.commit()

    def _add_items_to_aggr(self, aggr_order: AggrOrder, items: list[tuple[int, int]]):
        """
        Приватная логика добавления (id, qty)
        """
        category = aggr_order.category
        ids = [i[0] for i in items]

        if category == 'clothes':
            existing_ids = {acs.cqs_id for acs in aggr_order.aggr_clothes_sizes}
            objects = {obj.id: obj for obj in ClothesQuantitySize.query.filter(ClothesQuantitySize.id.in_(ids)).all()}

            for cqs_id, qty in items:
                if cqs_id in existing_ids:
                    continue  # Пропускаем, если уже есть
                obj = objects.get(cqs_id)
                if not obj:
                    raise ValueError(f"CQS ID {cqs_id} не найден")
                aggr_order.aggr_clothes_sizes.append(
                    AggrClothesSize(cqs=obj, total_quantity=qty)
                )

        elif category == 'socks':
            existing_ids = {ass.sqs_id for ass in aggr_order.aggr_socks_sizes}
            objects = {obj.id: obj for obj in SocksQuantitySize.query.filter(SocksQuantitySize.id.in_(ids)).all()}

            for sqs_id, qty in items:
                if sqs_id in existing_ids:
                    continue
                obj = objects.get(sqs_id)
                if not obj:
                    raise ValueError(f"SQS ID {sqs_id} не найден")
                aggr_order.aggr_socks_sizes.append(
                    AggrSocksSize(sqs=obj, total_quantity=qty)
                )

        else:
            raise ValueError("Неверная категория")


def h_create_aggr_order(order_id):
    order = Order.query.get_or_404(order_id)
    service = AggrOrderService(order)

    data = request.get_json()
    category = data.get('category')
    raw_items = data.get('items', [])  # ['123##2', ...]
    count = data.get('count', 1)
    # print(category, raw_items, count, sep='\n')
    parsed_items = []
    for _id, qty in raw_items:
        try:
            _id = int(_id)
            qty = int(qty)
            if qty <= 0:
                continue
            parsed_items.append((_id, qty))
        except Exception:
            continue

    if not parsed_items:
        return jsonify({
            'status': 'error',
            'message': 'Не передано ни одной позиции или количества.',
        })

    try:
        # Здесь передаём и количество наборов
        aggr = service.create(category=category, items=parsed_items, count=count)

        return jsonify({
            'status': 'success',
            'message': f'Набор «{aggr.name}» создан.',
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
        })


def h_delete_aggr_order(order_id, aggr_id):
    order = Order.query.get_or_404(order_id)
    aggr = AggrOrder.query.get_or_404(aggr_id)

    service = AggrOrderService(order)

    try:
        if not service.delete(aggr):
            return jsonify({'status': 'error', 'message': 'Набор не принадлежит текущему заказу'})
        return jsonify({'status': 'success', 'message': 'Набор удалён'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


def h_get_all_aggr_orders(order_id: int):
    order = Order.query.get_or_404(order_id)

    html = render_template(f'helpers/order_aggregations/table.html', order=order)
    return jsonify({
        'status': 'success',
        'html': html
    })


def h_add_items_to_aggr(order_id, aggr_id):
    order = Order.query.get_or_404(order_id)
    aggr = AggrOrder.query.get_or_404(aggr_id)
    service = AggrOrderService(order)

    raw_ids = request.form.getlist('item_ids[]')  # ['1212::3', '1215::1']
    try:
        item_tuples = []
        for raw in raw_ids:
            if '::' not in raw:
                continue
            item_id, qty = raw.split('::', 1)
            item_tuples.append((int(item_id.strip()), int(qty.strip())))
    except Exception:
        return jsonify({
            'status': 'error',
            'message': 'Ошибка обработки item_ids[]. Ожидается формат "id::qty"',
        })

    try:
        service.add_items(aggr, item_tuples)
        return jsonify({'status': 'success', 'message': f'Добавлены позиции в набор {aggr.name}'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


def h_marks_quantity(order: Order) -> int:
    """
    Возвращает общее количество марок (единиц товара) для заказа с наборами.
    Считается: total_quantity * box_quantity для каждой позиции.
    """
    if not order.has_aggr:
        return 0

    total = 0

    if order.category == 'clothes':
        for aggr in order.aggr_orders:
            for aggr_size in aggr.aggr_clothes_sizes:
                box_qty = aggr_size.cqs.clothes.box_quantity
                total += aggr_size.total_quantity * (box_qty or 1)

    elif order.category == 'socks':
        for aggr in order.aggr_orders:
            for aggr_size in aggr.aggr_socks_sizes:
                box_qty = aggr_size.sqs.socks.box_quantity
                total += aggr_size.total_quantity * (box_qty or 1)

    return total