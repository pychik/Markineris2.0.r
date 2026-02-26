from datetime import datetime
from sqlalchemy import func, distinct
from sqlalchemy.inspection import inspect
from flask import flash, request, jsonify, url_for, flash
from flask_login import current_user
from sqlalchemy.orm import selectinload

from config import settings
from logger import logger
from models import db, Order, ProductCard, Clothes, Parfum, ClothesQuantitySize, Socks, SocksQuantitySize, Shoe, \
    ShoeQuantitySize, Linen, LinenQuantitySize, User
from utilities.categories_data.subcategories_data import ClothesSubcategories
from utilities.saving_uts import get_clothes_size_type, save_copy_order_shoes, save_copy_order_clothes, \
    save_copy_order_socks, save_copy_order_linen, save_copy_order_parfum

ALLOWED_CARD_DATA_STATUSES: set[str] = {"approved", "partially_approved"}

_COLUMNS_CACHE: dict[type, list[str]] = {}


def _json_error(message: str, code: int = 400, **extra):
    payload = {"status": "error", "message": message}
    if extra:
        payload.update(extra)
    return jsonify(payload), code


def _count_open_moderation_orders(user_id: int, category: str, subcategory: str | None) -> int:
    q = Order.query.filter(
        Order.user_id == user_id,
        Order.category == category,
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

    ds = (pc.data_status or "").strip()
    if ds not in ALLOWED_CARD_DATA_STATUSES:
        # можно дополнить pc.status / pc.reject_reason
        return f"Карточка #{pc.id} не прошла модерацию (статус: {ds})"

    return None


def _units_map_for_card(pc: ProductCard):
    """
    Возвращаем "карта" доступных approved-юнитов для валидации выбранных размеров.
    Для parfum: проверяем, что есть approved parfum-юниты.
    Для остальных: ключом будет tuple, зависящий от категории.
    """
    if pc.category == "parfum":
        approved = [p for p in pc.parfum if getattr(p, "is_approved", False)]
        return {"_parfum_units": approved}

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

    cards = q.all()
    return {c.id: c for c in cards}


def _add_order_item_from_card(order: Order, pc: ProductCard, item_payload: dict):
    """
    Создаёт строку заказа из ProductCard.
    ВАЖНО:
      - копируем ВСЕ колонки из записи карточки (src) в запись заказа (new_obj)
      - НЕ проставляем new_obj.card_id (в заказных строках он должен быть None)
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
        return

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
                    size_type=get_clothes_size_type(size, st),
                    # is_approved можно не ставить, но если хочешь — оставь True:
                    is_approved=True,
                )
            )

        # НЕ трогаем new_obj.card_id
        order.clothes.append(new_obj)
        return

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
        return

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
        return

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
        return

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
    return q.count()


def common_save_copy_pc_order(user: User, category: str, order: Order) -> int | None:
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
            has_aggr=order.has_aggr,

            # ✅ pc-поля
            is_moderation=True,
            stage=settings.OrderStage.CREATING,
            to_delete=False,
            payment=False,
        )

        # копируем категории/позиции
        match category:
            case settings.Shoes.CATEGORY:
                new_order = save_copy_order_shoes(order_category_list=order.shoes, new_order=new_order)
            case settings.Clothes.CATEGORY:
                new_order = save_copy_order_clothes(order_category_list=order.clothes, new_order=new_order,
                                                    old_aggrs=order.aggr_orders)
            case settings.Socks.CATEGORY:
                new_order = save_copy_order_socks(order_category_list=order.socks, new_order=new_order,
                                                  old_aggrs=order.aggr_orders)
            case settings.Linen.CATEGORY:
                new_order = save_copy_order_linen(order_category_list=order.linen, new_order=new_order)
            case settings.Parfum.CATEGORY:
                new_order = save_copy_order_parfum(order_category_list=order.parfum, new_order=new_order)
            case _:
                raise Exception("Неизвестная категория")

        user.orders.append(new_order)
        db.session.commit()

        # вернём id
        return new_order.id

    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.ORDER_ADD_ERROR} {e}"
        flash(message=message, category="error")
        logger.error(message)
        return None


