from typing import Union

from flask import flash, jsonify, render_template, request, Response, redirect, url_for
from flask_login import current_user
from config import settings
from settings.start import db
from tezaurus.runtime_catalogs import (
    get_all_countries,
    get_clothes_tnved_types,
    get_clothes_tnved_genders,
    get_colors,
    get_rd_countries,
)
from utilities.categories_data.subcategories_data import ClothesSubcategories, Category
from utilities.support import helper_get_order_notification, helper_category_common_index
from views.main.categories.clothes.subcategories import ClothesSubcategoryProcessor


def _build_tnved_choices(codes: list[str] | tuple[str, ...]) -> list[dict[str, str]]:
    return [{"code": str(code), "label": ""} for code in codes]


def _get_clothes_category_tiles() -> tuple[dict, ...]:
    common_creds = ClothesSubcategoryProcessor(ClothesSubcategories.common.value).get_creds()
    underwear_creds = ClothesSubcategoryProcessor(ClothesSubcategories.underwear.value).get_creds()
    swimming_creds = ClothesSubcategoryProcessor(ClothesSubcategories.swimming_accessories.value).get_creds()
    hats_creds = ClothesSubcategoryProcessor(ClothesSubcategories.hats.value).get_creds()
    gloves_creds = ClothesSubcategoryProcessor(ClothesSubcategories.gloves.value).get_creds()
    shawls_creds = ClothesSubcategoryProcessor(ClothesSubcategories.shawls.value).get_creds()

    return (
        {
            "slug": ClothesSubcategories.common.value,
            "title": "Одежда основная",
            "url": url_for("clothes.index", subcategory=ClothesSubcategories.common.value),
            "icon": "crm_mod/img/icons/clothes.svg",
            "product_types": list(common_creds.types),
            "allowed_tnved_codes": list(common_creds.clothes_all_tnved),
        },
        {
            "slug": ClothesSubcategories.underwear.value,
            "title": "Нижнее белье",
            "url": url_for("clothes.index", subcategory=ClothesSubcategories.underwear.value),
            "icon": "crm_mod/img/icons/underwear.svg",
            "product_types": list(underwear_creds.types),
            "allowed_tnved_codes": list(underwear_creds.clothes_all_tnved),
        },
        {
            "slug": "socks",
            "title": "Чулочно-носочные изделия",
            "url": url_for("clothes.index", subcategory="socks"),
            "icon": "crm_mod/img/icons/socks.svg",
            "product_types": list(settings.Socks.TYPES),
            "allowed_tnved_codes": list(settings.Socks.TNVED_ALL),
        },
        {
            "slug": ClothesSubcategories.swimming_accessories.value,
            "title": "Купальные принадлежности",
            "url": url_for("clothes.index", subcategory=ClothesSubcategories.swimming_accessories.value),
            "icon": "crm_mod/img/icons/swimming_accessories.svg",
            "product_types": list(swimming_creds.types),
            "allowed_tnved_codes": list(swimming_creds.clothes_all_tnved),
        },
        {
            "slug": ClothesSubcategories.hats.value,
            "title": "Шляпы",
            "url": url_for("clothes.index", subcategory=ClothesSubcategories.hats.value),
            "icon": "crm_mod/img/icons/hats.svg",
            "product_types": list(hats_creds.types),
            "allowed_tnved_codes": list(hats_creds.clothes_all_tnved),
        },
        {
            "slug": ClothesSubcategories.gloves.value,
            "title": "Перчатки",
            "url": url_for("clothes.index", subcategory=ClothesSubcategories.gloves.value),
            "icon": "crm_mod/img/icons/gloves.svg",
            "product_types": list(gloves_creds.types),
            "allowed_tnved_codes": list(gloves_creds.clothes_all_tnved),
        },
        {
            "slug": ClothesSubcategories.shawls.value,
            "title": "Шали",
            "url": url_for("clothes.index", subcategory=ClothesSubcategories.shawls.value),
            "icon": "crm_mod/img/icons/shawls.svg",
            "product_types": list(shawls_creds.types),
            "allowed_tnved_codes": list(shawls_creds.clothes_all_tnved),
        },
    )


def render_clothes_categories_index() -> str:
    page_title = "Основные категории одежды"
    search_placeholder = "Введите ТНВЭД или вид товара для определения категории"
    clothes_category_tiles = _get_clothes_category_tiles()
    clothes_search_index = [
        {
            **tile,
            "allowed_tnved_choices": _build_tnved_choices(tile.get("allowed_tnved_codes", [])),
        }
        for tile in clothes_category_tiles
    ]
    return render_template("categories/clothes/index.html", **locals())


def _allowed_clothes_types(subcategory: str | None) -> list[str]:
    subcategory_value = subcategory if subcategory not in ("", None, "None") else ClothesSubcategories.common.value
    dynamic_subcategories = {
        ClothesSubcategories.common.value,
        ClothesSubcategories.underwear.value,
    }
    if subcategory_value in dynamic_subcategories:
        return get_clothes_tnved_types(subcategory_value)
    return settings.Clothes.ALL_TYPES_WITH_SUBCATEGORIES


def helper_clothes_index(o_id: int, p_id: int = None, update_flag: int = None,
                         subcategory: str | None = None,
                         copied_order: db.Model = None, edit_order: str = None) -> Union[Response, str]:
    copy_order_edit_org = request.args.get('copy_order_edit_org')
    user = current_user

    # Формируем набор глобальных переменных для категории одежда и ее подкатегорий
    admin_id = user.admin_parent_id
    order_notification, admin_name, crm = helper_get_order_notification(admin_id=admin_id if admin_id else user.id)

    price_description = settings.PRICE_DESCRIPTION
    tnved_description = settings.TNVED_DESCRIPTION

    rd_description = settings.RD_DESCRIPTION
    rd_types_list = settings.RD_TYPES

    price_text = settings.PRICES_TEXT
    company_types = settings.COMPANY_TYPES
    edo_types = settings.EDO_TYPES
    tax_list = settings.TAX_LIST
    countries = get_all_countries()
    rd_countries = get_rd_countries(settings.Clothes.CATEGORY_PROCESS)
    clothes_content = settings.Clothes.CLOTHES_CONTENT
    clothes_nat_content = settings.Clothes.CLOTHES_NAT_CONTENT
    # colors = settings.Clothes.COLORS
    colors = get_colors()
    genders = settings.Clothes.GENDERS

    clothes_size_description = settings.Clothes.CLOTHES_SIZE_DESC
    category = settings.Clothes.CATEGORY
    category_process_name = settings.Clothes.CATEGORY_PROCESS

    # clothes_tnved = settings.Clothes.TNVED_CODE
    # clothes_upper = settings.Clothes.UPPER_TYPES
    subcategory = subcategory if subcategory is not None else request.args.get('subcategory', '')
    if subcategory == 'socks':
        return redirect(url_for('socks.index'))
    if not Category.check_subcategory(category=category, subcategory=subcategory):
        flash(message=settings.Messages.STRANGE_REQUESTS + f' подкатегория неизвестна сервису', category='error')
        return redirect(url_for(f'main.enter'))
    # cs = ClothesSubcategoryProcessor(subcategory=subcategory)

    # (clothes_all_tnved, clothes_sizes,
    #  clothes_types_sizes_dict, types, subcategory_name) = ClothesSubcategoryProcessor(
    #     subcategory=subcategory).get_creds()
    # clothes_all_tnved = settings.Clothes.TNVED_ALL
    # clothes_sizes = settings.Clothes.SIZES_ALL
    # clothes_types_sizes_dict = settings.Clothes.SIZE_ALL_DICT
    # types = settings.Clothes.TYPES

    return helper_category_common_index(**locals())


def h_bck_clothes_tnved() -> Response:
    status = settings.ERROR
    message = settings.Messages.MANUAL_TNVED_ERROR
    cl_type = request.form.get('cl_type', '').replace('--', '')
    subcategory = request.args.get('subcategory', ClothesSubcategories.common.value)
    cl_gender = request.form.get('gender', '').replace('--', '')

    if not cl_type or cl_type not in _allowed_clothes_types(subcategory):
        return jsonify(dict(status=status, message=message + settings.Messages.STRANGE_REQUESTS))

    # tnved_list: tuple = settings.Clothes.CLOTHES_TNVED_DICT.get(cl_type)[1]

    tnved_list = ClothesSubcategoryProcessor.get_tnveds(subcategory=subcategory, cl_type=cl_type, cl_gender=cl_gender)

    if not tnved_list:
        return jsonify(dict(status=status, message=message + f" {subcategory=}, {cl_type=}"))
    status = settings.SUCCESS
    message = settings.Messages.MANUAL_TNVED_SUCCESS
    return jsonify(dict(status=status, message=message,
                        tnved_report=render_template('helpers/clothes/manual_tnved_modal_report.html', **locals())))


def h_bck_clothes_genders():
    def _needs_gender(subcategory: str) -> bool:
        # учитываем '', 'common', None и строковый 'None' из шаблона
        return subcategory in ('', ClothesSubcategories.common.value, ClothesSubcategories.underwear.value, None, 'None')
    status = settings.ERROR
    message = 'Не удалось загрузить список полов.'
    cl_type = (request.form.get('cl_type', '') or '').replace('--', '').strip()

    # в GET, как в вашем примере
    subcategory = request.args.get('subcategory', ClothesSubcategories.common.value)

    if not cl_type or cl_type not in _allowed_clothes_types(subcategory):
        return jsonify(dict(
            status=status,
            message=message + settings.Messages.STRANGE_REQUESTS
        ))

    # если для подкатегории пол требуется — отдаём список, иначе — пустой список
    if _needs_gender(subcategory):
        genders = get_clothes_tnved_genders(subcategory, cl_type)
        if not genders:
            return jsonify(dict(status=settings.ERROR, message=f'Для типа {cl_type} не найден список полов.'))
        return jsonify(dict(status=settings.SUCCESS, genders=genders, needs_gender=True))
    else:
        return jsonify(dict(status=settings.SUCCESS, genders=[], needs_gender=False))


def h_bck_socks_tnved() -> Response:

    status = settings.ERROR
    message = settings.Messages.MANUAL_TNVED_ERROR
    socks_type = request.form.get('socks_type', '').replace('--', '')
    if not socks_type or socks_type not in settings.Socks.TYPES:

        return jsonify(dict(status=status, message=message + settings.Messages.STRANGE_REQUESTS))

    tnved_list: tuple = settings.Socks.SOCKS_TNVED_DICT.get(socks_type)[1]
    status = settings.SUCCESS
    message = settings.Messages.MANUAL_TNVED_SUCCESS
    return jsonify(dict(status=status, message=message,
                        tnved_report=render_template('helpers/socks/manual_tnved_modal_report.html', **locals())))
