from datetime import date, datetime, timedelta
from typing import Optional
from uuid import uuid4

from flask import jsonify, redirect, render_template, flash, url_for, send_file
from flask_login import current_user

from sqlalchemy.sql import exists
from sqlalchemy import or_
from sqlalchemy.orm import joinedload, selectinload

from config import settings
from models import User, db, ProductCard, ModerationStatus, Clothes, Socks, Linen, Shoe, UserProcessingCompany, \
    ProcessingCompany, Parfum
from utilities.download import ShoesProcessor, ClothesProcessor, SocksProcessor, LinenProcessor, ParfumProcessor

from utilities.support import order_count

from views.main.product_cards.chat.helpers import h_pc_chat_unread_count, h_unread_map_for_cards

from views.main.product_cards.support import CATEGORIES_COMMON

CRM_STATUSES = [
    ModerationStatus.SENT.value,
    ModerationStatus.SENT_NO_RD.value,
    ModerationStatus.IN_PROGRESS.value,
    ModerationStatus.IN_MODERATION.value,
    ModerationStatus.CLARIFICATION.value,
    ModerationStatus.APPROVED.value,
    ModerationStatus.REJECTED.value,
]

CRM_ADMIN_ROLES = {"superuser", "supermanager"}  # кто видит всё
CRM_MANAGER_ROLE = "manager"


def helper_categories_counter(all_cards: list | tuple) -> dict:
    """
    Возвращает счётчики карточек по категориям.
    Учитывает только активные карточки (stage < 8).
    """

    # если all_cards — это ORM-объекты ProductCard,
    # то stage надо брать из card.status, а не stage
    active_cards = [
        c for c in all_cards
        if getattr(c, "status", None) not in (
            ModerationStatus.REJECTED,
        )
    ]

    counters = {
        "all": len(active_cards)
    }

    for cat_key, cfg in CATEGORIES_COMMON.items():
        counters[cat_key] = sum(
            1 for c in active_cards
            if c.category == cat_key
        )

    return counters


def crm_get_cards(category: str = None, subcategory: str = None, user: User = None):
    q = ProductCard.query

    if category:
        q = q.filter(ProductCard.category == category)

    q = q.filter(ProductCard.status.in_([
        ModerationStatus.SENT_NO_RD,
        ModerationStatus.SENT,
        ModerationStatus.IN_PROGRESS,
        ModerationStatus.IN_MODERATION,
        ModerationStatus.CLARIFICATION
    ]))

    if user and getattr(user, "role", None) == CRM_MANAGER_ROLE:

        q = q.filter(
            or_(
                ProductCard.status.in_([ModerationStatus.SENT, ModerationStatus.SENT_NO_RD]),
                ProductCard.manager_id == user.id
            )
        )

    # subcategory только для clothes
    if subcategory:
        q = q.filter(
            exists().where(
                (Clothes.card_id == ProductCard.id) &
                (Clothes.subcategory == subcategory)
            )
        )

    # базовые связи (не раздувают)
    q = q.options(
        joinedload(ProductCard.creator),
        joinedload(ProductCard.manager),
    )

    # грузим данные товара + sizes только если знаем категорию
    if category == settings.Clothes.CATEGORY_PROCESS:
        q = q.options(selectinload(ProductCard.clothes).selectinload(Clothes.sizes_quantities))
    elif category == settings.Shoes.CATEGORY_PROCESS:
        q = q.options(selectinload(ProductCard.shoes).selectinload(Shoe.sizes_quantities))
    elif category == settings.Linen.CATEGORY_PROCESS:
        q = q.options(selectinload(ProductCard.linen).selectinload(Linen.sizes_quantities))
    elif category == settings.Socks.CATEGORY_PROCESS:
        q = q.options(selectinload(ProductCard.socks).selectinload(Socks.sizes_quantities))
    elif category == settings.Parfum.CATEGORY_PROCESS:
        q = q.options(selectinload(ProductCard.parfum))
    else:
        # category не задана → список смешанный. Если sizes реально нужны в CRM-колонках всегда:
        q = q.options(
            selectinload(ProductCard.clothes).selectinload(Clothes.sizes_quantities),
            selectinload(ProductCard.shoes).selectinload(Shoe.sizes_quantities),
            selectinload(ProductCard.linen).selectinload(Linen.sizes_quantities),
            selectinload(ProductCard.socks).selectinload(Socks.sizes_quantities),
            selectinload(ProductCard.parfum),
        )

    q = q.order_by(ProductCard.created_at.desc())
    return q.all()


def split_cards_by_status(cards: list[ProductCard]) -> dict[str, list[dict]]:
    buckets = {
        ModerationStatus.SENT.value: [],
        ModerationStatus.SENT_NO_RD.value: [],
        ModerationStatus.IN_PROGRESS.value: [],
        ModerationStatus.IN_MODERATION.value: [],
        ModerationStatus.CLARIFICATION.value: [],
        ModerationStatus.APPROVED.value: [],
        ModerationStatus.PARTIALLY_APPROVED.value: [],
        ModerationStatus.REJECTED.value: [],
    }

    # unread только для нужных статусов
    need_ids = []
    statuses_need_unread = {"in_progress", "clarification"}
    for card in cards:
        st = card.status.value if hasattr(card.status, "value") else card.status
        if st in statuses_need_unread:
            need_ids.append(card.id)

    unread_map = h_unread_map_for_cards(need_ids, current_user) if need_ids else {}

    for card in cards:
        st = card.status.value if hasattr(card.status, "value") else card.status
        buckets.setdefault(st, [])

        sizes_count, sizes_label = crm_card_sizes_label(card)

        buckets[st].append({
            "id": card.id,
            "category": card.category,
            "subcategory": crm_card_subcategory_slug(card),
            "subcategory_title": crm_card_subcategory_title(card),
            "status": st,
            "created_at": card.created_at,
            "sent_at": card.sent_at,
            "processing_info": card.processing_info,
            "user_id": card.user_id,

            "user_login": card.creator.login_name if card.creator else "",
            "user_phone": card.creator.phone if card.creator else "",
            "user_email": card.creator.email if card.creator else "",
            "user_comment": card.user_comment,
            "reject_reason": card.reject_reason,
            "manager_id": card.manager.id if card.manager else "",
            "manager_login": card.manager.login_name if card.manager else "",

            "article_or_trademark": crm_card_article(card),
            "sizes": sizes_label,
            "sizes_count": sizes_count,

            "data_status": getattr(card, "data_status", None),
            "unread_count": unread_map.get(card.id, 0),
        })

    return buckets


def crm_card_article(card: ProductCard) -> str:
    cfg = CATEGORIES_COMMON.get(card.category)
    if not cfg:
        return "-"
    rel_name = cfg["rel_name"]
    items = getattr(card, rel_name) or []
    main = items[0] if items else None
    return getattr(main, "article", None) or "-" if card.category != settings.Parfum.CATEGORY_PROCESS \
        else getattr(main, "trademark", None) or "-"


def crm_card_sizes_label(card: ProductCard) -> tuple[int, str]:
    # количества не показываем, только размеры

    if card.category == settings.Clothes.CATEGORY_PROCESS:
        parts = []
        for c in card.clothes:
            for sq in c.sizes_quantities:
                # например "M (EU)" или "M"
                if getattr(sq, "size_type", None):
                    parts.append(f"{sq.size} {sq.size_type}")
                else:
                    parts.append(f"{sq.size}")
        return len(parts), ", ".join(sorted(set(parts))) if parts else "-"

    if card.category == settings.Socks.CATEGORY_PROCESS:
        parts = []
        for s in card.socks:
            for sq in s.sizes_quantities:
                if getattr(sq, "size_type", None):
                    parts.append(f"{sq.size} {sq.size_type}")
                else:
                    parts.append(f"{sq.size}")
        return len(parts), ", ".join(sorted(set(parts))) if parts else "-"

    if card.category == settings.Shoes.CATEGORY_PROCESS:
        parts = []
        for sh in card.shoes:
            for sq in sh.sizes_quantities:
                parts.append(str(sq.size))
        return len(parts), ", ".join(sorted(set(parts))) if parts else "-"

    if card.category == settings.Linen.CATEGORY_PROCESS:
        parts = []
        for l in card.linen:
            for sq in l.sizes_quantities:
                # size уже вида "70*140", unit отдельно
                if getattr(sq, "unit", None):
                    parts.append(f"{sq.size} {sq.unit}")
                else:
                    parts.append(f"{sq.size}")
        return len(parts), ", ".join(sorted(set(parts))) if parts else "-"

    # parfum: размеров нет
    if card.category == settings.Parfum.CATEGORY_PROCESS:
        return 1 , "-"

    return 0, "-"


def crm_card_subcategory_slug(card: ProductCard) -> str | None:
    if card.category != "clothes":
        return None
    main = (card.clothes or [None])[0]
    return getattr(main, "subcategory", None)


def crm_card_subcategory_title(card: ProductCard) -> str | None:
    slug = crm_card_subcategory_slug(card)
    if not slug:
        return None
    return (CATEGORIES_COMMON.get("clothes", {}).get("subcategories") or {}).get(slug, slug)


def product_card_download_common(user: User, pc_id: int):
    (
        category,
        card,
        pos_count,
        orders_pos_count,
        files_list,
    ) = get_card_download_info(pc_id=pc_id, user=user)

    if not files_list:
        return redirect(url_for('main.index'))

    return send_file(
        files_list[0],
        download_name=files_list[1],
        as_attachment=True
    )


def get_card_download_info(pc_id: int, user: User):
    card = (
        ProductCard.query
        .filter(
            ProductCard.id == pc_id,
            ProductCard.user_id == user.id
        )
        .first()
    )

    if not card:
        flash(message="Карточка не найдена", category="error")
        return (None,) * 5

    category = CATEGORIES_COMMON.get(card.category).get('title')

    # ---- выбираем список позиций ----
    if category == settings.Shoes.CATEGORY:
        items = card.shoes
        processor_cls = ShoesProcessor

    elif category == settings.Clothes.CATEGORY:
        items = card.clothes
        processor_cls = ClothesProcessor

    elif category == settings.Socks.CATEGORY:
        items = card.socks
        processor_cls = SocksProcessor

    elif category == settings.Linen.CATEGORY:
        items = card.linen
        processor_cls = LinenProcessor

    elif category == settings.Parfum.CATEGORY:
        items = card.parfum
        processor_cls = ParfumProcessor

    else:
        flash(message=settings.Messages.CATEGORY_UNKNOWN_ERROR, category="error")
        return (None,) * 5

    if not items:
        flash(message="Карточка пустая", category="error")
        return (None,) * 5

    # ---- считаем количества (используем старую функцию) ----
    rd_exist, quantity_list_raw, pos_count, orders_pos_count = order_count(
        category=category,
        order_list=items
    )

    # ---- создаём processor
    processor = processor_cls(
        category=category,
        company_idn="",          # у карточки нет компании — можно оставить пустым
        orders_list=items,
        flag_046=False,
        has_aggr=card.has_aggr
    )

    # ---- генерим Excel ----
    files_list = processor.make_file(
        order=None,              # ⚠️ order не нужен, processor его не использует критично
        order_num=card.id,       # используем id карточки
        category=category,
        pos_count=pos_count,
        orders_pos_count=orders_pos_count,
        c_partner_code="",
        company_type="",
        company_name="",
        company_idn="",
        edo_type="",
        edo_id="",
        mark_type="",
        c_name=user.login_name,
        c_phone=user.phone,
        c_email=user.email,
    )

    return (
        category,
        card,
        pos_count,
        orders_pos_count,
        files_list
    )


def move_user_approved_cards_to_partially(user_id: int):
    (ProductCard.query
     .filter(ProductCard.user_id == user_id,
             ProductCard.status == ModerationStatus.APPROVED)
     .update(
         {ProductCard.status: ModerationStatus.PARTIALLY_APPROVED},
         synchronize_session=False
     ))


def delete_company_from_pool_no_reassign(company_id: int) -> tuple[bool, str, dict]:
    company = ProcessingCompany.query.get(company_id)
    if not company:
        return False, "Фирма не найдена", {}

    total = db.session.query(ProcessingCompany.id).count()

    # запрет удаления последней фирмы
    if total <= 1:
        affected_logins = (
            db.session.query(User.login_name)
            .join(UserProcessingCompany, UserProcessingCompany.user_id == User.id)
            .filter(UserProcessingCompany.company_id == company_id)
            .distinct()
            .order_by(User.login_name.asc())
            .all()
        )
        logins = [x[0] for x in affected_logins if x and x[0]]

        # построчно
        lines = "\n".join(logins) if logins else "(пользователей нет)"
        msg = (
            "Нельзя удалить последнюю компанию из пула.\n"
            "Затронутые пользователи:\n"
            f"{lines}"
        )
        return False, msg, {"affected_users": logins}

    # пользователи, у кого была эта фирма
    affected_user_ids = [
        x[0] for x in (
            db.session.query(UserProcessingCompany.user_id)
            .filter(UserProcessingCompany.company_id == company_id)
            .distinct()
            .all()
        )
    ]

    # 1) удалить привязки user->company
    UserProcessingCompany.query.filter_by(company_id=company_id).delete(synchronize_session=False)

    # 2) удалить фирму из пула
    db.session.delete(company)

    # 3) всем затронутым пользователям перевести APPROVED карточки -> PARTIALLY_APPROVED
    if affected_user_ids:
        (ProductCard.query
         .filter(
             ProductCard.user_id.in_(affected_user_ids),
             ProductCard.status == ModerationStatus.APPROVED
         )
         .update(
             {ProductCard.status: ModerationStatus.PARTIALLY_APPROVED},
             synchronize_session=False
         ))

    meta = {"affected_users_count": len(affected_user_ids)}
    msg = f"Фирма удалена. Затронутых пользователей: {len(affected_user_ids)}. APPROVED карточки переведены в PARTIALLY_APPROVED."
    return True, msg, meta


ALLOWED_BACK_ROLES = {"superuser", "supermanager", "markineris_admin"}


def h_pc_move_get_cards_by_status(status_value: str, category=None, subcategory=None, company_id=None):
    q = (
        ProductCard.query
        .options(
            joinedload(ProductCard.creator),
            joinedload(ProductCard.manager),
        )
        .order_by(ProductCard.created_at.desc())
        .filter(ProductCard.status == ModerationStatus(status_value))
    )

    if category:
        q = q.filter(ProductCard.category == category)

        if category == settings.Clothes.CATEGORY_PROCESS:
            q = q.options(selectinload(ProductCard.clothes).selectinload(Clothes.sizes_quantities))
        elif category == settings.Shoes.CATEGORY_PROCESS:
            q = q.options(selectinload(ProductCard.shoes).selectinload(Shoe.sizes_quantities))
        elif category == settings.Linen.CATEGORY_PROCESS:
            q = q.options(selectinload(ProductCard.linen).selectinload(Linen.sizes_quantities))
        elif category == settings.Socks.CATEGORY_PROCESS:
            q = q.options(selectinload(ProductCard.socks).selectinload(Socks.sizes_quantities))
        elif category == settings.Parfum.CATEGORY_PROCESS:
            q = q.options(selectinload(ProductCard.parfum))

    else:
        q = q.options(
            selectinload(ProductCard.clothes).selectinload(Clothes.sizes_quantities),
            selectinload(ProductCard.shoes).selectinload(Shoe.sizes_quantities),
            selectinload(ProductCard.linen).selectinload(Linen.sizes_quantities),
            selectinload(ProductCard.socks).selectinload(Socks.sizes_quantities),
            selectinload(ProductCard.parfum),
        )

    if subcategory:
        q = q.filter(ProductCard.clothes.any(Clothes.subcategory == subcategory))

    if company_id:
        q = (
            q.join(UserProcessingCompany, UserProcessingCompany.user_id == ProductCard.user_id)
             .join(ProcessingCompany, ProcessingCompany.id == UserProcessingCompany.company_id)
             .filter(
                 UserProcessingCompany.company_id == company_id,
                 UserProcessingCompany.is_approved.is_(True),
                 ProcessingCompany.is_active.is_(True),
             )
        )

    if getattr(current_user, "role", None) == "manager":
        if status_value not in [ModerationStatus.SENT.value, ModerationStatus.SENT_NO_RD.value]:
            q = q.filter(ProductCard.manager_id == current_user.id)

    return q.all()


def h_pc_move_pack_cards(cards: list[ProductCard]) -> list[dict]:
    packed = []

    # unread только для нужных статусов
    need_ids = []
    for card in cards:
        st = card.status.value if hasattr(card.status, "value") else card.status
        if st in (ModerationStatus.IN_PROGRESS.value, ModerationStatus.IN_MODERATION.value,
                  ModerationStatus.CLARIFICATION.value):
            need_ids.append(card.id)

    unread_map = {c.id: 0 for c in cards}
    unread_map.update(h_unread_map_for_cards(need_ids, current_user))

    for card in cards:
        st = card.status.value if hasattr(card.status, "value") else card.status

        sizes_count, sizes_label = crm_card_sizes_label(card)  # вычислим 1 раз
        packed.append({
            "id": card.id,
            "category": card.category,
            "subcategory": crm_card_subcategory_slug(card),
            "subcategory_title": crm_card_subcategory_title(card),
            "status": st,
            "created_at": card.created_at,
            "sent_at": card.sent_at,
            "processing_info": card.processing_info,

            "user_id": card.user_id,
            "manager_id": card.manager_id,

            "user_login": card.creator.login_name if card.creator else "",
            "article_or_trademark": crm_card_article(card),
            "sizes": sizes_label,

            "manager_login": card.manager.login_name if card.manager else "",
            "reject_reason": card.reject_reason or "",

            "user_phone": card.creator.phone if card.creator else "",
            "user_email": card.creator.email if card.creator else "",
            "user_comment": card.user_comment,

            "sizes_count": sizes_count,
            "data_status": getattr(card, "data_status", None),

            "unread_count": unread_map.get(card.id, 0),
        })
    return packed


def h_pc_move_template_for_status(status_value: str) -> str:
    m = {
        ModerationStatus.SENT.value: "product_cards/crm/cards/updated_stages/_sent_list.html",
        ModerationStatus.SENT_NO_RD.value: "product_cards/crm/cards/updated_stages/_sent_no_rd_list.html",
        ModerationStatus.IN_PROGRESS.value: "product_cards/crm/cards/updated_stages/_in_progress_list.html",
        ModerationStatus.IN_MODERATION.value: "product_cards/crm/cards/updated_stages/_in_moderation_list.html",
        ModerationStatus.CLARIFICATION.value: "product_cards/crm/cards/updated_stages/_clarification_list.html",
        ModerationStatus.APPROVED.value: "product_cards/crm/cards/updated_stages/_approved_list.html",
        ModerationStatus.REJECTED.value: "product_cards/crm/cards/updated_stages/_rejected_list.html",
        ModerationStatus.PARTIALLY_APPROVED.value: "product_cards/crm/cards/updated_stages/_partially_approved_list.html",
    }
    return m.get(status_value)


def h_cards_ctx_key_for_status(st: str) -> str | None:
    return {
        ModerationStatus.SENT.value: "sent_cards",
        ModerationStatus.SENT_NO_RD.value: "sent_no_rd_cards",
        ModerationStatus.IN_PROGRESS.value: "in_progress_cards",
        ModerationStatus.IN_MODERATION.value: "in_moderation_cards",
        ModerationStatus.CLARIFICATION.value: "clarification_cards",
        ModerationStatus.APPROVED.value: "approved_cards",
        ModerationStatus.REJECTED.value: "rejected_cards",
        ModerationStatus.PARTIALLY_APPROVED.value: "partially_approved_cards",
    }.get(st)


def h_find_card_ids_by_article_or_tm(q: str) -> list[int]:
    def _escape_like(pattern: str) -> str:
        """Экранирование спецсимволов LIKE для SQL"""
        # Экранируем спецсимволы: % _ и саму обратную косую
        escaped = pattern.replace('\\', '\\\\')  # экранируем обратную косую
        escaped = escaped.replace('%', '\\%')  # экранируем %
        escaped = escaped.replace('_', '\\_')  # экранируем _
        return escaped

    q = (q or "").strip()
    if not q:
        return []
    q_escaped = _escape_like(q)
    like = f"%{q_escaped}%"

    ids = set()

    # article (OrderCommon.article) — обувь/бельё/одежда/носки
    ids.update(
        r[0] for r in db.session.query(Shoe.card_id)
        .filter(Shoe.card_id.isnot(None), Shoe.article.ilike(like))
        .distinct().all()
    )
    ids.update(
        r[0] for r in db.session.query(Linen.card_id)
        .filter(Linen.card_id.isnot(None), Linen.article.ilike(like))
        .distinct().all()
    )

    ids.update(
        r[0] for r in db.session.query(Clothes.card_id)
        .filter(Clothes.card_id.isnot(None), Clothes.article.ilike(like))
        .distinct().all()
    )
    ids.update(
        r[0] for r in db.session.query(Socks.card_id)
        .filter(Socks.card_id.isnot(None), Socks.article.ilike(like))
        .distinct().all()
    )

    # parfum — ищем по trademark
    ids.update(
        r[0] for r in db.session.query(Parfum.card_id)
        .filter(Parfum.card_id.isnot(None), Parfum.trademark.ilike(like))
        .distinct().all()
    )
    print(ids)
    return sorted(ids)


def h_pc_move_render_list_html(status_value: str, category=None, subcategory=None) -> tuple[str, int]:
    tpl = h_pc_move_template_for_status(status_value)
    if not tpl:
        return "", 0

    cards = h_pc_move_get_cards_by_status(status_value, category=category, subcategory=subcategory)
    packed = h_pc_move_pack_cards(cards)

    ctx = {
        "categories_common": CATEGORIES_COMMON,
        "sent_cards": packed if status_value == ModerationStatus.SENT.value else [],
        "sent_no_rd_cards": packed if status_value == ModerationStatus.SENT_NO_RD.value else [],
        "in_progress_cards": packed if status_value == ModerationStatus.IN_PROGRESS.value else [],
        "in_moderation_cards": packed if status_value == ModerationStatus.IN_MODERATION.value else [],
        "clarification_cards": packed if status_value == ModerationStatus.CLARIFICATION.value else [],
        "approved_cards": packed if status_value == ModerationStatus.APPROVED.value else [],
        "rejected_cards": packed if status_value == ModerationStatus.REJECTED.value else [],
    }

    html = render_template(tpl, **ctx)
    return html, len(packed)


def h_pc_move_apply_status_transition(card: ProductCard, target: str, reject_reason: str | None = None):
    """
    Применяет изменение статуса и пишет лог/тайминги.
    """
    dt = datetime.now()
    manager_login = getattr(current_user, "login_name", "") or str(current_user.id)
    dt_str = dt.strftime("%d-%m-%Y %H:%M:%S")

    if target == ModerationStatus.SENT.value:
        card.status = ModerationStatus.SENT
        card.manager_id = None
        card.taken_at = None
        card.card_log = h_append_card_log(card.card_log, f"\n{dt_str} вернул в отправленные {manager_login};")

    elif target == ModerationStatus.IN_PROGRESS.value:
        card.status = ModerationStatus.IN_PROGRESS
        # если карточку возвращают в работу, taken_at логично иметь
        if not card.taken_at:
            card.taken_at = dt
        card.card_log = h_append_card_log(card.card_log, f"\n{dt_str} перевёл в обработку {manager_login};")
    elif target == ModerationStatus.IN_MODERATION.value:
        card.status = ModerationStatus.IN_MODERATION
        # если карточку возвращают в работу, taken_at логично иметь
        if not card.moderation_at:
            card.moderation_at = dt
        card.card_log = h_append_card_log(card.card_log, f"\n{dt_str} перевёл на модерацию {manager_login};")
    elif target == ModerationStatus.CLARIFICATION.value:
        card.status = ModerationStatus.CLARIFICATION
        card.clarification_requested_at = dt
        card.card_log = h_append_card_log(card.card_log, f"\n{dt_str} отправил на уточнение {manager_login};")

    elif target == ModerationStatus.APPROVED.value:
        card.status = ModerationStatus.APPROVED
        card.approved_at = dt
        card.card_log = h_append_card_log(card.card_log, f"\n{dt_str} одобрил {manager_login};")

    elif target == ModerationStatus.REJECTED.value:
        if not reject_reason:
            raise ValueError("Укажите причину отмены")
        card.status = ModerationStatus.REJECTED
        card.reject_reason = reject_reason
        card.rejected_at = dt
        card.card_log = h_append_card_log(card.card_log, f"\n{dt_str} отменил {manager_login}; причина: {reject_reason};")

    else:
        raise ValueError("Некорректный target")


def h_pc_move_check_permissions(card: ProductCard, target: str):
    """
    Проверки:
    - двигаем только из IN_PROGRESS
    - назад в SENT — только роли ALLOWED_BACK_ROLES
    - manager может двигать только свои карточки (manager_id == current_user.id)
    """
    if card.status != ModerationStatus.IN_PROGRESS:
        raise PermissionError("Карточка не в статусе 'В обработке'")

    # возврат назад — только админские роли
    if target == ModerationStatus.SENT.value and current_user.role not in ALLOWED_BACK_ROLES:
        raise PermissionError("Недостаточно прав")

    # админы могут двигать любую карточку
    if current_user.role in ALLOWED_BACK_ROLES:
        return

    # менеджер — только свои
    if current_user.role == "manager":
        if card.manager_id != current_user.id:
            raise PermissionError("Карточка закреплена за другим оператором")
        return

    # остальные роли (если вдруг есть) — безопасный дефолт: как manager (только свои)
    if card.manager_id != current_user.id:
        raise PermissionError("Недостаточно прав (карточка не закреплена за вами)")


def h_append_card_log(old: str | None, line: str) -> str:
    return ((old or "") + line)[-settings.ProducCards.MAX_LOG:]


def get_users_processing_companies_map(user_ids: list[int]) -> dict[int, list[dict]]:
    if not user_ids:
        return {}

    rows = (
        UserProcessingCompany.query
        .options(joinedload(UserProcessingCompany.company))
        .filter(UserProcessingCompany.user_id.in_(user_ids))
        .order_by(UserProcessingCompany.user_id.asc(), UserProcessingCompany.slot.asc())
        .all()
    )

    out: dict[int, list[dict]] = {}
    for r in rows:
        out.setdefault(r.user_id, []).append({
            "slot": r.slot,
            "is_approved": bool(r.is_approved),
            "company_id": r.company_id,
            "title": r.company.title if r.company else "",
            "inn": r.company.inn if r.company else "",
            "is_active": bool(r.company.is_active) if r.company else True,
        })
    return out


def helper_reject_cards_by_rd_date_to_today() -> dict:
    today = date.today()
    dt_str = datetime.now().strftime("%d.%m.%Y")

    # подстраховка: лог-строка (короткая и понятная)
    log_line = f"\n{dt_str} карточка переведена в отклоненные по Дате РД;"
    reject_reason = "Истек срок действия РД (Дата 'До' = сегодня)"

    # ВАЖНО: исключаем уже отклоненные, и (по желанию) можно исключить черновики created
    base = ProductCard.query.filter(
        ProductCard.status != ModerationStatus.REJECTED
    )

    # Для каждой категории тянем rd_date_to из дочерней сущности
    # Предполагаю, что поле называется rd_date_to (как в форме).
    # Если у тебя в моделях это поле называется иначе — скажи, поправлю.
    q = (
        base.outerjoin(Clothes, Clothes.card_id == ProductCard.id)
            .outerjoin(Socks,   Socks.card_id == ProductCard.id)
            .outerjoin(Shoe,    Shoe.card_id == ProductCard.id)
            .outerjoin(Linen,   Linen.card_id == ProductCard.id)
            .outerjoin(Parfum,  Parfum.card_id == ProductCard.id)
            .filter(
                or_(
                    Clothes.rd_date_to == today,
                    Socks.rd_date_to == today,
                    Shoe.rd_date_to == today,
                    Linen.rd_date_to == today,
                    Parfum.rd_date_to == today,
                )
            )
            .distinct()
    )

    cards = q.all()
    if not cards:
        return {"status": "success", "rejected": 0}

    rejected_cnt = 0
    for card in cards:
        card.status = ModerationStatus.REJECTED
        card.rejected_at = datetime.now()
        card.reject_reason = reject_reason

        card.card_log = h_append_card_log((card.card_log or ""), log_line)
        rejected_cnt += 1
    try:
        db.session.commit()
        return {"status": "success", "rejected": rejected_cnt}
    except Exception:
        db.session.rollback()
        return {"status": "error"}

