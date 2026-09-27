from datetime import datetime
from flask import request, render_template, jsonify, flash, url_for, redirect, Response
from flask_login import current_user
from markupsafe import Markup
from sqlalchemy import case, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload, selectinload, load_only

from config import settings
from logger import logger
from models import db, ExceptionDataUsers, Order, ProductCard, Shoe, Linen, Parfum, Clothes, Socks, Cosmetics, Toys, \
    ModerationStatus
from utilities.categories_data.subcategories_data import ClothesSubcategories
from utilities.categories_data.subcategories_logic import get_subcategory
from utilities.helpers.h_tg_notify import helper_send_user_order_tg_notify
from utilities.sql_categories_aggregations import SQLQueryCategoriesAll, SQLQueryFactory
from utilities.support import check_forbidden_words, helper_preload_common, helper_check_uoabm, \
    helper_check_user_order_in_archive, check_order_pos, process_admin_order_num, process_order_start, \
    parse_rd_replacement_consent
from utilities.telegram import MarkinerisInform
from utilities.validators import ValidatorProcessor, validate_and_build_contact_info, validate_order_comment_length
from tezaurus.api_client import TezaurusApiClient
from tezaurus.exceptions import TezaurusApiError, TezaurusConfigurationError
from tezaurus.processing_companies import ProcessingCompaniesClient
from tezaurus.runtime_catalogs import get_processing_companies
from views.main.product_cards.chat.helpers import h_pc_chat_unread_count, h_unread_map_for_cards, \
    h_visible_chat_card_ids, USER_CHAT_WRITE_STATUSES
from views.main.product_cards.crm.helpers import crm_card_subcategory_title, crm_card_sizes_label, crm_card_article, \
    h_append_card_log
from views.main.product_cards.order_helpers import _json_error, _add_order_item_from_card, \
    _count_open_moderation_orders, _get_card_or_fail, _validate_card_access_and_status, _load_cards_for_order, \
    _count_open_pc_orders, _filter_copyable_fast_order_items, common_save_copy_pc_order, \
    get_or_create_fast_order_company, validate_pc_order_items_ready_for_process
from views.main.product_cards.support import validate_card_form, save_clothes_card, save_shoes_card, save_linen_card, \
    save_socks_card, save_parfum_card, save_cosmetics_card, save_toys_card, parse_sizes_for_category, \
    CATEGORIES_COMMON, MODERATION_STATUS_TITLES, MODERATION_STATUS_COLORS, normalize_article_for_category, \
    normalize_color_for_category, collect_existing_size_keys, filter_new_sizes, CARD_FIELDS, \
    extract_card_main_and_sizes, get_card_ctx, check_same_fields_if_exists, CATEGORY_TITLES, \
    get_card_entity_for_prefill, assert_frozen_fields_unchanged, \
    update_card_allowed_fields, ALLOWED_CARDS_DELETE_STATUSES, card_has_rd, CARD_STATUS_DATETIME_ATTR, \
    get_card_allowed_field_changes, merge_selected_created_wear_cards, assign_tezaurus_processing_companies, \
    assign_tezaurus_processing_company, build_pc_category_search_index, find_approved_wear_card_for_size_extension, \
    copy_card_processing_company
from views.main.product_cards.utils import validate_rd_block
from views.main.categories.cosmetics.subcategories.registry import \
    SUBCATEGORY_CONFIG as COSMETICS_SUBCATEGORY_CONFIG
from views.main.categories.toys.subcategories.registry import SUBCATEGORY_CONFIG as TOYS_SUBCATEGORY_CONFIG


CARD_SUBCATEGORY_DEFAULTS = {
    settings.Cosmetics.CATEGORY_PROCESS: "decor_ukhod",
    settings.Toys.CATEGORY_PROCESS: "doll_accessories",
}

CARD_SUBCATEGORY_ORDER = {
    settings.Cosmetics.CATEGORY_PROCESS: (
        "decor_ukhod",
        "cosmetics_eye",
        "cosmetics_lips",
        "cosmetics_the_rest_hair",
        "cosmetics_rascheski",
        "razor_blades_and_cassettes",
        "cosmetics_tooth",
        "cosmetics_salt_bomb",
        "cosmetics_mochalki",
        "cosmetics_aroma",
        "cosmetics_cleaning_products",
        "cosmetics_deodorants",
        "cosmetics_nails",
        "cosmetics_toilet_paper",
        "cosmetics_tweezers",
    ),
    settings.Toys.CATEGORY_PROCESS: (
        "doll_accessories",
        "puzzles",
        "competition_cars",
        "sets_kits",
        "motorized_toys",
        "animal_creature",
        "scale_models_other",
        "musical_toy_instruments",
        "dolls_human_figures",
        "construction_sets",
        "card_games",
        "board_room_games_inventory",
        "toy_weapons",
        "play_tents",
        "electric_train_sets",
    ),
}

INTERACTIVE_TEZAURUS_TIMEOUT = 8
PROCESSING_COMPANY_REASSIGNMENT_ERROR = (
    "Редактирование не сохранено: не удалось связаться с Tezaurus или подобрать новую "
    "компанию обработки после смены страны. Проверьте сеть/Tezaurus и попробуйте снова."
)


def _card_subcategory_registry(category: str):
    if category == settings.Cosmetics.CATEGORY_PROCESS:
        return COSMETICS_SUBCATEGORY_CONFIG
    if category == settings.Toys.CATEGORY_PROCESS:
        return TOYS_SUBCATEGORY_CONFIG
    return {}


def _card_subcategory_tiles(category: str):
    registry = _card_subcategory_registry(category)
    ordered_slugs = CARD_SUBCATEGORY_ORDER.get(category, ())
    tiles = []
    for slug in ordered_slugs:
        config = registry.get(slug)
        if not config:
            continue
        tiles.append({
            "slug": config["slug"],
            "title": config["title"],
            "icon": config.get("icon"),
        })
    return tuple(tiles)


def _card_identity_value(category: str, entity) -> tuple[str, str]:
    if not entity:
        return "", "артикул"
    if category in (settings.Parfum.CATEGORY_PROCESS, settings.Cosmetics.CATEGORY_PROCESS):
        return (getattr(entity, "trademark", "") or ""), "товарный знак"
    if category == settings.Toys.CATEGORY_PROCESS:
        return (getattr(entity, "model_article", "") or getattr(entity, "trademark", "") or ""), "модель/артикул"
    return (getattr(entity, "article", "") or ""), "артикул"


def _pc_visible_fields_for_entity(category_process: str, entity):
    fields = dict(CARD_FIELDS.get(category_process, {}))
    if (
        category_process == settings.Cosmetics.CATEGORY_PROCESS
        and getattr(entity, "subcategory", "") == "razor_blades_and_cassettes"
        and str(getattr(entity, "tnved_code", "") or "").strip() != "8212109000"
    ):
        fields.pop("blade_count", None)
        fields.pop("complectation", None)
    return fields


def _ensure_card_form_defaults(ctx: dict) -> dict:
    ctx.setdefault("copied_order", None)
    ctx.setdefault("edit_mode", False)
    ctx.setdefault("edit_card_id", None)
    ctx.setdefault("crm_", False)
    ctx.setdefault("edit_order", "")
    ctx.setdefault("excepted_articles", settings.ExceptionOrders.EXCEPTED_ARTICLES)
    return ctx


def _card_processing_origin(*, category: str, country: str | None) -> str:
    if not country:
        return ""
    ProcessingCompaniesClient.normalize_category(category)
    return ProcessingCompaniesClient.origin_from_country(country)


def _interactive_processing_companies_client() -> ProcessingCompaniesClient:
    return ProcessingCompaniesClient(api_client=TezaurusApiClient(timeout=INTERACTIVE_TEZAURUS_TIMEOUT))


def _card_processing_company_response(card: ProductCard) -> dict:
    assigned_at = card.processing_company_assigned_at
    return {
        "external_id": card.processing_company_external_id or "",
        "inn": card.processing_company_inn or "",
        "title": card.processing_company_title or "",
        "label": card.processing_company_label or card.processing_info or "-",
        "assigned_at": assigned_at.strftime("%d.%m.%Y %H:%M") if assigned_at else "",
    }


def h_cards():
    category = request.args.get("category", "shoes")
    subcategory = request.args.get("subcategory")
    article_query = request.args.get("article_query", "").strip()

    if category in CARD_SUBCATEGORY_DEFAULTS and not subcategory:
        subcategory = CARD_SUBCATEGORY_DEFAULTS[category]

    created_cards_count = ProductCard.query.filter(
        ProductCard.user_id == current_user.id,
        ProductCard.status == ModerationStatus.CREATED,
    ).count()

    return render_template(
        "product_cards/user/main.html",
        current_category=category,
        current_subcategory=subcategory,
        article_query=article_query,
        mapper_categories=CATEGORIES_COMMON,
        pc_subcategory_tiles=_card_subcategory_tiles(category),
        pc_category_search_index=build_pc_category_search_index(),
        created_cards_count=created_cards_count,
        show_cards_video=False,
    )


def h_card_category_subcategories(category: str):
    category = (category or "").strip()
    cfg = CATEGORIES_COMMON.get(category)
    if not cfg or not cfg.get("has_subcategory"):
        flash("У выбранной категории нет страницы подкатегорий", "error")
        return redirect(url_for("user_product_cards.cards"))

    if category in CARD_SUBCATEGORY_DEFAULTS:
        return redirect(url_for(
            "user_product_cards.cards",
            category=category,
            subcategory=CARD_SUBCATEGORY_DEFAULTS[category],
        ))

    if category == settings.Cosmetics.CATEGORY_PROCESS:
        registry = COSMETICS_SUBCATEGORY_CONFIG
        ordered_slugs = CARD_SUBCATEGORY_ORDER[category]
        search_index_name = "COSMETICS_SEARCH_INDEX"
        search_input_id = "cosmetics-category-search"
        search_result_id = "cosmetics-search-result"
        extra_css = ("main_v2/css/categories/cosmetics.css",)
        script_path = "main_v2/js/categories/cosmetics.js"
        script_version = "12"
        image_version = "20260623-cosmetics-teasers-2"
        page_title = "Основные категории косметики"
    elif category == settings.Toys.CATEGORY_PROCESS:
        registry = TOYS_SUBCATEGORY_CONFIG
        ordered_slugs = CARD_SUBCATEGORY_ORDER[category]
        search_index_name = "TOYS_SEARCH_INDEX"
        search_input_id = "toys-category-search"
        search_result_id = "toys-search-result"
        extra_css = ("main_v2/css/categories/cosmetics.css", "main_v2/css/categories/toys.css")
        script_path = "main_v2/js/categories/toys.js"
        script_version = "4"
        image_version = "20260810-toys-subcategories"
        page_title = "Основные категории игрушек"
    else:
        flash("Категория не поддерживает карточки через подкатегории", "error")
        return redirect(url_for("user_product_cards.cards"))

    tiles_by_slug = {
        config["slug"]: {
            "slug": config["slug"],
            "title": config["title"],
            "icon": config["icon"],
            "icon_class": config.get("icon_class", ""),
            "is_disabled": False,
            "url": url_for(
                "user_product_cards.new_product_card",
                category=category,
                subcategory=config["slug"],
            ),
        }
        for config in registry.values()
    }
    category_tiles = tuple(tiles_by_slug[slug] for slug in ordered_slugs if slug in tiles_by_slug)
    search_index = [
        {
            "slug": config["slug"],
            "title": config["title"],
            "url": url_for(
                "user_product_cards.new_product_card",
                category=category,
                subcategory=config["slug"],
            ),
            "allowed_tnved_codes": list(config["allowed_tnved_codes"]),
            "allowed_tnved_choices": [
                {"code": code, "label": label}
                for code, label in config["allowed_tnved_choices"]
            ],
            "product_types": list(config["product_types"]),
        }
        for config in registry.values()
    ]

    return render_template(
        "product_cards/new/subcategories.html",
        category=category,
        category_title=cfg["title"],
        page_title=page_title,
        search_placeholder="Введите ТНВЭД или вид товара для определения категории",
        category_tiles=category_tiles,
        search_index=search_index,
        search_index_name=search_index_name,
        search_input_id=search_input_id,
        search_result_id=search_result_id,
        extra_css=extra_css,
        script_path=script_path,
        script_version=script_version,
        image_version=image_version,
    )


# @profile_db_verbose('cards_table')
def h_cards_table():
    def _get_card_status_datetime(card: ProductCard):
        status_value = card.status.value if hasattr(card.status, "value") else str(card.status)
        attr_name = CARD_STATUS_DATETIME_ATTR.get(status_value, "created_at")
        return getattr(card, attr_name, None) or card.created_at
    category = request.form.get("category", settings.Shoes.CATEGORY_PROCESS)
    subcategory = request.form.get("subcategory") or None
    article_query = request.form.get("article_query", "").strip()
    page = request.form.get("page", default=1, type=int)
    per_page = 20
    if category == settings.Clothes.CATEGORY_PROCESS and not subcategory:
        subcategory = ClothesSubcategories.common.value
    if category in CARD_SUBCATEGORY_DEFAULTS and not subcategory:
        subcategory = CARD_SUBCATEGORY_DEFAULTS[category]
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
            "message": "Подкатегория недоступна для выбранной категории"
        }), 400

    if cfg["has_subcategory"] and subcategory:
        valid_subcats = cfg.get("subcategories") or {}
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

    if has_subcategory and subcategory:
        rel = getattr(ProductCard, rel_name)
        query = query.filter(rel.any(model.subcategory == subcategory))

    # поиск по артикулу / trademark
    if article_query:
        like = f"%{article_query}%"
        rel = getattr(ProductCard, rel_name)

        if hasattr(model, "article"):
            query = query.filter(rel.any(model.article.ilike(like)))
        elif hasattr(model, "model_article"):
            query = query.filter(rel.any(
                model.trademark.ilike(like) | model.model_article.ilike(like)
            ))
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
    elif category == settings.Cosmetics.CATEGORY_PROCESS:
        query = query.options(selectinload(ProductCard.cosmetics))
    elif category == settings.Toys.CATEGORY_PROCESS:
        query = query.options(selectinload(ProductCard.toys))

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
    if isinstance(ctx, Response):
        return ctx
    _ensure_card_form_defaults(ctx)

    return render_template("product_cards/new/main_card.html", **ctx)


def h_save_product_card():
    form_data = request.form
    form_dict = form_data.to_dict()
    single_unit_categories = {
        settings.Parfum.CATEGORY_PROCESS,
        settings.Cosmetics.CATEGORY_PROCESS,
        settings.Toys.CATEGORY_PROCESS,
    }

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
        rd_replacement_consent = parse_rd_replacement_consent(
            form_dict.get("rd_replacement_consent"),
            required=str(form_dict.get("has_rd") or "").lower() in ("1", "true", "on", "yes"),
        )

    except Exception as e:
        return jsonify(status="error", message=str(e))

    if category in single_unit_categories:
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
            subcategory=subcategory,
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
        rd_replacement_consent=rd_replacement_consent,
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
        settings.Cosmetics.CATEGORY_PROCESS: save_cosmetics_card,
        settings.Toys.CATEGORY_PROCESS: save_toys_card,
    }
    saver = save_map[category]

    try:
        if category in single_unit_categories:
            saver(
                card=card,
                form_dict=form_dict,
                sizes_quantities=None,
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
    if isinstance(ctx, Response):
        return ctx
    ctx["copied_order"] = copied_order
    ctx["edit_mode"] = True
    ctx["edit_card_id"] = card.id
    ctx["crm_"] = crm_
    ctx["rd_replacement_consent"] = card.rd_replacement_consent
    _ensure_card_form_defaults(ctx)

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
    old_country = (getattr(entity_before, "country", "") or "").strip() if entity_before else ""
    field_title = "артикул"
    if entity_before:
        old_identity, field_title = _card_identity_value(category, entity_before)
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
        if crm_:
            rd_replacement_consent = card.rd_replacement_consent
        else:
            rd_replacement_consent = parse_rd_replacement_consent(
                form_dict.get("rd_replacement_consent"),
                required=str(form_dict.get("has_rd") or "").lower() in ("1", "true", "on", "yes"),
            )
    except Exception as e:
        return jsonify(status="error", message=str(e))

    # 2) ЗАПРЕЩАЕМ менять "замороженные" поля:
    try:
        assert_frozen_fields_unchanged(card=card, form_data=form_data)
    except Exception as e:
        return jsonify(status="error", message=str(e))

    # 3) обновляем только разрешённые поля; identity-поля уже проверены выше
    try:
        log_user_changes = card.status == ModerationStatus.CLARIFICATION
        changes = get_card_allowed_field_changes(card=card, form_dict=form_dict) if (crm_ or log_user_changes) else []
        old_origin = (
            card.processing_company_origin
            or _card_processing_origin(category=category, country=old_country)
        )
        old_company_label = card.processing_company_label or card.processing_info or "-"
        old_rd_replacement_consent = card.rd_replacement_consent
        update_card_allowed_fields(card=card, form_dict=form_dict, form_data=form_data)
        card.rd_replacement_consent = rd_replacement_consent
        entity_after = get_card_entity_for_prefill(card)
        new_identity = ""
        processing_company_reassigned = False
        new_origin = ""
        if entity_after:
            new_identity, field_title = _card_identity_value(category, entity_after)
            new_country = (getattr(entity_after, "country", "") or "").strip()
            new_origin = _card_processing_origin(category=category, country=new_country)
            if new_origin and new_origin != old_origin:
                try:
                    processing_client = _interactive_processing_companies_client()
                    assigned = assign_tezaurus_processing_company(
                        card,
                        client=processing_client,
                        assigned_at=datetime.now(),
                    )
                except (TezaurusApiError, TezaurusConfigurationError, ValueError) as exc:
                    logger.exception("Failed to reassign product card processing company after origin change")
                    raise RuntimeError(PROCESSING_COMPANY_REASSIGNMENT_ERROR) from exc
                processing_company_reassigned = True
                changes.append("Компания обработки")
                dt_str = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                actor = getattr(current_user, "login_name", "") or str(current_user.id)
                card.card_log = h_append_card_log(
                    card.card_log,
                    (
                        f"\n{dt_str} {actor} сменил origin карточки: "
                        f"{old_origin or '-'} -> {new_origin}; компания обработки: "
                        f"{old_company_label} -> {assigned['label']};"
                    ),
                )
        if old_identity != new_identity:
            dt_str = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            actor = getattr(current_user, "login_name", "") or str(current_user.id)
            card.card_log = h_append_card_log(
                card.card_log,
                f"\n{dt_str} изменил {field_title}: '{old_identity}' -> '{new_identity}' пользователь {actor};")
        if changes:
            dt_str = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            user_login = getattr(current_user, "login_name", "") or str(current_user.id)
            actor_label = user_login if crm_ else f"Клиент {user_login}" if current_user.id == card.user_id else user_login
            status_log_label = {
                ModerationStatus.CLARIFICATION: "НУ",
                ModerationStatus.SENT_NO_RD: "ОБРД",
            }.get(card.status, "")
            card.card_log = h_append_card_log(
                card.card_log,
                f"\n{dt_str} {actor_label} исправил ({status_log_label}): {', '.join(changes)};"
            )
            if crm_ and "РД" in changes:
                card.card_log = h_append_card_log(
                    card.card_log,
                    f"\n{dt_str} {actor_label} установил РД оператором ({status_log_label});"
                )
        if old_rd_replacement_consent != card.rd_replacement_consent:
            dt_str = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            actor = getattr(current_user, "login_name", "") or str(current_user.id)
            value_label = "да" if card.rd_replacement_consent is True else "нет" if card.rd_replacement_consent is False else "-"
            card.card_log = h_append_card_log(
                card.card_log,
                f"\n{dt_str} {actor} изменил согласие на использование нашей РД: {value_label};"
            )
        db.session.commit()
    except RuntimeError as e:
        db.session.rollback()
        return jsonify(status="error", message=str(e))
    except Exception as e:
        db.session.rollback()
        return jsonify(status="error", message=str(e))

    return jsonify(
        status="success",
        message="Карточка обновлена",
        card_id=card.id,
        article_or_trademark=new_identity,
        processing_company_reassigned=processing_company_reassigned,
        processing_company=_card_processing_company_response(card),
    )


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
    if settings.Cosmetics.CATEGORY_PROCESS in cats:
        q = q.options(selectinload(ProductCard.cosmetics))
    if settings.Toys.CATEGORY_PROCESS in cats:
        q = q.options(selectinload(ProductCard.toys))

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
            elif cat == "cosmetics":
                q = q.options(joinedload(ProductCard.cosmetics))
            elif cat == "toys":
                q = q.options(joinedload(ProductCard.toys))
            else:
                # неизвестная категория — всё равно загрузим карточки без релейшенов
                pass

            cards.extend(q.all())

        merge_result = merge_selected_created_wear_cards(cards)
        cards = merge_result["cards"]
        db.session.flush()

        ids_with_rd: list[int] = []

        for c in cards:
            if card_has_rd(c):
                ids_with_rd.append(c.id)

        updated_sent = 0
        updated_no_rd = 0
        tezaurus_client = ProcessingCompaniesClient()
        cards_to_send = [
            card
            for card in cards
            if card.user_id == current_user.id and card.status == ModerationStatus.CREATED
        ]
        assignments: dict[int, dict] = {}
        cards_for_tezaurus: list[ProductCard] = []
        for card in cards_to_send:
            base_card = find_approved_wear_card_for_size_extension(card)
            if base_card and base_card.processing_company_label:
                assignments[card.id] = copy_card_processing_company(
                    target=card,
                    source=base_card,
                    assigned_at=now,
                )
                continue

            cards_for_tezaurus.append(card)

        tezaurus_assignments = assign_tezaurus_processing_companies(
            cards_for_tezaurus,
            client=tezaurus_client,
            assigned_at=now,
        )
        assignments.update(tezaurus_assignments)

        for card in cards_to_send:
            if card.id in ids_with_rd:
                card.status = ModerationStatus.SENT
                updated_sent += 1
            else:
                card.status = ModerationStatus.SENT_NO_RD
                updated_no_rd += 1

            card.sent_at = now
            assigned = assignments[card.id]
            if assigned.get("source_card_id"):
                card.card_log = h_append_card_log(
                    card.card_log,
                    (
                        f"\n{now:%d.%m.%Y %H:%M} компания {assigned['label']} "
                        f"унаследована из карточки №{assigned['source_card_id']}; "
                        "карточка отправлена на модерацию;"
                    )
                )
            else:
                card.card_log = h_append_card_log(
                    card.card_log,
                    (
                        f"\n{now:%d.%m.%Y %H:%M} назначена компания "
                        f"{assigned['label']}; карточка отправлена на модерацию;"
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
    except ValueError as exc:
        db.session.rollback()
        logger.exception("Processing company assignment failed in send_cards_moderate")
        message = str(exc)
        return jsonify({"status": "error", "error": message, "message": message}), 400
    except TezaurusConfigurationError as exc:
        db.session.rollback()
        logger.exception("Tezaurus configuration error in send_cards_moderate")
        return jsonify({"status": "error", "error": str(exc)}), 503
    except TezaurusApiError as exc:
        db.session.rollback()
        logger.exception("Tezaurus API error in send_cards_moderate")
        return jsonify({"status": "error", "error": str(exc)}), 502
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
        elif cat == settings.Cosmetics.CATEGORY_PROCESS:
            q = q.options(selectinload(ProductCard.cosmetics))
        elif cat == settings.Toys.CATEGORY_PROCESS:
            q = q.options(selectinload(ProductCard.toys))

        return q.first_or_404()

    card = _get_card_for_view(card_id=card_id, crm_=crm_)

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
    elif card.category in (settings.Cosmetics.CATEGORY_PROCESS, settings.Toys.CATEGORY_PROCESS):
        sizes = []
    fields = _pc_visible_fields_for_entity(card.category, main)

    rd_description = settings.RD_DESCRIPTION
    rd_types_list = settings.RD_TYPES
    card_status_value = card.status.value if hasattr(card.status, "value") else card.status
    can_change_processing_company = (
        crm_
        and current_user.role in [settings.SUPER_USER, settings.SUPER_MANAGER, settings.MANAGER_USER]
        and card_status_value not in [ModerationStatus.APPROVED.value, ModerationStatus.REJECTED.value]
    )

    html = render_template(
        "product_cards/user/card_view.html",
        card=card,
        cfg=cfg,
        main=main,
        sizes=sizes,
        status_titles=MODERATION_STATUS_TITLES,
        fields=fields.items(),
        rd_description=rd_description,
        rd_types_list=rd_types_list,
        is_operator_view=crm_,
        can_change_processing_company=can_change_processing_company,
        processing_companies=get_processing_companies() if crm_ else [],
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
    if CATEGORIES_COMMON.get(category, {}).get("has_subcategory"):
        subcategory = getattr(main, "subcategory", None)

    ctx = get_card_ctx(category=card.category, subcategory=subcategory)
    if isinstance(ctx, Response):
        return ctx
    _ensure_card_form_defaults(ctx)
    ctx.update({
        "mode": "edit",
        "copied_order": main,
        "sizes": sizes,
        "card": card,
        "card_id": card.id,
    })

    return render_template("product_cards/new/main_card.html", **ctx)


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
        if CATEGORIES_COMMON.get(category, {}).get("has_subcategory"):
            subcategory = (o.get("subcategory") or items[0].get("subcategory") or "").strip()
            if not subcategory:
                raise ValueError(f"Для категории '{category_ru}' не указана подкатегория")

        # лимит: максимум 2 черновика на категорию (+ субкатегория для clothes)
        open_cnt = _count_open_moderation_orders(current_user.id, category, subcategory)
        if open_cnt >= 2:
            if CATEGORIES_COMMON.get(category, {}).get("has_subcategory"):
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
        missing_card_ids = sorted({card_id for card_id in card_ids if card_id not in cards_map})
        if missing_card_ids:
            raise ValueError(
                {
                    "message": "Некоторые карточки больше недоступны. Корзина будет обновлена.",
                    "missing_card_ids": missing_card_ids,
                }
            )

        fast_company_cache = {}
        position_company_pairs = []
        for it in items:
            card_id = int(it["card_id"])
            pc = cards_map.get(card_id)
            err = _validate_card_access_and_status(pc, category)
            if err:
                # тут лучше 403, но через исключение
                raise PermissionError(err)

            if CATEGORIES_COMMON.get(category, {}).get("has_subcategory"):
                it_sub = (it.get("subcategory") or "").strip()
                if it_sub != subcategory:
                    raise ValueError("Корзина должна быть в одной подкатегории. Обнаружена смешанная subcategory.")

            fast_company = get_or_create_fast_order_company(new_order, pc, fast_company_cache)
            position = _add_order_item_from_card(new_order, pc, it)
            position_company_pairs.append((position, fast_company))

        db.session.flush()
        for position, fast_company in position_company_pairs:
            position.fast_order_company_id = fast_company.id

        db.session.commit()

    except PermissionError as pe:
        db.session.rollback()
        return _json_error(str(pe), 403)
    except ValueError as ve:
        db.session.rollback()
        if isinstance(ve.args[0] if ve.args else None, dict):
            payload = ve.args[0]
            return _json_error(
                payload.get("message", "Ошибка валидации"),
                400,
                missing_card_ids=payload.get("missing_card_ids", []),
            )
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


def _get_pc_order_header(o_id: int, *, require_unprocessed: bool = False):
    query = (
        db.session.query(
            Order.id,
            Order.category,
            Order.company_name,
            Order.company_idn,
        )
        .filter(
            Order.id == o_id,
            Order.user_id == current_user.id,
            Order.stage == 0,
            Order.is_moderation.is_(True),
            Order.to_delete.is_(False),
        )
    )
    if require_unprocessed:
        query = query.filter(Order.processed.is_(False))
    return query.first()


def _get_pc_order_pos_model(category: str):
    cat = (category or "").strip()
    if cat == settings.Clothes.CATEGORY:
        return Clothes
    if cat == settings.Shoes.CATEGORY:
        return Shoe
    if cat == settings.Linen.CATEGORY:
        return Linen
    if cat == settings.Socks.CATEGORY:
        return Socks
    if cat == settings.Parfum.CATEGORY:
        return Parfum
    if cat == settings.Cosmetics.CATEGORY:
        return Cosmetics
    if cat == settings.Toys.CATEGORY:
        return Toys
    return None


def _get_pc_order_rows_by_category(category: str, o_id: int):
    model = _get_pc_order_pos_model(category)
    if model is None:
        return []
    return model.query.filter_by(order_id=o_id).all()


def _get_pc_order_counts_by_category(category: str, o_id: int) -> tuple[int, int]:
    category_process = settings.CATEGORIES_DICT.get(category)
    if not category_process:
        return 0, 0

    stmt = text(f"""
        SELECT
            COALESCE({SQLQueryFactory.get_stmt(category_process, 'rows_count')}, 0) AS rows_count,
            COALESCE({SQLQueryFactory.get_stmt(category_process, 'marks_count')}, 0) AS marks_count
        FROM public.orders o
        {SQLQueryFactory.get_joins(category_process)}
        WHERE o.category = :category AND o.id = :o_id
        GROUP BY o.id
        LIMIT 1
    """)

    row = db.session.execute(stmt, {"category": category, "o_id": o_id}).fetchone()
    if not row:
        return 0, 0
    return int(row.rows_count or 0), int(row.marks_count or 0)


def h_pc_order_view(o_id: int):
    order = _get_pc_order_header(o_id)

    if not order:
        flash("Заказ не найден", "error")
        return redirect(url_for("user_product_cards.pc_orders_drafts"))

    category_process = settings.CATEGORIES_DICT.get(order.category)
    cat_cfg = CATEGORIES_COMMON.get(category_process, {})
    category_title = order.category
    order_list = _get_pc_order_rows_by_category(order.category, order.id)
    subcategory = ""
    sub_title = ""
    if cat_cfg.get("has_subcategory"):
        entity = order_list[0] if order_list else None
        subcategory = (getattr(entity, "subcategory", "") or "").strip() if entity else ""
        sub_title = (cat_cfg.get("subcategories") or {}).get(subcategory, subcategory)

    return render_template(
        "product_cards/user/order/pc_order_view.html",
        order=order,
        o_id=order.id,
        category=order.category,
        category_process_name=category_process,
        category_title=category_title,
        subcategory=subcategory,
        subcategory_title=sub_title,
        order_list=order_list,
        marks_count=len(order_list),
        orders_pos_count=len(order_list),
    )


def h_pc_order_table(o_id: int):
    order = _get_pc_order_header(o_id)

    if not order:
        return "", 404

    order_list = _get_pc_order_rows_by_category(order.category, order.id)
    return render_template(
        "product_cards/user/order/_pc_order_table.html",
        order=order,
        o_id=o_id,
        category=order.category,
        category_process_name=settings.CATEGORIES_DICT.get(order.category),
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

    order_items = _get_pc_order_rows_by_category(category, order.id)
    if not order_items:
        flash(message="Нельзя скопировать быстрый заказ: в заказе нет позиций", category="error")
        return redirect(url_for("user_product_cards.pc_orders_drafts"))

    copyable_items = _filter_copyable_fast_order_items(order_items)
    skipped_count = len(order_items) - len(copyable_items)
    if not copyable_items:
        flash(
            message="Нельзя скопировать быстрый заказ: в заказе нет позиций, доступных для копирования",
            category="error",
        )
        return redirect(url_for("user_product_cards.pc_orders_drafts"))

    subcategory = get_subcategory(order_id=order.id, category=category) or None

    # лимит: максимум 2 pc-заказа на категорию (+ subcat для clothes)
    active_pc_count = _count_open_pc_orders(user_id=user.id, category=category, subcategory=subcategory)

    if active_pc_count >= 2:
        if category in (settings.Clothes.CATEGORY, settings.Cosmetics.CATEGORY, settings.Toys.CATEGORY) and subcategory:
            flash(message=f"Достигнут лимит (2) заказов на категорию '{category}' и подкатегорию '{settings.CATEGORIES_DICT.get(subcategory)}'", category="error")
        else:
            flash(message=f"Достигнут лимит (2) заказов на категорию '{category}'", category="error")
        return redirect(url_for("user_product_cards.pc_orders_drafts"))

    # копируем
    new_id = common_save_copy_pc_order(
        user=user,
        category=category,
        order=order,
        only_copyable_items=True,
    )
    if not new_id:
        return redirect(url_for("user_product_cards.pc_orders_drafts"))

    if skipped_count:
        flash(
            message=f"При копировании пропущены позиции без одобренных данных или без компании: {skipped_count}",
            category="warning",
        )
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
    order = _get_pc_order_header(o_id)
    if not order:
        return "", 404

    category = order.category

    category_process = settings.CATEGORIES_DICT.get(category, "")

    model = _get_pc_order_pos_model(category)
    pos = model.query.filter_by(id=pos_id, order_id=o_id).first() if model is not None else None
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
    fields_cfg = _pc_visible_fields_for_entity(category_process, pos)

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
        elif order.category == settings.Cosmetics.CATEGORY:
            obj = Cosmetics.query.filter_by(id=pos_id, order_id=o_id).first()
        elif order.category == settings.Toys.CATEGORY:
            obj = Toys.query.filter_by(id=pos_id, order_id=o_id).first()
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

        subcategory = ""
        cat = _norm_cat(o.category)
        cat_cfg = CATEGORIES_COMMON.get(cat, {})
        if cat_cfg.get("has_subcategory"):
            if o.category == settings.Clothes.CATEGORY and o.clothes and o.clothes[0].subcategory:
                subcategory = (o.clothes[0].subcategory or "").strip()
            elif o.category == settings.Cosmetics.CATEGORY and o.cosmetics and o.cosmetics[0].subcategory:
                subcategory = (o.cosmetics[0].subcategory or "").strip()
            elif o.category == settings.Toys.CATEGORY and o.toys and o.toys[0].subcategory:
                subcategory = (o.toys[0].subcategory or "").strip()
            if not subcategory:
                subcategory = "common" if cat == settings.Clothes.CATEGORY_PROCESS else ""

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

        sub_key = subcategory if cat_cfg.get("has_subcategory") and subcategory else "__no_sub__"
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
    order = _get_pc_order_header(o_id, require_unprocessed=True)
    if not order:
        return jsonify(status="error", message="Заказ не найден"), 404

    category = (order.category or "").strip()

    order_items = _get_pc_order_rows_by_category(category, o_id)
    card_errors = validate_pc_order_items_ready_for_process(category, order_items)
    if card_errors:
        return jsonify(
            status="error",
            message="Заказ не отправлен в обработку: " + " ".join(card_errors),
        ), 400

    rows_count, marks_count = _get_pc_order_counts_by_category(category=category, o_id=o_id)

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

    order_items = _get_pc_order_rows_by_category(category, order.id)
    card_errors = validate_pc_order_items_ready_for_process(category, order_items)
    if card_errors:
        flash(message="Заказ не отправлен в обработку: " + " ".join(card_errors), category="error")
        return _back_to_order_view()

    if not validate_order_comment_length(order_comment=order_comment):
        return _back_to_order_view()

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
