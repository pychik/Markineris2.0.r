"""Strict counts for order forms, checked before any persistence or editing."""
import re

MAX_ORDER_QUANTITY = 100000000


def parse_quantity(value, label="Количество", maximum=MAX_ORDER_QUANTITY):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]+", value):
        raise ValueError(f"{label}: укажите целое число от 1 до {maximum}.")
    normalized = value.lstrip("0") or "0"
    if len(normalized) > len(str(maximum)) or not 1 <= int(normalized) <= maximum:
        raise ValueError(f"{label}: укажите целое число от 1 до {maximum}.")
    return int(normalized)


def validate_order_quantities(form_data, category, *, is_kpb=False):
    if category in {"clothes", "socks", "shoes", "linen"}:
        if category == "linen" and is_kpb:
            quantity_key = "linen_set_item_quantity"
            size_keys = ("linen_set_item_type", "linen_set_item_sizeX", "linen_set_item_sizeY", "linen_set_item_sizeUnit")
            maximum = 5
            parse_quantity(form_data.get("kpb_quantity"), "Количество КПБ")
        else:
            quantity_key = "quantity"
            size_keys = ("sizeX", "sizeY", "sizeUnit") if category == "linen" else ("size",)
            if category in {"clothes", "socks"}:
                size_keys += ("size_type",)
            maximum = 50000 if category == "socks" else MAX_ORDER_QUANTITY
        quantities = form_data.getlist(quantity_key)
        if not quantities or any(len(form_data.getlist(key)) != len(quantities) for key in size_keys):
            raise ValueError("Выберите размеры и укажите целое количество для каждого размера.")
        for quantity in quantities:
            parse_quantity(quantity, "Количество для размера", maximum)
    elif category in {"parfum", "cosmetics", "toys"}:
        quantities = form_data.getlist("quantity")
        if len(quantities) != 1:
            raise ValueError("Укажите одно целое количество товара.")
        parse_quantity(quantities[0])
    if "box_quantity" in form_data:
        parse_quantity(form_data.get("box_quantity"), "Количество в комплекте")
