import dataclasses
import re
from base64 import encodebytes
from datetime import datetime, timedelta
from functools import wraps
from math import floor as m_floor
from time import time
from typing import Optional, Union
from uuid import uuid4

from flask import flash, jsonify, Markup, redirect, url_for, request, Response, render_template
from flask_login import current_user
from flask_paginate import Pagination
from flask_sqlalchemy.pagination import QueryPagination
from sqlalchemy import asc, create_engine, desc, text, or_, not_, UnaryExpression, func
from sqlalchemy.engine.row import Row
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql.elements import TextClause
from werkzeug.datastructures import FileStorage, ImmutableMultiDict

from config import settings
from logger import logger
from models import (
    Order,
    OrderStat,
    User,
    EmailMessage,
    db,
    Shoe,
    Clothes,
    ClothesQuantitySize,
    Socks,
    Linen,
    Parfum,
    Price,
    Promo,
    ServerParam,
    ServiceAccount,
    UserTransaction,
    users_promos,
    TransactionTypes,
    TransactionStatuses,
    LinenSizesUnits,
)
from utilities.daily_price import get_cocmd
from utilities.helpers.h_tg_notify import helper_send_user_order_tg_notify
from utilities.pdf_processor import get_first_page_as_image
from utilities.sql_categories_aggregations import SQLQueryCategoriesAll
from utilities.validators import ValidatorProcessor
from views.crm.schema import CrmDefaults
from views.main.categories.clothes.subcategories import ClothesSubcategoryProcessor
from .categories_data.subcategories_data import ClothesSubcategories, Category
from .categories_data.subcategories_logic import get_subcategory
from .cipher.instance import encryptor
from .exceptions import GetFirstPageFromPDFError
from .helpers.h_categories import order_table_update
from .http_client import Requester
from .minio_service.services import get_s3_service
from .saving_uts import common_save_db, get_delete_pos_stmts, get_rows_marks
from .telegram import TelegramProcessor, MarkinerisInform
from .useful_objects import Olc, OLC_NONE, OLC_PARFUM_NONE, OLC_PARFUM_9NONE


def time_count(func):
    @wraps(func)
    def wrapper(*args, **kw):
        t_start = time()
        result = func(*args, **kw)
        res = f"{func.__name__}, :  {time() - t_start}"
        logger.info(res)
        return result
    return wrapper


def sql_count(func):
    @wraps(func)
    def wrapper(*args, **kw):
        result = func(*args, **kw)
        from flask_sqlalchemy import get_debug_queries

        debug_queries = get_debug_queries()
        mes = f"Quantity: {len(debug_queries)}\n{debug_queries}"
        logger.info(mes)

        return result

    return wrapper


def order_count(category: str, order_list) -> tuple:

    match category:
        case settings.Parfum.CATEGORY:
            quantity_list_raw = [el.box_quantity if el.with_packages == 'да' else el.quantity for el in order_list]
            rd_exist = True if [el.rd_type for el in order_list if el.rd_type] else False
            return rd_exist, quantity_list_raw, len(quantity_list_raw), sum(quantity_list_raw)

        case settings.Shoes.CATEGORY:
            quantity_list_raw = [[(e.quantity, el.article_price, el.box_quantity) for e in el.sizes_quantities]
                                 for el in order_list]

        case settings.Clothes.CATEGORY:
            quantity_list_raw = [[(e.quantity, el.article_price, el.box_quantity) for e in el.sizes_quantities]
                                 for el in order_list]

        case settings.Socks.CATEGORY:
            quantity_list_raw = [[(e.quantity, el.article_price, el.box_quantity) for e in el.sizes_quantities]
                                 for el in order_list]

        case settings.Linen.CATEGORY:
            quantity_list_raw = [[(e.quantity, el.article_price, el.box_quantity, el.with_packages) for e in el.sizes_quantities]
                                 for el in order_list]

            quantity_list = [item[2] if item[3] == 'да' else item[0] * item[2] for sublist in quantity_list_raw for item in sublist]
            rd_exist = True if [el.rd_type for el in order_list if el.rd_type] else False
            return rd_exist, quantity_list_raw, len(quantity_list), sum(quantity_list)
    # for pep8
        case _:
            return [], 0, 0
    quantity_list = [item[0] * item[2] for sublist in quantity_list_raw for item in sublist]
    rd_exist = True if [el.rd_type for el in order_list if el.rd_type] else False
    return rd_exist, quantity_list_raw, len(quantity_list), sum(quantity_list)


def parfum_orders(user: User, stage: int = settings.OrderStage.CREATING, o_id: int = None, new: bool = False,) -> tuple:

    if new or not o_id:
        order_list, trademark, mark_type, company_idn, company_type, company_name,\
            edo_type, edo_id, order_list = OLC_PARFUM_9NONE

    else:
        order, order_list = get_category_orders(user=user, category=settings.Parfum.CATEGORY, o_id=o_id,
                                                stage=stage)
        if not order:
            return OLC_PARFUM_NONE
        company_idn = order.company_idn
        company_type = order.company_type
        company_name = order.company_name
        edo_type = order.edo_type
        edo_id = order.edo_id
        mark_type = order.mark_type

    if order_list:
        # prepare vars for our template
        price_exist = True if order_list[0].article_price != 0 else False
        trademark = order_list[0].trademark
        quantity_list = [el.box_quantity if el.with_packages == 'да' else el.quantity for el in order_list]
        pos_count = len(quantity_list)
        orders_pos_count = sum(quantity_list)
        if price_exist:
            price_list = [el.article_price * el.quantity for el in order_list]
            total_price = sum(price_list)
        else:
            total_price = 0
    else:
        price_exist, trademark, orders_pos_count, pos_count, total_price = False, None, None, None, None
    return order_list, trademark, mark_type, company_idn, company_type, company_name, edo_type, edo_id,\
        orders_pos_count, pos_count, price_exist, total_price


# for not processed orders
def orders_list_common(category: str, user: User, new: bool = False, o_id: int = None,
                       stage: int = settings.OrderStage.CREATING) -> Optional[Olc]:
    if new is True:
        return OLC_NONE

    order, orders = get_category_orders(user=user, category=category, o_id=o_id, stage=stage)

    if not orders:
        return OLC_NONE
    company_idn = order.company_idn
    company_type = order.company_type
    company_name = order.company_name
    edo_type = order.edo_type
    edo_id = order.edo_id
    mark_type = order.mark_type

    # prepare vars for our template
    price_exist = True if orders[0].article_price != 0 else False
    trademark = orders[0].trademark
    subcategory = orders[0].subcategory if category == settings.Clothes.CATEGORY else ''

    rd_exist, quantity_list_raw, pos_count, orders_pos_count = order_count(category, order_list=orders)
    if price_exist:
        price_list = [item[0] * item[1]*item[2] for sublist in quantity_list_raw for item in sublist]
        total_price = sum(price_list)
    else:
        total_price = 0
    olc = Olc(orders, company_type, company_name, company_idn,
              edo_type, edo_id, mark_type, trademark, orders_pos_count, pos_count, total_price, price_exist, subcategory)
    return olc


def check_order_pos(category: str, order: Order) -> Optional[int]:
    match category:

        case settings.Shoes.CATEGORY:
            rd_exist, quantity_list_raw, pos_count, order_pos_count = order_count(category=settings.Shoes.CATEGORY,
                                                                                  order_list=order.shoes)

        case settings.Clothes.CATEGORY:
            rd_exist, quantity_list_raw, pos_count, order_pos_count = order_count(category=settings.Clothes.CATEGORY,
                                                                                  order_list=order.clothes)
        case settings.Socks.CATEGORY:
            rd_exist, quantity_list_raw, pos_count, order_pos_count = order_count(category=settings.Socks.CATEGORY,
                                                                                  order_list=order.socks)
        case settings.Linen.CATEGORY:
            rd_exist, quantity_list_raw, pos_count, order_pos_count = order_count(category=settings.Linen.CATEGORY,
                                                                                  order_list=order.linen)
        case settings.Parfum.CATEGORY:
            rd_exist, quantity_list_raw, pos_count, order_pos_count = order_count(category=settings.Parfum.CATEGORY,
                                                                                  order_list=order.parfum)
        case _:
            pos_count = settings.ORDER_LIMIT_ARTICLES

    if pos_count >= settings.ORDER_LIMIT_ARTICLES:
        flash(message=f"{settings.Messages.ORDER_LIMIT} {settings.ORDER_LIMIT_ARTICLES}."
                      f" В вашей накладной {pos_count} шт. "
                      f"Позиций должно быть меньше на  {pos_count - settings.ORDER_LIMIT_ARTICLES} шт. "
                      f"Удалите последний артикул.", category='error')

        return False
    return True


def preprocess_order_category(o_id: int, p_id: int, category: str) -> Union[Response, str]:
    form_data_raw = request.form

    # validate clothes TNVED is in CLOTHES tnveds(only clothes and socks tnveds have dicts to check)
    # clothes_tnved_condition = category == settings.Clothes.CATEGORY and \
    #         ValidatorProcessor.clothes_pre_validate_tnved(tnved_str=form_data_raw.get('tnved_code'))
    # socks_tnved_condition = category == settings.Socks.CATEGORY and \
    #         ValidatorProcessor.socks_pre_validate_tnved(tnved_str=form_data_raw.get('tnved_code'))
    subcategory = request.args.get('subcategory', '')
    if not Category.check_subcategory(category=category, subcategory=subcategory):
        return jsonify(dict(status='error', message=settings.Messages.STRANGE_REQUESTS + 'у одежды нет такой подкатегории'))

    check_tnved_condition = ValidatorProcessor.check_tnveds(category=category,
                                                            subcategory=subcategory,
                                                            tnved_str=form_data_raw.get('tnved_code'))
    if check_tnved_condition:
        if o_id and not p_id:
            return jsonify(dict(status='error', message=settings.Messages.TNVED_ABSENCE_ERROR))

        else:
            flash(message=settings.Messages.TNVED_ABSENCE_ERROR, category='error')
            return redirect(url_for(f'{settings.CATEGORIES_DICT[category]}.index', o_id=o_id, subcategory=subcategory))

    order_id, sort_type, sort_order = preprocess_order_common(user=current_user, form_data_raw=form_data_raw,
                                                              category=category, subcategory=subcategory,
                                                              o_id=o_id, p_id=p_id) \
        if category != settings.Parfum.CATEGORY else parfum_preprocess_order(user=current_user,
                                                                             form_dict=form_data_raw.to_dict(),
                                                                             o_id=o_id, p_id=p_id)
    if not order_id:
        flash(message=settings.Messages.ORDER_ADD_POS_ERROR, category='error')

    # check copy or edit then add
    if o_id and not p_id:
        return order_table_update(user=current_user, o_id=o_id, category=category) if order_id \
            else jsonify(dict(status='error'))
    if o_id and p_id and order_id:
        flash(message=settings.Messages.ORDER_EDIT_POS_SUCCESS)
    if not o_id and not p_id and order_id:
        flash(message=f"{settings.Messages.ORDER_ADD_POS_SUCCESS} {form_data_raw.get('article') if category != settings.Parfum.CATEGORY else form_data_raw.get('trademark')}")

    return redirect(url_for(f'{settings.CATEGORIES_DICT[category]}.index', o_id=order_id, subcategory=subcategory,
                            sort_type=sort_type, sort_order=sort_order))


def preprocess_order_common(user: User, form_data_raw: ImmutableMultiDict,
                            category: str, subcategory: str = ClothesSubcategories.common.value,
                            o_id: int = None, p_id: int = None, ) -> tuple[Optional[int], Optional[str],
                                                                                          Optional[str]]:
    form_dict: dict = form_data_raw.to_dict()

    # this check not raises error and redirect in sequence of response logic
    # add check for clothes and tnved not empty
    # if category == settings.Clothes.CATEGORY and \
    #         ValidatorProcessor.clothes_pre_validate_tnved(tnved_str=form_dict.get('tnved_code'),
    #                                                       cl_type=form_dict.get('type')):
    #     flash(message=settings.Messages.TNVED_ABSENCE_ERROR, category='error')
    #     return o_id, None, None

    if o_id:
        order = user.orders.filter_by(category=category, processed=False, id=o_id).filter(~Order.to_delete).first()
        if not check_order_pos(category=category, order=order):
            return o_id, None, None
        if p_id:
            process_delete_order_pos(o_id=o_id, m_id=p_id, category=category, edit=True)

    else:
        company_idn = form_dict.get("company_idn")
        if company_idn in settings.ExceptionOrders.COMPANIES_IDNS:
            flash(message=settings.ExceptionOrders.COMPANY_IDN_ERROR.format(company_idn=company_idn), category='error')
            return (None,) * 3
        order = Order(company_type=form_dict.get("company_type"), company_name=form_dict.get("company_name"),
                      edo_type=form_dict.get("edo_type"), edo_id=form_dict.get("edo_id"),
                      company_idn=company_idn, mark_type=form_dict.get("mark_type_hidden", "МАРКИРОВКА НЕ УКАЗАНА"),
                      category=category, stage=settings.OrderStage.CREATING, processed=False, to_delete=False)
    try:
        if category == settings.Clothes.CATEGORY:
            sizes = form_data_raw.getlist("size")
            quantities = form_data_raw.getlist("quantity")
            size_types = form_data_raw.getlist("size_type")
            sizes_quantities = sorted(list(zip(sizes, quantities, size_types)), key=lambda x: x[0])
        elif category == settings.Socks.CATEGORY:
            sizes = form_data_raw.getlist("size")
            quantities = form_data_raw.getlist("quantity")
            size_types = form_data_raw.getlist("size_type")
            sizes_quantities = sorted(list(zip(sizes, quantities, size_types)), key=lambda x: x[0])
        elif category == settings.Shoes.CATEGORY:
            sizes = form_data_raw.getlist("size")
            quantities = form_data_raw.getlist("quantity")
            sizes_quantities = sorted(list(zip(sizes, quantities)), key=lambda x: x[0])
        elif category == settings.Linen.CATEGORY:
            sizesX = form_data_raw.getlist("sizeX")
            sizesY = form_data_raw.getlist("sizeY")
            sizes = list(map(lambda x: f"{x[0]}*{x[1]}", zip(sizesX, sizesY)))
            sizes_units = form_data_raw.getlist("sizeUnit")
            quantities = form_data_raw.getlist("quantity")
            sizes_quantities = sorted(list(zip(sizes, sizes_units,  quantities)), key=lambda x: x[0])
        else:
            raise IntegrityError('Выбрана некорректная категория')

        updated_order = common_save_db(order=order, form_dict=form_dict,
                                       category=category, subcategory=subcategory, sizes_quantities=sizes_quantities)

        user.orders.append(updated_order)

        db.session.commit()

    except IntegrityError as e:
        logger.error(e)
        db.session.rollback()
        return (None,)*3
    sort_type, sort_order = helper_get_sort_order(sort_type_order=form_dict.get("sort_type_order"))
    o_id = updated_order.id

    return o_id,  sort_type, sort_order


def parfum_preprocess_order(user: User, form_dict: dict, o_id: int = None, p_id: int = None) -> tuple:

    if not o_id:
        try:
            order = Order(company_type=form_dict.get("company_type"), company_name=form_dict.get("company_name"),
                          edo_type=form_dict.get("edo_type"), edo_id=form_dict.get("edo_id"),
                          company_idn=form_dict.get("company_idn"), mark_type=form_dict.get("mark_type_hidden", "МАРКИРОВКА НЕ УКАЗАНА"),
                          category=settings.Parfum.CATEGORY, stage=settings.OrderStage.CREATING, processed=False)

            updated_order = common_save_db(order=order, form_dict=form_dict,
                                           category=settings.Parfum.CATEGORY)
            user.orders.append(updated_order)

            db.session.commit()
        except IntegrityError as e:
            logger.error(e)
            db.session.rollback()
            return (None, )*3
    else:

        order = user.orders.filter_by(category=settings.Parfum.CATEGORY, processed=False, id=o_id).first()

        if not check_order_pos(category=settings.Parfum.CATEGORY, order=order):
            return (None, )*3

        if p_id:
            process_delete_order_pos(o_id=o_id, m_id=p_id, category=settings.Parfum.CATEGORY, edit=True)

        updated_order = common_save_db(order=order, form_dict=form_dict,
                                       category=settings.Parfum.CATEGORY)
        user.orders.append(updated_order)

        db.session.commit()
    sort_type, sort_order = helper_get_sort_order(sort_type_order=form_dict.get("sort_type_order"))
    o_id = updated_order.id
    return o_id, sort_type, sort_order


def helper_category_common_index(o_id: int, category: str, category_process_name: str, user: User,
                                 update_flag: int = None, **kwargs):
    with_packages = False
    active_orders = get_category_p_orders(user=user, category=category, subcategory=kwargs.get('subcategory'), processed=False)

    # if not specific order
    if not o_id:
        if len(active_orders) >= 5:
            specific_order = True
            o_id = active_orders[0].id
            flash(message=settings.Messages.USER_ORDERS_LIMIT, category='warning')
            return redirect(url_for(f'{category_process_name}.index', o_id=o_id))

        subcategory = kwargs.get('subcategory')

        # else:
        #     order_list, company_type, company_name, company_idn, \
        #         edo_type, edo_id, mark_type, trademark, orders_pos_count, pos_count, \
        #         total_price, price_exist, subcategory_proc = orders_list_common(category=category, user=user, new=True)
            # if subcategory:
            #     kwargs.pop('subcategory')
            # else:
            #     del subcategory
    else:
        specific_order = True
        orders, company_type, company_name, company_idn, \
            edo_type, edo_id, mark_type, trademark, orders_pos_count, pos_count, \
            total_price, price_exist, subcategory = orders_list_common(category=category, user=user, o_id=o_id)

        if not orders:
            flash(message=settings.Messages.NO_SUCH_ORDER, category='error')
            return redirect(url_for(f'{category_process_name}.index'))

        if update_flag:
            return order_table_update(user=current_user, o_id=o_id, category=category)

        link = f'javascript:{category_process_name}_update_table(\'' + url_for(f'{category_process_name}.index', o_id=o_id,
                                                            update_flag=1) + '?page={0}\');'
        page, per_page, offset, pagination, order_list = helper_paginate_data(data=orders, href=link)
        with_packages = order_list[-1].with_packages if category not in [settings.Clothes.CATEGORY,
                                                                         settings.Socks.CATEGORY, ] \
            else False

    kwargs.pop('subcategory') if 'subcategory' in kwargs else None
    if category == settings.Clothes.CATEGORY:
        (clothes_all_tnved, clothes_sizes,
         clothes_types_sizes_dict, types, subcategory_name) = ClothesSubcategoryProcessor(
            subcategory=subcategory).get_creds()
    return render_template(f'categories/category_v2.html', **locals(), **kwargs)


def helper_shoes_index(o_id: int, p_id: int = None, update_flag: int = None,
                         copied_order: db.Model = None, edit_order: str = None, ):
    copy_order_edit_org = request.args.get('copy_order_edit_org')

    user = current_user
    admin_id = user.admin_parent_id
    order_notification, admin_name, crm = helper_get_order_notification(admin_id=admin_id if admin_id else user.id)

    price_description = settings.PRICE_DESCRIPTION
    rd_description = settings.RD_DESCRIPTION
    rd_types_list = settings.RD_TYPES

    category = settings.Shoes.CATEGORY
    category_process_name = settings.Shoes.CATEGORY_PROCESS
    types = settings.Shoes.TYPES
    company_types = settings.COMPANY_TYPES
    edo_types = settings.EDO_TYPES
    tax_list = settings.TAX_LIST
    countries = settings.COUNTRIES_LIST
    shoe_tnved = settings.Shoes.TNVED_CODE
    shoe_al = settings.Shoes.SHOE_AL
    shoe_ot = settings.Shoes.SHOE_OT
    shoe_nl = settings.Shoes.SHOE_NL
    shoe_sizes = settings.Shoes.SIZES_ALL
    shoe_size_description = settings.Shoes.SHOE_SIZE_DESC

    colors = settings.Shoes.COLORS
    genders = settings.Shoes.GENDERS
    materials_up_linen = settings.Shoes.MATERIALS_UP_LINEN
    materials_bottom = settings.Shoes.MATERIALS_BOTTOM

    subcategory = request.args.get('subcategory', '')
    if subcategory:
        flash(message=settings.Messages.STRANGE_REQUESTS + f'подкатегория неизвестна сервису', category='error')
        return redirect(url_for(f'main.enter'))

    return helper_category_common_index(**locals())


def helper_socks_index(o_id: int, p_id: int = None, update_flag: int = None,
                         copied_order: db.Model = None, edit_order: str = None) -> Union[Response, str]:
    copy_order_edit_org = request.args.get('copy_order_edit_org')
    user = current_user
    admin_id = user.admin_parent_id
    order_notification, admin_name, crm = helper_get_order_notification(admin_id=admin_id if admin_id else user.id)

    price_description = settings.PRICE_DESCRIPTION
    tnved_description = settings.TNVED_DESCRIPTION
    socks_all_tnved = settings.Socks.TNVED_ALL

    rd_description = settings.RD_DESCRIPTION
    rd_types_list = settings.RD_TYPES

    price_text = settings.PRICES_TEXT
    company_types = settings.COMPANY_TYPES
    edo_types = settings.EDO_TYPES
    tax_list = settings.TAX_LIST
    countries = settings.COUNTRIES_LIST
    socks_content = settings.Socks.CLOTHES_CONTENT
    socks_types_sizes_dict = settings.Socks.SIZE_ALL_DICT

    category = settings.Socks.CATEGORY
    category_process_name = settings.Socks.CATEGORY_PROCESS

    types = settings.Socks.TYPES
    colors = settings.Clothes.COLORS
    genders = settings.Socks.GENDERS

    subcategory = request.args.get('subcategory', '')
    if subcategory:
        flash(message=settings.Messages.STRANGE_REQUESTS + f'подкатегория неизвестна сервису', category='error')
        return redirect(url_for(f'main.enter'))

    return helper_category_common_index(**locals())


def helper_linen_index(o_id: int, p_id: int = None, update_flag: int = None,
                         copied_order: db.Model = None, edit_order: str = None) -> Union[Response, str]:
    copy_order_edit_org = request.args.get('copy_order_edit_org')

    user = current_user
    admin_id = user.admin_parent_id
    order_notification, admin_name, crm = helper_get_order_notification(admin_id=admin_id if admin_id else user.id)

    category = settings.Linen.CATEGORY
    category_process_name = settings.Linen.CATEGORY_PROCESS

    price_description = settings.PRICE_DESCRIPTION
    tnved_description = settings.TNVED_DESCRIPTION
    linen_tnved = settings.Linen.TNVED_CODE
    rd_description = settings.RD_DESCRIPTION
    rd_types_list = settings.RD_TYPES

    price_text = settings.PRICES_TEXT
    company_types = settings.COMPANY_TYPES
    edo_types = settings.EDO_TYPES
    tax_list = settings.TAX_LIST
    countries = settings.COUNTRIES_LIST

    types = settings.Linen.TYPES
    colors = settings.Linen.COLORS
    textile_types = settings.Linen.TEXTILE_TYPES
    customer_ages = settings.Linen.CUSTOMER_AGES
    size_units = LinenSizesUnits.choices()
    box_quantity_description = settings.Linen.BOX_QUANTITY_DESCRIPTION

    subcategory = request.args.get('subcategory', '')
    if subcategory:
        flash(message=settings.Messages.STRANGE_REQUESTS + f'подкатегория неизвестна сервису', category='error')
        return redirect(url_for(f'main.enter'))

    return helper_category_common_index(**locals())


def helper_parfum_index(o_id: int, p_id: int = None, update_flag: int = None,
                         copied_order: db.Model = None, edit_order: str = None) -> Union[Response, str]:
    copy_order_edit_org = request.args.get('copy_order_edit_org')

    user = current_user
    admin_id = user.admin_parent_id
    order_notification, admin_name, crm = helper_get_order_notification(admin_id=admin_id if admin_id else user.id)

    price_description = settings.PRICE_DESCRIPTION
    tnved_description = settings.TNVED_DESCRIPTION
    parfum_tnved = settings.Parfum.TNVED_CODE
    rd_description = settings.RD_DESCRIPTION
    rd_types_list = settings.RD_TYPES

    price_text = settings.PRICES_TEXT
    company_types = settings.COMPANY_TYPES
    edo_types = settings.EDO_TYPES
    tax_list = settings.TAX_LIST
    countries = settings.COUNTRIES_LIST

    category = settings.Parfum.CATEGORY
    category_process_name = settings.Parfum.CATEGORY_PROCESS
    types = settings.Parfum.TYPES
    volume_types = settings.Parfum.VOLUMES
    package_types = settings.Parfum.PACKAGE_TYPES
    material_packages = settings.Parfum.MATERIAL_PACKAGES
    price_text = settings.PRICES_TEXT

    subcategory = request.args.get('subcategory', '')
    if subcategory:
        flash(message=settings.Messages.STRANGE_REQUESTS + f'подкатегория неизвестна сервису', category='error')
        return redirect(url_for(f'main.enter'))

    active_orders = get_category_p_orders(user=user, category=settings.Parfum.CATEGORY, processed=False)
    if not o_id:
        if len(active_orders) >= 5:
            specific_order = True
            o_id = active_orders[0].id
            flash(message=settings.Messages.USER_ORDERS_LIMIT, category='error')
            return redirect(url_for('parfum.index', o_id=o_id))

        else:
            order_list, trademark, mark_type, company_idn, company_type, company_name, edo_type, edo_id,\
                orders_pos_count, pos_count, price_exist, total_price = parfum_orders(user=user, new=True)
    else:
        specific_order = True
        orders, trademark, mark_type, company_idn, company_type, company_name, edo_type, edo_id, \
            orders_pos_count, pos_count, price_exist, total_price = parfum_orders(user=user, o_id=o_id)

        if not orders:
            flash(message=settings.Messages.NO_SUCH_ORDER, category='error')
            return redirect(url_for('parfum.index'))
        if update_flag:
            return order_table_update(user=current_user, o_id=o_id, category=category)

        link = f'javascript:{category_process_name}_update_table(\'' + url_for(f'{category_process_name}.index',
                                                                               o_id=o_id,
                                                                               update_flag=1) + '?page={0}\');'
        page, per_page, offset, pagination, order_list = helper_paginate_data(data=orders, href=link)
        with_packages = order_list[-1].with_packages if category != settings.Clothes.CATEGORY else False

    return render_template('categories/category_v2.html', **locals())


def helper_get_sort_order(sort_type_order: str) -> tuple:
    sort_type, sort_order = None, None
    if sort_type_order:
        sto: list = sort_type_order.split(';')
        sort_type, sort_order = sto[0], sto[1]
    return sort_type, sort_order


def helper_preload_common(o_id: int, stage: int, category: str, category_process_name: str):
    user = current_user

    admin_id = user.admin_parent_id
    order_notification, admin_name, crm = helper_get_order_notification(admin_id=admin_id if admin_id else user.id)

    orders, company_type, company_name, company_idn, \
        edo_type, edo_id, mark_type, trademark, orders_pos_count, pos_count, \
        total_price, price_exist, subcategory = orders_list_common(category=category, user=user, o_id=o_id, stage=stage)

    if not orders:
        flash(message=settings.Messages.NO_SUCH_ORDER, category='error')
        return redirect(url_for(f'{category_process_name}.index'))

    from utilities.download import orders_common_preload
    start_list, page, per_page, offset, pagination, order_list = orders_common_preload(category=category,
                                                                                       company_idn=company_idn,
                                                                                       orders_list=orders)

    return render_template('preload.html', **locals())


def send_file_tg(user: User, company_idn: str, company_type: str, company_name: str, edo_type: str, edo_id: str,
                 mark_type: str, table_file: FileStorage) -> None:
    try:

        admin_user = User.query.filter_by(id=user.admin_parent_id).first() \
            if user.role == settings.ORD_USER else user
        if user.is_at2:
            telegram_raw = user.telegram
            telegram_id = telegram_raw[0].channel_id if telegram_raw else settings.Telegram.TELEGRAM_MAIN_GROUP_ID
        else:
            telegram_id = settings.Telegram.TELEGRAM_MAIN_GROUP_ID

        filename = f"{user.login_name} {settings.SEND_TABLE_NAME}"

        TelegramProcessor.send_message_file.delay(
            user=user,
            admin_user=admin_user,
            company_type=company_type,
            company_name=company_name,
            company_idn=company_idn,
            edo_type=edo_type,
            edo_id=edo_id,
            mark_type=mark_type,
            telegram_id=telegram_id,
            vfn=filename,
            document=table_file,
        )

        flash(message=settings.Messages.SEND_FILE_SUCCESS)
    except Exception as e:
        message = f"{settings.Messages.SEND_FILE_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)


# https://stackoverflow.com/questions/8290397/how-to-split-an-iterable-in-constant-size-chunks
def batch_order(order_list: iter, batch_length=1):
    length = len(order_list)
    for ndx in range(0, length, batch_length):
        yield order_list[ndx:min(ndx + batch_length, length)]

def batch_order_with_rf(order_list: iter, order_list_rf: iter, order_list_norf: iter, batch_length=1):
    for ndx in range(0, len(order_list), batch_length):
        # Батч из общего списка (order_list)
        batch1 = list(filter(lambda x: x is not None, order_list[ndx:min(ndx + batch_length, len(order_list))]))

        # Батчи из подсписков order_list_rf и order_list_norf
        batch2, batch3 = [], []

        for elem in batch1:
            # Проверка принадлежности к подсписку rf
            if elem in order_list_rf:
                batch2.append(elem)
            # Проверка принадлежности к подсписку norf
            elif elem in order_list_norf:
                batch3.append(elem)

        yield batch1, batch2, batch3

def helper_get_clothes_divided_list(order_id: int) -> tuple[list, list, list]:
    old_t_list = Clothes.query.join(ClothesQuantitySize, ClothesQuantitySize.cl_id == Clothes.id).filter(Clothes.order_id == order_id, Clothes.tnved_code.in_(settings.Clothes.OLD_TNVEDS)).order_by(desc(Clothes.id)).all()
    new_t_list = Clothes.query.join(ClothesQuantitySize, ClothesQuantitySize.cl_id == Clothes.id).filter(Clothes.order_id == order_id, Clothes.tnved_code.not_in(settings.Clothes.OLD_TNVEDS)).order_by(desc(Clothes.id)).all()
    return old_t_list + new_t_list, old_t_list, new_t_list


def process_admin_order_num(user: User) -> tuple[Optional[int], Optional[str], Optional[bool], Optional[bool]]:
    if user.role == settings.ORD_USER:
        admin_id = User.query.with_entities(User.id).filter_by(id=user.admin_parent_id).order_by(
            desc(User.id)).first().id
    else:
        admin_id = user.id
        # admin.admin_order_num += 1
    stmt = text(
        """UPDATE public.users SET admin_order_num=admin_order_num + 1 
           WHERE id=:admin_id RETURNING admin_order_num, is_crm, is_at2;""").bindparams(admin_id=admin_id)
    res = db.session.execute(stmt).fetchone()

    db.session.commit()  # make commit to fix order_num
    return (res.admin_order_num, "{admin_id}_{admin_order_num}".format(admin_id=admin_id, admin_order_num=res.admin_order_num), res.is_crm,
            res.is_at2)


def get_process_stage(o_id: int, category: str) -> int:
    row_count, mark_count = get_rows_marks(o_id=o_id, category=category)
    stage_defaults = helper_get_limits()
    min_rows, min_marks = stage_defaults.ap_rows, stage_defaults.ap_marks

    return settings.OrderStage.POOL if row_count <= min_rows and mark_count <= min_marks else settings.OrderStage.NEW


def process_order_start(user: User, category: str, o_id: int, order_idn: str, order_comment: str = "") -> Optional[int]:
    def check_new_tnved_in_list() -> Optional[bool]:
        if category == settings.Clothes.CATEGORY:
            tnveds = list(map(lambda x: True if x.tnved_code not in settings.Clothes.OLD_TNVEDS else False,
                              order.clothes))
            return any(tnveds)

    order = user.orders.filter(Order.category == category, Order.id == o_id, Order.stage == settings.OrderStage.CREATING,
                               ~Order.processed,  ~Order.to_delete).first()

    if order:
        # row_count, mark_count = get_rows_marks(o_id=o_id, category=category)
        #
        # try:
        #     # check for CRM or telegram process type
        #     if tg_flag:
        #         order.processed = True
        #         order.stage = settings.OrderStage.TELEGRAM_PROCESSED
        #         order.closed_at = datetime.now()
        #         new_stat = OrderStat(category=category, company_idn=order.company_idn, company_type=order.company_type,
        #                              company_name=order.company_name, order_idn=order_idn,
        #                              rows_count=row_count, marks_count=mark_count, created_at=order.created_at,
        #                              closed_at=datetime.now(),
        #                              manager_id=user.admin_parent_id if user.admin_parent_id else user.id)
        #         user.orders_stats.append(new_stat)
        #     else:
        #         order.stage = settings.OrderStage.NEW
        #         order.crm_created_at = datetime.now()

        _stage = get_process_stage(o_id=o_id, category=category)
        try:
            if check_new_tnved_in_list():
                order.has_new_tnveds = True
            mark_type = order.mark_type
            order.mark_type = mark_type if mark_type else 'МАРКИРОВКА НЕ УКАЗАНА'
            dt = datetime.now()
            order.stage = _stage  # settings.OrderStage.NEW
            order.crm_created_at = dt
            order.order_idn = order_idn
            order.user_comment = order_comment
            if _stage == settings.OrderStage.POOL:
                create_order_stats(order_info=order)
                order.p_started = dt
            return _stage
        except IntegrityError:
            db.session.rollback()
            flash(message=settings.Messages.PROCESS_ARCHIVE_ERROR, category='error')
            logger.error(settings.Messages.PROCESS_ARCHIVE_ERROR)

    else:
        flash(message=settings.Messages.STRANGE_REQUESTS, category='error')


def create_order_stats(order_info: Order) -> None:
    # no commit

    row_count, mark_count = get_rows_marks(o_id=order_info.id, category=order_info.category)
    new_stat = OrderStat(category=order_info.category, company_idn=order_info.company_idn,
                         company_type=order_info.company_type,
                         company_name=order_info.company_name, order_idn=order_info.order_idn,
                         rows_count=row_count, marks_count=mark_count,
                         created_at=order_info.created_at,
                         crm_created_at=order_info.crm_created_at,
                         manager_id=order_info.manager_id, user_id=order_info.user_id,)
    # closed_at = datetime.now(),
    db.session.add(new_stat)


def process_complete_delete_order(order: Order) -> None:

    try:

        db.session.execute(text(f"DELETE FROM public.orders AS o WHERE o.id={order.id}"))
        db.session.commit()
    except Exception as e:
        logger.error(e)
        db.session.rollback()


def common_process_delete_order(o_id: int, stage: int,) -> Optional[str]:

    order = current_user.orders.with_entities(Order.id, Order.category, Order.company_type,
                                              Order.company_name, Order.created_at, Order.stage)\
                        .filter(Order.id == o_id, Order.stage == stage, ~Order.to_delete).first()
    if order:
        if order.stage not in (settings.OrderStage.CREATING, settings.OrderStage.NEW,
                               settings.OrderStage.CANCELLED, settings.OrderStage.TELEGRAM_PROCESSED, settings.OrderStage.CRM_PROCESSED):
            flash(message=settings.Messages.ORDER_DELETE_STAGE, category='error')
            return settings.Messages.ORDER_DELETE_STAGE

        subcategory = ''
        if order.category == settings.Clothes.CATEGORY:
            subcategory = get_subcategory(order_id=o_id, category=settings.Clothes.CATEGORY)

        try:

            # db.session.execute(text(f"DELETE FROM public.orders AS o WHERE o.id={order.id}"))
            db.session.execute(
                text(f"UPDATE public.orders set to_delete = True  WHERE id=:o_id").bindparams(o_id=order.id))
            db.session.commit()

        except Exception as e:
            db.session.rollback()
            message = f"{settings.Messages.ORDER_DELETE_ERROR} {e}"
            flash(message=message, category='error')
            logger.error(message)

            return settings.Messages.ORDER_DELETE_ERROR

        order_text = f"{order.category if not subcategory else settings.SUB_CATEGORIES_DICT[subcategory]} {order.company_type} {order.company_name}" \
                     f" от {order.created_at.strftime('%Y-%m-%d %H:%M:%S')}"

        flash(message=f"{settings.Messages.ORDER_DELETE_SUCCESS} {order_text}")
        return 'success'
    else:
        flash(message=settings.Messages.CLEAN_EMPTY, category='error')
        return settings.Messages.CLEAN_EMPTY


def process_delete_order_pos(category: str, o_id: int, m_id: int, edit: bool = False,
                             async_type: int = None) -> Optional[str]:
    order = current_user.orders.with_entities(Order.id, Order.category, Order.company_type,
                                              Order.company_name, Order.created_at) \
        .filter(Order.id == o_id, Order.stage == settings.OrderStage.CREATING, ~Order.to_delete).first()
    if not order:
        flash(message=settings.Messages.CLEAN_EMPTY, category='error')
        return settings.Messages.CLEAN_EMPTY
    else:

        try:
            stmt = get_delete_pos_stmts(category=category, m_id=m_id)
            db.session.execute(text(stmt))
            db.session.commit()
            if not edit and not async_type:
                flash(message=f"{settings.Messages.ORDER_DELETE_POS_SUCCESS} ")
            return 'success'
        except Exception as e:
            db.session.rollback()
            message = f"{settings.Messages.ORDER_DELETE_ERROR} {e}"
            flash(message=message, category='error')
            logger.error(message)

            return settings.Messages.ORDER_DELETE_ERROR


def helper_delete_order_pos(o_id: int, m_id: int, category: str, model: db.Model,
                            async_type: int = None) -> Union[tuple, Response]:
    cat_list = model.query.with_entities(model.id).filter_by(order_id=o_id).all()
    subcategory = request.args.get('subcategory', '')
    if not Category.check_subcategory(category=category, subcategory=subcategory):
        return jsonify(
            dict(status='error', message=settings.Messages.STRANGE_REQUESTS + ' нет такой подкатегории'))

    if len(cat_list) > 1:
        if not async_type:
            process_delete_order_pos(category=category, o_id=o_id, m_id=m_id)
        else:
            status = process_delete_order_pos(category=category, o_id=o_id, m_id=m_id, async_type=async_type)
            content = dict(status=status, type='async')
            from utilities.helpers.h_categories import order_table_update
            content.update(order_table_update(user=current_user, o_id=o_id, category=category, jsonify_flag=False))
            return jsonify(content)
    else:

        status = common_process_delete_order(o_id=o_id, stage=settings.OrderStage.CREATING)
        o_id = None
        if async_type:
            content = dict(status=status, type='order_delete',
                           url=url_for(f'{settings.CATEGORIES_DICT.get(category)}.index', subcategory=subcategory))
            return jsonify(content)
    return redirect(url_for(f'{settings.CATEGORIES_DICT.get(category)}.index', o_id=o_id, subcategory=subcategory))


def get_file_extension(filename: str) -> Optional[str]:
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()


def check_file_extension(filename: str, extensions: tuple = settings.ALLOWED_EXTENSIONS) -> bool:
    return get_file_extension(filename=filename) in extensions


def upload_divide_sizes_quantities(value: str) -> tuple:
    data_obj = value.split("(")
    if len(data_obj) != 2:
        return None, None
    sizes = data_obj[0].split("-")

    quantities_raw = data_obj[1]
    quantities = quantities_raw.rstrip(')').split('-')

    return sizes, quantities


def url_encrypt(to_encrypt_data: str) -> str:
    return encryptor.encrypt_url(to_encrypt_data)


def url_decrypt(to_decrypt_data: str) -> str:
    return encryptor.decrypt_url(to_decrypt_data)


def check_email(email: str):
    emails = User.query.filter_by(email=email).all()
    if len(emails) > 1:
        return False
    else:
        return True


def check_user_messages(user_info: User, message: str) -> bool:
    user_messages = user_info.em_messages

    today_messages = []

    if user_messages:
        today_mid = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        today_messages = user_messages.filter(EmailMessage.created_at >= today_mid).all()
    if len(today_messages) < settings.EMAIL_USER_SEND_LIMIT:

        try:
            email_message = EmailMessage(message=message)
            user_info.em_messages.append(email_message)
            db.session.add(user_info)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            message = f"{settings.Messages.GET_RESTORE_LINK_COMMON_ERROR} {e}"
            flash(message=message, category='error')
            logger.error(message)

            return False
    else:
        flash(message=settings.Messages.EMAIL_SEND_LIMIT_ERROR, category='error')
        return False


def check_custom_tnved(order_list: list) -> bool:
    check = any(map(lambda x: True if x.tnved_code not in settings.Tnved.BIG_TNVED_LIST else False,
                    order_list))
    return check


def user_activated(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.is_authenticated :
            if current_user.status is True:
                if func.__name__ == 'send_table':
                    if current_user.is_send_excel:
                        return func(*args, **kwargs)
                    else:
                        flash(message=f"{settings.Messages.NO_SUCH_USER_SERVICE}", category='error')
                        return redirect(url_for('main.enter'))
                return func(*args, **kwargs)
            else:
                name = current_user.login_name
                flash(message=Markup(f"{settings.Messages.USER_NOT_ACTIVATED_1}"
                                 f"\"<span class=\"text-danger\"><b>{name}</b></span>\"."
                                 f"{settings.Messages.USER_NOT_ACTIVATED_2}"), category='error')
        else:
            flash(message=settings.Messages.AUTH_OR_SIGNUP, category='error')

            return redirect(url_for('auth.login'))
    return wrapper


def manager_forbidden(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.role not in [settings.MANAGER_USER, settings.SUPER_MANAGER]:

            return func(*args, **kwargs)
        else:
            flash(message=settings.Messages.CRM_MANAGER_USER_FORBIDDEN, category='error')
            return redirect(url_for('crm_d.managers'))
    return wrapper


def user_crm(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.role == settings.SUPER_MANAGER:
            return func(*args, **kwargs)
        elif check_user_crm(user=current_user):
            return func(*args, **kwargs)
        else:
            flash(message=settings.Messages.STRANGE_REQUESTS, category='error')
            return redirect(url_for('main.enter'))
    return wrapper


def check_user_crm(user: User) -> bool:
    if user.role == settings.ADMIN_USER and user.is_crm:
        return True
    elif user.role == settings.ORD_USER:
        admin_id = user.admin_parent_id
        order_notification, admin_name, crm = helper_get_order_notification(admin_id=admin_id if admin_id else user.id)
        return crm
    else:
        return False


def get_category_orders(user: User, category: str, o_id: int, stage: int) -> tuple[Optional[Order],
                                                                                   Optional[QueryPagination]]:
    order = helper_get_order(user=user, category=category, o_id=o_id, stage=stage)

    if not order:
        order_list = None
        return order, order_list
    match category:
        case settings.Shoes.CATEGORY:
            sort_model = helper_get_sort_model(category=category)
            order_list = Shoe.query.filter_by(order_id=o_id).order_by(sort_model).all()
        case settings.Clothes.CATEGORY:
            sort_model = helper_get_sort_model(category=category)
            order_list = Clothes.query.filter_by(order_id=o_id).order_by(sort_model).all()
        case settings.Socks.CATEGORY:
            sort_model = helper_get_sort_model(category=category)
            order_list = Socks.query.filter_by(order_id=o_id).order_by(sort_model).all()
        case settings.Linen.CATEGORY:
            sort_model = helper_get_sort_model(category=category)
            order_list = Linen.query.filter_by(order_id=o_id).order_by(sort_model).all()
        case settings.Parfum.CATEGORY:
            sort_model = helper_get_sort_model(category=category)
            order_list = Parfum.query.filter_by(order_id=o_id).order_by(sort_model).all()
        case _:
            order, order_list = None, None
    return order, order_list


def helper_get_sort_model(category: str) -> db.Model:
    sort_type_request = request.args.get('sort_type', 'id', type=str)
    sort_order_request_raw = request.args.get('sort_order', 'false', type=str)
    sort_order_request = True if sort_order_request_raw == 'true' else False

    sort_dict = helper_get_cat_models_sort_dict(category=category)

    # create default models for quering if request is incorrect or empty
    models_default: dict = {"обувь": Shoe.id,
                            "одежда": Clothes.id,
                            "белье": Linen.id,
                            "парфюм": Parfum.id, }
    sort_model = sort_dict.get(sort_type_request, models_default.get(category)) if sort_order_request else desc(
        sort_dict.get(sort_type_request, models_default.get(category)))

    return sort_model


def helper_paginate_data(data: list, key_page: str = 'page', href: str = None,
                         per_page: int = settings.PAGINATION_PER_PAGE, anchor: str = 'orders_table',
                         css_framework: str = 'semantic') -> tuple[int, int, int,  Pagination, list]:
    page = request.args.get(key_page, 1, type=int)

    offset = per_page * (page - 1)

    pagination = Pagination(page=page, page_parameter=key_page, per_page=per_page, offset=offset, total=len(data),
                            search=False, href=href,
                            record_name='order_list', anchor=anchor, alignment='right', css_framework=css_framework)
    order_list = data[offset:offset + per_page]

    return page, per_page, offset, pagination, order_list


def helper_get_order(user: User, category: str, o_id: int, stage: int) -> Optional[Order]:

    if not o_id:
        order = user.orders.filter_by(category=category, stage=stage).filter(~Order.to_delete)\
            .with_entities(Order.company_idn,
                           Order.company_type,
                           Order.company_name,
                           Order.edo_type, Order.edo_id,
                           Order.mark_type, Order.stage).first()
    else:
        order = user.orders.filter_by(category=category, id=o_id, stage=stage).filter(~Order.to_delete)\
            .with_entities(Order.company_idn, Order.company_type, Order.company_name, Order.edo_type, Order.edo_id,
                           Order.mark_type, Order.stage).first()

    return order


def h_helper_get_clothes_p_orders(user: User, processed: bool, subcategory: str = None) -> list:
    subcategory_filter = ClothesSubcategories.common.value if not subcategory else subcategory

    ClothesAlias = aliased(Clothes)

    base_query = user.orders.join(ClothesAlias).filter(ClothesAlias.subcategory == subcategory_filter)

    if processed:
        base_query = base_query.filter(Order.category == settings.Clothes.CATEGORY_PROCESS, Order.processed == True)
    else:
        base_query = base_query.filter(
            Order.category == settings.Clothes.CATEGORY,
            Order.processed == False,
            Order.stage == settings.OrderStage.CREATING
        )

    base_query = base_query.filter(~Order.to_delete)

    return base_query.with_entities(
        Order.id,
        func.array_agg(Order.order_idn).label("order_idns"),
        Order.category,
        Order.company_type,
        Order.company_name,
        Order.company_idn,
        Order.to_delete,
        Order.created_at,
        Order.stage,
        Order.closed_at,
        func.array_agg(ClothesAlias.subcategory).label("subcategories")
    ).group_by(
        Order.id, Order.category, Order.company_type, Order.company_name, Order.company_idn,
        Order.to_delete, Order.created_at, Order.stage, Order.closed_at
    ).order_by(desc(Order.created_at)).all()


def helper_get_p_order(user: User, category: str, processed: bool):
    match processed:
        case True:
            return (user.orders.filter_by(category=category, processed=True).filter(~Order.to_delete)
                        .with_entities(Order.id, Order.order_idn, Order.category, Order.company_type,
                                       Order.company_name, Order.company_idn, Order.to_delete,
                                       Order.created_at, Order.stage, Order.closed_at)
                        .order_by(desc(Order.created_at)).all())
        case False:
            return user.orders.filter_by(category=category, processed=False,
                                         stage=settings.OrderStage.CREATING).filter(~Order.to_delete) \
                        .with_entities(Order.id, Order.company_type,
                                       Order.company_name, Order.to_delete, Order.created_at) \
                        .order_by(desc(Order.created_at)).all()


# def get_subcategory(order_id: int, category: str) -> str | None:
#     try:
#         match category:
#             case settings.Clothes.CATEGORY:
#                 return Clothes.query.filter(
#                         Clothes.order_id == order_id).first().subcategory
#             case _:
#                 return None
#     except Exception:
#         logger.exception(f'Ошибка подкатегории {order_id=}, {category=}')
#         return None
#

def get_category_p_orders(user: User, category: str, processed: bool, subcategory: str = None) -> list:
    match category:
        case settings.Clothes.CATEGORY:
            return h_helper_get_clothes_p_orders(user=user, processed=processed, subcategory=subcategory)
        case _:
            return helper_get_p_order(user=user, category=category, processed=processed)


def get_category_archive_all(user: User) -> list:

    return user.orders.filter(~Order.to_delete). \
               with_entities(Order.id, Order.stage, Order.order_idn, Order.category, Order.company_type,
                             Order.company_name, Order.company_idn, Order.to_delete, Order.processed,
                             Order.created_at, Order.stage, Order.closed_at).order_by(desc(Order.created_at)).all()


def helper_category_archive_orders(all_orders: list) -> tuple:
    shoe_orders = list(filter(lambda x: x.category == settings.Shoes.CATEGORY and x.processed == True, all_orders))

    clothes_orders = list(filter(lambda x: x.category == settings.Clothes.CATEGORY and x.processed == True, all_orders))

    linen_orders = list(filter(lambda x: x.category == settings.Linen.CATEGORY and x.processed == True, all_orders))

    parfum_orders = list(filter(lambda x: x.category == settings.Parfum.CATEGORY and x.processed == True, all_orders))

    return shoe_orders, clothes_orders, linen_orders, parfum_orders


def helper_category_archive_orders_crm(all_orders: list) -> tuple:
    shoe_co = list(
        filter(lambda x: x.category == settings.Shoes.CATEGORY and
                         (settings.OrderStage.CREATING < x.stage < settings.OrderStage.TELEGRAM_PROCESSED), all_orders))
    clothes_co = list(
        filter(lambda x: x.category == settings.Clothes.CATEGORY and
                         (settings.OrderStage.CREATING < x.stage < settings.OrderStage.TELEGRAM_PROCESSED), all_orders))

    linen_co = list(
        filter(lambda x: x.category == settings.Linen.CATEGORY and
                         (settings.OrderStage.CREATING < x.stage < settings.OrderStage.TELEGRAM_PROCESSED), all_orders))

    parfum_co = list(
        filter(lambda x: x.category == settings.Parfum.CATEGORY and
                         (settings.OrderStage.CREATING < x.stage < settings.OrderStage.TELEGRAM_PROCESSED), all_orders))
    return shoe_co, clothes_co, linen_co, parfum_co


def helper_get_cat_models_sort_dict(category: str) -> Optional[dict]:

    match category:
        case settings.Shoes.CATEGORY:
            cat_models_dict: dict = {"id": Shoe.id,
                                     "trademark": Shoe.trademark,
                                     }
        case settings.Clothes.CATEGORY:
            cat_models_dict: dict = {"id": Clothes.id,
                                     "trademark": Clothes.trademark,
                                     }
        case settings.Linen.CATEGORY:
            cat_models_dict: dict = {"id": Linen.id,
                                     "trademark": Linen.trademark,
                                     }
        case settings.Parfum.CATEGORY:
            cat_models_dict: dict = {"id": Parfum.id,
                                     "trademark": Parfum.trademark,
                                     }
        case settings.Socks.CATEGORY:
            cat_models_dict: dict = {"id": Socks.id,
                                     "trademark": Socks.trademark,
                                     }
    return cat_models_dict


def helper_process_category_order(user: User, order: Order, category: str, order_comment: str) -> Response:
    from .download import orders_process_send_order
    _category_name = settings.CATEGORIES_DICT.get(category)
    if not order:
        flash(message=settings.Messages.EMPTY_ORDER, category='error')
        return redirect(url_for(f'{_category_name}.index'))
    o_id = order.id

    # check for company_idn exception
    company_idn = order.company_idn
    if company_idn in settings.ExceptionOrders.COMPANIES_IDNS:
        flash(message=settings.ExceptionOrders.COMPANY_IDN_ERROR.format(company_idn=company_idn), category='error')
        return redirect(url_for(f'{_category_name}.index', o_id=o_id))

    status_balance, total_order_price, agent_at2, message_balance = helper_check_uoabm(user=current_user, o_id=o_id)
    if status_balance == 0:
        flash(message=Markup(message_balance), category='error')
        return redirect(url_for(f'{_category_name}.index'))

    try:

        order_num, order_idn, is_crm, is_at2 = process_admin_order_num(user=user)

        if not order_idn:
            db.session.rollback()
            flash(message=f"{settings.Messages.PROCESS_ERROR}: Ошибка БД", category='error')
            return redirect(url_for(f'{_category_name}.index'))

        _stage = process_order_start(user=user, category=category, o_id=o_id, order_idn=order_idn, order_comment=order_comment)
        if not _stage:
            db.session.rollback()
            flash(message=f"{settings.Messages.PROCESS_ERROR}: Такого заказа нет в бд", category='error')
            return redirect(url_for(f'{_category_name}.index'))

        if is_at2:
            sent_flag = orders_process_send_order(
                o_id=o_id, user=user,
                order_comment=order_comment,
                order_idn=order_idn,
                flag_046=False,
            )

            flash(message=Markup(f"{settings.Messages.PROCESS_SUCCESS}<b>{order_idn}</b>!")) if sent_flag else None
        else:
            flash(message=Markup(f"{settings.Messages.PROCESS_SUCCESS}<b>{order_idn}</b>!"))
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.ORDER_ADD_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)
    else:
        # notify client
        helper_send_user_order_tg_notify(user_id=user.id, order_idn=order_idn, order_stage=_stage)

        # notify markineris common group
        MarkinerisInform.send_message_tg.delay(order_idn=order_idn)
    return redirect(url_for(f'{_category_name}.index'))


def helper_get_order_notification(admin_id: int) -> tuple:
    res = db.session.execute(text("""
                                                SELECT u.order_notification as order_notification,
                                                       u.login_name as admin_name,
                                                       u.is_crm as crm
                                                FROM public.users u
                                                WHERE u.id=:admin_id;
                                                """).bindparams(admin_id=admin_id)).fetchone()

    return (res.order_notification, res.admin_name, res.crm, ) if res else (settings.AGENT_DEFAULT_NOTE, None, None, )


def helper_update_order_note(on: str, u_id: int) -> bool:
    try:
        db.session.execute(text("""
                                    UPDATE public.users 
                                    SET order_notification =:on
                                    WHERE public.users.id= :u_id;
                                    """).bindparams(on=on, u_id=u_id))
        db.session.commit()
        return True
    except Exception as e:
        logger.error(e)
        db.session.rollback()
        return False


def helper_get_user_balance(u_id: int) -> tuple[int, int]:
    try:
        res = db.session.execute(text("""SELECT u.balance,
                                            u.pending_balance_rf
                                          FROM public.users u
                                          WHERE u.id=:u_id LIMIT 1;
                                          """).bindparams(u_id=u_id)).fetchone()
        return res.balance, res.pending_balance_rf

    except Exception as e:
        logger.error(f"got an error while getting user_balance: {e}")
        return 0, 0


def helper_get_server_balance() -> tuple[int, int, int, int, int]:
    serv_res = db.session.execute(text("""SELECT sp.balance as balance,
                                             sp.pending_balance_rf as pending_balance_rf
                                      FROM public.server_params sp;
                                      """)).fetchone()
    if not serv_res:
        try:
            serv_res = ServerParam()
            db.session.add(serv_res)
            db.session.commit()
        except Exception as e:
            logger.error(f"{settings.Messages.SP_UPDATE_ERROR} {e}")

    summ_at_1 = db.session.execute(text("""SELECT SUM(u.balance) AS at_1_summ FROM public.users u WHERE u.role != 'ordinary_user' and is_at2!=True""")).fetchone()
    summ_at_2 = db.session.execute(text("""SELECT SUM(u.balance) AS at_2_summ FROM public.users u WHERE u.role != 'ordinary_user' and is_at2=True""")).fetchone()
    summ_client = db.session.execute(text(
        """SELECT SUM(u.balance) AS client_summ FROM public.users u WHERE u.role = 'ordinary_user';""")).fetchone()
    return (serv_res.balance, serv_res.pending_balance_rf,
            summ_at_1.at_1_summ if summ_at_1 else 0, summ_at_2.at_2_summ if summ_at_2 else 0,
            summ_client.client_summ if summ_client else 0)


@dataclasses.dataclass
class TransactionFilters:
    status: int
    date_from: datetime
    date_to: datetime
    operation_type: int | None = None
    service_account: int | None = None
    transaction_type: str | None = None
    model_conditions: tuple | None = None
    model_order_type: UnaryExpression | None = None
    link_filters: str | None = None


def helper_get_filters_transactions(
        tr_status: int | None = None,
        transaction_type: str | None = None,
        operation_type: str | None = None,
        report: bool = False,
        current_user_id: int | None = None,
) -> TransactionFilters:
    """
        returns tuple of params with  filter conditions, link string and model conditions and order type
    :param tr_status:
    :param transaction_type:
    :param operation_type:
    :param report:
    :param current_user_id:
    :return:
    """
    if report:
        date_from_raw = request.form.get('date_from', '', type=str)
        date_to_raw = request.form.get('date_to', '', type=str)
        tr_status = request.form.get('tr_status', 0, type=int) if not tr_status else tr_status
        transaction_type = request.form.get('transaction_type', None, type=str) if not transaction_type else transaction_type
        operation_type = request.form.get('operation_type', None, type=int) if not operation_type else operation_type
        service_account = request.form.get('service_account', None, type=int)
        sort_type = request.form.get('sort_type', 0, type=int)
        amount = request.form.get('amount', 0, type=int)
        agent_id = request.form.get('agent_id', None, type=int)
    else:
        date_from_raw = request.args.get('date_from', '', type=str)
        date_to_raw = request.args.get('date_to', '', type=str)
        tr_status = request.args.get('tr_status', 0, type=int) if not tr_status else tr_status
        transaction_type = request.args.get('transaction_type', None, type=str) if not transaction_type else transaction_type
        operation_type = request.args.get('operation_type', None, type=int) if not operation_type else operation_type
        service_account = request.args.get('service_account', None, type=int)
        sort_type = request.args.get('sort_type', 0, type=int)
        amount = request.args.get('amount', 0, type=int)
        agent_id = request.args.get('agent_id', None, type=int)

    if current_user_id:
        agent_id = current_user_id

    link_filters = (
        f'&tr_status={tr_status}'
        f'&transaction_type={transaction_type}'
        f'&operation_type={operation_type}'
        f'&service_account={service_account}'
        f'&date_from={date_from_raw}'
        f'&date_to={date_to_raw}'
        f'&agent_id={agent_id}&'
    )

    model_conditions_list_raw = (
        UserTransaction.sa_id == service_account if service_account else None,
        UserTransaction.status == tr_status if tr_status in settings.Transactions.TRANSACTIONS.keys() else None,
        or_(User.id == agent_id, User.admin_parent_id == agent_id) if agent_id else None,
        UserTransaction.type == bool(operation_type) if operation_type is not None else None,
        UserTransaction.transaction_type == transaction_type if transaction_type in [item.value for item in TransactionTypes] else None,
    )

    date_to = datetime.strptime(date_to_raw, '%d.%m.%Y') if date_to_raw else datetime.now()
    date_from = datetime.strptime(date_from_raw, '%d.%m.%Y') if date_from_raw \
        else date_to - timedelta(days=settings.Transactions.DEFAULT_DAYS_RANGE)

    if (date_from and date_to) and (date_to >= date_from):
        # increment + 1 day because <= not working normally
        date_range_conditions = UserTransaction.created_at >= date_from, UserTransaction.created_at <= date_to + timedelta(
            days=1)
    elif (date_from and date_to) and (date_to < date_from):
        date_from, date_to = date_to, date_from
        date_range_conditions = UserTransaction.created_at >= date_from, UserTransaction.created_at <= date_to + timedelta(
            days=1)
    else:
        date_range_conditions = tuple()

    # if amount > 0:
    amount_conditions = (UserTransaction.amount == amount,) if amount else (None,)
    model_conditions = tuple(
        filter(lambda x: x is not None, model_conditions_list_raw + date_range_conditions + amount_conditions))
    model_order_type = desc(UserTransaction.created_at) if (sort_type == 0 or not sort_type) \
        else asc(UserTransaction.created_at)

    return TransactionFilters(
        status=tr_status,
        transaction_type=transaction_type,
        operation_type=operation_type,
        service_account=service_account,
        date_from=date_from,
        date_to=date_to,
        link_filters=link_filters,
        model_conditions=model_conditions,
        model_order_type=model_order_type,
    )


def helper_get_filter_users(excel_report: bool = False) -> tuple:
    """
        returns tuple of params with  filter conditions, link string and order type
    :param excel_report
    :return:
    """
    if not excel_report:
        date_quantity_raw = request.args.get('date_quantity', '', type=str)
        date_type_raw = request.args.get('date_type', '', type=str)
        sort_type = request.args.get('sort_type', 1, type=int)
    else:
        date_quantity_raw = request.form.get('date_quantity', '', type=str)
        date_type_raw = request.form.get('date_type', '', type=str)
        sort_type = request.form.get('sort_type', 1, type=int)

    link_filters = f'date_quantity={date_quantity_raw}&date_type={date_type_raw}&'

    date_quantity = int(date_quantity_raw) if date_quantity_raw else settings.Users.DEFAULT_DAYS_RANGE
    date_type = date_type_raw if date_type_raw and date_type_raw in settings.Users.FILTER_DATE_TYPES \
        else settings.Users.FILTER_DATE_DAYS

    return date_quantity, date_type, link_filters, sort_type


def helper_get_filter_fin_order_report(report: bool = False):
    default_day_to = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')
    default_day_from = (datetime.today() - timedelta(days=settings.ORDERS_REPORT_TIMEDELTA)).strftime('%Y-%m-%d')
    if report:
        url_date_from = request.form.get('date_from', '', type=str)
        url_date_to = request.form.get('date_to', '', type=str)
        sort_type = request.form.get('sort_type', 'desc', str)
        order_type = (settings.OrderStage.SENT, settings.OrderStage.CRM_PROCESSED) if request.form.get('order_type', 'sent', str) == 'sent' else (settings.OrderStage.CANCELLED,)
        payment_status = request.form.get('payment_status', 'pay_in_full', str)

    else:
        url_date_from = request.args.get('date_from', '', type=str)
        url_date_to = request.args.get('date_to', '',  type=str)

        sort_type = request.args.get('sort_type', 'desc', str)
        order_type = (settings.OrderStage.SENT, settings.OrderStage.CRM_PROCESSED) if request.args.get('order_type', 'sent', str) == 'sent' else (settings.OrderStage.CANCELLED,)
        payment_status = request.args.get('payment_status', 'pay_in_full', str)

    date_from = datetime.strptime(url_date_from, '%d.%m.%Y').strftime('%Y-%m-%d') if url_date_from else default_day_to
    date_to = (datetime.strptime(url_date_to, '%d.%m.%Y') + timedelta(days=1)).strftime(
        '%Y-%m-%d') if url_date_to else default_day_from
    if payment_status == 'pay_in_full':
        payment_status = (True,)
    elif payment_status == 'waiting_for_payment':
        payment_status = (False,)
    else:
        payment_status = (True, False,)

    sort_type = 'desc' if sort_type.lower() == 'desc' else 'asc'

    return date_from, date_to, sort_type, order_type, payment_status


def helper_get_stmt_for_fin_order_report(
        date_from: str = (datetime.today() - timedelta(days=settings.ORDERS_REPORT_TIMEDELTA)).strftime('%Y-%m-%d'),
        date_to: str = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d'),
        order_type: tuple[int] = (settings.OrderStage.SENT, settings.OrderStage.CRM_PROCESSED),
        payment_status: tuple[bool] = (True, ),
        sort_type: str = 'DESC'
) -> TextClause:
    sort_type = 'desc' if sort_type.lower() == 'desc' else 'asc'
    if order_type == (9,):
        # cancel order
        stmt = text(f"""
                SELECT 
                o.cc_created as handle_date,
                o.order_idn as order_idn,
                o.company_type ||' ' || o.company_name || ' '|| o.company_idn as company,
                cli.phone as cli_phone_number,
	            CASE WHEN MAX(agnt.login_name) IS NOT NULL THEN MAX(agnt.login_name) ELSE cli.login_name end as agent_login,
                {SQLQueryCategoriesAll.get_stmt(field='marks_count')} as pos_count,
                {SQLQueryCategoriesAll.get_stmt(field='rows_count')} as rows_count,
                o.category as category,
                utr.op_cost as op_cost,
                utr.op_cost*{SQLQueryCategoriesAll.get_stmt(field='marks_count')} as amount
            FROM public.orders o
                {SQLQueryCategoriesAll.get_joins()} 
                LEFT JOIN public.user_transactions utr ON o.transaction_id = utr.id
                JOIN public.users cli on cli.id = o.user_id
 	            LEFT JOIN public.users agnt on cli.admin_parent_id = agnt.id
                WHERE (o.cc_created >= :date_from AND o.cc_created < :date_to)  AND o.stage in :order_type
                GROUP BY o.id, o.order_idn, utr.op_cost, utr.amount , o.cc_created, cli.phone, agnt.login_name, cli.login_name
                ORDER BY o.cc_created {sort_type};

            """).bindparams(date_from=date_from, date_to=date_to, order_type=order_type,)
    else:
        stmt = text(f"""
                SELECT 
                o.sent_at as handle_date,
                o.order_idn as order_idn,
                o.company_type ||' ' || o.company_name || ' '|| o.company_idn as company,
                cli.phone as cli_phone_number,
	            CASE WHEN MAX(agnt.login_name) IS NOT NULL THEN MAX(agnt.login_name) ELSE cli.login_name end as agent_login,
                {SQLQueryCategoriesAll.get_stmt(field='marks_count')} as pos_count,
                {SQLQueryCategoriesAll.get_stmt(field='rows_count')} as rows_count,
                o.category as category,
                utr.op_cost as op_cost,
                utr.op_cost*{SQLQueryCategoriesAll.get_stmt(field='marks_count')} as amount
            FROM public.orders o
                {SQLQueryCategoriesAll.get_joins()} 
                LEFT JOIN public.user_transactions utr ON o.transaction_id = utr.id
                JOIN public.users cli on cli.id = o.user_id
 	            LEFT JOIN public.users agnt on cli.admin_parent_id = agnt.id
                WHERE o.payment in :payment_status AND (o.sent_at >= :date_from AND o.sent_at  < :date_to)  AND o.stage in :order_type
                GROUP BY o.id, o.order_idn, utr.op_cost, utr.amount , o.sent_at, cli.phone, agnt.login_name, cli.login_name
                ORDER BY o.sent_at {sort_type};

            """).bindparams(date_from=date_from, date_to=date_to, order_type=order_type, payment_status=payment_status)
    return stmt


def helper_isolated_session(query: str, return_flag: bool = True) -> tuple | bool:

    plain_engine = create_engine(settings.SQL_DATABASE_URL)

    with Session(bind=plain_engine) as session:
        session.connection(execution_options={"isolation_level": "SERIALIZABLE"})
        try:
            if return_flag:
                res = session.execute(text(query)).fetchone()

                session.commit()

                del plain_engine
                return res
            else:
                session.execute(text(query))
                session.commit()

                del plain_engine
                return True

        except Exception as e:
            logger.error(e)
            session.rollback()
            del plain_engine
            return False


def helper_get_current_sa() -> ServiceAccount:

    cur_account = db.session.execute(text(""" SELECT * from public.service_accounts sa
                                         WHERE sa.id =(SELECT sa.id FROM public.service_accounts sa WHERE sa.sa_type=(SELECT sp.account_type FROM public.server_params sp ORDER BY ID LIMIT 1)
                                          AND sa.current_use=True AND sa.is_active=True
                                         ORDER BY id LIMIT 1 );""")).fetchone()
    if not cur_account:

        # creating new session because sqlachemy orm db session makes additional current user query
        cur_account = helper_isolated_session(query=""" UPDATE public.service_accounts
                                         SET current_use=True
                                         WHERE id =(SELECT sa.id FROM public.service_accounts sa WHERE sa.sa_type=(SELECT sp.account_type FROM public.server_params sp ORDER BY ID LIMIT 1) AND sa.is_active=True
                                         ORDER BY id ASC LIMIT 1 ) RETURNING *;""")
    return cur_account


def h_choose_sa_id(cur_sa: ServiceAccount, cur_sa_ids_list: list[ServiceAccount.id]) -> int:
    next_sa_list = list(filter(lambda x: x != cur_sa.id, cur_sa_ids_list))
    if cur_sa.id == cur_sa_ids_list[-1]:
        return next_sa_list[0]
    else:
        return list(filter(lambda x: x > cur_sa.id, next_sa_list))[0]


def helper_get_stmt_for_fin_promo_history(
        date_from: str = (datetime.today() - timedelta(settings.PROMO_HISTORY_TIMEDELTA)).strftime('%Y-%m-%d'),
        date_to: str = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d'),
        promo_code: Optional[str] = None,
        sort_type: str = 'DESC'
) -> TextClause:
    sort_type = 'desc' if sort_type.lower() == 'desc' else 'asc'
    stmt = text(f"""select
                        usr_promo.activated_at as activate_date,
                        cli.email as user_email,
                        COALESCE(agent.login_name, cli.login_name) as agent_login,
                        promo.code as code,
                        promo.value as promo_value
                        from
                            public.users cli
                            left join public.users agent on agent.id = cli.admin_parent_id
                            join public.users_promos usr_promo on usr_promo.user_id = cli.id
                            join public.promos  promo on promo.id = usr_promo.promo_id
                        where
                            activated_at >= :date_from
                            and activated_at < :date_to
                        order by activated_at {sort_type}
                        """
                ).bindparams(date_from=date_from, date_to=date_to) if not promo_code else text(f"""select
                        usr_promo.activated_at as activate_date,
                        cli.email as user_email,
                        COALESCE(agent.login_name, cli.login_name) as agent_login,
                        promo.code as code,
                        promo.value as promo_value
                        from
                            public.users cli
                            left join public.users agent on agent.id = cli.admin_parent_id
                            join public.users_promos usr_promo on usr_promo.user_id = cli.id
                            join public.promos  promo on promo.id = usr_promo.promo_id
                        where
                            activated_at >= :date_from
                            and activated_at < :date_to
                            and promo.code = :promo_code
                        order by activated_at {sort_type}
                        """).bindparams(
        date_from=date_from, date_to=date_to, promo_code=promo_code)
    return stmt


def helper_get_filter_fin_promo_history(report: bool = False) -> tuple[str, str, str, str]:
    default_day_to = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')
    default_day_from = (datetime.today() - timedelta(days=settings.PROMO_HISTORY_TIMEDELTA)).strftime('%Y-%m-%d')
    if report:
        url_date_from = request.form.get('date_from', '', type=str)
        url_date_to = request.form.get('date_to', '', type=str)
        sort_type = request.form.get('sort_type', 'desc', str)
        promo_code = request.form.get('promo_code', '', str)

    else:
        url_date_from = request.args.get('date_from', '', type=str)
        url_date_to = request.args.get('date_to', '', type=str)
        sort_type = request.args.get('sort_type', 'desc', str)
        promo_code = request.args.get('promo_code', '', str)

    date_from = datetime.strptime(url_date_from, '%d.%m.%Y').strftime('%Y-%m-%d') if url_date_from else default_day_to
    date_to = (datetime.strptime(url_date_to, '%d.%m.%Y') + timedelta(days=1)).strftime(
        '%Y-%m-%d') if url_date_to else default_day_from
    sort_type = 'desc' if sort_type.lower() == 'desc' else 'asc'
    return date_from, date_to, promo_code, sort_type


def helper_get_stmt_for_fin_bonus_history(
        date_from: str = (datetime.today() - timedelta(settings.PROMO_HISTORY_TIMEDELTA)).strftime('%Y-%m-%d'),
        date_to: str = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d'),
        bonus_code: Optional[str] = None,
        sort_type: str = 'DESC'
) -> TextClause:
    stmt = text(f"""select
                        usr_bonus.activated_at as activate_date,
                        cli.email as user_email,
                        COALESCE(agent.login_name, cli.login_name) as agent_login,
                        bonus.code as code,
                        bonus.value as bonus_value
                        from
                            public.users cli
                            left join public.users agent on agent.id = cli.admin_parent_id
                            join public.users_bonus_codes usr_bonus on usr_bonus.user_id = cli.id
                            join public.bonus_codes bonus on bonus.id = usr_bonus.promo_id
                        where
                            activated_at >= :date_from
                            and activated_at < :date_to
                        order by activated_at {sort_type}
                        """
                ).bindparams(date_from=date_from, date_to=date_to) if not bonus_code else text(f"""select
                        usr_bonus.activated_at as activate_date,
                        cli.email as user_email,
                        COALESCE(agent.login_name, cli.login_name) as agent_login,
                        bonus.code as code,
                        bonus.value as promo_value
                        from
                            public.users cli
                            left join public.users agent on agent.id = cli.admin_parent_id
                            join public.users_bonus_codes usr_bonus on usr_bonus.user_id = cli.id
                            join public.bonus_codes bonus on bonus.id = usr_bonus.promo_id
                        where
                            activated_at >= :date_from
                            and activated_at < :date_to
                            and bonus.code = :bonus_code
                        order by activated_at {sort_type}
                        """).bindparams(
        date_from=date_from, date_to=date_to, bonus_code=bonus_code)
    return stmt


def helper_get_filter_fin_bonus_history(report: bool = False) -> tuple[str, str, str, str]:
    default_day_to = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')
    default_day_from = (datetime.today() - timedelta(days=settings.PROMO_HISTORY_TIMEDELTA)).strftime('%Y-%m-%d')
    if report:
        url_date_from = request.form.get('date_from', '', type=str)
        url_date_to = request.form.get('date_to', '', type=str)
        sort_type = request.form.get('sort_type', 'desc', str)
        bonus_code = request.form.get('bonus_code', '', str)

    else:
        url_date_from = request.args.get('date_from', '', type=str)
        url_date_to = request.args.get('date_to', '', type=str)
        sort_type = request.args.get('sort_type', 'desc', str)
        bonus_code = request.args.get('bonus_code', '', str)

    date_from = datetime.strptime(url_date_from, '%d.%m.%Y').strftime('%Y-%m-%d') if url_date_from else default_day_to
    date_to = (datetime.strptime(url_date_to, '%d.%m.%Y') + timedelta(days=1)).strftime(
        '%Y-%m-%d') if url_date_to else default_day_from
    sort_type = 'desc' if sort_type.lower() == 'desc' else 'asc'

    return date_from, date_to, bonus_code, sort_type


def helper_process_sa(sa_id: int) -> bool:
    try:
        cur_accounts = [a for a in db.session.execute(text(""" SELECT * from public.service_accounts sa
                                                  WHERE sa.sa_type=(SELECT sp.account_type FROM public.server_params sp ORDER BY ID LIMIT 1)
                                                    AND sa.is_active=True
                                                  ORDER BY sa.id;""")).fetchall()]

        if cur_accounts:
            cur_accounts_ids = list(map(lambda x: x.id, cur_accounts))
            if sa_id not in cur_accounts_ids:
                logger.error('Странные запросы. Такого аккаунта нет')
                return False
            if len(cur_accounts) > 1:
                current_processing_sa = list(filter(lambda x: x.current_use == True, cur_accounts))[0]
                if current_processing_sa.summ_transfer > settings.ServiceAccounts.SUMM_LIMIT:
                    choosed_next_sa_id = h_choose_sa_id(cur_sa=current_processing_sa, cur_sa_ids_list=cur_accounts_ids)

                    db.session.execute(text("""UPDATE public.service_accounts SET current_use=False, summ_transfer=0 WHERE id = :sa_id;
                                               UPDATE public.service_accounts SET current_use=True WHERE id = :choosed_next_sa_id; """).bindparams(
                        sa_id=sa_id, choosed_next_sa_id=choosed_next_sa_id
                    ))
                    db.session.commit()
            return True

        else:
            return False
    except Exception as e:
        db.session.rollback()
        logger.error(f"Проверка счета сервиса и обновление не произведена возникла ошибка {e}")
        return False


def helper_check_promo(user: User, promo_code: str) -> tuple[bool, int, str]:
    all_promos_raw = (Promo.query.with_entities(Promo.id, Promo.code, Promo.value)
                      .filter(not_(Promo.is_archived.is_(True))))

    all_promos = all_promos_raw.all()
    all_promos_codes = list(map(lambda x: x.code, all_promos))
    if promo_code not in all_promos_codes:
        return False, 0, settings.Messages.PROMO_NE_ERROR
    user_promo_codes = list(map(lambda x: x.code, user.promos))
    if promo_code in user_promo_codes:
        return False, 0, settings.Messages.PROMO_USED_ERROR
    else:

        promo_append = all_promos_raw.filter(Promo.code == promo_code).first()
        res = helper_isolated_session(
            query="INSERT into public.users_promos VALUES({user_id}, {promo_append_id}, '{date_val}');"
            .format(user_id=user.id, promo_append_id=promo_append.id, date_val=datetime.now()),
            return_flag=False)
        if not res:
            logger.error(f"{settings.Messages.PROMO_ADD_USER_ERROR}")
            return False, 0, settings.Messages.PROMO_ADD_USER_ERROR
        return True, promo_append.value, ''


def helper_get_promo_on_cancel_transaction(u_id: int, promo_info: str) -> None:
    promo_code = promo_info.split(':')[0]

    promo = Promo.query.with_entities(Promo.id).filter(Promo.code == promo_code).first()

    if promo:
        promo_id = promo.id

        user_promo = db.session.query(users_promos).filter(
            users_promos.c.user_id == u_id,
            users_promos.c.promo_id == promo_id
        ).first()

        if user_promo:
            db.session.query(users_promos).filter(
                users_promos.c.user_id == u_id,
                users_promos.c.promo_id == promo_id
            ).delete(synchronize_session=False)


def helper_check_form(on: str) -> bool:
    if any(sub in on for sub in settings.SQL_EXPR_CHECK):
        return False
    return True


def helper_get_transactions(u_id: int, date_from: str = settings.Transactions.DEFAULT_DATE_FROM,
                            date_to: str = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"), sort_type: str = 'desc'):
    model_order_type = desc(UserTransaction.created_at) if sort_type == 'desc'  \
        else asc(UserTransaction.created_at)

    pa_detalize_list = (UserTransaction.query.filter_by(user_id=u_id)
                        .filter(UserTransaction.created_at >= date_from, UserTransaction.created_at <= date_to)
                        .order_by(model_order_type).all())
    sum_fill = sum(list(
        map(lambda x: x.amount if x.type and x.status != TransactionStatuses.cancelled.value else 0, pa_detalize_list)))
    sum_spend = sum(list(
        map(lambda x: x.amount if not x.type and x.status != TransactionStatuses.cancelled.value else 0, pa_detalize_list)))
    return pa_detalize_list, sum_fill, sum_spend


def helper_refill_transaction(amount: int, status: int, promo_info: str, transaction_type: str,
                              user_id: int, sa_id: int | None, bill_path: str, only_promo: bool = False) -> bool:

    created_at = datetime.now()
    query = f"""INSERT into public.user_transactions (type, status, amount, transaction_type, promo_info, user_id, sa_id, bill_path, created_at)
                VALUES(True, {status}, {amount}, '{transaction_type}', '{promo_info}', {user_id}, {sa_id}, '{bill_path}', '{created_at}');
                UPDATE public.users SET pending_balance_rf=pending_balance_rf + {amount} WHERE public.users.id = {user_id};
                UPDATE public.server_params SET pending_balance_rf=pending_balance_rf + {amount};
            """ if not only_promo else \
        f"""INSERT into public.user_transactions (type, status, amount, transaction_type, promo_info, user_id, sa_id, bill_path, created_at)
                VALUES(True, {status}, {amount}, '{transaction_type}', '{promo_info}', {user_id}, {sa_id}, '{bill_path}', '{created_at}');
                UPDATE public.users SET balance=balance + {amount} WHERE public.users.id = {user_id};
                UPDATE public.server_params SET balance=balance + {amount};
            """
    try:
        db.session.execute(text(query))
        db.session.commit()
        return True
    except Exception as e:
        logger.error(f"new pa refill transaction add query processing caused exception: {e}")
        db.session.rollback()
        return False


def helper_get_agent_wo_pending_transactions(u_id: int) -> bool | int:
    query = text("""SELECT SUM(ut.amount) as pending_amount 
                    FROM public.user_transactions ut
                    WHERE ut.user_id = :u_id AND ut.type=False AND ut.status=1;""").bindparams(u_id=u_id)
    try:
        res = db.session.execute(query).fetchone().pending_amount
    except Exception as e:
        logger.error(f"Во время проверки всех транзакций на списание агента: {e}")
        return False
    return res if res else 0


def helper_agent_wo_transaction(amount: int, status: int, user_id: int, bill_path: str,
                                wo_account_info: str) -> tuple[bool, str]:
    if not (amount and wo_account_info):
        return False, 'Incorrect input: amount-{amount}, wo_account_info-{wo_account_info}'

    pending_amount = helper_get_agent_wo_pending_transactions(u_id=user_id)
    if pending_amount is False:
        return False, settings.Messages.WO_TRANSACTION_PENDING_AMOUNT_ERROR

    balance = helper_get_user_balance(u_id=user_id)[0]
    summary_request = amount + pending_amount
    if balance < summary_request:
        return False, settings.Messages.WO_TRANSACTION_BALANCE_ERROR.format(request_summ=summary_request,
                                                                            balance=balance)

    if helper_get_user_balance(u_id=user_id)[0] < amount:
        return False, settings.Messages.WO_TRANSACTION_BALANCE_ERROR

    created_at = datetime.now()
    query = text(f"""INSERT into public.user_transactions (type, status, transaction_type, amount, user_id, bill_path, wo_account_info, created_at)
                VALUES(False, :status, :transaction_type, :amount, :user_id, :bill_path, :wo_account_info, :created_at);

            """).bindparams(status=status, amount=amount, user_id=user_id, bill_path=bill_path,
                            wo_account_info=wo_account_info, created_at=created_at,
                            transaction_type=TransactionTypes.agent_withdrawal.value)
    try:
        db.session.execute(query)
        db.session.commit()
        return True, ''
    except Exception as e:
        logger.error(f"new agent write off transaction add query processing caused exception: {e}")
        db.session.rollback()
        return False, 'Возникло исключение, Обратитесь к администратору'


def helper_update_pending_rf_transaction_status(u_id: int, t_id: int, amount: int, operation_type: int,
                                                tr_status: int) -> tuple[bool, str]:

    sp_query = ''  # server params
    u_query = ''  # user
    sa_query = ''  # service accounts
    sa_id = None

    match tr_status:
        case TransactionStatuses.cancelled.value:
            sp_query = f"""UPDATE public.server_params SET pending_balance_rf=pending_balance_rf - 
                       {amount};""" if operation_type else ' '
            u_query = f"""UPDATE public.users SET pending_balance_rf=pending_balance_rf - 
               {amount} WHERE id={u_id};""" if operation_type else ' '

        case TransactionStatuses.success.value:
            if operation_type:
                sp_query = f"""UPDATE public.server_params SET pending_balance_rf=pending_balance_rf - 
                       {amount},
                       balance=balance + {amount};"""
                u_query = f"""UPDATE public.users SET pending_balance_rf=
                      pending_balance_rf -  
                      {amount}, balance=balance + {amount} WHERE id={u_id};"""

                sa_id_request = UserTransaction.query.with_entities(UserTransaction.sa_id).filter(
                    UserTransaction.id == t_id, UserTransaction.sa_id.isnot(None)).first()
                if not sa_id_request:
                    return False, 'Возникло исключение- счета на который нужно зарегистрировать пополнение не существует. обратитесь к администратору'
                sa_id = sa_id_request.sa_id
                sa_query = f"""UPDATE public.service_accounts SET summ_transfer=summ_transfer + {amount} WHERE id = {sa_id};"""

            else:

                # check if agent balance is ok
                if helper_get_user_balance(u_id=u_id)[0] < amount:
                    return False, settings.Messages.WO_TRANSACTION_BALANCE_ERROR_2
                u_query = f"""UPDATE public.users SET balance=balance - {amount} WHERE id={u_id};"""
    t_query = f"""UPDATE public.user_transactions SET status={tr_status} WHERE id={t_id};"""

    try:
        db.session.execute(text(f"{sp_query}{u_query}{sa_query}{t_query}"))
        db.session.commit()

        # make check of current sa
        if sa_id:
            helper_process_sa(sa_id=sa_id)
        return True, ''
    except Exception as e:
        logger.error(f"pending_transaction queries processing caused exception: {e}")
        db.session.rollback()
        return False, 'Возникло исключение- обратитесь к администратору'


def helper_get_image_html(img_path: str):
    image_obj = b''

    try:
        s3_service = get_s3_service()
        image_obj = s3_service.get_object(object_name=img_path, bucket_name=settings.MINIO_BILL_BUCKET_NAME).data
    except Exception:
        logger.exception(f"Ошибка при получении файла {img_path} из хранилища")

    if img_path.endswith('.pdf'):
        try:
            return get_first_page_as_image(pdf_file_stream=image_obj)
        except GetFirstPageFromPDFError:
            logger.error(f"Ошибка при получении первой страницы PDF файла {img_path}")

    if image_obj:
        transaction_image = f"""
        <img id="bill-modal-image" class="border border-1 rounded img-zoom-orig" 
        onclick="zoom_image();" src="data:image/png;base64,{encodebytes(image_obj).decode()}">
        """
    else:
        transaction_image = f"""<p>Не удалось загрузить изображение.</p>"""
    return transaction_image


def helper_get_check_archive(category_process: str, order_ids: str) -> list:
    res = db.session.execute(text(
        f"""
            SELECT 
                 string_agg( public.{category_process}.type, ''
                 ) AS types,
                 string_agg(public.{category_process}.country, '') AS countries,
                 string_agg( public.{category_process}.trademark, ''
                 ) AS trademarks

            FROM public.orders 
                JOIN public.{category_process} on public.{category_process}.order_id=public.orders.id
            WHERE public.orders.id in ({order_ids}) 
            GROUP BY public.orders.id ORDER BY public.orders.id DESC;    
        """
    ))

    return res.fetchall()


def helper_check_user_order_in_archive(category: str, o_id: int) -> tuple[int, str]:
    check_res = helper_get_check_archive(category_process=settings.CATEGORIES_DICT.get(category),
                                         order_ids=str(o_id))
    check_order_list = ''.join(check_res[0]) if check_res else None
    result_status = 0

    if not check_order_list:
        answer = settings.Messages.CHECK_ORDER_REQUEST_ABS_ERROR

    else:
        dt_from = datetime.today() - timedelta(days=settings.ARCHIVE_CHECK_DAYS)

        # check archive orders for last 30 days for doubles prevent
        a_orders = Order.query.with_entities(Order.id, Order.created_at,
                                             Order.order_idn).filter(Order.category == category,
                                                                     Order.user_id == current_user.id,
                                                                     Order.stage > settings.OrderStage.CREATING,
                                                                     Order.created_at >= dt_from) \
            .order_by(desc(Order.id)).all()

        # we need to add null for new users with empty ordersarchive
        a_orders_ids = 'null, ' + ','.join(list(map(lambda x: str(x.id), a_orders))) if a_orders else 'null'

        archive_orders = list(map(lambda x: ''.join(x),
                                  helper_get_check_archive(category_process=settings.CATEGORIES_DICT.get(category),
                                                           order_ids=a_orders_ids)))

        if archive_orders.count(check_order_list) >= 1:
            check_index = archive_orders.index(check_order_list)
            result_status = 1

            answer = f"<u>{settings.Messages.CHECK_ORDER_MATCH}</u><br>{a_orders[check_index].order_idn} от" \
                     f" <u>{a_orders[check_index].created_at.strftime('%d-%m-%Y %H:%M:%S')}</u>, все равно оформить?"

        else:
            answer = settings.Messages.CHECK_ORDER_REQUEST_NO_MATCH

    return result_status, answer


def helper_get_orders_marks(u_id: int, o_id: int = None, wo_flag: bool = False) -> Optional[tuple | Row]:
    if o_id:
        add_stmt = f"o.id={o_id}"
    else:
        start_stage = settings.OrderStage.NEW if wo_flag else settings.OrderStage.CREATING
        add_stmt = f"o.stage > {start_stage} AND o.stage != {settings.OrderStage.CANCELLED} AND order_idn != ''"
    stmt_orders = f"""SELECT 
                        o.order_idn as order_idn,
                        {SQLQueryCategoriesAll.get_stmt(field='marks_count')} as pos_count
                      FROM public.orders o
                        {SQLQueryCategoriesAll.get_joins()} 
                      WHERE o.user_id = {u_id} AND o.processed != True AND o.payment != True AND o.to_delete != True AND {add_stmt}
                      GROUP BY o.order_idn  
                      ORDER BY o.order_idn DESC 
                   """
    return db.session.execute(text(stmt_orders)).fetchone() if o_id else db.session.execute(text(stmt_orders)).fetchall()


def helper_get_at2_pending_balance(admin_id: int, price_id: int, balance: int, trust_limit: int) -> tuple[bool, str]:
    """Check agent type 2 balance with user orders that haven't been yet paid but already are in crm processing"""
    # stmt = f"""SELECT u.id as user_id,
    #                   SUM(os.marks_count) as pos_count
    #            FROM public.users u
    #                RIGHT JOIN public.orders_stats os ON os.user_id = u.id AND os.op_cost is NULL
    #            WHERE u.id in (SELECT au.id FROM public.users au where au.admin_parent_id={admin_id} or au.id={admin_id})
    #            GROUP BY u.id"""
    message = ''
    status = False
    stmt = f"""SELECT DISTINCT u.id as user_id,
                      {SQLQueryCategoriesAll.get_stmt(field='marks_count')} as pos_count
               FROM public.users u
                   JOIN public.orders o on o.user_id = u.id
                      {SQLQueryCategoriesAll.get_joins()} 
               WHERE u.id in (SELECT au.id FROM public.users au where au.admin_parent_id={admin_id} or au.id={admin_id}) 
               and o.payment=False and (o.to_delete = FALSE OR o.to_delete IS NULL) and o.stage>=1 and o.stage !=9 
               GROUP BY u.id;
    """
    res = db.session.execute(text(stmt)).fetchall()

    total_cost = 0
    for row in res:
        current_price = helper_get_user_price2(price_id=price_id, pos_count=row.pos_count)
        total_cost += current_price*row.pos_count
    if total_cost > (balance + trust_limit):
        # flash(message=f"{settings.Messages.CRM_CHANGE_STAGE_AT2_BALANCE_ERROR} {total_cost} превышает ваш баланс {balance}р. "
        #               f"и доверенный лимит {trust_limit}", category='error')
        message = (f"{settings.Messages.CRM_CHANGE_STAGE_AT2_BALANCE_ERROR} {total_cost} превышает ваш баланс {balance}р."
                   f" и доверенный лимит {trust_limit}")

    elif balance < total_cost < (balance + trust_limit):
        message = (f"{settings.Messages.CRM_CHANGE_STAGE_AT2_BALANCE_ERROR} {total_cost}р. {balance}р."
                   f" Вы в зоне доверенного лимита {trust_limit}")
        status = True
    else:
        status = True
    return status, message


def helper_update_tid_orders_stats(order_idn: str, transaction_id: int):
    stmt = f"""UPDATE os set os.transaction_id={transaction_id}, os.op_cost=(SELECT ut.op_cost from public.user_transactions ut WHERE ut.id={transaction_id} LIMIT 1)
               FROM public.orders_stats os
               WHERE os.order_idn == '{order_idn}';
            """
    db.session.execute(text(stmt))
    db.session.commit()


def helper_get_user_pb(user_id: int, admin_id: int, is_at2: bool) -> tuple[str, int, int, int]:
    # """
    #     Return user price_id and user balance and login_name or agent_type 2 balance and price_id
    # :param user_id:
    # :param admin_id:
    # :param is_at2:
    # :return:
    # """
    # if is_at2:
    #     stmt = f"SELECT (SELECT uu.login_name FROM public.users uu WHERE uu.id={user_id} LIMIT 1) AS login_name, u.price_id as price_id, u.balance as balance, u.trust_limit as trust_limit FROM public.users u WHERE u.id={admin_id};"
    # else:
    #     stmt = f"SELECT u.login_name as login_name, u.price_id as price_id, u.balance as balance, u.trust_limit as trust_limit FROM public.users u WHERE u.id={user_id};"
    #
    # res = db.session.execute(text(stmt)).fetchone()
    # return res.login_name, res.price_id, res.balance, res.trust_limit
    """
    Return user price_id and user balance and login_name or agent_type 2 balance and price_id.

    If the client's `price_id` differs from the admin's `price_id` (considering `is_at2`),
    the client's `price_id` will be used.

    :param user_id: ID of the user for whom data is being retrieved.
    :param admin_id: ID of the admin or agent managing the user.
    :param is_at2: Indicates whether the user is of agent_type 2.
    :return: Tuple containing login_name, price_id, balance, and trust_limit.
    """
    if is_at2:
        # Fetch the admin's price_id and balance when is_at2 is True.
        stmt = """
            SELECT 
                CASE 
                    WHEN u.price_id != (SELECT uu.price_id FROM public.users uu WHERE uu.id = :user_id LIMIT 1) 
                    THEN (SELECT uu.price_id FROM public.users uu WHERE uu.id = :user_id LIMIT 1) 
                    ELSE u.price_id 
                END AS price_id,
                (SELECT uu.login_name FROM public.users uu WHERE uu.id = :user_id LIMIT 1) AS login_name,
                u.balance AS balance, 
                u.trust_limit AS trust_limit
            FROM public.users u 
            WHERE u.id = :admin_id;
        """
    else:
        # Fetch the user's price_id and balance directly when is_at2 is False.
        stmt = """
            SELECT 
                u.login_name AS login_name, 
                u.price_id AS price_id, 
                u.balance AS balance, 
                u.trust_limit AS trust_limit 
            FROM public.users u 
            WHERE u.id = :user_id;
        """

    # Execute the SQL query with parameters.
    result = db.session.execute(text(stmt), {'user_id': user_id, 'admin_id': admin_id}).fetchone()

    return (result.login_name, result.price_id, result.balance, result.trust_limit) if result \
        else ("Unknown", 0, 0, 0)


def helper_find_price_index(target: int) -> int:
    quant_list = list(filter(lambda x: target <= x, settings.Prices.RANGES))
    if quant_list:
        index = settings.Prices.RANGES.index(quant_list[0])
    else:
        index = -1
    return index


# currently unused may be removed
# def helper_get_user_price(pos_count: int, price_id: int) -> int:
#     up = Price.query.filter_by(id=price_id).first()
#     index = helper_find_price_index(target=pos_count)
#     if not up:
#         up = settings.Prices.BASIC_PRICES
#         index += 1
#
#     else:
#         up = (up.price_1, up.price_2, up.price_3, up.price_4, up.price_5, )
#
#     return up[index]


def helper_get_user_price2(price_id: Optional[int], pos_count: int) -> int:

    index = helper_find_price_index(target=pos_count)
    if not price_id:
        up = settings.Prices.BASIC_PRICES
        index += 1 if index != -1 else 0
    else:
        up = Price.query.filter_by(id=price_id).first()
        up = (up.price_1, up.price_2, up.price_3, up.price_4, up.price_5, up.price_6, up.price_7, up.price_8, up.price_9, up.price_10, up.price_11,)
    return up[index]


def update_price_defaults():
    """Support_function to update values of new price fields after migration"""
    # Fetch all Price records
    prices = Price.query.all()

    for price in prices:
        # Check each new field if it's None, then set the default value
        if price.price_6 is None:
            price.price_6 = settings.Prices.F_5K_10K
        if price.price_7 is None:
            price.price_7 = settings.Prices.F_10K_20K
        if price.price_8 is None:
            price.price_8 = settings.Prices.F_20K_35K
        if price.price_9 is None:
            price.price_9 = settings.Prices.F_35K_50K
        if price.price_10 is None:
            price.price_10 = settings.Prices.F_50K_100K
        if price.price_11 is None:
            price.price_11 = settings.Prices.F_100K

    # Commit the changes to the database
    db.session.commit()


def helper_check_useroragent_balance(user: User, o_id: int = None) -> tuple[int, int, bool, str]:
    # get agent info and check for agents
    agent_info = User.query.filter(User.id == user.admin_parent_id) \
        .with_entities(User.is_at2, User.login_name, User.role, User.balance, User.trust_limit, User.price_id).first() \
        if user.role == settings.ORD_USER else user

    if agent_info and agent_info.role == settings.ADMIN_USER and agent_info.is_at2:
        # balance = agent_info.balance + agent_info.trust_limit

        # hard code defense against huge orders
        balance = agent_info.balance + agent_info.trust_limit
        is_at2 = True
    else:
        is_at2 = False
        balance = user.balance

    orders_marks = helper_get_orders_marks(u_id=user.id)

    prev_marks = sum(list(map(lambda x: x.pos_count, orders_marks)))

    # if we need to count specific order we search for sumcount- else we need only previous order marks values
    cur_order_marks = helper_get_orders_marks(u_id=user.id, o_id=o_id).pos_count if o_id else 0

    sum_count = prev_marks + cur_order_marks

    # get price packet for agent type 2 and ordinary common
    price_id = agent_info.price_id if is_at2 else user.price_id
    current_price = helper_get_user_price2(price_id=price_id, pos_count=sum_count,)

    # check balance for ordinary users and  make defense against huge orders for agent type 2

    # if not is_at2 and current_price * sum_count > balance:
    # print(type(current_price), current_price, type(sum_count), sum_count)
    if round(current_price * sum_count, 2) > balance:
        # make unnecessary check of agent type 2
        return 0, 0, is_at2, settings.Messages.answer_refill_balance(balance=balance, current_price=current_price,
                                                                     sum_count=sum_count, is_at2=is_at2)
    else:
        return 1, round(current_price * prev_marks), is_at2, ''


def helper_check_uoabm(user: User, o_id: int = None):
    """
        helper_check_useroragent_balance_mod
    :param user:
    :param o_id:
    :return: status 0 if not ok and 1 if ok, cost of all orders thats stage is more than CREATING
    """
    # from utilities.daily_price import get_cocmd

    agent_info = User.query.filter(User.id == user.admin_parent_id) \
        .with_entities(User.is_at2, User.login_name, User.role, User.balance, User.trust_limit, User.price_id).first() \
        if user.role == settings.ORD_USER else user
    if agent_info and agent_info.role == settings.ADMIN_USER and agent_info.is_at2:
        # balance = agent_info.balance + agent_info.trust_limit

        # hard code defense against huge orders
        balance = agent_info.balance + agent_info.trust_limit
        is_at2 = True
    else:
        is_at2 = False
        balance = user.balance

    data_res = get_cocmd(user_id=user.id, price_id=user.price_id, order_id=o_id)

    # check balance for ordinary users and  make defense against huge orders for agent type 2

    sum_cost = data_res['report_data']['ao_price'] + data_res['current_order']['order_cost'] \
        if data_res['current_order'] and data_res['current_order']['new_idn'] else data_res['report_data']['ao_price']

    if sum_cost > balance:  # this check is correct for both logic options with order_id and without
        # make unnecessary check of agent type 2
        return (0, 0,
                is_at2,
                settings.Messages.answer_refill_balance(balance=balance,
                                                        current_price=data_res['current_order'].get('op_cost'),
                                                        # price of mark for current order
                                                        sum_count=data_res['current_order'].get('marks_count'),
                                                        # summ marks for current order
                                                        all_marks=data_res['report_data']['smc'],
                                                        # summ of all marks in all orders
                                                        sum_cost=sum_cost,
                                                        # summ of orders costs
                                                        is_at2=is_at2))
    else:
        # specificly here we don't need any info except status - 1
        return 1, data_res['report_data']['ao_price'], is_at2, ''


def helper_utb_mod(user_id: int, admin_id: int, is_at2: bool) -> tuple[int, str, tuple[tuple[float, int, str], ...]]:
    """
      checks user balance for write off transactions
    :param user_id:
    :param admin_id:
    :param is_at2:
    :return: status_balance, login_name, tuple of tuples transaction_price, total_order_price, order_idns
    """
    def _get_transactions_data(user_orders_data: dict) -> tuple[tuple[float, int, str], ...]:
        def _join_order_idns(order_idns: list[str]) -> str:
            """

            :param order_idns:
            :return: a string of order_ifdns ready to use in db query
            """
            return ', '.join(f"'{order_idn}'" for order_idn in order_idns)

        pc_order_idns = _join_order_idns(user_orders_data['pc']['order_idns'])
        pc_transaction_price = user_orders_data['pc']['op_cost']
        pc_total_order_price = round(user_orders_data['pc']['marks_count'] * pc_transaction_price)

        pc_tuple = (pc_transaction_price, pc_total_order_price, pc_order_idns)

        # Extract lpc data
        lpc_tuples = []
        for lpc in user_orders_data['lpc']:
            lpc_order_idns = _join_order_idns(lpc['order_idns'])
            lpc_transaction_price = lpc['lpc_op_cost']
            lpc_total_order_price = round(lpc['lpc_marks_count'] * lpc_transaction_price)
            lpc_tuples.append((lpc_transaction_price, lpc_total_order_price, lpc_order_idns))

        return pc_tuple, *lpc_tuples

    login_name, price_id, balance, trust_limit = helper_get_user_pb(user_id=user_id, admin_id=admin_id, is_at2=is_at2)

    data_res = get_cocmd(user_id=user_id, price_id=price_id, )
    # print(data_res)
    # hard code defense against huge orders for agent type2

    if (not is_at2 and data_res['report_data']['ao_price'] > balance) \
            or (is_at2 and data_res['report_data']['ao_price'] > balance + trust_limit):
        return 0, login_name, ((0, 0, ''), )
    else:
        return 1, login_name, _get_transactions_data(user_orders_data=data_res)


def helper_get_transaction_orders_detail(t_id: int) -> tuple:
    orders_stmt = f"""SELECT DISTINCT ON (os.order_idn)
                          os.order_idn AS order_idn,
                          os.category AS category,
                          cl.subcategory AS subcategory,
                          os.marks_count AS marks_count,
                          os.op_cost AS op_cost
                      FROM public.orders_stats os
                      JOIN public.orders o ON o.order_idn = os.order_idn
                      LEFT JOIN public.clothes cl ON o.id = cl.order_id
                      WHERE os.transaction_id = {t_id}
                      ORDER BY os.order_idn DESC;
                            """
    # order_detail = db.session.execute(text(orders_stmt)).fetchall()
    return db.session.execute(text(orders_stmt)).fetchall()


def check_leather(content: str) -> bool:
    materials = list(map(str.upper, content.split(', ')))
    check = set(materials).intersection(settings.Clothes.CLOTHES_NAT_CONTENT)
    return True if check else False


def helper_check_org(organization_idn: str, admin_id: str, admin_name: str, user_name: str) -> tuple:
    info_flag = False

    stmt = f"""SELECT distinct 
                    u.id as user_id,
                    u.login_name as login_name,
                    u.email as email,
                    u.phone as phone, 
                    (SELECT a.login_name from public.users a WHERE ( a.id=u.admin_parent_id AND (a.role in('admin', 'superuser'))) OR (a.id=u.id AND (a.role in('admin', 'superuser')))) as admin,
                    pos.user_id as u_id
                FROM public.users u
                LEFT JOIN public.orders_stats pos on pos.user_id=u.id
                WHERE u.admin_parent_id!={admin_id}
                GROUP BY u.id, u_id, pos.company_idn
                HAVING pos.company_idn='{organization_idn}'  
                ORDER BY user_id DESC
               """

    stmt2 = f"""
                SELECT distinct 
                    u.id as user_id,
                    u.login_name as login_name,
                    u.email as email,
                    u.phone as phone, 
                    (SELECT a.login_name from public.users a WHERE ( a.id=u.admin_parent_id AND (a.role in('admin', 'superuser'))) OR (a.id=u.id AND (a.role in('admin', 'superuser')))) as admin
                FROM public.users u
                WHERE u.organization_idn='{organization_idn}' AND u.admin_parent_id!={admin_id}
                ORDER BY user_id DESC
             """

    res_order_stats = db.session.execute(text(stmt))
    res_tuple_os = res_order_stats.fetchall()

    res_users = db.session.execute(text(stmt2))
    res_tuple_u = res_users.fetchall()

    response_str = f'При регистрации нового пользователя  <b>{user_name}</b> от агента <b>{admin_name}</b> выявлено:\n\n '
    if res_tuple_os:
        info_flag = True
        start_str_os = f"{settings.Messages.SO_ORG_IDN_USER_MATCH}<b>{organization_idn}</b>\n\n"
        res_list = [f"<b>{el.login_name}</b> | {el.email} |  {el.phone} | Агент <b>{el.admin}</b>\n" for el in res_tuple_os]
        response_str += start_str_os + ''.join(res_list[:3]) + '\n******************\n'
    if res_tuple_u:
        info_flag = True
        start_str_u = f"\n{settings.Messages.SO_ORG_IDN_USER_SIGN_UP_MATCH}<b>{organization_idn}</b>\n\n"
        res_list = [f"<b>{el.login_name}</b> | {el.email} |  {el.phone} | Агент <b>{el.admin}</b>\n" for el in res_tuple_u]
        response_str += start_str_u + ''.join(res_list[:3]) + '\n******************\n'

    sended_m, mes = Requester.crm_post(organization_idn=organization_idn)
    if sended_m:
        info_flag = True
        response_str += f"\n{mes}"
    # some business logic here
    return info_flag, response_str


def helper_modal_intro_signup(admin_name: str) -> tuple[str, str]:
    modal_header = f"Приветствуем на сервисе {admin_name} orders!"
    modal_main = f'<h5>Вы находитесь на этапе регистрации!</h5>' \
                 f'<div><span class="badge badge-secondary mr-1" style="font-size:23px">{admin_name}</span>' \
                 f'<span class="badge badge-warning" style="font-size:23px">Orders</div>' \
                 f'<h5 class="mt-3">Желает вам продуктивной работы и успехов!</h5>'
    return modal_header, modal_main


def helper_get_model_type(category: str) -> db.Model:
    match category:
        case settings.Shoes.CATEGORY:
            return Shoe
        case settings.Clothes.CATEGORY:
            return Clothes
        case settings.Linen.CATEGORY:
            return Linen
        case settings.Parfum.CATEGORY:
            return Parfum


def helper_perform_ut_wo_test(users: list[User]):
    total_amount = 0
    try:
        for u in users:
            pending_orders = Order.query.filter(~Order.payment, ~Order.processed,~Order.to_delete,
                                                Order.stage > settings.OrderStage.CREATING,
                                                Order.stage != settings.OrderStage.CANCELLED,
                                                Order.user_id == u.id).all()
            if not pending_orders:
                continue
            # check balance
            status_balance, total_order_price, agent_at2, message_balance = helper_check_useroragent_balance(user=u, )

            if status_balance == 0:
                continue

            uuid_postfix = str(uuid4())
            bill_path = f'patch_{u.login_name}{uuid_postfix}'
            new_transaction_wo = UserTransaction(amount=total_order_price, status=settings.Transactions.SUCCESS,
                                                 bill_path=bill_path, user_id=u.id, orders=pending_orders)

            u.balance = u.balance - total_order_price
            total_amount += total_order_price

            db.session.add(new_transaction_wo)

            # O(n^2) oh yeah
            for o in pending_orders:
                o.payment = True
            db.session.commit()

        update_server_balance_stmt = f"UPDATE server_params set balance=balance-{total_amount}"
        db.session.execute(text(update_server_balance_stmt))
        db.session.commit()
    except Exception as e:
        logger.error(f"An error occured during transaction write off perform: {str(e)}")
        db.session.rollback()


def helper_get_admin_info(u_id: int) -> tuple[Optional[int], Optional[int], Optional[bool]]:
    """
        returns admin_id, agent_fee, agent_type 2 bool value
    :param u_id:
    :return:
    """
    admin_id_stmt = text("""SELECT u.admin_parent_id as admin_parent_id, u.role as role
                        FROM public.users u WHERE u.id=:u_id;""").bindparams(u_id=u_id)

    res_admin_info = db.session.execute(admin_id_stmt).fetchone()

    if res_admin_info.admin_parent_id and res_admin_info.role == settings.ORD_USER:
        # if user is a client and has agent
        admin_info = db.session.execute(text(f"""SELECT u.agent_fee as agent_fee, u.is_at2 as is_at2
                                                 FROM public.users u WHERE u.id={res_admin_info.admin_parent_id};""")).fetchone()
        return res_admin_info.admin_parent_id, admin_info.agent_fee, admin_info.is_at2
    else:
        if res_admin_info.role in (settings.SUPER_USER, settings.ADMIN_USER, ):
            # if user is and agent or superuser
            admin_info = db.session.execute(text(
                f"SELECT u.agent_fee as agent_fee, u.is_at2 as is_at2 FROM public.users u WHERE u.id={u_id};")).fetchone()
            return u_id, 0, admin_info.is_at2  # we set agent_fee 0 for agent orders
        else:
            return None, None, None


def helper_perform_ut_wo_mod(user_ids: list[tuple[int]]) -> tuple[int, int | str]:
    total_amount = 0

    try:
        for u_raw in user_ids:
            u_id = u_raw[0]

            # get admin id and fee for processing
            admin_id, agent_fee, is_at2 = helper_get_admin_info(u_id=u_id)
            if not admin_id:
                logger.error(f"User {u_id} troubles with admin id")
                continue

            # check balance
            status_balance, login_name, data_transactions = helper_utb_mod(
                user_id=u_id,
                admin_id=admin_id,
                is_at2=is_at2,
            )

            if status_balance == 0:
                logger.warning(
                    f"User {u_id} not enough balance" if not is_at2 else f"Agent {admin_id} not enough balance")
                continue

            created_at = datetime.now()

            for data_pack in data_transactions:
                # set vars for comfort
                transaction_price = data_pack[0]
                total_order_price = data_pack[1]
                order_idns = data_pack[2]

                transaction_type = TransactionTypes.order_payment.value
                agent_balance_and_commission_stmt = ''
                relevant_user_id = u_id

                uuid_postfix = str(uuid4())
                bill_path = f'patch_{login_name}{uuid_postfix}'

                if is_at2:
                    relevant_user_id = admin_id
                    if u_id != admin_id:
                        transaction_type = TransactionTypes.users_order_payment.value
                elif agent_fee != 0:
                    agent_fee_part = m_floor(total_order_price * agent_fee / 100)
                    transaction_agent_commission_stmt = (
                        f"""INSERT into public.user_transactions (
                            type, 
                            amount, 
                            status, 
                            transaction_type, 
                            promo_info, 
                            bill_path, 
                            created_at,
                            user_id
                        )
                        VALUES(
                            True, 
                            {agent_fee_part}, 
                            {TransactionStatuses.success.value}, 
                            '{TransactionTypes.agent_commission.value}', 
                            '', 
                            '{bill_path}_{TransactionTypes.agent_commission.value}', 
                            '{created_at}',
                            {admin_id}
                        );
                        """
                    )
                    agent_balance_stmt = f"""UPDATE public.users set balance=balance+{agent_fee_part} WHERE id = {admin_id};"""
                    agent_balance_and_commission_stmt = transaction_agent_commission_stmt + agent_balance_stmt

                create_transaction = (
                    f"""INSERT INTO public.user_transactions (
                                        type, 
                                        amount, 
                                        op_cost, 
                                        transaction_type, 
                                        agent_fee, 
                                        status, 
                                        bill_path, 
                                        promo_info, 
                                        created_at, 
                                        user_id
                                    )
                                    VALUES (
                                        False, 
                                        {total_order_price}, 
                                        {transaction_price},  
                                        '{transaction_type}', 
                                        {agent_fee}, 
                                        {TransactionStatuses.success.value}, 
                                        '{bill_path}', 
                                        '', 
                                        '{created_at}', 
                                        {relevant_user_id}
                                    ) RETURNING id AS tr_id;
                                    """
                )
                tr_id = db.session.execute(text(create_transaction)).fetchone()[0]

                upsert_orders_stats_stmt = f"""WITH inserted_data AS (
                                            SELECT 
                                                o.category as category, 
                                                o.company_idn as company_idn, 
                                                o.company_type as company_type, 
                                                o.company_name as company_name, 
                                                o.order_idn as order_idn, 
                                                {SQLQueryCategoriesAll.get_stmt(field='rows_count')} as rows_count, 
                                                {SQLQueryCategoriesAll.get_stmt(field='marks_count')} as marks_count, 
                                                {transaction_price} AS transaction_price, 
                                                o.created_at as created_at, 
                                                o.crm_created_at as crm_created_at, 
                                                o.user_id as user_id, 
                                                {tr_id} AS tr_id, 
                                                '{created_at}'::timestamp AS saved_at
                                            FROM 
                                                public.orders o
                                                {SQLQueryCategoriesAll.get_joins()} 
                                            WHERE 
                                                o.order_idn IN ({order_idns})
                                            GROUP BY 
                                                o.category, 
                                                o.company_idn, 
                                                o.company_type, 
                                                o.company_name, 
                                                o.order_idn, 
                                                o.created_at, 
                                                o.crm_created_at, 
                                                o.user_id
                                        )
                                        INSERT INTO public.orders_stats (
                                            category, company_idn, company_type, company_name, order_idn, 
                                            rows_count, marks_count, op_cost, created_at, crm_created_at, 
                                            user_id, transaction_id, saved_at
                                        ) 
                                        SELECT 
                                            category, company_idn, company_type, company_name, order_idn, 
                                            rows_count, marks_count, transaction_price, created_at, crm_created_at, 
                                            user_id, tr_id, saved_at
                                        FROM 
                                            inserted_data
                                        ON CONFLICT (order_idn) DO UPDATE 
                                        SET 
                                            transaction_id = EXCLUDED.transaction_id, 
                                            op_cost = EXCLUDED.op_cost;"""

                update_orders_stmt = f"""UPDATE public.orders set transaction_id={tr_id}, payment=True WHERE order_idn in ({order_idns});"""

                user_balance_stmt = f"""UPDATE public.users set balance=balance-{total_order_price} WHERE id = {relevant_user_id};"""

                db.session.execute(text(upsert_orders_stats_stmt + user_balance_stmt + update_orders_stmt + agent_balance_and_commission_stmt))
                total_amount += total_order_price

                db.session.commit()

        if total_amount:
            update_server_balance_stmt = f"""UPDATE public.server_params set balance=balance-{total_amount} RETURNING balance;"""
            server_balance = db.session.execute(text(update_server_balance_stmt)).fetchone().balance

            db.session.commit()

            return 1, server_balance
        else:
            return 0, 0
    except Exception as e:
        logger.exception(f"An error occured during transaction write off perform: {str(e)}")
        db.session.rollback()
        return 0, 0


def helper_get_user_at2(user: User) -> bool:
    if user.role == settings.ORD_USER:
        agent_info = User.query.with_entities(User.is_at2).filter(User.id == user.admin_parent_id).first()
        is_at2 = agent_info.is_at2 if agent_info else False  # not sure
    else:
        is_at2 = False
    return is_at2


def helper_get_user_at2_opt2(u_id: int) -> tuple[bool, int, str, str, int] | None:
    user = User.query.with_entities(User.id, User.balance, User.email, User.role, User.admin_parent_id).filter(User.id == u_id).first()
    if not user:
        return
    agent_info = User.query.with_entities(User.is_at2, User.id, User.email).filter(
        User.id == user.admin_parent_id).first()

    if not agent_info:
        agent_id = user.id
        agent_email = user.email
    else:
        agent_id = agent_info.id
        agent_email = agent_info.email
    if user.role == settings.ORD_USER:
        is_at2 = agent_info.is_at2 if agent_info else False  # not sure
    else:
        is_at2 = False
    return is_at2, agent_id, agent_email, user.email, user.balance


def su_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.status is True and current_user.role == settings.SUPER_USER:
            return func(*args, **kwargs)
        else:
            flash(message=settings.Messages.SUPERUSER_REQUIRED, category='error')
            return redirect(url_for('main.index'))
    return wrapper


def susmu_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.status is True and current_user.role in [settings.SUPER_USER, settings.SUPER_MANAGER]:
            return func(*args, **kwargs)
        else:
            flash(message=settings.Messages.SUPERUM_REQUIRED, category='error')
            return redirect(url_for('main.index'))
    return wrapper


def susmumu_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.status is True and current_user.role in [settings.SUPER_USER, settings.SUPER_MANAGER,
                                                                 settings.MANAGER_USER]:
            return func(*args, **kwargs)
        else:
            flash(message=settings.Messages.CRM_MANAGER_USER_REQUIRED, category='error')
            return redirect(url_for('main.index'))
    return wrapper


def sumausmumu_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.status is True and current_user.role in [settings.SUPER_USER, settings.MARKINERIS_ADMIN_USER, settings.SUPER_MANAGER,
                                                                 settings.MANAGER_USER]:
            return func(*args, **kwargs)
        else:
            flash(message=settings.Messages.CRM_MANAGER_AGENT_USER_REQUIRED, category='error')
            return redirect(url_for('main.index'))
    return wrapper


# admin user required with id checks
def au_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.status is True and (current_user.role in [settings.ADMIN_USER, settings.SUPER_USER]):
            if current_user.role != settings.SUPER_USER and current_user.id != kwargs.get('u_id'):
                flash(message=settings.Messages.SUPERUSER_REQUIRED, category='error')
                return redirect(url_for('admin_control.admin', u_id=current_user.id))
            return func(*args, **kwargs)
        else:
            flash(message=settings.Messages.SUPERADMINUSER_REQUIRED, category='error')
            return redirect(url_for('main.index'))
    return wrapper


def bck_at2_required(func):
    """
        Checks if user is TYPE 2 and returns dict with message if not or redirects
    :param func:
    :return:
    """

    @wraps(func)
    def wrapper(*args, **kwargs):

        if current_user.status is True and current_user.is_at2:
            return func(*args, **kwargs)
        else:
            # check if its bck request error
            bck = request.args.get('bck', 0, type=int)
            if bck:
                return jsonify(dict(status='danger', message=settings.Messages.AT2_USER_REQUIRED))
            else:
                flash(message=settings.Messages.AT2_USER_REQUIRED, category='error')
                return redirect(url_for('main.index'))

    return wrapper


# admin user simplified required
def aus_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.status is True and (current_user.role in [settings.ADMIN_USER, settings.SUPER_USER, ]):
            return func(*args, **kwargs)
        else:
            flash(message=settings.Messages.SUPERADMINUSER_REQUIRED, category='error')

            return redirect(url_for('main.index'))
    return wrapper


def bck_aus_required(func):
    """
        Checks if user is ADMIN or SUPERUSER and returns dict with message if not
    :param func:
    :return:
    """
    @wraps(func)
    def wrapper(*args, **kwargs):

        if current_user.status is True and (current_user.role in [settings.ADMIN_USER, settings.SUPER_USER, ]):
            return func(*args, **kwargs)
        else:
            # check if its bck request error
            bck = request.args.get('bck', 0, type=int)
            if bck:
                return jsonify(dict(status='danger', message=settings.Messages.SUPERADMINUSER_REQUIRED))
            else:
                flash(message=settings.Messages.SUPERADMINUSER_REQUIRED, category='error')
                return redirect(url_for('main.index'))
    return wrapper


def bck_su_required(func):
    """
        Checks if user is SUPERUSER and returns dict with message if not
    :param func:
    :return:
    """
    @wraps(func)
    def wrapper(*args, **kwargs):

        if current_user.status is True and (current_user.role in [settings.SUPER_USER, ]):
            return func(*args, **kwargs)
        else:
            # check if its bck request error
            bck = request.args.get('bck', 0, type=int)
            if bck:
                return jsonify(dict(status='danger', message=settings.Messages.SUPERADMINUSER_REQUIRED))
            else:
                flash(message=settings.Messages.SUPERADMINUSER_REQUIRED, category='error')
                return redirect(url_for('main.index'))
    return wrapper


def bck_su_mod_required(func):
    """
        Checks if user is SUPERUSER or Markineris admin and returns dict with message if not
    :param func:
    :return:
    """

    @wraps(func)
    def wrapper(*args, **kwargs):

        if current_user.status is True and (current_user.role in [settings.SUPER_USER, settings.MARKINERIS_ADMIN_USER]):
            return func(*args, **kwargs)
        else:
            # check if its bck request error
            bck = request.args.get('bck', 0, type=int)
            if bck:
                return jsonify(dict(status='danger', message=settings.Messages.SUPERADMINUSER_REQUIRED))
            else:
                flash(message=settings.Messages.SUPERADMINUSER_REQUIRED, category='error')
                return redirect(url_for('main.index'))

    return wrapper


def crmau_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.status is True and \
                (current_user.role == settings.MARKINERIS_ADMIN_USER or
                 current_user.role == settings.SUPER_USER):

            return func(*args, **kwargs)
        else:
            flash(message=settings.Messages.SUPERADMIN_MADMIN_USER_REQUIRED, category='error')
            return redirect(url_for('main.index'))
    return wrapper


def su_mod_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.status is True and current_user.role in [settings.SUPER_USER, settings.MARKINERIS_ADMIN_USER]:
            return func(*args, **kwargs)
        else:
            flash(message=settings.Messages.SUPER_MOD_REQUIRED, category='error')
            return redirect(url_for('main.index'))
    return wrapper


def user_exist_check(func):
    @wraps(func)
    def wrapper(*args, **kwargs):

        user = User.query.filter_by(id=kwargs.get("u_id")).first()

        if user:
            if user.role != settings.SUPER_USER:
                return func(*args, **kwargs)
            else:
                flash(message=f"{settings.Messages.SUPERUSER_NOT_EDIT}", category='error')
                return redirect(url_for('admin_control.index'))
        else:
            flash(message=f"{settings.Messages.NO_SUCH_USER}", category='error')
            return redirect(url_for('admin_control.index'))
    return wrapper


def manager_exist_check(func):
    @wraps(func)
    def wrapper(*args, **kwargs):

        user = User.query.filter_by(id=kwargs.get("u_id")).first()

        if user:
            if user.role != settings.SUPER_USER:
                return func(*args, **kwargs)
            else:
                flash(message=f"{settings.Messages.SUPERUSER_NOT_EDIT}", category='error')
                return redirect(url_for('crm_uc.index'))
        else:
            flash(message=f"{settings.Messages.NO_SUCH_USER}", category='error')
            return redirect(url_for('crm_uc.index'))
    return wrapper


def helper_strange_response(redir_url: str = None, message: str = settings.Messages.STRANGE_REQUESTS):
    if not redir_url:
        redir_url = url_for('main.enter')
    bck = request.args.get('bck', 0, type=int)
    if not bck:
        flash(message=message, category='error')
        return redirect(redir_url)
    else:
        jsonify(dict(status='danger', message=message))


def helper_get_limits() -> CrmDefaults:
    limits_qry = ServerParam.query.get(1)

    if limits_qry:
        ps_limit = limits_qry.crm_manager_ps_limit if limits_qry.crm_manager_ps_limit else settings.OrderStage.DEFAULT_PS_LIMIT
        mo_limit = limits_qry.crm_manager_mo_limit if limits_qry.crm_manager_mo_limit else settings.OrderStage.DEFAULT_MO_LIMIT
        po_limit = limits_qry.crm_manager_po_limit if limits_qry.crm_manager_po_limit else settings.OrderStage.DEFAULT_PO_LIMIT
        ap_rows = limits_qry.auto_pool_rows if limits_qry.auto_pool_rows or limits_qry.auto_pool_rows == 0 \
            else settings.OrderStage.DEFAULT_AP_ROWS
        ap_marks = limits_qry.auto_pool_marks if limits_qry.auto_pool_marks or limits_qry.auto_pool_marks == 0 \
            else settings.OrderStage.DEFAULT_AP_MARKS
        as_minutes = limits_qry.auto_sent_minutes if limits_qry.auto_sent_minutes or limits_qry.auto_sent_minutes == 0 \
            else settings.OrderStage.DEFAULT_AS_MINUTES
    else:
        ps_limit = settings.OrderStage.DEFAULT_PS_LIMIT
        mo_limit = settings.OrderStage.DEFAULT_MO_LIMIT
        po_limit = settings.OrderStage.DEFAULT_PO_LIMIT
        ap_rows = settings.OrderStage.DEFAULT_AP_ROWS
        ap_marks = settings.OrderStage.DEFAULT_AP_MARKS
        as_minutes = settings.OrderStage.DEFAULT_AS_MINUTES

    return CrmDefaults(ps_limit=ps_limit, mo_limit=mo_limit, po_limit=po_limit,
                       ap_rows=ap_rows, ap_marks=ap_marks, as_minutes=as_minutes)


def user_is_send_check(func):
    @wraps(func)
    def wrapper(*args, **kwargs):

        if current_user.is_send_excel:

            return func(*args, **kwargs)
        else:
            flash(message=f"{settings.Messages.NO_SUCH_USER_SERVICE}", category='error')
            return redirect(url_for('main.enter'))
    return wrapper


def extract_id_from_partner_name(name) -> Optional[int]:
    match = re.search(r'_(\d+)$', name)
    return int(match.group(1)) if match else None


def get_partner_code_max_id(partners) -> str:
    partners_id = [extract_id_from_partner_name(partner.name) for partner in partners if
                   extract_id_from_partner_name(partner.name) is not None]
    auto_increment_id = max(partners_id) + 1 if partners_id else 1
    return str(auto_increment_id)


def helper_get_filter_avg_order_time_processing_report(report: bool = False):
    default_day_to = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')
    default_day_from = (datetime.today() - timedelta(days=settings.ORDERS_REPORT_TIMEDELTA)).strftime('%Y-%m-%d')
    if report:
        url_date_from = request.form.get('date_from', '', type=str)
        url_date_to = request.form.get('date_to', 0, type=str)
        manager_id = request.form.get('manager', 0, int)

    else:
        url_date_from = request.args.get('date_from', '', type=str)
        url_date_to = request.args.get('date_to', '', type=str)
        manager_id = request.args.get('manager', 0, int)

    date_from = datetime.strptime(url_date_from, '%d.%m.%Y').strftime('%Y-%m-%d') if url_date_from else default_day_to
    date_to = (datetime.strptime(url_date_to, '%d.%m.%Y') + timedelta(days=1)).strftime(
        '%Y-%m-%d') if url_date_to else default_day_from

    return date_from, date_to, manager_id


def helper_get_stmt_avg_order_time_processing_report(
        date_from: str = (datetime.today() - timedelta(days=settings.ORDERS_REPORT_TIMEDELTA)).strftime('%Y-%m-%d'),
        date_to: str = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d'),
        manager_id: int = 0,
) -> TextClause:

    stmt = text(f"""
            SELECT
                U.LOGIN_NAME,
                count(distinct o.id) as order_count,
                {SQLQueryCategoriesAll.get_stmt(field='marks_count')} AS pos_count,
                {SQLQueryCategoriesAll.get_stmt(field='rows_count')} AS rows_count,
                TRUNC(AVG(
                    EXTRACT(
                        epoch
                        FROM
                            O.M_FINISHED - O.M_STARTED
                    ) 
                ) / 60, 1) AS PROCESSING_TIME,
                TRUNC(AVG(
                    EXTRACT(
                        epoch
                        FROM
                            O.M_FINISHED - O.M_STARTED
                    ) 
                ) / 60 / 60, 1) AS PROCESSING_TIME_HOUR
            FROM
                ORDERS O
                JOIN USERS U ON O.MANAGER_ID = U.ID
                {SQLQueryCategoriesAll.get_joins()}
            WHERE
                O.M_STARTED >= :date_from
                and O.M_FINISHED < :date_to
                and (o.stage = 5 or o.stage > 7)
                and (o.manager_id = :manager_id or 0 = :manager_id)
            GROUP BY
                U.LOGIN_NAME
            ORDER BY 3 DESC;
        """).bindparams(date_from=date_from, date_to=date_to, manager_id=manager_id)
    return stmt


def ausumsuu_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.status is True and current_user.role in [settings.SUPER_MANAGER, settings.SUPER_USER, settings.ADMIN_USER]:
            return func(*args, **kwargs)
        else:
            bck = request.args.get('bck', 0, type=int)
            if bck:
                return jsonify(dict(status='danger', message=settings.Messages.CRM_MANAGER_AGENT_USER_REQUIRED))
    return wrapper

def sumsuu_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.status is True and current_user.role in [settings.SUPER_MANAGER, settings.SUPER_USER, ]:
            return func(*args, **kwargs)
        else:
            bck = request.args.get('bck', 0, type=int)
            if bck:
                return jsonify(dict(status='danger', message=settings.Messages.CRM_REPORT_USER_REQUIRED))
    return wrapper


def create_bill_path(filename: str) -> str:
    return f'{str(uuid4())[:8]}_{current_user.login_name}.{filename}'
