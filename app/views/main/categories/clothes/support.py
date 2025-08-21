from typing import Union

from flask import flash, jsonify, render_template, request, Response, redirect, url_for
from flask_login import current_user
from config import settings
from settings.start import db
from utilities.categories_data.subcategories_data import ClothesSubcategories, Category
from utilities.support import helper_get_order_notification, helper_category_common_index
from views.main.categories.clothes.subcategories import ClothesSubcategoryProcessor


def helper_clothes_index(o_id: int, p_id: int = None, update_flag: int = None,
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
    countries = settings.COUNTRIES_LIST
    clothes_content = settings.Clothes.CLOTHES_CONTENT
    clothes_nat_content = settings.Clothes.CLOTHES_NAT_CONTENT
    colors = settings.Clothes.COLORS
    genders = settings.Clothes.GENDERS

    clothes_size_description = settings.Clothes.CLOTHES_SIZE_DESC
    category = settings.Clothes.CATEGORY
    category_process_name = settings.Clothes.CATEGORY_PROCESS

    # clothes_tnved = settings.Clothes.TNVED_CODE
    # clothes_upper = settings.Clothes.UPPER_TYPES
    subcategory = request.args.get('subcategory', '')
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

    if not cl_type or cl_type not in settings.Clothes.ALL_TYPES_WITH_SUBCATEGORIES:
        return jsonify(dict(status=status, message=message + settings.Messages.STRANGE_REQUESTS))

    subcategory = request.args.get('subcategory', ClothesSubcategories.common.value)
    # tnved_list: tuple = settings.Clothes.CLOTHES_TNVED_DICT.get(cl_type)[1]

    tnved_list = ClothesSubcategoryProcessor.get_tnveds(subcategory=subcategory, cl_type=cl_type)
    if not tnved_list:
        return jsonify(dict(status=status, message=message + f" {subcategory=}, {cl_type=}"))
    status = settings.SUCCESS
    message = settings.Messages.MANUAL_TNVED_SUCCESS
    return jsonify(dict(status=status, message=message,
                        tnved_report=render_template('helpers/clothes/manual_tnved_modal_report.html', **locals())))


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


