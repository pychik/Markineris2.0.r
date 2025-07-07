from flask import Blueprint, jsonify, render_template, redirect, url_for, flash, Response, make_response, request
from flask_login import current_user
from sqlalchemy import desc, func, or_

from loguru import logger
from config import settings
from models import Clothes, Order, OrderFile
from utilities.categories_data.subcategories_data import ClothesSubcategories, Category
from utilities.categories_data.subcategories_logic import get_subcategory
from utilities.minio_service.services import download_file_from_minio, get_s3_service
from utilities.pdf_processor import RarZipPdfProcessor
from utilities.saving_uts import common_save_copy_order
from utilities.support import get_category_archive_all, \
    common_process_delete_order, helper_get_order_notification, \
    helper_category_archive_orders, helper_paginate_data, get_category_p_orders

orders_archive = Blueprint('orders_archive', __name__)


def h_index() -> tuple:
    user = current_user
    admin_id = user.admin_parent_id
    order_notification, admin_name, crm = helper_get_order_notification(admin_id=admin_id if admin_id else user.id)
    all_orders = get_category_archive_all(user=user)

    shoe_orders, clothes_orders, linen_orders, parfum_orders = helper_category_archive_orders(all_orders=all_orders)

    stages_description = settings.OrderStage.STAGES
    return render_template('archive/a_base_v2.html', **locals()), 200


def h_category(category: str = settings.Shoes.CATEGORY, upload_flag: int = None):
    user = current_user
    admin_id = user.admin_parent_id
    order_notification, admin_name, crm = helper_get_order_notification(admin_id=admin_id if admin_id else user.id)

    subcategory = request.args.get('subcategory', '')
    if not Category.check_subcategory(category=category, subcategory=subcategory):
        message = settings.Messages.STRANGE_REQUESTS + ' нет такой подкатегории'
        if upload_flag:
            return jsonify(dict(status='error', message=message))
        else:
            flash(message=message, category='error')
            return redirect(url_for('main.enter'))
    query = (user.orders.filter(
            ~Order.to_delete,
            Order.category == category,
            Order.stage > 0
        )
        .with_entities(
            Order.id, Order.stage, Order.order_idn, Order.category,
            Order.company_type, Order.company_name, Order.company_idn, Order.user_comment,
            Order.to_delete, Order.processed, Order.payment, Order.created_at,
            Order.crm_created_at, Order.stage, Order.closed_at, Order.processing_info,
            func.max(OrderFile.file_link).label('file_link')  # Агрегируем file_link
        )
        .outerjoin(OrderFile, Order.order_zip_file)
        .group_by(Order.id)
        .order_by(desc(Order.crm_created_at))
    )

    # Добавляем проверку на подкатегорию
    if category == settings.Clothes.CATEGORY:
        query = query.join(Clothes, Order.id == Clothes.order_id)

        if subcategory is None or subcategory == '' or subcategory == 'common':
            query = query.filter(or_(
                Clothes.subcategory.is_(None),  # subcategory = NULL в базе
                Clothes.subcategory == '',  # subcategory = '' в базе
                Clothes.subcategory == 'common'  # subcategory = 'common' в базе
            ))
        else:
            # Иначе фильтруем по конкретному subcategory
            query = query.filter(Clothes.subcategory == subcategory)

    category_orders = query.all()

    link = 'javascript:get_category_history(\''+url_for('orders_archive.index', category=category,
                                                        upload_flag=settings.UPLOAD_BACKGROUND,
                                                        subcategory=subcategory) + \
           '&page={0}\', \'' + settings.CATEGORIES_DICT[category] + '\', \'' + subcategory + '\');'

    page, per_page, \
        offset, pagination, \
        category_orders = helper_paginate_data(data=category_orders,
                                               href=link,
                                               per_page=settings.PAGINATION_PER_PAGE_HISTORY_ORDERS)
    stages_description = settings.OrderStage.STAGES
    if upload_flag == 111:
        return jsonify({'htmlresponse': render_template(f'archive/a_category_common_v2.html', **locals())})
    return render_template('archive/a_base_v2.html', **locals()), 200


def h_delete_order(o_id: int, stage: int, category: str = settings.Shoes.CATEGORY) -> Response:
    if not current_user.is_at2:
        common_process_delete_order(o_id=o_id, stage=stage)
    return redirect(url_for('orders_archive.index', category=category))


def h_copy_order(o_id: int, category: str) -> Response:
    if category not in settings.CATEGORIES_DICT.keys():
        flash(message=settings.Messages.STRANGE_REQUESTS, category='error')
        return redirect(url_for('orders_archive.index'))
    user = current_user
    u_id = user.id
    orders_id = [o.id for o in user.orders.with_entities(Order.id).filter(~Order.to_delete).all()]

    order = Order.query.filter_by(id=o_id, category=category).filter(~Order.to_delete).first()

    if not order or order.id not in orders_id:
        flash(message=f"{settings.Messages.NO_SUCH_ORDER_COPY}", category='error')
        return redirect(url_for('orders_archive.index'))

    subcategory = get_subcategory(order_id=order.id, category=category)

    active_orders = get_category_p_orders(user=user, category=category, subcategory=subcategory, processed=False)

    if len(active_orders) >= 5:

        flash(message=settings.Messages.USER_ORDERS_COPY_LIMIT, category='error')
        return redirect(url_for('orders_archive.index'))
    category_process_name = settings.CATEGORIES_DICT.get(category)

    o_id = common_save_copy_order(u_id=u_id, user=user, order=order, category=category)

    if o_id:
        flash(message=f"{settings.Messages.ORDER_COPY_SUCCESS} {category}")
        return redirect(url_for(f'{category_process_name}.index', o_id=o_id,
                                copy_order_edit_org='edit_org_card'))
    else:
        return redirect(url_for('orders_archive.index'))


def h_download_oa(o_id: int, category: str = settings.Shoes.CATEGORY) -> Response:
    user = current_user

    order = (Order.query.with_entities(Order.id, Order.user_id).filter_by(id=o_id, category=category, user_id=user.id)
             .filter(~Order.to_delete).first())

    if not order:
        flash(message=settings.Messages.STRANGE_REQUESTS, category='error')
        return redirect(url_for('orders_archive.index'))
    file_download_obj = OrderFile.query.with_entities(OrderFile.origin_name, OrderFile.file_system_name,
                                                      OrderFile.file_link).filter_by(order_id=order.id).first()
    if not file_download_obj:
        flash(message=settings.Messages.NO_FILES_TO_DOWNLOAD, category='error')
        return redirect(url_for('orders_archive.index'))

    fs_name = file_download_obj.file_system_name
    f_link = file_download_obj.file_link

    if fs_name:
        if fs_name.lower().endswith('.zip'):
            archive_ext = 'zip'
        else:
            archive_ext = 'rar'

        archive_name = f"order_{o_id}.{archive_ext}"
        return download_file_from_minio(
            bucket_name=settings.MINIO_CRM_BUCKET_NAME,
            object_name=fs_name,
            download_name=archive_name,
        )
    elif f_link is not None:
        flash(message=f"{settings.Messages.FILE_DOWNLOAD_LINK} "
                      f"<a href=\"{file_download_obj.file_link}\">Ссылка на скачивание архива</a>", category="info")
        return redirect(url_for('orders_archive.index', category=category))
    else:
        flash(message=settings.Messages.NO_FILES_TO_DOWNLOAD, category='error')
        return redirect(url_for('orders_archive.index'))


def h_download_opdf(o_id: int, category: str = settings.Shoes.CATEGORY) -> Response:
    user = current_user

    order = (Order.query.with_entities(Order.id, Order.user_id, Order.order_idn).filter_by(id=o_id, category=category,
                                                                                           user_id=user.id)
             .filter(~Order.to_delete).first())
    response = jsonify()
    response.headers['Content-Type'] = 'text/plain; charset=utf-8'
    if not order:

        response.headers['data_status'] = 'no file'
        response.headers['data_message'] = settings.Messages.STRANGE_REQUESTS_ENG
        return response
    file_download_obj = OrderFile.query.with_entities(OrderFile.origin_name, OrderFile.file_system_name,
                                                      OrderFile.file_link).filter_by(order_id=order.id).first()
    if not file_download_obj:
        response.headers['data_status'] = 'no file'
        response.headers['data_message'] = settings.Messages.NO_FILES_TO_DOWNLOAD_ENG
        return response

    fs_name = file_download_obj.file_system_name
    f_link = file_download_obj.file_link

    if fs_name:
        try:
            s3_service = get_s3_service()
            rar_file = s3_service.get_object(object_name=fs_name, bucket_name=settings.MINIO_CRM_BUCKET_NAME)
        except Exception:
            response.headers['data_status'] = 'no file'
            response.headers['data_message'] = settings.Messages.NO_FILES_TO_DOWNLOAD_ENG
            logger.exception("Ошибка при получении файла из хранилища")
        else:
            archive_type = 'zip' if fs_name.lower().endswith('.zip') else 'rar'
            rar_pdf_proc = RarZipPdfProcessor(rar_file=rar_file.data, archive_type=archive_type)
            pdf_io = rar_pdf_proc.get_extract_and_merge_pdfs()
            pdf_name = "order_{order_idn}.pdf".format(order_idn=order.order_idn)
            response = make_response(pdf_io.getvalue())
            response.headers['data_file_name'] = pdf_name
            response.headers['Content-type'] = 'text/plain'
            response.headers['data_status'] = 'success'

    elif f_link is not None:
        response.headers['data_status'] = 'file_link_download'
        response.headers['data_message'] = f"<a href=\"{file_download_obj.file_link}\">Click</a>"

    else:
        response.headers['data_status'] = 'no file'
        response.headers['data_message'] = settings.Messages.NO_FILES_TO_DOWNLOAD_ENG

    return response
