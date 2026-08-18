from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user

from config import settings
from models import Order
from tezaurus.runtime_catalogs import get_all_countries
from utilities.support import (
    helper_get_order_notification,
    helper_paginate_data,
    get_category_p_orders,
    orders_list_common,
)
from utilities.helpers.h_categories import order_table_update
from views.main.categories.cosmetics.subcategories import CosmeticsSubcategories, get_subcategory_config
from views.main.categories.cosmetics.subcategories.registry import SUBCATEGORY_CONFIG


def helper_cosmetics_index(
    subcategory: str | None = None,
    o_id: int | None = None,
    p_id: int | None = None,
    update_flag: int | None = None,
    copied_order=None,
    edit_order: str | None = None,
):
    user = current_user
    page_title = "Основные категории косметики"
    search_placeholder = "Введите ТНВЭД или вид товара для определения категории"

    if not subcategory:
        cosmetics_subcategories = {
            config["slug"]: {
                "slug": config["slug"],
                "title": config["title"],
                "icon": config["icon"],
                "is_disabled": False,
            }
            for config in SUBCATEGORY_CONFIG.values()
        }
        cosmetics_category_tiles = tuple(
            tile
            for tile in (
                *(
                    cosmetics_subcategories.get(slug)
                    for slug in (
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
                    )
                ),
            )
            if tile
        )
        cosmetics_search_index = [
            {
                "slug": config["slug"],
                "title": config["title"],
                "url": url_for("cosmetics.index", subcategory=config["slug"]),
                "allowed_tnved_codes": list(config["allowed_tnved_codes"]),
                "allowed_tnved_choices": [
                    {"code": code, "label": label}
                    for code, label in config["allowed_tnved_choices"]
                ],
                "product_types": list(config["product_types"]),
            }
            for config in SUBCATEGORY_CONFIG.values()
        ]
        return render_template("categories/cosmetics/index.html", **locals())

    if not CosmeticsSubcategories.has_value(subcategory):
        flash("Неизвестная подкатегория косметики.", "error")
        return redirect(url_for("cosmetics.index"))

    subcategory_config = get_subcategory_config(subcategory)
    if not subcategory_config:
        flash("Подкатегория косметики пока не настроена.", "error")
        return redirect(url_for("cosmetics.index"))

    copy_order_edit_org = request.args.get("copy_order_edit_org")
    admin_id = user.admin_parent_id
    order_notification, admin_name, crm = helper_get_order_notification(admin_id=admin_id if admin_id else user.id)

    subcategory_title = subcategory_config["title"]
    category_code = subcategory_config["category_code"]
    allowed_tnved_codes = subcategory_config["allowed_tnved_codes"]
    allowed_tnved_choices = subcategory_config["allowed_tnved_choices"]
    nominal_quantity_types = subcategory_config["nominal_quantity_types"]
    nominal_quantity_types_by_product_type = subcategory_config["nominal_quantity_types_by_product_type"]
    product_types = subcategory_config["product_types"]
    usage_term_types = subcategory_config["usage_term_types"]
    content_type_choices = subcategory_config["content_type_choices"]
    for_children_choices = subcategory_config["for_children_choices"]
    step_2_template = subcategory_config.get("step_2_template", "helpers/cosmetics/decor_ukhod/2nd_step.html")
    step_3_template = subcategory_config.get("step_3_template", "helpers/cosmetics/decor_ukhod/3rd_step.html")
    countries = tuple(country.upper() for country in subcategory_config["default_countries"])
    rd_countries = tuple(country.upper() for country in get_all_countries())
    rd_types_list = settings.RD_TYPES
    company_types = settings.COMPANY_TYPES
    edo_types = settings.EDO_TYPES
    tax_list = settings.TAX_LIST
    category = settings.Cosmetics.CATEGORY
    category_process_name = settings.Cosmetics.CATEGORY_PROCESS
    with_packages = False
    has_aggr = False

    if not o_id:
        active_orders = get_category_p_orders(user=user, category=category, processed=False, subcategory=subcategory)
        if len(active_orders) >= 5:
            flash(message=settings.Messages.USER_ORDERS_LIMIT, category="warning")
            return redirect(url_for("cosmetics.index", subcategory=subcategory, o_id=active_orders[0].id))

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
            return redirect(url_for("cosmetics.index", subcategory=subcategory))

        if update_flag:
            return order_table_update(user=current_user, o_id=o_id, category=category)

        link = (
            f"javascript:{category_process_name}_update_table('"
            + url_for("cosmetics.index", subcategory=subcategory, o_id=o_id, update_flag=1)
            + "?page={0}');"
        )
        page, per_page, offset, pagination, order_list = helper_paginate_data(data=orders, href=link)

    return render_template("categories/cosmetics/category_v2.html", **locals())
