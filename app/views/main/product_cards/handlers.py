from datetime import datetime
from flask import request, render_template, jsonify, flash, url_for, redirect, Response
from flask_login import current_user
from markupsafe import Markup
from sqlalchemy import case, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload, selectinload, load_only

from config import settings
from logger import logger
from models import db, ExceptionDataUsers, Order, ProductCard, Shoe, Linen, Parfum, Clothes, Socks, ModerationStatus, \
    UserProcessingCompany, ProcessingCompany
from utilities.categories_data.subcategories_data import ClothesSubcategories
from utilities.categories_data.subcategories_logic import get_subcategory
from utilities.helpers.h_tg_notify import helper_send_user_order_tg_notify
from utilities.saving_uts import get_rows_marks
from utilities.sql_categories_aggregations import SQLQueryCategoriesAll
from utilities.support import check_forbidden_words, helper_preload_common, helper_check_uoabm, \
    helper_check_user_order_in_archive, check_order_pos, process_admin_order_num, process_order_start
from utilities.telegram import MarkinerisInform
from utilities.validators import ValidatorProcessor, validate_and_build_contact_info
from views.main.product_cards.chat.helpers import (
    USER_CHAT_WRITE_STATUSES,
    h_pc_chat_unread_count,
    h_unread_map_for_cards,
    h_visible_chat_card_ids,
)
from views.main.product_cards.crm.helpers import crm_card_subcategory_title, crm_card_sizes_label, crm_card_article, h_append_card_log
from views.main.product_cards.order_helpers import _json_error, _add_order_item_from_card, \
    _count_open_moderation_orders, _get_card_or_fail, _validate_card_access_and_status, _load_cards_for_order, \
    _count_open_pc_orders, common_save_copy_pc_order
from views.main.product_cards.support import validate_card_form, save_clothes_card, save_shoes_card, save_linen_card, \
    save_socks_card, save_parfum_card, parse_sizes_for_category, CATEGORIES_COMMON, MODERATION_STATUS_TITLES, \
    MODERATION_STATUS_COLORS, normalize_article_for_category, normalize_color_for_category, collect_existing_size_keys, \
    filter_new_sizes, CARD_FIELDS, \
    extract_card_main_and_sizes, get_card_ctx, check_same_fields_if_exists, \
    require_user_two_companies, CATEGORY_TITLES, get_card_entity_for_prefill, assert_frozen_fields_unchanged, \
    update_card_allowed_fields, ALLOWED_CARDS_DELETE_STATUSES, card_has_rd, CARD_STATUS_DATETIME_ATTR, \
    get_card_allowed_field_changes, merge_selected_created_wear_cards
from views.main.product_cards.utils import validate_rd_block


def h_cards():
    # cards_video_key = 'vid02_create_order'
    category = request.args.get("category", "clothes")
    subcategory = request.args.get("subcategory")
    article_query = request.args.get("article_query", "").strip()

    # 1) проверяем, есть ли запись
    # exists = db.session.execute(
    #     select(UserSeen.id).where(
    #         UserSeen.user_id == current_user.id,
    #         UserSeen.key == cards_video_key
    #     ).limit(1)
    # ).first()

    # show_video = exists is None
    #
    # # 2) если надо показать — создаём запись
    # if show_video:
    #     db.session.add(UserSeen(user_id=current_user.id, key=cards_video_key))
    #     db.session.commit()

    return render_template(
        "product_cards/user/main.html",
        current_category=category,
        current_subcategory=subcategory,
        article_query=article_query,
        mapper_categories=CATEGORIES_COMMON,
        # show_cards_video=show_video
    )


# @profile_db_verbose('cards_table')
def h_cards_table():
    def _get_card_status_datetime(card: ProductCard):
        status_value = card.status.value if hasattr(card.status, "value") else str(card.status)
        attr_name = CARD_STATUS_DATETIME_ATTR.get(status_value, "created_at")
        return getattr(card, attr_name, None) or card.created_at
    category = request.form.get("category", settings.Clothes.CATEGORY_PROCESS )
    subcategory = request.form.get("subcategory") or None
    article_query = request.form.get("article_query", "").strip()
    page = request.form.get("page", default=1, type=int)
    per_page = 20
    if category == settings.Clothes.CATEGORY_PROCESS and not subcategory:
        subcategory = ClothesSubcategories.common.value
    # --- проверки категории / подкатегории ---
    cfg = CATEGORIES_COMMON.get(category)
    if cfg is None:
        return jsonify({
            "status": "error",
            "message": f"Категория '{category}' не существует"
        }), 400

    if subcategory and not cfg["has_subcategory"]:
        return jsonify({
            "status": "error",
            "message": "Подкатегория доступна только для категории 'clothes'"
        }), 400

    if cfg["has_subcategory"] and subcategory:
        valid_subcats = [s.value for s in ClothesSubcategories]
        if subcategory not in valid_subcats:
            return jsonify({
                "status": "error",
                "message": f"Подкатегория '{subcategory}' не существует"
            }), 400

    model = cfg["model"]
    rel_name = cfg["rel_name"]
    has_subcategory = cfg["has_subcategory"]

    query = ProductCard.query.filter(
        ProductCard.user_id == current_user.id,
        ProductCard.category == category,
    )

    # фильтр по подкатегории — только для одежды
    if has_subcategory and subcategory:
        query = query.filter(ProductCard.clothes.any(Clothes.subcategory == subcategory))

    # поиск по артикулу / trademark
    if article_query:
        like = f"%{article_query}%"
        rel = getattr(ProductCard, rel_name)

        if hasattr(model, "article"):
            query = query.filter(rel.any(model.article.ilike(like)))
        else:
            query = query.filter(rel.any(model.trademark.ilike(like)))

    status_order = case(
        (ProductCard.status == ModerationStatus.APPROVED, 1),
        (ProductCard.status == ModerationStatus.PARTIALLY_APPROVED, 2),
        else_=3
    )

    query = query.order_by(status_order, ProductCard.created_at.desc())
    if category == settings.Clothes.CATEGORY_PROCESS:
        query = query.options(selectinload(ProductCard.clothes).selectinload(Clothes.sizes_quantities))
    elif category == settings.Socks.CATEGORY_PROCESS:
        query = query.options(selectinload(ProductCard.socks).selectinload(Socks.sizes_quantities))
    elif category == settings.Shoes.CATEGORY_PROCESS:
        query = query.options(selectinload(ProductCard.shoes).selectinload(Shoe.sizes_quantities))
    elif category == settings.Linen.CATEGORY_PROCESS:
        query = query.options(selectinload(ProductCard.linen).selectinload(Linen.sizes_quantities))
    elif category == settings.Parfum.CATEGORY_PROCESS:
        query = query.options(selectinload(ProductCard.parfum))

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    offset = (pagination.page - 1) * pagination.per_page

    cards = pagination.items
    card_ids = [c.id for c in cards]
    chat_visible_ids = h_visible_chat_card_ids(card_ids, current_user)
    chat_readable_ids = {
        c.id for c in cards
        if (c.status.value if hasattr(c.status, "value") else str(c.status)) in USER_CHAT_WRITE_STATUSES
        or c.id in chat_visible_ids
    }

    unread_map = {c.id: 0 for c in cards}
    unread_map.update(h_unread_map_for_cards(list(chat_readable_ids), current_user))

    html = render_template(
        "product_cards/user/table.html",
        product_cards=cards,
        pagination=pagination,
        current_category=category,
        current_subcategory=subcategory,
        article_query=article_query,
        categories_common=CATEGORIES_COMMON,
        category_titles=CATEGORY_TITLES,
        status_titles=MODERATION_STATUS_TITLES,
        # status_colors=MODERATION_STATUS_COLORS,
        offset=offset,
        unread_map=unread_map,
        chat_readable_ids=chat_readable_ids,
        get_card_status_datetime=_get_card_status_datetime
    )
    return jsonify({
        "status": "success",
        "html": html})


def h_new_product_card():
    category = request.args.get("category")
    subcategory = request.args.get("subcategory")
    # if category == 'shoes':
    #     flash("Ведется обновление раздела карточки категории обувь. Карточки категории обувь временно не обрабатываются", "error")
    #     return redirect(url_for('user_product_cards.cards'))
    if category not in CATEGORIES_COMMON:
        flash("Неизвестная категория", "error")
        return redirect(url_for('user_product_cards.cards'))

    flash(
        message=f"Открыта страница добавления новой карточки товара, категория {CATEGORIES_COMMON[category]['title']}",
        category="success"
    )

    ctx = get_card_ctx(category=category, subcategory=subcategory)

    return render_template("product_cards/new/main_card.html", **ctx)


def h_save_product_card():
    form_data = request.form
    form_dict = form_data.to_dict()

    category = form_data.get("category")
    subcategory = form_data.get("subcategory")
    # if category == 'shoes':
    #     return jsonify(status="error", message="Ведется обновление раздела карточки категории обувь. Карточки категории обувь временно не обрабатываются")
    if category not in CATEGORIES_COMMON:
        return jsonify(status="error", message="Неизвестная категория")

    # 1. Валидация
    try:
        validate_card_form(
            category_process=category,
            subcategory=subcategory,
            form_data=form_data
        )
    except Exception as e:
        return jsonify(status="error", message=str(e))

    # 1.1 Запрещённые слова
    try:
        check_forbidden_words(form_dict.get("article", "").strip(), "article")
        check_forbidden_words(form_dict.get("trademark", "").strip(), "trademark")
    except Exception as e:
        return jsonify(status="error", message=str(e))

    # 1.2 Если такой товар уже есть — поля из CARD_FIELDS должны совпадать
    try:
        check_same_fields_if_exists(
            category=category,
            subcategory=subcategory,
            form_dict=form_dict,
        )
    except Exception as e:
        return jsonify(status="error", message=str(e))

    # 1.3 Валидация РД (единая для всех категорий)
    try:
        validate_rd_block(form_dict)

    except Exception as e:
        return jsonify(status="error", message=str(e))

    # --- ОТДЕЛЬНАЯ ВЕТКА ДЛЯ ПАРФЮМА ---
    if category == settings.Parfum.CATEGORY_PROCESS:
        # Для парфюма нет размеров, только quantity, никаких уникальностей по size
        sizes_quantities = []
        filtered_sq = []
        skipped_labels = []
        existing_card_ids = set()

    else:
        # 2. Парсим размеры (для всех, кроме парфюма)
        try:
            sizes_quantities = parse_sizes_for_category(
                category=category,
                form_data_raw=form_data,
                subcategory=subcategory,
            )
        except Exception as e:
            return jsonify(status="error", message=str(e))

        # 2.1 Нормализованный артикул и поиск уже существующих размеров
        article_norm = normalize_article_for_category(category, form_dict)
        color_norm = normalize_color_for_category(form_dict)

        existing_keys, existing_card_ids = collect_existing_size_keys(user_id=current_user.id,
            category=category,
            subcategory=subcategory,
            article=article_norm,
            color=color_norm,
        )

        # 2.2 Фильтруем дублирующиеся размеры
        filtered_sq, skipped_labels = filter_new_sizes(
            category=category,
            sizes_quantities=sizes_quantities,
            existing_keys=existing_keys,
        )

        if not filtered_sq:
            # все размеры — дубликаты, карточку не создаём
            if existing_card_ids:
                ids_str = ", ".join(str(cid) for cid in sorted(existing_card_ids))
                msg = (
                    f"Все указанные размеры уже есть в ваших карточках ID: {ids_str}. "
                    f"Новая карточка не создана."
                )
            else:
                msg = (
                    "Все указанные размеры уже присутствуют в ваших карточках. "
                    "Новая карточка не создана."
                )
            return jsonify(status="error", message=msg)


    # 3. Создаём карточку
    card = ProductCard(
        user_id=current_user.id,
        category=category,
        status=ModerationStatus.CREATED.value,
    )
    db.session.add(card)
    db.session.flush()

    # 4. Сохраняем позиции категории
    save_map = {
        settings.Clothes.CATEGORY_PROCESS: save_clothes_card,
        settings.Shoes.CATEGORY_PROCESS:   save_shoes_card,
        settings.Linen.CATEGORY_PROCESS:   save_linen_card,
        settings.Socks.CATEGORY_PROCESS:   save_socks_card,
        settings.Parfum.CATEGORY_PROCESS:  save_parfum_card,
    }
    saver = save_map[category]

    try:
        if category == settings.Parfum.CATEGORY_PROCESS:
            # парфюм — sizes_quantities не нужны, saver сам возьмёт quantity из form_dict
            saver(
                card=card,
                form_dict=form_dict,
                sizes_quantities=None,  # можно и не передавать, если сигнатура позволяет
                subcategory=subcategory,
            )
        else:
            # обычные категории — сохраняем только новые размеры
            saver(
                card=card,
                form_dict=form_dict,
                sizes_quantities=filtered_sq,
                subcategory=subcategory,
            )

            # ВСЕГДА: гарантируем 2 компании или падаем
        require_user_two_companies(current_user.id)

        db.session.commit()
    except Exception as e:
        logger.exception('save_product_card category')
        db.session.rollback()
        return jsonify(status="error", message=str(e))

    # 5. Сообщение пользователю
    base_msg = f"Карточка товара добавлена (ID {card.id})."

    # для парфюма skipped_labels всегда пустой, этот блок просто не сработает
    if skipped_labels and existing_card_ids:
        ids_str = ", ".join(str(cid) for cid in sorted(existing_card_ids))
        sizes_str = ", ".join(skipped_labels)
        extra = (
            f" Размеры {sizes_str} уже есть в ваших карточках ID: {ids_str} "
            f"и не были добавлены в новую карточку."
        )
        message = base_msg + extra
    else:
        message = base_msg

    return jsonify(
        status="success",
        card_id=card.id,
        message=message,
    )


def h_edit_product_card(card_id: int, crm_: bool = False):
    card = ProductCard.query.filter_by(id=card_id).first()

    if crm_:
        if (current_user.role == settings.MANAGER_USER
                and card.status not in [ModerationStatus.SENT_NO_RD, ModerationStatus.SENT]
                and card.manager_id != current_user.id):
            flash("Ошибка! Вы пытаетесь редактировать не свою карточку.", "error")
            return redirect(url_for('crm_product_cards.cards'))
    else:
        if current_user.role == settings.ORD_USER and card.user_id != current_user.id:
            flash("Ошибка! Вы пытаетесь редактировать не свою карточку.", "error")
            return redirect(url_for('user_product_cards.cards'))
    # if card.category == 'shoes' and not crm_:
    #     flash("Ведется обновление раздела карточки категории обувь. Карточки категории обувь временно не обрабатываются", "error")
    #     return redirect(url_for("user_product_cards.cards"))
    allowed_statuses = (
        [ModerationStatus.SENT_NO_RD, ModerationStatus.CLARIFICATION]
        if crm_
        else [ModerationStatus.CLARIFICATION]
    )
    if card.status not in allowed_statuses:
        message = (
            "Редактирование доступно только для карточек 'На уточнении' и 'Отправлены без РД'."
            if crm_
            else "Редактирование доступно только для карточек 'На уточнении'."
        )
        flash(message, "error")
        return redirect(url_for("user_product_cards.cards")) if not crm_ else redirect(url_for("crm_product_cards.cards"))

    # достаём данные категории (первая запись)
    copied_order = get_card_entity_for_prefill(card=card)

    ctx = get_card_ctx(category=card.category, subcategory=getattr(copied_order, "subcategory", None))
    ctx["copied_order"] = copied_order
    ctx["edit_mode"] = True
    ctx["edit_card_id"] = card.id
    ctx["crm_"] = crm_

    return render_template("product_cards/new/main_card.html", **ctx)


def h_update_product_card(crm_: bool = False):
    form_data = request.form
    form_dict = form_data.to_dict()

    card_id = form_data.get("card_id", type=int)
    if not card_id:
        return jsonify(status="error", message="card_id не передан")

    card = ProductCard.query.filter_by(id=card_id,).first()
    if not card:
        return jsonify(status="error", message="Карточка не найдена")

    if current_user.role == settings.ORD_USER and card.user_id != current_user.id:
        return jsonify(status="error", message="Вы пытаетесь редактировать не свою карточку.")

    if current_user.role == settings.ORD_USER and card.status != ModerationStatus.CLARIFICATION:
        return jsonify(status="error", message="Редактирование доступно только для карточек 'На уточнении'.")
    if current_user.role != settings.ORD_USER and card.status not in [ModerationStatus.SENT_NO_RD,
                                                                      ModerationStatus.CLARIFICATION]:
        return jsonify(status="error",
                       message="Редактирование доступно только для статусов 'Отправлены без РД' и 'На уточнении'")
    if (
            current_user.role == settings.MANAGER_USER
            and card.status not in [ModerationStatus.SENT_NO_RD, ModerationStatus.SENT]
            and card.manager_id != current_user.id
    ):
        return jsonify(status="error", message="Вы пытаетесь редактировать не свою карточку.")

    category = card.category
    subcategory = form_data.get("subcategory")
    entity_before = get_card_entity_for_prefill(card)
    old_identity = ""
    if entity_before:
        old_identity = (
                           getattr(entity_before, "trademark", "") if category == settings.Parfum.CATEGORY_PROCESS
                           else getattr(entity_before, "article", "")
                       ) or ""
    # 1) валидируем форму как обычно,
    try:
        validate_card_form(category_process=category, subcategory=subcategory, form_data=form_data)
    except Exception as e:
        return jsonify(status="error", message=str(e))
    try:
        check_forbidden_words(form_dict.get("article", "").strip(), "article")
        check_forbidden_words(form_dict.get("trademark", "").strip(), "trademark")
    except Exception as e:
        return jsonify(status="error", message=str(e))
    try:
        validate_rd_block(form_dict)
    except Exception as e:
        return jsonify(status="error", message=str(e))

    # 2) ЗАПРЕЩАЕМ менять "замороженные" поля:
    try:
        assert_frozen_fields_unchanged(card=card, form_data=form_data)
    except Exception as e:
        return jsonify(status="error", message=str(e))

    # 3) обновляем только разрешённые поля (кроме артикула/цвета/размеров) identity-поля уже проверены выше
    try:
        log_user_changes = card.status == ModerationStatus.CLARIFICATION
        changes = get_card_allowed_field_changes(card=card, form_dict=form_dict) if (crm_ or log_user_changes) else []
        update_card_allowed_fields(card=card, form_dict=form_dict, form_data=form_data)
        entity_after = get_card_entity_for_prefill(card)
        new_identity = ""
        if entity_after:
            new_identity = (
                               getattr(entity_after, "trademark", "") if category == settings.Parfum.CATEGORY_PROCESS
                               else getattr(entity_after, "article", "")
                           ) or ""
        if old_identity != new_identity:
            dt_str = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            field_title = "товарный знак" if category == settings.Parfum.CATEGORY_PROCESS else "артикул"
            actor = getattr(current_user, "login_name", "") or str(current_user.id)
            card.card_log = h_append_card_log(
                card.card_log,
                f"\n{dt_str} изменил {field_title}: '{old_identity}' -> '{new_identity}' пользователь {actor};")
        if changes:
            dt_str = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            user_login = getattr(current_user, "login_name", "") or str(current_user.id)
            actor_label = f"Клиент {user_login}" if current_user.id == card.user_id else user_login
            status_log_label = {
                ModerationStatus.CLARIFICATION: "НУ",
                ModerationStatus.SENT_NO_RD: "ОБРД",
            }.get(card.status, "")
            card.card_log = h_append_card_log(
                card.card_log,
                f"\n{dt_str} {actor_label} исправил ({status_log_label}): {', '.join(changes)};"
            )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify(status="error", message=str(e))

    return jsonify(status="success", message="Карточка обновлена")


def h_get_created_cards():
    base = (
        ProductCard.query
        .options(load_only(ProductCard.id, ProductCard.category, ProductCard.created_at, ProductCard.status))
        .filter(
            ProductCard.user_id == current_user.id,
            ProductCard.status == ModerationStatus.CREATED
        )
        .order_by(ProductCard.created_at.desc())
        .all()
    )

    # какие категории реально есть
    cats = {c.category for c in base}
    ids = [c.id for c in base]

    # второй запрос: догружаем только нужные связи (в том же порядке потом соберём)
    q = ProductCard.query.filter(ProductCard.id.in_(ids)).options(
        load_only(ProductCard.id, ProductCard.category, ProductCard.created_at, ProductCard.status)
    )

    if settings.Clothes.CATEGORY_PROCESS in cats:
        q = q.options(selectinload(ProductCard.clothes).selectinload(Clothes.sizes_quantities))
    if settings.Shoes.CATEGORY_PROCESS in cats:
        q = q.options(selectinload(ProductCard.shoes).selectinload(Shoe.sizes_quantities))
    if settings.Linen.CATEGORY_PROCESS in cats:
        q = q.options(selectinload(ProductCard.linen).selectinload(Linen.sizes_quantities))
    if settings.Socks.CATEGORY_PROCESS in cats:
        q = q.options(selectinload(ProductCard.socks).selectinload(Socks.sizes_quantities))
    if settings.Parfum.CATEGORY_PROCESS in cats:
        q = q.options(selectinload(ProductCard.parfum))

    full = q.all()
    full_by_id = {c.id: c for c in full}
    cards_raw = [full_by_id[c.id] for c in base]  # восстановим сортировку

    cards = []
    for card in cards_raw:
        cfg = CATEGORIES_COMMON.get(card.category, {})
        cards.append({
            "id": card.id,
            "category": card.category,
            "category_title": cfg.get("title", card.category),
            "subcategory": crm_card_subcategory_title(card),
            "article": crm_card_article(card),
            "color": getattr(get_card_entity_for_prefill(card), "color",
                             None) if card.category != settings.Parfum.CATEGORY_PROCESS else None,
            "sizes": crm_card_sizes_label(card)[1],
        })

    return jsonify(status="success", cards=cards)


def h_send_cards_moderate():
    data = request.get_json(silent=True) or {}
    card_ids = data.get("card_ids")

    if not isinstance(card_ids, list) or not card_ids or not all(isinstance(x, int) for x in card_ids):
        return jsonify({"status": "error", "error": "card_ids must be a non-empty list of integers"}), 400

    try:
        now = datetime.now()

        # 1) Берём только id+category для нужных карточек
        base = (
            ProductCard.query
            .filter(
                ProductCard.id.in_(card_ids),
                ProductCard.user_id == current_user.id,
                ProductCard.status == ModerationStatus.CREATED,
            )
            .with_entities(ProductCard.id, ProductCard.category)
            .all()
        )

        if not base:
            return jsonify({"status": "error", "error": "No cards to send"}), 404

        ids_by_cat: dict[str, list[int]] = {}
        for cid, cat in base:
            ids_by_cat.setdefault(cat, []).append(cid)

        # 2) Для каждой категории — 1 запрос с нужным joinedload
        cards: list[ProductCard] = []
        for cat, ids in ids_by_cat.items():
            q = ProductCard.query.filter(ProductCard.id.in_(ids))

            if cat == "shoes":
                # return jsonify({"status": "error", "error": "Ведется обновление раздела карточки категории обувь. Карточки категории обувь временно не обрабатываются"}), 404
                q = q.options(joinedload(ProductCard.shoes).joinedload(Shoe.sizes_quantities))
            elif cat == "clothes":
                q = q.options(joinedload(ProductCard.clothes).joinedload(Clothes.sizes_quantities))
            elif cat == "socks":
                q = q.options(joinedload(ProductCard.socks).joinedload(Socks.sizes_quantities))
            elif cat == "linen":
                q = q.options(joinedload(ProductCard.linen).joinedload(Linen.sizes_quantities))
            elif cat == "parfum":
                q = q.options(joinedload(ProductCard.parfum))
            else:
                # неизвестная категория — всё равно загрузим карточки без релейшенов
                pass

            cards.extend(q.all())

        merge_result = merge_selected_created_wear_cards(cards)
        cards = merge_result["cards"]
        db.session.flush()

        ids_with_rd: list[int] = []
        ids_no_rd: list[int] = []

        for c in cards:
            (ids_with_rd if card_has_rd(c) else ids_no_rd).append(c.id)

        # 4) Два апдейта (быстро)
        updated_sent = 0
        updated_no_rd = 0

        if ids_with_rd:
            updated_sent = (
                ProductCard.query
                .filter(
                    ProductCard.id.in_(ids_with_rd),
                    ProductCard.user_id == current_user.id,
                    ProductCard.status == ModerationStatus.CREATED,
                )
                .update(
                    {ProductCard.status: ModerationStatus.SENT, ProductCard.sent_at: now},
                    synchronize_session=False
                )
            )

        if ids_no_rd:
            updated_no_rd = (
                ProductCard.query
                .filter(
                    ProductCard.id.in_(ids_no_rd),
                    ProductCard.user_id == current_user.id,
                    ProductCard.status == ModerationStatus.CREATED,
                )
                .update(
                    {ProductCard.status: ModerationStatus.SENT_NO_RD, ProductCard.sent_at: now},
                    synchronize_session=False
                )
            )

        db.session.commit()

        message = f"Отправлено с РД: {updated_sent}, без РД: {updated_no_rd}"
        if merge_result["merged_cards"]:
            message += (
                f". Объединено карточек: {merge_result['merged_cards']}, "
                f"перенесено размеров: {merge_result['moved_sizes']}"
            )
            if merge_result["skipped_sizes"]:
                message += f", пропущено дублей размеров: {merge_result['skipped_sizes']}"

        return jsonify({
            "status": "success",
            "requested": len(card_ids),
            "updated": updated_sent + updated_no_rd,
            "merged_cards": merge_result["merged_cards"],
            "moved_sizes": merge_result["moved_sizes"],
            "skipped_sizes": merge_result["skipped_sizes"],
            "deleted_card_ids": merge_result["deleted_card_ids"],
            "message": message,
        })

    except SQLAlchemyError:
        db.session.rollback()
        logger.exception("DB error in send_cards_moderate")
        return jsonify({"status": "error", "error": "Database error"}), 500
    except Exception:
        db.session.rollback()
        logger.exception("Unexpected error in send_cards_moderate")
        return jsonify({"status": "error", "error": "Unexpected error"}), 500


# @profile_db_verbose("card_view")
def h_card_view(card_id: int, crm_: bool = False):
    """
        Возвращает HTML для модалки просмотра карточки.
        """

    def _get_card_for_view(card_id: int, crm_: bool):
        base = (
            ProductCard.query
            .with_entities(ProductCard.id, ProductCard.category, ProductCard.user_id)
            .filter(ProductCard.id == card_id)
        )
        if not crm_:
            base = base.filter(ProductCard.user_id == current_user.id)

        row = base.first_or_404()

        q = (
            ProductCard.query
            .filter(ProductCard.id == row.id)
            .options(
                joinedload(ProductCard.creator),
                joinedload(ProductCard.manager),
            )
        )

        cat = row.category
        if cat == settings.Clothes.CATEGORY_PROCESS:
            q = q.options(selectinload(ProductCard.clothes).selectinload(Clothes.sizes_quantities))
        elif cat == settings.Socks.CATEGORY_PROCESS:
            q = q.options(selectinload(ProductCard.socks).selectinload(Socks.sizes_quantities))
        elif cat == settings.Shoes.CATEGORY_PROCESS:
            q = q.options(selectinload(ProductCard.shoes).selectinload(Shoe.sizes_quantities))
        elif cat == settings.Linen.CATEGORY_PROCESS:
            q = q.options(selectinload(ProductCard.linen).selectinload(Linen.sizes_quantities))
        elif cat == settings.Parfum.CATEGORY_PROCESS:
            q = q.options(selectinload(ProductCard.parfum))

        return q.first_or_404()

    card = _get_card_for_view(card_id=card_id, crm_=crm_)

    # --- компании пользователя (автора карточки) ---
    user_companies_rows = (
        UserProcessingCompany.query
        .options(joinedload(UserProcessingCompany.company))
        .filter(UserProcessingCompany.user_id == card.user_id)
        .order_by(UserProcessingCompany.slot.asc())
        .all()
    )

    user_companies = []
    for r in user_companies_rows:
        comp = r.company
        user_companies.append({
            "slot": r.slot,
            "is_approved": bool(r.is_approved),
            "assigned_at": r.assigned_at,
            "title": comp.title if comp else "",
            "inn": comp.inn if comp else "",
            "is_active": bool(comp.is_active) if comp else True,
        })
    can_edit_companies = bool(
        crm_
        and (card.status == ModerationStatus.PARTIALLY_APPROVED)
        and (current_user.role in {"manager", "supermanager", "superuser"})
    )

    pool_companies = []
    if can_edit_companies:
        pool_companies = (
            ProcessingCompany.query
            .filter(ProcessingCompany.is_active.is_(True))
            .order_by(ProcessingCompany.title.asc())
            .all()
        )

    cfg = CATEGORIES_COMMON.get(card.category)
    if not cfg:
        return jsonify(status="error", message="Неизвестная категория карточки"), 400

    rel_name = cfg["rel_name"]  # shoes / clothes / ...
    items = getattr(card, rel_name)  # список дочерних записей
    main = items[0 ] if items else None

    # --- соберём размеры/кол-ва в плоский список для шаблона ---
    sizes = []

    if card.category == settings.Clothes.CATEGORY_PROCESS:
        # одежда
        for c in card.clothes:
            for sq in c.sizes_quantities:
                sizes.append({
                    "size": sq.size,
                    # "quantity": sq.quantity,
                    "size_type": sq.size_type,
                    "is_approved": getattr(sq, "is_approved", False),
                })

    elif card.category == settings.Socks.CATEGORY_PROCESS:
        for s in card.socks:
            for sq in s.sizes_quantities:
                sizes.append({
                    "size": sq.size,
                    # "quantity": sq.quantity,
                    "size_type": sq.size_type,
                    "is_approved": getattr(sq, "is_approved", False),
                })

    elif card.category == settings.Shoes.CATEGORY_PROCESS:
        for sh in card.shoes:
            for sq in sh.sizes_quantities:
                sizes.append({
                    "size": sq.size,
                    # "quantity": sq.quantity,
                    "is_approved": getattr(sq, "is_approved", False),
                })

    elif card.category == settings.Linen.CATEGORY_PROCESS:
        for l in card.linen:
            for sq in l.sizes_quantities:
                sizes.append({
                    "size": sq.size,
                    "unit": sq.unit,
                    # "quantity": sq.quantity,
                    "is_approved": getattr(sq, "is_approved", False),
                })

    elif card.category == settings.Parfum.CATEGORY_PROCESS:
        # у парфюма нет размеров – всё в одной записи
        sizes = []
    fields = CARD_FIELDS.get(card.category, {})

    rd_description = settings.RD_DESCRIPTION
    rd_types_list = settings.RD_TYPES
    by_slot = {uc["slot"]: uc for uc in user_companies}

    slot1_filled = bool(by_slot.get(1) and by_slot[1].get("inn"))
    slot2_filled = bool(by_slot.get(2) and by_slot[2].get("inn"))

    html = render_template(
        "product_cards/user/card_view.html",
        card=card,
        cfg=cfg,
        main=main,
        sizes=sizes,
        status_titles=MODERATION_STATUS_TITLES,
        fields=fields.items(),
        user_companies=user_companies,
        rd_description=rd_description,
        rd_types_list=rd_types_list,
        pool_companies=pool_companies,
        can_edit_companies=can_edit_companies,
        is_operator_view=crm_,
        slot1_filled=slot1_filled,
        slot2_filled=slot2_filled,
    )
    return jsonify(status="success", html=html)


def h_pc_order_preview(o_id: int):
    user = current_user

    # 1️⃣ Получаем заказ
    order = (
        Order.query
        .filter(
            Order.id == o_id,
            Order.user_id == user.id
        )
        .with_entities(Order.id, Order.stage, Order.category)
        .first()
    )

    # 2️⃣ Проверки
    if not order:
        flash(settings.Messages.NO_SUCH_ORDER, 'error')
        return redirect(url_for('user_product_cards.cards_table'))

    if order.stage != settings.OrderStage.CREATING:
        flash(settings.Messages.ORDER_NOT_AVAILABLE, 'warning')
        return redirect(url_for('user_product_cards.cards_table'))

    if not order.category:
        flash(settings.Messages.ORDER_CATEGORY_NOT_FOUND, 'error')
        return redirect(url_for('user_product_cards.cards_table'))

    # 3️⃣ Вытаскиваем category и вызываем helper
    return helper_preload_common(
        o_id=o_id,
        stage=settings.OrderStage.CREATING,
        category=order.category,
        category_process_name=settings.CATEGORIES_DICT.get(order.category)
    )


def h_card_edit(card_id: int):

    card = (
        ProductCard.query
        .filter_by(id=card_id, user_id=current_user.id)
        .first_or_404()
    )
    category = card.category
    # if category == 'shoes':
    #     flash("Ведется обновление раздела карточки категории обувь. Карточки категории обувь временно не обрабатываются", "error")
    #     return redirect(url_for("user_product_cards.cards"))
    main, sizes = extract_card_main_and_sizes(card)
    if not main:
        flash("Карточка пуста, редактировать нечего", "error")
        return redirect(url_for("user_product_cards.cards"))

    subcategory = None
    if category == settings.Clothes.CATEGORY_PROCESS:
        subcategory = getattr(main, "subcategory", None)

    ctx = get_card_ctx(category=card.category, subcategory=subcategory)

    return render_template(
        "product_cards/new/main_card.html",
        mode="edit",
        copied_order=main,
        sizes=sizes,
        card=card,
        card_id=card.id,
        **ctx
    )


def h_card_delete(card_id: int):
    # Берём карточку только текущего пользователя
    card: ProductCard = (
        ProductCard.query
        .filter_by(id=card_id, user_id=current_user.id)
        .first()
    )

    if card is None:
        return jsonify(
            status="error",
            message="Указанной карточки не существует! Обратитесь к администратору!",
        ), 404

    if card.status not in ALLOWED_CARDS_DELETE_STATUSES:
        return jsonify(
            status="error",
            message=(
                "Удаление карточки невозможно. "
                "Карточку можно удалить только в статусах: "
                "создана, одобрена, отклонена или частично одобрена."
            ),
        ), 400

    try:
        db.session.delete(card)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        logger.exception(
            "Ошибка при удалении карточки",
            extra={"card_id": card_id, "user_id": current_user.id},
        )
        return jsonify(
            status="error",
            message="Во время удаления карточки товара произошло исключение. Операция прервана",
        ), 500

    return jsonify(
        status="success",
        message=f"Успешно удалена карточка товара {card.id}",
    ), 200


def h_make_pc_basket_order():
    payload = request.get_json(silent=True) or {}
    orders = payload.get("orders") or []

    if not isinstance(orders, list) or not orders:
        return _json_error("Корзина пуста или неверный формат", 400)

    o = orders[0]  # ✅ всегда один заказ

    try:
        category = (o.get("category") or "").strip()
        mark_type = (o.get("mark_type") or "").strip() or "МАРКИРОВКА НЕ ВЫБРАНА"
        company = o.get("company") or {}
        items = o.get("items") or []
        # print(o)
        if category not in settings.CATEGORIES_PROCESS_NAMES or not isinstance(items, list) or not items:
            raise ValueError("Неверный формат заказа: category/items")
        category_ru = CATEGORIES_COMMON.get(category, '').get('title')

        subcategory = ""
        if category == "clothes":
            subcategory = (o.get("subcategory") or items[0].get("subcategory") or "").strip()
            if not subcategory:
                raise ValueError("Для одежды не указана подкатегория")

        # лимит: максимум 2 черновика на категорию (+ субкатегория для clothes)
        open_cnt = _count_open_moderation_orders(current_user.id, category, subcategory)
        if open_cnt >= 2:
            if category == "clothes":
                raise ValueError(f"Достигнут лимит черновиков (2) для категории '{category_ru}' и подкатегории '{subcategory}'")
            raise ValueError(f"Достигнут лимит черновиков (2) для категории '{category_ru}'")

        # создаём Order
        new_order = Order(
            category=category_ru,
            user_id=current_user.id,
            stage=0,
            is_moderation=True,
        )

        # company поля
        new_order.company_idn = (company.get("company_idn") or "").strip()
        new_order.company_type = (company.get("company_type") or "").strip()
        new_order.company_name = (company.get("company_name") or "").strip()
        new_order.edo_type = (company.get("edo_type") or "ЭДО-ЛАЙТ").strip()
        new_order.edo_id = (company.get("edo_id") or "").strip()
        new_order.mark_type = mark_type

        db.session.add(new_order)
        db.session.flush()  # ✅ new_order.id уже есть

        card_ids = [int(it["card_id"]) for it in items if it.get("card_id")]
        cards_map = _load_cards_for_order(card_ids, category=category)

        for it in items:
            card_id = int(it["card_id"])
            pc = cards_map.get(card_id)
            err = _validate_card_access_and_status(pc, category)
            if err:
                # тут лучше 403, но через исключение
                raise PermissionError(err)

            if category == "clothes":
                it_sub = (it.get("subcategory") or "").strip()
                if it_sub != subcategory:
                    raise ValueError("Корзина должна быть в одной подкатегории одежды. Обнаружена смешанная subcategory.")

            _add_order_item_from_card(new_order, pc, it)

        db.session.commit()

    except PermissionError as pe:
        db.session.rollback()
        return _json_error(str(pe), 403)
    except ValueError as ve:
        db.session.rollback()
        return _json_error(str(ve), 400)
    except Exception as e:
        db.session.rollback()
        return _json_error(f"Ошибка при создании заказа: {e}", 500)

    sub = f" / {subcategory}" if subcategory else ""
    message = f"Создан заказ: {category}{sub}"

    return jsonify(
        status="success",
        message=message,
        redirect_url=url_for("user_product_cards.pc_order_view", o_id=new_order.id),
    ), 200


def h_pc_order_view(o_id: int):
    order = (Order.query
             .filter(
        Order.id == o_id,
        Order.user_id == current_user.id,
        Order.stage == 0,
        Order.is_moderation.is_(True),
        Order.to_delete.is_(False),
    )
             .first())

    if not order:
        flash("Заказ не найден", "error")
        return redirect(url_for("user_product_cards.pc_orders_drafts"))

    category_process = settings.CATEGORIES_DICT.get(order.category)
    cat_cfg = CATEGORIES_COMMON.get(category_process, {})
    category_title = order.category
    subcategory = ""
    sub_title = ""
    if order.category == settings.Clothes.CATEGORY and order.clothes:
        subcategory = (order.clothes[0].subcategory or "").strip()
        sub_title = (cat_cfg.get("subcategories") or {}).get(subcategory, subcategory)

    return render_template(
        "product_cards/user/order/pc_order_view.html",
        order=order,
        o_id=order.id,
        category=order.category,
        category_title=category_title,
        subcategory=subcategory,
        subcategory_title=sub_title,
    )


def h_pc_order_table(o_id: int):

    def _get_order_rows(order: Order):
        """
        Возвращает список "строк" заказа (модели категории).
        ВАЖНО: строки заказа — это записи с order_id=order.id и card_id=None (мы так сделали).
        """
        cat = (order.category or "").strip()

        if cat == settings.Clothes.CATEGORY:
            return order.clothes or []
        if cat == settings.Shoes.CATEGORY:
            return order.shoes or []
        if cat == settings.Linen.CATEGORY:
            return order.linen or []
        if cat == settings.Socks.CATEGORY:
            return order.socks or []
        if cat == settings.Parfum.CATEGORY:
            return order.parfum or []

        return []
    order = (Order.query
             .filter(
                 Order.id == o_id,
                 Order.user_id == current_user.id,
                 Order.stage == 0,
                 Order.is_moderation.is_(True),
                 Order.to_delete.is_(False),
             ).first())

    if not order:
        return "", 404

    order_list = _get_order_rows(order)
    return render_template(
        "product_cards/user/order/_pc_order_table.html",
        order=order,
        o_id=o_id,
        category=order.category,
        order_list=order_list,
    )


def h_pc_order_copy(o_id: int) -> Response:
    user = current_user

    # берём исходный заказ ТОЛЬКО pc
    order = (Order.query
             .filter(
                 Order.id == o_id,
                 Order.user_id == user.id,
                 Order.is_moderation.is_(True),
                 Order.to_delete.is_(False),
             )
             .first())

    if not order:
        flash(message="Нет такого заказа для копирования", category="error")
        return redirect(url_for("user_product_cards.pc_orders_drafts"))

    category = (order.category or "").strip()
    if category not in settings.CATEGORIES_DICT.keys():
        flash(message=settings.Messages.STRANGE_REQUESTS, category="error")
        return redirect(url_for("user_product_cards.pc_orders_drafts"))

    # подкатегория нужна только для clothes (чтобы лимит 2 работал корректно)
    subcategory = get_subcategory(order_id=order.id, category=category) or None

    # лимит: максимум 2 pc-заказа на категорию (+ subcat для clothes)
    active_pc_count = _count_open_pc_orders(user_id=user.id, category=category, subcategory=subcategory)

    if active_pc_count >= 2:
        if category == settings.Clothes.CATEGORY and subcategory:
            flash(message=f"Достигнут лимит (2) заказов на категорию '{category}' и подкатегорию '{settings.CATEGORIES_DICT.get(subcategory)}'", category="error")
        else:
            flash(message=f"Достигнут лимит (2) заказов на категорию '{category}'", category="error")
        return redirect(url_for("user_product_cards.pc_orders_drafts"))

    # копируем
    new_id = common_save_copy_pc_order(user=user, category=category, order=order)
    if not new_id:
        return redirect(url_for("user_product_cards.pc_orders_drafts"))

    flash(message=f"Заказ скопирован: {category}, Идентификатор {new_id}", category="success")
    return redirect(url_for("user_product_cards.pc_orders_drafts"))


def h_pc_order_draft_delete(o_id: int) -> Response:
    user = current_user
    # берём исходный заказ ТОЛЬКО pc
    order = (Order.query
             .filter(
                    Order.id == o_id,
                    Order.user_id == user.id,
                    Order.is_moderation.is_(True),
                    Order.to_delete.is_(False),
                    ).first())

    if not order:
        flash(message=f"Нет такого заказа с идентификатором {o_id}", category="error")
        return redirect(url_for("user_product_cards.pc_orders_drafts"))

    try:
        # удаляем мягко
        order.to_delete = True
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.ORDER_DELETE_ERROR}"
        flash(message=message, category="error")
        logger.error(message + f' {e}')
        return redirect(url_for("user_product_cards.pc_orders_drafts"))

    flash(message=f"Заказ {o_id} удален", category="success")
    return redirect(url_for("user_product_cards.pc_orders_drafts"))


def h_pc_order_draft_delete_jsonify(o_id: int) -> tuple[Response, int]:
    user = current_user
    status = 'error'

    # берём исходный заказ ТОЛЬКО pc
    order = (Order.query
             .filter(
                    Order.id == o_id,
                    Order.user_id == user.id,
                    Order.is_moderation.is_(True),
                    Order.to_delete.is_(False),
                    ).first())

    if not order:
        message = f"Нет такого заказа с идентификатором {o_id}"
        return jsonify(status=status, message=message), 404

    try:
        # удаляем мягко
        order.to_delete = True
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.ORDER_DELETE_ERROR}"
        logger.error(message + f' {e}')
        return jsonify(status=status, message=message), 404

    message = f"Заказ {o_id} удален"
    status = "success"

    return jsonify(status=status, message=message), 200


def h_pc_order_pos_view(o_id: int, pos_id: int):
    def _get_order_pos_by_id(category: str, o_id: int, pos_id: int):
        if category == settings.Clothes.CATEGORY:
            return Clothes.query.filter_by(id=pos_id, order_id=o_id).first()
        if category == settings.Shoes.CATEGORY:
            return Shoe.query.filter_by(id=pos_id, order_id=o_id).first()
        if category == settings.Linen.CATEGORY:
            return Linen.query.filter_by(id=pos_id, order_id=o_id).first()
        if category == settings.Socks.CATEGORY:
            return Socks.query.filter_by(id=pos_id, order_id=o_id).first()
        if category == settings.Parfum.CATEGORY:
            return Parfum.query.filter_by(id=pos_id, order_id=o_id).first()
        return None

    order = (Order.query
             .filter(
        Order.id == o_id,
        Order.user_id == current_user.id,
        Order.stage == 0,
        Order.is_moderation.is_(True),
        Order.to_delete.is_(False),
    ).first())
    if not order:
        return "", 404

    category = order.category

    category_process = settings.CATEGORIES_DICT.get(category, "")

    pos = _get_order_pos_by_id(category, o_id, pos_id)
    if not pos:
        return "", 404

    cat_cfg = CATEGORIES_COMMON.get(category_process, {})
    subcategory_title = None
    if cat_cfg.get("has_subcategory"):
        sub = getattr(pos, "subcategory", None)  # поле в pos
        if sub:
            # sub — англоподобный ключ (underwear, hats...)
            subcategory_title = cat_cfg.get("subcategories", {}).get(sub, sub)
    # готовим список (label, value) по CARD_FIELDS
    fields_cfg = CARD_FIELDS.get(category_process, {})

    fields_prepared = []
    for field, label in fields_cfg.items():
        if field == "subcategory":
            continue
        val = getattr(pos, field, None)
        if val is None or val == "":
            val = "-"
        fields_prepared.append((label, val))

    return render_template(
        "product_cards/user/order/_pc_pos_modal_body.html",
        category=category,
        subcategory_title=subcategory_title,
        pos=pos,
        fields_prepared=fields_prepared,
    )


def h_pc_order_delete_pos(o_id: int, pos_id: int):
    order = (Order.query
             .filter(
                 Order.id == o_id,
                 Order.user_id == current_user.id,
                 Order.stage == 0,
                 Order.is_moderation.is_(True),
                 Order.to_delete.is_(False),
             ).first())
    if not order:
        return jsonify(status="error", message="Заказ не найден"), 404

    try:
        if order.category == settings.Clothes.CATEGORY:
            obj = Clothes.query.filter_by(id=pos_id, order_id=o_id).first()
        elif order.category == settings.Shoes.CATEGORY:
            obj = Shoe.query.filter_by(id=pos_id, order_id=o_id).first()
        elif order.category == settings.Linen.CATEGORY:
            obj = Linen.query.filter_by(id=pos_id, order_id=o_id).first()
        elif order.category == settings.Socks.CATEGORY:
            obj = Socks.query.filter_by(id=pos_id, order_id=o_id).first()
        elif order.category == settings.Parfum.CATEGORY:
            obj = Parfum.query.filter_by(id=pos_id, order_id=o_id).first()
        else:
            obj = None

        if not obj:
            return jsonify(status="error", message="Позиция не найдена"), 404

        db.session.delete(obj)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify(status="error", message=f"Ошибка удаления: {e}"), 500

    return jsonify(status="success", message="Позиция удалена"), 200


def h_pc_order_delete(o_id: int):
    order = (Order.query
             .filter(
        Order.id == o_id,
        Order.user_id == current_user.id,
        Order.is_moderation.is_(True),
        Order.to_delete.is_(False),
    )
             .first())

    if not order:
        return jsonify(status="error", message="Заказ не найден"), 404

    try:
        # ВАЖНО: stage у вас int. settings.OrderStage.CREATING обычно = 0
        if order.stage == settings.OrderStage.CREATING:
            Order.query.filter_by(id=order.id).delete()
            # Если нужно — можно ещё подчистить связанные сущности/агрегации, но каскады должны справиться
            # AggrOrder.query.filter_by(order_id=order.id).delete()
        else:
            db.session.execute(
                text("UPDATE public.orders SET to_delete = true WHERE id = :o_id").bindparams(o_id=order.id)
            )

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        return jsonify(status="error", message=f"Ошибка: {e}"), 500

    return jsonify(
        status="success",
        message="Заказ удалён",
        redirect_url=url_for("user_product_cards.pc_orders_drafts"),
    ), 200


def h_pc_orders_drafts():
    def _norm_cat(cat: str) -> str:
        c = (cat or "").strip()
        return settings.CATEGORIES_DICT.get(c, c)

    drafts = (Order.query
              .filter(
                  Order.user_id == current_user.id,
                  Order.stage == settings.OrderStage.CREATING,   # = 0
                  Order.is_moderation.is_(True),
                  Order.to_delete.is_(False),
                  Order.processed.is_(False),
              )
              .order_by(Order.created_at.desc())
              .all())

    if not drafts:
        return render_template(
            "product_cards/user/order/pc_orders_drafts.html",
            grouped={},
            categories=CATEGORIES_COMMON,
        )

    order_ids = [o.id for o in drafts]

    # одним SQL считаем КС/КМ
    sql = text(f"""
        SELECT
            o.id AS o_id,
            COALESCE( {SQLQueryCategoriesAll.get_stmt('rows_count')} , 0)  AS rows_count,
            COALESCE( {SQLQueryCategoriesAll.get_stmt('marks_count')} , 0) AS marks_count
        FROM public.orders o
        {SQLQueryCategoriesAll.get_joins()}
        WHERE o.id = ANY(:order_ids)
        GROUP BY o.id
    """)
    res = db.session.execute(sql, {"order_ids": order_ids}).fetchall()

    counts_map = {}
    for row in res:
        try:
            oid = int(getattr(row, "o_id"))
            rows_count = int(getattr(row, "rows_count") or 0)
            marks_count = int(getattr(row, "marks_count") or 0)
        except Exception:
            oid = int(row[0])
            rows_count = int(row[1] or 0)
            marks_count = int(row[2] or 0)
        counts_map[oid] = (rows_count, marks_count)

    grouped = {}
    for o in drafts:
        rows_count, marks_count = counts_map.get(o.id, (0, 0))

        # subcategory только для одежды
        subcategory = ""
        if o.category == settings.Clothes.CATEGORY:
            if o.clothes and o.clothes[0].subcategory:
                subcategory = (o.clothes[0].subcategory or "").strip()
            if not subcategory:
                subcategory = "common"  # чтобы в шаблоне было “одежда”

        row = {
            "id": o.id,
            "created_at": o.created_at,
            "category": o.category,
            "subcategory": subcategory,          # common/underwear/...
            "company_name": o.company_name,
            "company_idn": o.company_idn,
            "pos_count": rows_count,
            "marks_count": marks_count,
        }

        cat_raw = o.category
        cat = _norm_cat(cat_raw)
        sub_key = subcategory if cat == settings.Clothes.CATEGORY_PROCESS else "__no_sub__"
        grouped.setdefault(cat, {}).setdefault(sub_key, []).append(row)

    return render_template(
        "product_cards/user/order/pc_orders_drafts.html",
        grouped=grouped,
        categories=CATEGORIES_COMMON,
    )


def h_pc_order_check_before_process(o_id: int):
    """
        Проверки перед оформлением:
        - дубль в архиве (helper_check_user_order_in_archive)
        - баланс/стоимость (helper_check_uoabm)
        """
    order = (Order.query
             .filter(
        Order.id == o_id,
        Order.user_id == current_user.id,
        Order.is_moderation.is_(True),
        Order.stage == settings.OrderStage.CREATING,
        Order.to_delete.is_(False),
        Order.processed.is_(False),
    ).first())


    if not order:
        return jsonify(status="error", message="Заказ не найден"), 404

    category = (order.category or "").strip()

    rows_count, marks_count = get_rows_marks(o_id=o_id, category=category)

    # 1) дубль в архиве
    status_order, answer_order = helper_check_user_order_in_archive(category=category, o_id=o_id)

    # 2) баланс
    status_balance, total_order_price, agent_at2, answer_balance = helper_check_uoabm(user=current_user, o_id=o_id)

    return jsonify(dict(
        status="success",
        status_order=status_order,
        answer_orders=str(answer_order),
        status_balance=status_balance,
        answer_balance=str(answer_balance),
        agent_at2=bool(agent_at2),
        total_order_price=float(total_order_price or 0),
        rows_count=int(rows_count or 0),
        marks_count=int(marks_count or 0),
    )), 200


def h_pc_order_process(o_id: int):
    # куда редиректить при ошибках/успехе
    def _back_to_order_view():
        # страница просмотра pc-заказа
        return redirect(url_for("user_product_cards.pc_order_view", o_id=order.id if order else None))

    def _back_to_list():
        # страница списка pc-заказов
        return redirect(url_for("user_product_cards.pc_orders_drafts"))

    from utilities.download import orders_process_send_order

    order_comment = (request.form.to_dict().get("order_comment") or "").strip()

    order = (Order.query
             .filter(
        Order.id == o_id,
        Order.user_id == current_user.id,
        Order.stage == settings.OrderStage.CREATING,  # 0
        Order.is_moderation.is_(True),  # ✅ только pc-заказы
        Order.processed.is_(False),
        Order.to_delete.is_(False),
    )
             .first())

    if not order:
        flash(message=settings.Messages.EMPTY_ORDER, category="error")
        return _back_to_list()

    category = (order.category or "").strip()

    # ok, payload, vbci_err = validate_and_build_contact_info(
    #     request.form.get("contact_type"),
    #     request.form.get("contact_value")
    # )
    #
    # if not ok:
    #     flash(vbci_err, "error")
    #     return _back_to_order_view()

    # order.contact_info = payload

    # 1) company_idn exception
    company_idn = order.company_idn
    if company_idn and company_idn in ExceptionDataUsers.get_company_idns():
        flash(message=settings.ExceptionOrders.COMPANY_IDN_ERROR.format(company_idn=company_idn), category="error")
        return _back_to_order_view()

    # 2) есть ли позиции / валидность
    if not check_order_pos(category=category, order=order):
        # check_order_pos сам флешит, если у вас так сделано
        return _back_to_order_view()

    # 3) проверка наборов
    # if not ValidatorProcessor.validate_aggr_order_completeness(order=order):
    #     flash(message="Заказ не передан на оформление. В режиме наборы необходимо включить все размеры", category="error")
    #     return _back_to_order_view()
    user = current_user
    # 4) баланс
    status_balance, total_order_price, agent_at2, message_balance = helper_check_uoabm(user=user, o_id=order.id)
    if status_balance == 0:
        flash(message=Markup(message_balance), category="error")
        return _back_to_order_view()

    try:
        # 5) генерим order_idn
        order_num, order_idn, is_crm, is_at2 = process_admin_order_num(user=user)

        if not order_idn:
            db.session.rollback()
            flash(message=f"{settings.Messages.PROCESS_ERROR}: Ошибка БД", category="error")
            return _back_to_order_view()

        # 6) переводим заказ из stage=0 в нужный stage, пишем idn, comment
        _stage = process_order_start(user=user, category=category, o_id=order.id, order_idn=order_idn,
                                     order_comment=order_comment)
        if not _stage:
            db.session.rollback()
            flash(message=f"{settings.Messages.PROCESS_ERROR}: Такого заказа нет в бд", category="error")
            return _back_to_order_view()

        if is_at2:
            sent_flag = orders_process_send_order(
                o_id=order.id, user=user,
                order_comment=order_comment,
                order_idn=order_idn,
                flag_046=False,
            )
            if sent_flag:
                flash(message=Markup(f"{settings.Messages.PROCESS_SUCCESS}<b>{order_idn}</b>!"))
        else:
            flash(message=Markup(f"{settings.Messages.PROCESS_SUCCESS}<b>{order_idn}</b>!"))

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.ORDER_ADD_ERROR} {e}"
        flash(message=message, category="error")
        logger.error(message)
        return _back_to_order_view()

    # уведомления как у вас
    try:
        helper_send_user_order_tg_notify(user_id=user.id, order_idn=order_idn, order_stage=_stage)
        MarkinerisInform.send_message_tg.delay(order_idn=order_idn)
    except Exception:
        # не ломаем flow
        pass


    return _back_to_list()
