from typing import Union

from flask import flash, redirect, url_for, request, Response, render_template, send_file
from flask_login import current_user

from config import settings
from logger import logger
from utilities.download import upload_errors_file
from utilities.support import check_file_extension, helper_get_order_notification, get_category_p_orders
from utilities.upload_order.upload_clothes import UploadClothes
from utilities.upload_order.upload_linen import UploadLinen
from utilities.upload_order.upload_parfum import UploadParfum
from utilities.upload_order.upload_saving_uts import upload_table_common
from utilities.upload_order.upload_shoes import UploadShoes


def helper_upload_common_get(category: str, category_process_name: str) -> Union[Response, str]:
    user = current_user
    price_description = settings.PRICE_DESCRIPTION
    company_types = settings.COMPANY_TYPES
    edo_types = settings.EDO_TYPES
    tax_list = settings.TAX_LIST

    admin_id = user.admin_parent_id
    order_notification, admin_name, crm = helper_get_order_notification(admin_id=admin_id if admin_id else user.id)
    active_orders = get_category_p_orders(user=user, category=category, processed=False)
    if len(active_orders) >= 5:
        specific_order = True
        o_id = active_orders[0].id
        flash(message=settings.Messages.USER_ORDERS_LIMIT, category='error')
        return redirect(url_for(f'{category_process_name}.index', o_id=o_id))

    company_type = request.args.get("company_type")
    company_name = request.args.get("company_name")
    company_idn = request.args.get("company_idn")
    edo_type = request.args.get("edo_type")
    edo_id = request.args.get("edo_id")
    mark_type = request.args.get("mark_type")
    templates = settings.TEMPLATES_DICT.get(category)
    download_instruction = settings.UPLOAD_ORDER_EXCEL_INSTRUCTION
    return render_template(f'upload/{category_process_name}_upload_footer_v2.html', **locals())


def helper_upload_common_post(category: str, category_process_name: str,
                              upload_model: type[UploadShoes | UploadLinen | UploadParfum | UploadClothes]):
    form_data_raw = request.form
    form_dict = form_data_raw.to_dict()
    table_type = form_dict.get("table_type")
    company_type = form_dict.get("company_type")
    company_name = form_dict.get("company_name")
    company_idn = form_dict.get("company_idn")
    edo_type = form_dict.get("edo_type")
    edo_id = form_dict.get("edo_id")
    mark_type = form_dict.get("mark_type")

    table_file = request.files.get('table_upload')

    if table_file is None or table_file is False or check_file_extension(filename=table_file.filename) is False:
        flash(message=settings.Messages.UPLOAD_FILE_EXTEXSION_ERROR, category='error')
        return redirect(url_for(f'{category_process_name}.upload', company_type=company_type, company_name=company_name,
                                company_idn=company_idn, edo_type=edo_type, edo_id=edo_id, mark_type=mark_type))

    try:
        us = upload_model(table_obj=table_file, type_upload=table_type)
        order_list, error_list = us.get_article_info()

        if not order_list:
            flash(message=settings.Messages.UPLOAD_FILE_EXTEXSION_ERROR, category='error')
            return redirect(url_for(f'{category_process_name}.upload', company_type=company_type, company_name=company_name,
                                    company_idn=company_idn, edo_type=edo_type, edo_id=edo_id, mark_type=mark_type))
        # process limit pos error
        if order_list[0] == settings.ORDER_LIMIT_ARTICLES:
            flash(message=f"{settings.Messages.ORDER_UPLOAD_POS_LIMIT} {order_list[1]}", category='error')
            return redirect(url_for(f'{category_process_name}.upload', company_type=company_type, company_name=company_name,
                                    company_idn=company_idn, edo_type=edo_type, edo_id=edo_id, mark_type=mark_type))
        if not error_list:
            order_id = upload_table_common(user=current_user, company_type=company_type, company_name=company_name,
                                           company_idn=company_idn, edo_type=edo_type, edo_id=edo_id,
                                           mark_type=mark_type,
                                           order_list=order_list, category=category,
                                           type_upload=table_type)
            match order_id:
                case None:
                    flash(message=f"{settings.Messages.ORDER_UPLOAD_CONFLICT}", category='error')
                    return redirect(url_for(f'{category_process_name}.index'))
                case _:
                    flash(message=f"{settings.Messages.ORDER_UPLOAD_SUCCESS}")

                    return redirect(url_for(f'{category_process_name}.index', o_id=order_id))

        else:

            flash(message=settings.Messages.UPLOAD_FILES_ERROR, category='error')
            return send_file(upload_errors_file(error_list=error_list),
                             as_attachment=True,
                             download_name=settings.UPLOAD_TABLE_ERRORS_FILE,
                             mimetype='text/csv')
    except TypeError as te:
        logger.error(te)
        flash(message=settings.Messages.UPLOAD_FILE_TYPE_ERROR, category='error')
    except ValueError as ve:
        logger.error(ve)
        flash(message=settings.Messages.UPLOAD_FILE_EXTEXSION_ERROR, category='error')

    except Exception as exception:
        message = settings.Messages.UPLOAD_CATEGORY_TEMPLATE_TYPE_ERROR \
            if str(exception).startswith(settings.POS_INDEX_EXCEPTION) \
            else f"{settings.Messages.UPLOAD_FILE_UNKNOWN_ERROR} {str(exception)}"
        flash(message=message, category='error')
        logger.error(message)

    return redirect(url_for(f'{category_process_name}.upload', company_type=company_type, company_name=company_name,
                            company_idn=company_idn, edo_type=edo_type, edo_id=edo_id, mark_type=mark_type))