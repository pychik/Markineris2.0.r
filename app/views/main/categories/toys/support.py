from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user

from config import settings
from models import Order
from tezaurus.runtime_catalogs import get_all_countries
from utilities.support import (
    get_category_p_orders,
    helper_get_order_notification,
    helper_paginate_data,
    orders_list_common,
)
from utilities.helpers.h_categories import order_table_update
from views.main.categories.toys.subcategories import ToysSubcategories, get_subcategory_config
from views.main.categories.toys.subcategories.registry import SUBCATEGORY_CONFIG


def helper_toys_index(
    subcategory: str | None = None,
    o_id: int | None = None,
    p_id: int | None = None,
    update_flag: int | None = None,
    copied_order=None,
    edit_order: str | None = None,
):
    user = current_user
    page_title = "Основные категории игрушек"
    search_placeholder = "Введите ТНВЭД или вид товара для определения категории"

    if not subcategory:
        toys_subcategories = {
            config["slug"]: {
                "slug": config["slug"],
                "title": config["title"],
                "icon": config["icon"],
                "icon_class": config.get("icon_class", "toys-category-icon--doll-accessories"),
                "is_disabled": False,
            }
            for config in SUBCATEGORY_CONFIG.values()
        }
        toys_upcoming_category_tiles = (
            {
                "title": "Палатки для игр",
                "icon": "main_v2/img/icons/toys/play_tents.png",
                "icon_class": "toys-category-icon--play-tents",
                "badge": "Скоро",
            },
            {
                "title": "Поезда электрические и наборы элементов для сборки моделей",
                "icon": "main_v2/img/icons/toys/train_set.png",
                "icon_class": "toys-category-icon--train-set",
                "badge": "Скоро",
            },
        )
        toys_category_tiles = tuple(
            tile
            for tile in (
                toys_subcategories.get("doll_accessories"),
                toys_subcategories.get("puzzles"),
                toys_subcategories.get("competition_cars"),
                toys_subcategories.get("sets_kits"),
                toys_subcategories.get("motorized_toys"),
                toys_subcategories.get("animal_creature"),
                toys_subcategories.get("scale_models_other"),
                toys_subcategories.get("musical_toy_instruments"),
                toys_subcategories.get("dolls_human_figures"),
                toys_subcategories.get("construction_sets"),
                toys_subcategories.get("card_games"),
                toys_subcategories.get("board_room_games_inventory"),
                toys_subcategories.get("toy_weapons"),
            )
            if tile
        )
        toys_search_index = [
            {
                "slug": config["slug"],
                "title": config["title"],
                "url": url_for("toys.index", subcategory=config["slug"]),
                "allowed_tnved_codes": list(config["allowed_tnved_codes"]),
                "allowed_tnved_choices": [
                    {"code": code, "label": label}
                    for code, label in config["allowed_tnved_choices"]
                ],
                "product_types": list(config["product_types"]),
            }
            for config in SUBCATEGORY_CONFIG.values()
        ]
        return render_template("categories/toys/index.html", **locals())

    if not ToysSubcategories.has_value(subcategory):
        flash("Неизвестная подкатегория игрушек.", "error")
        return redirect(url_for("toys.index"))

    subcategory_config = get_subcategory_config(subcategory)
    if not subcategory_config:
        flash("Подкатегория игрушек пока не настроена.", "error")
        return redirect(url_for("toys.index"))

    copy_order_edit_org = request.args.get("copy_order_edit_org")
    admin_id = user.admin_parent_id
    order_notification, admin_name, crm = helper_get_order_notification(admin_id=admin_id if admin_id else user.id)

    subcategory_title = subcategory_config["title"]
    category_code = subcategory_config["category_code"]
    category_code_by_tnved = subcategory_config.get("category_code_by_tnved", {})
    allowed_tnved_codes = subcategory_config["allowed_tnved_codes"]
    allowed_tnved_choices = subcategory_config["allowed_tnved_choices"]
    allowed_tnved_codes_by_product_type = subcategory_config.get("allowed_tnved_codes_by_product_type", {})
    tnved_group_choices = subcategory_config.get("tnved_group_choices", ())
    okpd2_choices_by_tnved = subcategory_config["okpd2_choices_by_tnved"]
    model_article_types = subcategory_config["model_article_types"]
    product_types = subcategory_config["product_types"]
    drive_type_choices = subcategory_config.get("drive_type_choices", ())
    material_choices = subcategory_config["material_choices"]
    min_child_age_choices = subcategory_config["min_child_age_choices"]
    usage_term_types = subcategory_config["usage_term_types"]
    service_life_types = subcategory_config["service_life_types"]
    step_2_template = subcategory_config.get("step_2_template", "helpers/toys/doll_accessories/2nd_step.html")
    step_3_template = subcategory_config.get("step_3_template", "helpers/toys/doll_accessories/3rd_step.html")
    countries = tuple(country.upper() for country in subcategory_config["default_countries"])
    rd_countries = tuple(country.upper() for country in get_all_countries())
    rd_types_list = settings.RD_TYPES
    company_types = settings.COMPANY_TYPES
    edo_types = settings.EDO_TYPES
    tax_list = settings.TAX_LIST
    category = settings.Toys.CATEGORY
    category_process_name = settings.Toys.CATEGORY_PROCESS
    with_packages = False

    if not o_id:
        active_orders = get_category_p_orders(user=user, category=category, processed=False, subcategory=subcategory)
        if len(active_orders) >= 5:
            flash(message=settings.Messages.USER_ORDERS_LIMIT, category="warning")
            return redirect(url_for("toys.index", subcategory=subcategory, o_id=active_orders[0].id))

        specific_order = False
        order_list = []
        company_type = ""
        company_name = ""
        company_idn = ""
        edo_type = ""
        edo_id = ""
        mark_type = ""
        mark_type_hidden = ""
        orders_pos_count = 0
        pos_count = 0
        total_price = 0
        price_exist = False
        trademark = ""
        pagination = None
        offset = 0
    else:
        specific_order = True
        order = user.orders.filter_by(
            category=category,
            processed=False,
            id=o_id,
            stage=settings.OrderStage.CREATING,
        ).filter(~Order.to_delete).first()
        orders, company_type, company_name, company_idn, edo_type, edo_id, mark_type, trademark, \
            orders_pos_count, pos_count, total_price, price_exist, _ = orders_list_common(
                category=category,
                user=user,
                o_id=o_id,
                subcategory=subcategory,
            )
        mark_type_hidden = mark_type

        if not orders or order.is_moderation:
            flash(message=settings.Messages.NO_SUCH_ORDER, category="error")
            return redirect(url_for("toys.index", subcategory=subcategory))

        if update_flag:
            return order_table_update(user=current_user, o_id=o_id, category=category)

        link = (
            f"javascript:{category_process_name}_update_table('"
            + url_for("toys.index", subcategory=subcategory, o_id=o_id, update_flag=1)
            + "?page={0}');"
        )
        page, per_page, offset, pagination, order_list = helper_paginate_data(data=orders, href=link)

    return render_template("categories/toys/category_v2.html", **locals())
