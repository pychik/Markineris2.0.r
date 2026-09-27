from datetime import datetime
from sqlalchemy import func, distinct
from sqlalchemy.inspection import inspect
from flask import flash, request, jsonify, url_for, flash
from flask_login import current_user
from sqlalchemy.orm import selectinload

from config import settings
from logger import logger
from models import db, Order, ProductCard, FastOrderCompanies, Clothes, Parfum, Cosmetics, Toys, ClothesQuantitySize, Socks, \
    SocksQuantitySize, Shoe, ShoeQuantitySize, Linen, LinenQuantitySize, ModerationStatus, User
from utilities.categories_data.subcategories_data import ClothesSubcategories
from utilities.saving_helpers import get_clothes_size_type
from utilities.saving_uts import save_copy_order_shoes, save_copy_order_clothes, \
    save_copy_order_socks, save_copy_order_linen, save_copy_order_parfum, save_copy_order_cosmetics, \
    save_copy_order_toys

ALLOWED_CARD_DATA_STATUSES: set[str] = {"approved"}
PC_ORDER_ITEM_APPROVAL_CATEGORIES = {
    settings.Parfum.CATEGORY,
    settings.Cosmetics.CATEGORY,
    settings.Toys.CATEGORY,
}
PC_ORDER_SIZE_APPROVAL_CATEGORIES = {
    settings.Clothes.CATEGORY,
    settings.Shoes.CATEGORY,
    settings.Linen.CATEGORY,
    settings.Socks.CATEGORY,
}

_COLUMNS_CACHE: dict[type, list[str]] = {}


def _order_items_for_category(order: Order, category: str) -> list:
    if category == settings.Shoes.CATEGORY:
        return list(order.shoes)
    if category == settings.Clothes.CATEGORY:
        return list(order.clothes)
    if category == settings.Socks.CATEGORY:
        return list(order.socks)
    if category == settings.Linen.CATEGORY:
        return list(order.linen)
    if category == settings.Parfum.CATEGORY:
        return list(order.parfum)
    if category == settings.Cosmetics.CATEGORY:
        return list(order.cosmetics)
    if category == settings.Toys.CATEGORY:
        return list(order.toys)
    return []


def fast_order_company_key(*, external_id: str | None, title: str | None, inn: str | None) -> str:
    return (inn or "").strip() or (external_id or "").strip() or (title or "").strip() or "unknown"


def get_or_create_fast_order_company(
    order: Order,
    pc: ProductCard,
    cache: dict[str, FastOrderCompanies],
) -> FastOrderCompanies:
    external_id = (pc.processing_company_external_id or "").strip()
    title = (pc.processing_company_title or "").strip()
    inn = (pc.processing_company_inn or "").strip()
    key = fast_order_company_key(external_id=external_id, title=title, inn=inn)

    if key not in cache:
        cache[key] = FastOrderCompanies(
            order_id=order.id,
            company_key=key,
            processing_company_external_id=external_id,
            processing_company_title=title,
            processing_company_inn=inn,
        )
        db.session.add(cache[key])

    return cache[key]


def _copy_fast_order_companies(source_order: Order, new_order: Order, category: str) -> None:
    new_items = _order_items_for_category(new_order, category)
    used_old_company_ids = {
        getattr(new_item, "fast_order_company_id", None)
        for new_item in new_items
        if getattr(new_item, "fast_order_company_id", None)
    }
    companies_by_old_id = {}
    for source_company in source_order.fast_order_companies:
        if source_company.id not in used_old_company_ids:
            continue
        new_company = FastOrderCompanies(
            order_id=new_order.id,
            company_key=source_company.company_key,
            processing_company_external_id=source_company.processing_company_external_id or "",
            processing_company_title=source_company.processing_company_title or "",
            processing_company_inn=source_company.processing_company_inn or "",
            upd_number=source_company.upd_number or "",
        )
        db.session.add(new_company)
        companies_by_old_id[source_company.id] = new_company

    db.session.flush()

    for new_item in new_items:
        old_company_id = getattr(new_item, "fast_order_company_id", None)
        new_company = companies_by_old_id.get(old_company_id)
        if new_company:
            new_item.fast_order_company_id = new_company.id


def _json_error(message: str, code: int = 400, **extra):
    payload = {"status": "error", "message": message}
    if extra:
        payload.update(extra)
    return jsonify(payload), code


def _count_open_moderation_orders(user_id: int, category: str, subcategory: str | None) -> int:
    category_ru = next(
        (title for title, process_name in settings.CATEGORIES_DICT.items() if process_name == category),
        category,
    )
    q = Order.query.filter(
        Order.user_id == user_id,
        Order.category == category_ru,
        Order.stage == 0,
        Order.is_moderation.is_(True),
        Order.to_delete.is_(False),
        Order.processed.is_(False),
    )

    if category == "clothes":
        sub = (subcategory or "").strip()
        if not sub:
            return 999999
        q = q.filter(Order.clothes.any(Clothes.subcategory == sub))
    elif category == "cosmetics":
        sub = (subcategory or "").strip()
        if not sub:
            return 999999
        q = q.filter(Order.cosmetics.any(Cosmetics.subcategory == sub))
    elif category == "toys":
        sub = (subcategory or "").strip()
        if not sub:
            return 999999
        q = q.filter(Order.toys.any(Toys.subcategory == sub))

    return q.with_entities(func.count(Order.id)).scalar() or 0



def _get_card_or_fail(card_id: int) -> ProductCard:
    pc = ProductCard.query.get(int(card_id))
    return pc


def _validate_card_access_and_status(pc: ProductCard, expected_category: str):
    if not pc:
        return "Карточка не найдена"

    if pc.user_id != current_user.id:
        return f"Карточка #{pc.id} не принадлежит текущему пользователю"

    if pc.category != expected_category:
        return f"Карточка #{pc.id} принадлежит категории '{pc.category}', а в заказе '{expected_category}'"

    if pc.status != ModerationStatus.APPROVED:
        return f"Карточка #{pc.id} не в статусе одобрено"

    ds = (pc.data_status or "").strip()
    if ds not in ALLOWED_CARD_DATA_STATUSES:
        # можно дополнить pc.status / pc.reject_reason
        return f"Карточка #{pc.id} не прошла модерацию (статус: {ds})"

    if not pc.processing_company_label:
        return (
            f"Карточка #{pc.id} не может быть добавлена в быстрый заказ: "
            "не назначена компания обработки"
        )

    return None


def _pc_order_item_label(item) -> str:
    for attr in ("article", "model_article", "trademark", "type"):
        value = (getattr(item, attr, None) or "").strip()
        if value:
            return value
    item_id = getattr(item, "id", None)
    return f"позиция #{item_id}" if item_id else "позиция"


def validate_pc_order_items_ready_for_process(category: str, items: list) -> list[str]:
    category = (category or "").strip()
    if not items:
        return ["В заказе нет позиций."]

    errors = []
    for item in items:
        label = _pc_order_item_label(item)
        if not getattr(item, "fast_order_company_id", None):
            errors.append(f"Позиция {label} без компании обработки.")
            continue

        if category in PC_ORDER_ITEM_APPROVAL_CATEGORIES:
            if not getattr(item, "is_approved", False):
                errors.append(f"Позиция {label} не одобрена.")
            continue

        if category in PC_ORDER_SIZE_APPROVAL_CATEGORIES:
            sizes_quantities = list(getattr(item, "sizes_quantities", []) or [])
            if not sizes_quantities:
                errors.append(f"Позиция {label} без размеров.")
                continue
            if any(not getattr(size, "is_approved", False) for size in sizes_quantities):
                errors.append(f"Позиция {label} содержит не одобренные размеры.")
            continue

        errors.append(f"Позиция {label} относится к неизвестной категории заказа.")

    return errors


def _units_map_for_card(pc: ProductCard):
    """
    Возвращаем "карта" доступных approved-юнитов для валидации выбранных размеров.
    Для parfum: проверяем, что есть approved parfum-юниты.
    Для остальных: ключом будет tuple, зависящий от категории.
    """
    if pc.category == "parfum":
        approved = [p for p in pc.parfum if getattr(p, "is_approved", False)]
        return {"_parfum_units": approved}
    if pc.category == "cosmetics":
        approved = [p for p in pc.cosmetics if getattr(p, "is_approved", False)]
        return {"_single_units": approved}
    if pc.category == "toys":
        approved = [p for p in pc.toys if getattr(p, "is_approved", False)]
        return {"_single_units": approved}

    # clothes/socks/shoes/linen: sizes_quantities лежат в миксинах
    if pc.category == "clothes":
        units = [s for c in pc.clothes for s in c.sizes_quantities]
        return { (u.size, u.size_type, ""): u for u in units if u.is_approved }

    if pc.category == "socks":
        units = [s for sk in pc.socks for s in sk.sizes_quantities]
        return { (u.size, u.size_type, ""): u for u in units if u.is_approved }

    if pc.category == "shoes":
        units = [s for sh in pc.shoes for s in sh.sizes_quantities]
        # у обуви size_type/unit нет — кладём пустые
        return { (u.size, "", ""): u for u in units if u.is_approved }

    if pc.category == "linen":
        units = [s for l in pc.linen for s in l.sizes_quantities]
        # у linen есть unit
        return { (u.size, "", u.unit or ""): u for u in units if u.is_approved }

    return {}


def _parse_rd(rd_obj):
    """
    rd_obj: {"rd_type": "...", "rd_name": "...", "rd_date": "dd.mm.yyyy"} | None
    Возвращает (rd_type, rd_name, rd_date_date_or_none)
    """
    if rd_obj is None:
        return None, None, None

    rd_type = (rd_obj.get("rd_type") or "").strip()
    rd_name = (rd_obj.get("rd_name") or "").strip()
    rd_date = (rd_obj.get("rd_date") or "").strip()

    if not (rd_type and rd_name and rd_date):
        raise ValueError("РД заполнена не полностью")

    try:
        rd_date_dt = datetime.strptime(rd_date, "%d.%m.%Y").date()
    except Exception:
        raise ValueError("Некорректная дата РД")

    return rd_type, rd_name, rd_date_dt


def _copy_common_fields_from_card_obj(dst_obj, src_obj, rd_tuple):
    """
    Копируем базовые поля, которые нужны в заказе.
    Вы можете расширить список под свои реальные требования.
    """
    rd_type, rd_name, rd_date = rd_tuple

    # CommonMixin / OrderCommon поля:
    for attr in ("type", "tnved_code", "country", "tax", "article_price", "trademark"):
        if hasattr(src_obj, attr) and hasattr(dst_obj, attr):
            setattr(dst_obj, attr, getattr(src_obj, attr))

    # RD:
    if hasattr(dst_obj, "rd_type"):
        dst_obj.rd_type = rd_type
    if hasattr(dst_obj, "rd_name"):
        dst_obj.rd_name = (rd_name or "").replace("№", "") if rd_name else None
    if hasattr(dst_obj, "rd_date"):
        dst_obj.rd_date = rd_date


def _load_cards_for_order(card_ids: list[int], *, category: str) -> dict[int, ProductCard]:
    q = ProductCard.query.filter(ProductCard.id.in_(card_ids))

    # подгрузка только нужной категории
    if category == "clothes":
        q = q.options(selectinload(ProductCard.clothes).selectinload(Clothes.sizes_quantities))
    elif category == "socks":
        q = q.options(selectinload(ProductCard.socks).selectinload(Socks.sizes_quantities))
    elif category == "shoes":
        q = q.options(selectinload(ProductCard.shoes).selectinload(Shoe.sizes_quantities))
    elif category == "linen":
        q = q.options(selectinload(ProductCard.linen).selectinload(Linen.sizes_quantities))
    elif category == "parfum":
        q = q.options(selectinload(ProductCard.parfum))
    elif category == "cosmetics":
        q = q.options(selectinload(ProductCard.cosmetics))
    elif category == "toys":
        q = q.options(selectinload(ProductCard.toys))

    cards = q.all()
    return {c.id: c for c in cards}


def _add_order_item_from_card(order: Order, pc: ProductCard, item_payload: dict):
    """
    Создаёт строку заказа из ProductCard.
    ВАЖНО:
      - копируем ВСЕ колонки из записи карточки (src) в запись заказа (new_obj)
      - не проставляем new_obj.card_id, чтобы оформленный заказ не зависел от жизни карточки
      - order_id выставится сам при append в relationship
    """

    # ---------- PARFUM ----------
    if pc.category == "parfum":
        approved_units = [p for p in pc.parfum if getattr(p, "is_approved", False)]
        if not approved_units:
            raise ValueError(f"Карточка #{pc.id}: нет approved позиций парфюма")

        src = approved_units[0]
        new_obj = Parfum()

        copy_model_columns(src, new_obj)

        # ✅ количество: сначала qty/quantity, потом fallback на sizes[0].qty
        qty_raw = item_payload.get("qty", None)
        if qty_raw is None:
            qty_raw = item_payload.get("quantity", None)


        if qty_raw is not None:
            try:
                qty = int(qty_raw)
            except Exception:
                qty = 0
        else:
            sizes = item_payload.get("sizes") or []
            try:
                qty = int(sizes[0].get("qty")) if sizes else 0
            except Exception:
                qty = 0

        if qty < 1:
            raise ValueError(f"Карточка #{pc.id}: некорректное количество парфюма")

        new_obj.quantity = qty

        tm = (item_payload.get("trademark") or "").strip()
        if tm:
            new_obj.trademark = tm

        order.parfum.append(new_obj)
        return new_obj

    # ---------- COSMETICS / TOYS ----------
    if pc.category in ("cosmetics", "toys"):
        approved_units = _units_map_for_card(pc).get("_single_units") or []
        if not approved_units:
            raise ValueError(f"Карточка #{pc.id}: нет approved позиции")

        src = approved_units[0]
        new_obj = Cosmetics() if pc.category == "cosmetics" else Toys()

        copy_model_columns(src, new_obj)

        qty_raw = item_payload.get("qty", None)
        if qty_raw is None:
            qty_raw = item_payload.get("quantity", None)
        if qty_raw is None:
            sizes = item_payload.get("sizes") or []
            try:
                qty_raw = sizes[0].get("qty") if sizes else None
            except Exception:
                qty_raw = None

        try:
            qty = int(qty_raw)
        except Exception:
            qty = 0

        if qty < 1:
            raise ValueError(f"Карточка #{pc.id}: некорректное количество")

        new_obj.quantity = qty

        tm = (item_payload.get("trademark") or "").strip()
        if tm:
            new_obj.trademark = tm

        if pc.category == "cosmetics":
            order.cosmetics.append(new_obj)
        else:
            order.toys.append(new_obj)
        return new_obj

    # ---------- COMMON FOR NON-PARFUM ----------
    sizes = item_payload.get("sizes") or []
    if not sizes:
        raise ValueError(f"Карточка #{pc.id}: не переданы размеры/количества")

    units_map = _units_map_for_card(pc)  # approved units map

    # ---------- CLOTHES ----------
    if pc.category == "clothes":
        if not pc.clothes:
            raise ValueError(f"Карточка #{pc.id}: нет данных clothes")

        src = pc.clothes[0]
        subcategory = (item_payload.get("subcategory") or src.subcategory or "common").strip()
        new_obj = Clothes(subcategory=subcategory)

        # ✅ копируем ВСЕ поля одежды (color, gender, content, type, tnved_code, country, tax, article_price, box_quantity...)
        copy_model_columns(src, new_obj)

        # ✅ article/trademark — из payload (как ты и описывал)
        new_obj.article = (item_payload.get("article") or "").strip()
        new_obj.trademark = (item_payload.get("trademark") or "").strip() or new_obj.trademark

        for s in sizes:
            size = (s.get("size") or "").strip()
            st = (s.get("size_type") or "").strip()
            qty = int(s.get("qty") or 0)
            if qty < 1:
                raise ValueError(f"Артикул {new_obj.article}: некорректное количество")

            key = (size, st, "")
            if key not in units_map:
                raise ValueError(f"Артикул {new_obj.article}: размер '{size}' ({st}) не approved в карточке")

            new_obj.sizes_quantities.append(
                ClothesQuantitySize(
                    size=size,
                    quantity=qty,
                    size_type=get_clothes_size_type(size, st, subcategory=subcategory),
                    # is_approved можно не ставить, но если хочешь — оставь True:
                    is_approved=True,
                )
            )

        order.clothes.append(new_obj)
        return new_obj

    # ---------- SOCKS ----------
    if pc.category == "socks":
        if not pc.socks:
            raise ValueError(f"Карточка #{pc.id}: нет данных socks")

        src = pc.socks[0]
        new_obj = Socks()

        # ✅ копируем ВСЕ поля носков (color, gender, content, etc.)
        copy_model_columns(src, new_obj)

        new_obj.article = (item_payload.get("article") or "").strip()
        new_obj.trademark = (item_payload.get("trademark") or "").strip() or new_obj.trademark

        for s in sizes:
            size = (s.get("size") or "").strip()
            st = (s.get("size_type") or "").strip()
            qty = int(s.get("qty") or 0)
            if qty < 1:
                raise ValueError(f"Артикул {new_obj.article}: некорректное количество")

            key = (size, st, "")
            if key not in units_map:
                raise ValueError(f"Артикул {new_obj.article}: размер '{size}' ({st}) не approved в карточке")

            new_obj.sizes_quantities.append(
                SocksQuantitySize(
                    size=size,
                    quantity=qty,
                    size_type=st,
                    is_approved=True,
                )
            )

        order.socks.append(new_obj)
        return new_obj

    # ---------- SHOES ----------
    if pc.category == "shoes":
        if not pc.shoes:
            raise ValueError(f"Карточка #{pc.id}: нет данных shoes")

        src = pc.shoes[0]
        new_obj = Shoe()

        # ✅ копируем ВСЕ поля обуви (color, material_top, material_lining, material_bottom, gender, with_packages...)
        copy_model_columns(src, new_obj)

        new_obj.article = (item_payload.get("article") or "").strip()
        new_obj.trademark = (item_payload.get("trademark") or "").strip() or new_obj.trademark

        for s in sizes:
            size = (s.get("size") or "").strip()
            qty = int(s.get("qty") or 0)
            if qty < 1:
                raise ValueError(f"Артикул {new_obj.article}: некорректное количество")

            key = (size, "", "")
            if key not in units_map:
                raise ValueError(f"Артикул {new_obj.article}: размер '{size}' не approved в карточке")

            new_obj.sizes_quantities.append(
                ShoeQuantitySize(
                    size=size,
                    quantity=qty,
                    is_approved=True,
                )
            )

        order.shoes.append(new_obj)
        return new_obj

    # ---------- LINEN ----------
    if pc.category == "linen":
        if not pc.linen:
            raise ValueError(f"Карточка #{pc.id}: нет данных linen")

        src = pc.linen[0]
        new_obj = Linen()

        # ✅ копируем ВСЕ поля белья (color, customer_age, textile_type, content, with_packages...)
        copy_model_columns(src, new_obj)

        new_obj.article = (item_payload.get("article") or "").strip()
        new_obj.trademark = (item_payload.get("trademark") or "").strip() or new_obj.trademark

        for s in sizes:
            size = (s.get("size") or "").strip()
            unit = (s.get("unit") or "").strip()
            qty = int(s.get("qty") or 0)
            if qty < 1:
                raise ValueError(f"Артикул {new_obj.article}: некорректное количество")

            key = (size, "", unit)
            if key not in units_map:
                raise ValueError(f"Артикул {new_obj.article}: размер '{size}' ({unit}) не approved в карточке")

            new_obj.sizes_quantities.append(
                LinenQuantitySize(
                    size=size,
                    unit=unit,
                    quantity=qty,
                    is_approved=True,
                )
            )

        order.linen.append(new_obj)
        return new_obj

    raise ValueError(f"Неизвестная категория карточки: {pc.category}")


def copy_model_columns(src, dst, *, exclude: set[str] | None = None):
    exclude = exclude or set()
    default_exclude = {
        "id", "order_id", "card_id",
        "created_at", "sent_at", "taken_at", "approved_at", "rejected_at",
    }
    exclude = exclude.union(default_exclude)

    cls = src.__class__
    cols = _COLUMNS_CACHE.get(cls)
    if cols is None:
        mapper = inspect(cls)
        cols = [c.key for c in mapper.columns]
        _COLUMNS_CACHE[cls] = cols

    for name in cols:
        if name in exclude:
            continue
        if hasattr(dst, name):
            setattr(dst, name, getattr(src, name))


def _count_open_pc_orders(user_id: int, category: str, subcategory: str | None = None) -> int:
    q = (Order.query
         .filter(
             Order.user_id == user_id,
             Order.category == category,
             Order.stage == settings.OrderStage.CREATING,   # 0
             Order.is_moderation.is_(True),
             Order.processed.is_(False),
             Order.to_delete.is_(False),
         ))

    if category == settings.Clothes.CATEGORY:
        sub = subcategory or ClothesSubcategories.common.value
        q = q.join(Clothes).filter(Clothes.subcategory == sub)
        return q.with_entities(func.count(distinct(Order.id))).scalar() or 0
    if category == settings.Cosmetics.CATEGORY:
        sub = subcategory or ""
        if not sub:
            return 999999
        q = q.join(Cosmetics).filter(Cosmetics.subcategory == sub)
        return q.with_entities(func.count(distinct(Order.id))).scalar() or 0
    if category == settings.Toys.CATEGORY:
        sub = subcategory or ""
        if not sub:
            return 999999
        q = q.join(Toys).filter(Toys.subcategory == sub)
        return q.with_entities(func.count(distinct(Order.id))).scalar() or 0
    return q.count()


def _filter_copyable_fast_order_items(order_items):
    def is_copyable(item) -> bool:
        if not getattr(item, "fast_order_company_id", None):
            return False
        if hasattr(item, "is_approved") and not item.is_approved:
            return False
        sizes_quantities = getattr(item, "sizes_quantities", None)
        if sizes_quantities is not None:
            return all(getattr(sq, "is_approved", False) for sq in sizes_quantities)
        return True

    return [
        item
        for item in order_items
        if is_copyable(item)
    ]


def _filtered_order_items(order_items, only_copyable_items: bool):
    if not only_copyable_items:
        return order_items
    return _filter_copyable_fast_order_items(order_items)


def common_save_copy_pc_order(
    user: User,
    category: str,
    order: Order,
    only_copyable_items: bool = False,
) -> int | None:
    try:
        new_order = Order(
            company_type=order.company_type,
            company_name=order.company_name,
            edo_type=order.edo_type,
            edo_id=order.edo_id,
            company_idn=order.company_idn,
            mark_type=order.mark_type,
            category=order.category,
            processed=False,
            # has_aggr=order.has_aggr,

            # ✅ pc-поля
            is_moderation=True,
            stage=settings.OrderStage.CREATING,
            to_delete=False,
            payment=False,
        )

        # копируем категории/позиции
        match category:
            case settings.Shoes.CATEGORY:
                new_order = save_copy_order_shoes(
                    order_category_list=_filtered_order_items(order.shoes, only_copyable_items),
                    new_order=new_order,
                )
            case settings.Clothes.CATEGORY:
                new_order = save_copy_order_clothes(
                    order_category_list=_filtered_order_items(order.clothes, only_copyable_items),
                    new_order=new_order,
                )
            case settings.Socks.CATEGORY:
                new_order = save_copy_order_socks(
                    order_category_list=_filtered_order_items(order.socks, only_copyable_items),
                    new_order=new_order,
                )
            case settings.Linen.CATEGORY:
                new_order = save_copy_order_linen(
                    order_category_list=_filtered_order_items(order.linen, only_copyable_items),
                    new_order=new_order,
                )
            case settings.Parfum.CATEGORY:
                new_order = save_copy_order_parfum(
                    order_category_list=_filtered_order_items(order.parfum, only_copyable_items),
                    new_order=new_order,
                )
            case settings.Cosmetics.CATEGORY:
                new_order = save_copy_order_cosmetics(
                    order_category_list=_filtered_order_items(order.cosmetics, only_copyable_items),
                    new_order=new_order,
                )
            case settings.Toys.CATEGORY:
                new_order = save_copy_order_toys(
                    order_category_list=_filtered_order_items(order.toys, only_copyable_items),
                    new_order=new_order,
                )
            case _:
                raise Exception("Неизвестная категория")

        user.orders.append(new_order)
        db.session.flush()
        _copy_fast_order_companies(order, new_order, category)
        db.session.commit()

        # вернём id
        return new_order.id

    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.ORDER_ADD_ERROR} {e}"
        flash(message=message, category="error")
        logger.error(message)
        return None
