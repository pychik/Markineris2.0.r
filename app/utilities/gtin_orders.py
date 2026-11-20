"""GTIN metadata and transactional grouping of ordinary order positions."""
import json
import re

from views.crm.schema import CompaniesOperators


class GTINCompanyConflict(ValueError):
    def __init__(self, gtin):
        super().__init__(f"GTIN {gtin} уже есть в этом заказе с другой проводящей компанией. "
                         "Для одинакового GTIN выберите ту же проводящую компанию.")


def company_options():
    return [{"value": f"g:{company.name}", "label": company.as_option()[1]}
            for company in CompaniesOperators]


def validate_gtin_fields(gtin, company_key):
    gtin = str(gtin or "").strip()
    company_key = str(company_key or "").strip()
    if bool(gtin) != bool(company_key):
        raise ValueError("Заполните GTIN и выберите проводящую компанию либо оставьте оба поля пустыми.")
    if not gtin:
        return "", ""
    if not re.fullmatch(r"046[0-9]{11}", gtin):
        raise ValueError("GTIN должен состоять из 14 цифр и начинаться с 046. Например: 04640735105562.")
    if company_key not in {option["value"] for option in company_options()}:
        raise ValueError("Выберите проводящую компанию из списка.")
    return gtin, company_key


def validate_gtin_company(positions, gtin, company_key):
    if gtin:
        for position in positions:
            pairs = [(position.gtin, position.gtin_company_key)]
            pairs.extend((getattr(sq, "gtin", None), getattr(sq, "gtin_company_key", None))
                         for sq in getattr(position, "sizes_quantities", ()))
            if any(value == gtin and key != company_key for value, key in pairs):
                raise GTINCompanyConflict(gtin)


def position_groups(positions):
    """Preserve first appearance order; ordinary positions form one group."""
    groups = {}
    companies_by_gtin = {}
    for position in positions:
        gtin, key = validate_gtin_fields(position.gtin, position.gtin_company_key)
        if gtin and companies_by_gtin.setdefault(gtin, key) != key:
            raise GTINCompanyConflict(gtin)
        groups.setdefault(key, []).append(position)
    return groups


class GTINSizeValidationError(ValueError):
    """A size mapping error that must be returned to the position form."""


def parse_size_gtins(raw):
    if raw is None or raw == "":
        return None  # Legacy position-level form / Excel upload.
    try:
        rows = json.loads(raw)
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError()
        result = {}
        used_gtins = {}
        for row in rows:
            identity = tuple(str(row.get(field) or "").strip() for field in ("size", "size_type", "unit"))
            if not identity[0] or identity in result:
                raise ValueError("Размеры в списке GTIN не должны повторяться.")
            gtin, key = validate_gtin_fields(row.get("gtin"), row.get("company"))
            if gtin and gtin in used_gtins:
                raise ValueError("У разных размеров одной позиции должны быть разные GTIN.")
            if gtin:
                used_gtins[gtin] = identity
            result[identity] = (gtin, key)
        return result
    except (ValueError, TypeError, AttributeError) as exc:
        raise GTINSizeValidationError(str(exc) or "Некорректный список GTIN по размерам.") from exc


def size_gtin_fields(size, position):
    """Old orders retain their position-level GTIN until explicitly edited."""
    if getattr(size, "gtin", None) or getattr(size, "gtin_company_key", None):
        return validate_gtin_fields(size.gtin, size.gtin_company_key)
    return validate_gtin_fields(position.gtin, position.gtin_company_key)


def apply_size_gtins(position, raw, size_rows):
    mapping = parse_size_gtins(raw)
    if mapping is None:
        if position.gtin and len(position.sizes_quantities) > 1:
            raise GTINSizeValidationError("Укажите отдельный GTIN для каждого размера через кнопку GTIN.")
        return
    if getattr(position, "set_items", None):
        raise GTINSizeValidationError("Для КПБ укажите GTIN и компанию на комплект целиком.")
    if position.gtin or position.gtin_company_key:
        raise GTINSizeValidationError("Укажите GTIN и компании только в строках размеров.")
    expected = {}
    for row, sq in zip(size_rows, position.sizes_quantities):
        identity = (str(row[0]).strip(), str(row[2]).strip() if hasattr(sq, "size_type") else "",
                    str(row[1]).strip() if hasattr(sq, "unit") else "")
        if identity in expected:
            raise GTINSizeValidationError("Размеры позиции не должны повторяться.")
        expected[identity] = sq
    if mapping.keys() != expected.keys():
        raise GTINSizeValidationError("Список размеров изменился. Откройте GTIN и проверьте данные размеров.")
    for identity, sq in expected.items():
        sq.gtin, sq.gtin_company_key = mapping[identity]
    position.gtin = None
    position.gtin_company_key = None


def materialize_size_positions(order, relation_name):
    """Keep existing exports/CRM working by giving each GTIN its own position at checkout.

    Size objects are moved, never copied. Integer weight
    is apportioned by quantity with the largest remainder method, preserving the sum.
    """
    from sqlalchemy import inspect
    from models import db

    positions = getattr(order, relation_name)
    for position in list(positions):
        sizes = list(getattr(position, "sizes_quantities", ()))
        if not sizes or not any(getattr(sq, "gtin", None) or getattr(sq, "gtin_company_key", None) for sq in sizes):
            continue
        groups = {}
        used_gtins = set()
        for sq in sizes:
            gtin, key = size_gtin_fields(sq, position)
            if gtin and gtin in used_gtins:
                raise GTINSizeValidationError("У разных размеров одной позиции должны быть разные GTIN.")
            if gtin:
                used_gtins.add(gtin)
            groups.setdefault((gtin, key), []).append(sq)
        quantities = [sum(int(sq.quantity) for sq in group) for group in groups.values()]
        total_quantity = sum(quantities)
        if any(quantity <= 0 for quantity in quantities):
            raise GTINSizeValidationError("Количество каждого размера должно быть больше нуля.")
        weight = int(position.weight_grams or 0)
        weights = [weight * quantity // total_quantity for quantity in quantities]
        remainders = sorted(range(len(weights)), key=lambda i: -(weight * quantities[i] % total_quantity))
        for i in remainders[:weight - sum(weights)]:
            weights[i] += 1
        if any(value <= 0 for value in weights):
            raise GTINSizeValidationError("Вес позиции слишком мал для разделения по GTIN. Уточните общий вес позиции.")
        attributes = {column.key: getattr(position, column.key) for column in inspect(type(position)).columns
                      if not column.primary_key and column.key != "order_id"}
        for index, ((gtin, key), group) in enumerate(groups.items()):
            if index == 0:
                target = position
            else:
                target = type(position)(**attributes)
                positions.append(target)
                for sq in group:
                    position.sizes_quantities.remove(sq)
                    target.sizes_quantities.append(sq)
            target.gtin, target.gtin_company_key = gtin or None, key or None
            target.weight_grams = weights[index]
    db.session.flush()


def reserve_order_numbers(user, count):
    """Reserve a contiguous range under the agent's row lock, without committing."""
    from sqlalchemy import text
    from models import db

    admin_id = user.admin_parent_id if user.role == "ordinary_user" else user.id
    row = db.session.execute(text("""
        UPDATE public.users SET admin_order_num = admin_order_num + :count
        WHERE id = :admin_id RETURNING admin_order_num
    """), {"count": count, "admin_id": admin_id}).first()
    if row is None:
        raise ValueError("Не найден агент для присвоения номеров заказа.")
    return [f"{admin_id}_{number}" for number in range(row.admin_order_num - count + 1, row.admin_order_num + 1)]


def split_order(order, relation_name):
    """Move positions without copying quantities; the caller owns the transaction."""
    from models import db, Order

    materialize_size_positions(order, relation_name)
    groups = position_groups(sorted(getattr(order, relation_name), key=lambda position: position.id))
    if not groups:
        raise ValueError("В заказе нет позиций.")

    result = []
    for index, (key, positions) in enumerate(groups.items()):
        if index == 0:
            target = order
        else:
            target = Order(**{field: getattr(order, field) for field in (
                "user_id", "category", "company_idn", "company_type", "company_name",
                "edo_type", "edo_id", "mark_type", "rd_replacement_consent",
                "created_at",
            )})
            db.session.add(target)
            for position in positions:
                getattr(target, relation_name).append(position)
        target.is_gtin_order = bool(key)
        target.processing_company_key = key or None
        target.processing_company_label = (
            next(option["label"] for option in company_options() if option["value"] == key) if key else None
        )
        target.processing_info = ""
        target.upd_number = None
        result.append(target)
    db.session.flush()
    return result
