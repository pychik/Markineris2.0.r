"""GTIN metadata and transactional grouping of ordinary order positions."""
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
            if position.gtin == gtin and position.gtin_company_key != company_key:
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
