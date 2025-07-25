from datetime import date, datetime, timedelta
from typing import Optional
from uuid import uuid4

from flask import jsonify, redirect, render_template, request, Response, flash, url_for
from flask_login import current_user
from redis import Redis
from rq import Queue
from rq_scheduler.scheduler import Scheduler
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

from config import settings
from logger import logger
from models import User, Order, OrderStat, db, ServerParam
from redis_queue.callbacks import on_success_periodic_task, on_failure_periodic_task
from utilities.download import crm_orders_common_preload
from utilities.exceptions import EmptyFileToUploadError
from utilities.helpers.h_tg_notify import helper_send_user_order_tg_notify, helper_suotls
from utilities.minio_service.services import get_s3_service, download_file_from_minio
from utilities.pdf_processor import helper_check_attached_file
from utilities.saving_uts import get_rows_marks
from utilities.sql_categories_aggregations import SQLQueryCategoriesAll
from utilities.support import (helper_get_at2_pending_balance, helper_get_limits, orders_list_common)
from utilities.telegram import MarkinerisInform
from .crm_support import h_cancel_order_process_payment
from .schema import CompaniesOperators


def helper_get_agent_orders(user: User, category: str | None = None) -> list:
    category_stmt = f" AND o.category=\'{category}\'" if category in settings.CATEGORIES_UPLOAD else ""

    conditional_stmt = f"o.stage>{settings.OrderStage.CREATING}  AND o.stage < {settings.OrderStage.SENT}{category_stmt}"
    additional_stmt = """
                                 o.comment_problem as comment_problem,
                                 o.comment_cancel as comment_cancel,
                                 o.cp_created as cp_created,
                                 o.cc_created as cc_created,
                                 o.crm_created_at as crm_created_at,
                                 o.p_started as p_started,
                                 o.m_started as m_started,
                                 o.m_finished as m_finished,
                                 o.sent_at as sent_at,
                                 o.closed_at as closed_at,
                              """
    stmt_get_agent = f"CASE WHEN MAX(a.login_name) IS NOT NULL THEN MAX(a.login_name) ELSE u.login_name end"

    if user.role != settings.SUPER_USER:
        admin_id = user.id

        stmt_users = f"""SELECT users.id AS users_id
                         FROM users
                         WHERE users.admin_parent_id = {admin_id} OR users.id = {admin_id}
                    """

        stmt_orders = f"""
                              SELECT u.client_code as client_code,
                                  {stmt_get_agent}  as agent_name ,
                                  u.login_name as login_name,
                                  u.phone as phone,
                                  u.email as email,
                                  u.is_at2 as is_at2,
                                  o.id as id,
                                  o.stage as stage,
                                  o.payment as payment,
                                  o.order_idn as order_idn,
                                  o.category as category,
                                  o.company_type as company_type,
                                  o.company_name as company_name,
                                  o.company_idn as company_idn,
                                  o.external_problem as external_problem,
                                  o.edo_type as edo_type,
                                  o.mark_type as mark_type,
                                  o.user_comment as user_comment,
                                  o.has_new_tnveds as has_new_tnveds,
                                  o.manager_id as manager_id,
                                  o.to_delete as to_delete,
                                  o.crm_created_at as crm_created_at,
                                  o.processing_info as processing_info,
                                  MAX(orf.origin_name) as order_file,
                                  MAX(orf.file_link) as order_file_link,
                                  MAX(managers.login_name) as manager,
                                  o.stage_setter_name as stage_setter_name,
                                  {additional_stmt}
                                  COUNT(o.id) as row_count,
                                  {SQLQueryCategoriesAll.get_stmt(field='subcategory')} as subcategory,
                                  {SQLQueryCategoriesAll.get_stmt(field='declar_doc')} as declar_doc,
                                  {SQLQueryCategoriesAll.get_stmt(field='marks_count')} as pos_count
                              FROM public.users u
                                  JOIN public.orders o ON o.user_id = u.id
                                  LEFT JOIN public.users a ON u.admin_parent_id = a.id
                                  LEFT JOIN public.order_files orf ON o.id=orf.order_id
                                  {SQLQueryCategoriesAll.get_joins()}
                                  LEFT JOIN public.users managers ON o.manager_id = managers.id
                        WHERE u.id in({stmt_users}) AND {conditional_stmt} AND o.to_delete != True
                        GROUP BY u.id, o.id, o.crm_created_at
                        ORDER BY o.crm_created_at ASC 
                       """
    else:
        stmt_orders = f"""
                              SELECT 
                                  u.client_code as client_code,
                                  {stmt_get_agent} as agent_name ,
                                  u.login_name as login_name, 
                                  u.phone as phone, 
                                  u.email as email, 
                                  u.is_at2 as is_at2,
                                  o.id as id,
                                  o.stage as stage,
                                  o.payment as payment,
                                  o.order_idn as order_idn,
                                  o.category as category,
                                  o.company_type as company_type,
                                  o.company_name as company_name,
                                  o.company_idn as company_idn,
                                  o.external_problem as external_problem,
                                  o.edo_type as edo_type,
                                  o.mark_type as mark_type,
                                  o.user_comment as user_comment,
                                  o.has_new_tnveds as has_new_tnveds,
                                  o.manager_id as manager_id,
                                  o.to_delete as to_delete,
                                  o.crm_created_at as crm_created_at,
                                  o.processing_info as processing_info,
                                  MAX(orf.origin_name) as order_file,
                                  MAX(orf.file_link) as order_file_link,
                                  MAX(managers.login_name) as manager,
                                  o.stage_setter_name as stage_setter_name,
                                  {additional_stmt}
                                  COUNT(o.id) as row_count,
                                  {SQLQueryCategoriesAll.get_stmt(field='subcategory')} as subcategory,
                                  {SQLQueryCategoriesAll.get_stmt(field='declar_doc')} as declar_doc,
                                  {SQLQueryCategoriesAll.get_stmt(field='marks_count')} as pos_count
                              FROM public.users u
                                  JOIN public.orders o ON o.user_id = u.id  
                                  LEFT JOIN public.users a ON u.admin_parent_id = a.id  
                                  LEFT JOIN public.order_files orf ON o.id=orf.order_id 
                                  {SQLQueryCategoriesAll.get_joins()}
                                  LEFT JOIN public.users managers ON o.manager_id = managers.id 
                              WHERE  {conditional_stmt} AND o.to_delete != True
                              GROUP BY u.id, o.id, o.crm_created_at
                              ORDER BY o.crm_created_at ASC
                               """

    res = db.session.execute(text(stmt_orders))
    return res.fetchall()


def helper_get_agent_stage_orders(stage: int, user: User, category: str = 'all') -> list:
    """
    returns a list of orders for cancelled sent and performed stages asynchroniously
    :param stage: stage of order
    :param user: current agent
    :param category: category
    :return:
    """
    date_compare = date.today() - timedelta(days=settings.OrderStage.DAYS_UPDATE_CONTENT)
    time_field = settings.OrderStage.STAGES_TF.get(stage, 'crm_created_at')
    time_stmt = f"AND o.{time_field} > '{date_compare}'" \
        if stage in [settings.OrderStage.SENT, settings.OrderStage.CANCELLED, settings.OrderStage.CRM_PROCESSED] else ""

    category_stmt = f"AND o.category='{category}'" if category in settings.CATEGORIES_UPLOAD else ""
    if user.role != settings.SUPER_USER:
        admin_id = user.id

        stmt_users = f"""SELECT users.id AS users_id
                                 FROM users
                                 WHERE users.admin_parent_id = {admin_id} OR users.id = {admin_id}
                            """

        stmt_orders = text(f"""
                                      SELECT u.client_code as client_code,
                                          CASE WHEN MAX(a.login_name) IS NOT NULL THEN MAX(a.login_name) ELSE u.login_name end as agent_name ,
                                          u.login_name as login_name,
                                          u.phone as phone,
                                          u.email as email,
                                          u.is_at2 as is_at2,
                                          o.id as id,
                                          o.stage as stage,
                                          o.payment as payment,
                                          o.order_idn as order_idn,
                                          o.category as category,
                                          o.company_type as company_type,
                                          o.company_name as company_name,
                                          o.company_idn as company_idn,
                                          o.external_problem as external_problem,
                                          o.edo_type as edo_type,
                                          o.mark_type as mark_type,
                                          o.user_comment as user_comment,
                                          o.has_new_tnveds as has_new_tnveds,
                                          o.manager_id as manager_id,
                                          o.to_delete as to_delete,
                                          o.crm_created_at as crm_created_at,
                                          o.processing_info as processing_info,
                                          MAX(orf.origin_name) as order_file,
                                          MAX(orf.file_link) as order_file_link,
                                          MAX(managers.login_name) as manager,
                                          o.stage_setter_name as stage_setter_name,
                                          o.comment_problem as comment_problem,
                                          o.comment_cancel as comment_cancel,
                                          o.cp_created as cp_created,
                                          o.cc_created as cc_created,
                                          o.crm_created_at as crm_created_at,
                                          o.p_started as p_started,
                                          o.m_started as m_started,
                                          o.m_finished as m_finished,
                                          o.sent_at as sent_at,
                                          o.closed_at as closed_at,
                                          COUNT(o.id) as row_count,
                                          {SQLQueryCategoriesAll.get_stmt(field='subcategory')} as subcategory,
                                          {SQLQueryCategoriesAll.get_stmt(field='declar_doc')} as declar_doc,
                                          {SQLQueryCategoriesAll.get_stmt(field='marks_count')} as pos_count
                                      FROM public.users u
                                          JOIN public.orders o ON o.user_id = u.id
                                          LEFT JOIN public.users a ON u.admin_parent_id = a.id  
                                          LEFT JOIN public.order_files orf ON o.id=orf.order_id
                                          {SQLQueryCategoriesAll.get_joins()}
                                          LEFT JOIN public.users managers ON o.manager_id = managers.id
                                WHERE o.stage=:stage AND u.id in({stmt_users}) {time_stmt} AND o.to_delete != True {category_stmt}
                                GROUP BY u.id, o.id, o,crm_created_at
                                ORDER BY o.crm_created_at ASC 
                               """.format(time_stmt=time_stmt)).bindparams(stage=stage)
    else:

        stmt_orders = text(f"""
                              SELECT 
                                  u.client_code as client_code,
                                  CASE WHEN MAX(a.login_name) IS NOT NULL THEN MAX(a.login_name) ELSE u.login_name end as agent_name ,
                                  u.login_name as login_name, 
                                  u.phone as phone, 
                                  u.email as email, 
                                  u.is_at2 as is_at2,
                                  o.id as id,
                                  o.stage as stage,
                                  o.payment as payment,
                                  o.order_idn as order_idn,
                                  o.category as category,
                                  o.company_type as company_type,
                                  o.company_name as company_name,
                                  o.company_idn as company_idn,
                                  o.external_problem as external_problem,
                                  o.edo_type as edo_type,
                                  o.mark_type as mark_type,
                                  o.user_comment as user_comment,
                                  o.has_new_tnveds as has_new_tnveds,
                                  o.manager_id as manager_id,
                                  o.to_delete as to_delete,
                                  o.crm_created_at as crm_created_at,
                                  o.processing_info as processing_info,
                                  MAX(orf.origin_name) as order_file,
                                  MAX(orf.file_link) as order_file_link,
                                  MAX(managers.login_name) as manager,
                                  o.stage_setter_name as stage_setter_name,
                                  o.comment_problem as comment_problem,
                                  o.comment_cancel as comment_cancel,
                                  o.cp_created as cp_created,
                                  o.cc_created as cc_created,
                                  o.crm_created_at as crm_created_at,
                                  o.p_started as p_started,
                                  o.m_started as m_started,
                                  o.m_finished as m_finished,
                                  o.sent_at as sent_at,
                                  o.closed_at as closed_at,
                                  COUNT(o.id) as row_count,
                                  {SQLQueryCategoriesAll.get_stmt(field='subcategory')} as subcategory,
                                  {SQLQueryCategoriesAll.get_stmt(field='declar_doc')} as declar_doc,
                                  {SQLQueryCategoriesAll.get_stmt(field='marks_count')} as pos_count
                              FROM public.users u
                                  JOIN public.orders o ON o.user_id = u.id  
                                  LEFT JOIN public.users a ON u.admin_parent_id = a.id  
                                  LEFT JOIN public.order_files orf ON o.id=orf.order_id 
                                  {SQLQueryCategoriesAll.get_joins()} 
                                  LEFT JOIN public.users managers ON o.manager_id = managers.id
                              WHERE  o.stage=:stage {time_stmt} AND o.to_delete != True {category_stmt}
                              GROUP BY u.id, o.id, o.crm_created_at
                              ORDER BY o.crm_created_at ASC
                               """.format(time_stmt=time_stmt)).bindparams(stage=stage)
    res = db.session.execute(stmt_orders)

    return res.fetchall()


def helper_get_manager_orders(
        user: User,
        filtered_manager_id: int | None = None,
        category: str | None = None,
        stage: int | None = None,
) -> tuple:
    manager_id = user.id
    stage_stmt = f" AND o.stage={stage}" if stage in settings.OrderStage.CHECK_TUPLE else ""
    category_stmt = f" AND o.category=\'{category}\'" if category in settings.CATEGORIES_UPLOAD else ""
    additional_stmt = """
                            o.comment_problem as comment_problem,
                            o.comment_cancel as comment_cancel,
                            o.cp_created as cp_created,
                            o.cc_created as cc_created,
                            o.crm_created_at as crm_created_at,
                            o.p_started as p_started,
                            o.m_started as m_started,
                            o.m_finished as m_finished,
                            o.sent_at as sent_at,
                            o.closed_at as closed_at,
                         """

    conditional_stmt_common = f"(o.stage!={settings.OrderStage.POOL} AND o.stage>{settings.OrderStage.CREATING} AND o.stage<={settings.OrderStage.MANAGER_SOLVED} AND o.stage!={settings.OrderStage.CRM_PROCESSED})"

    if user.role not in [settings.SUPER_USER, settings.SUPER_MANAGER, ]:
        conditional_stmt = f"(({conditional_stmt_common} AND o.manager_id=:manager_id) OR o.stage={settings.OrderStage.POOL}){category_stmt}{stage_stmt}"
        stmt_orders = text(f"""
                             SELECT u.client_code as client_code,
                                 u.login_name as login_name, 
                                 u.phone as phone, 
                                 u.email as email, 
                                 o.id as id,
                                 o.stage as stage,
                                 o.payment as payment,
                                 o.order_idn as order_idn,
                                 o.category as category,
                                 o.company_type as company_type,
                                 o.company_name as company_name,
                                 o.company_idn as company_idn,
                                 o.external_problem as external_problem,
                                 o.edo_type as edo_type,
                                 o.mark_type as mark_type,
                                 o.user_comment as user_comment,
                                 o.has_new_tnveds as has_new_tnveds,
                                 o.to_delete as to_delete,
                                 o.processing_info as processing_info,
                                 MAX(orf.origin_name) as order_file,
                                 MAX(orf.file_link) as order_file_link,
                                 o.manager_id as manager_id,
                                 MAX(managers.login_name) as manager,
                                 o.stage_setter_name as stage_setter_name,
                                 {additional_stmt}
                                 COUNT(o.id) as row_count,
                                 {SQLQueryCategoriesAll.get_stmt(field='subcategory')} as subcategory,
                                 {SQLQueryCategoriesAll.get_stmt(field='declar_doc')} as declar_doc,
                                 {SQLQueryCategoriesAll.get_stmt(field='marks_count')} as pos_count
                             FROM public.users u
                                 JOIN public.orders o ON o.user_id = u.id
                                 LEFT JOIN public.users a ON u.admin_parent_id = a.id   
                                 LEFT JOIN public.order_files orf ON o.id=orf.order_id
                                 {SQLQueryCategoriesAll.get_joins()} 
                                 LEFT JOIN public.users managers ON o.manager_id = managers.id
                           WHERE {conditional_stmt} AND o.to_delete != True
                           GROUP BY u.id, o.id, o.crm_created_at
                          ORDER BY o.p_started ASC NULLS LAST, o.crm_created_at ASC
                          """).bindparams(manager_id=manager_id)
    else:
        manager_condition = f" AND o.manager_id=:filtered_manager_id" if filtered_manager_id else ""
        conditional_stmt = f"({conditional_stmt_common}{manager_condition} OR o.stage={settings.OrderStage.POOL}){category_stmt}{stage_stmt}"
        # visibility spec orders condition
        vsoc = f" AND ( (o.manager_id is not NULL AND managers.role not in ('{settings.SUPER_USER}', '{settings.MARKINERIS_ADMIN_USER}')) or o.manager_id is NULL)" if current_user.role == settings.SUPER_MANAGER else ""
        stmt_orders_qry = text(f"""
                              SELECT 
                                  u.client_code as client_code,
                                  u.login_name as login_name, 
                                  u.phone as phone, 
                                  u.email as email, 
                                  o.id as id,
                                  o.stage as stage,
                                  o.payment as payment,
                                  o.order_idn as order_idn,
                                  o.category as category,
                                  o.company_type as company_type,
                                  o.company_name as company_name,
                                  o.company_idn as company_idn,
                                  o.external_problem as external_problem,
                                  o.edo_type as edo_type,
                                  o.mark_type as mark_type,
                                  o.user_comment as user_comment,
                                  o.has_new_tnveds as has_new_tnveds,
                                  o.to_delete as to_delete,
                                  o.processing_info as processing_info,
                                  MAX(orf.origin_name) as order_file,
                                  MAX(orf.file_link) as order_file_link,
                                  o.manager_id as manager_id,
                                  MAX(managers.login_name) as manager,
                                  o.stage_setter_name as stage_setter_name,
                                  {additional_stmt}
                                  COUNT(o.id) as row_count,
                                  {SQLQueryCategoriesAll.get_stmt(field='subcategory')} as subcategory,
                                  {SQLQueryCategoriesAll.get_stmt(field='declar_doc')} as declar_doc,
                                  {SQLQueryCategoriesAll.get_stmt(field='marks_count')} as pos_count
                              FROM public.users u
                                  JOIN public.orders o ON o.user_id = u.id
                                  LEFT JOIN public.users a ON u.admin_parent_id = a.id   
                                  LEFT JOIN public.order_files orf ON o.id=orf.order_id
                                  {SQLQueryCategoriesAll.get_joins()}
                                  LEFT JOIN public.users managers ON o.manager_id = managers.id 
                              WHERE  {conditional_stmt}{vsoc} AND o.to_delete != True
                              GROUP BY u.id, o.id, o.crm_created_at
                              ORDER BY o.p_started ASC NULLS LAST, o.crm_created_at ASC
                               """)
        stmt_orders = stmt_orders_qry.bindparams(
            filtered_manager_id=filtered_manager_id) if filtered_manager_id else stmt_orders_qry
    res = db.session.execute(stmt_orders)
    return res.fetchall()


def helper_check_extension(filename: str) -> bool:
    return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in settings.CRM_ALLOWED_EXTENSIONS


def helper_create_filename(order_idn: int, manager_name: str, filename: str) -> tuple[Optional[str], Optional[str]]:
    try:
        extension = filename.rsplit('.')[-1]
    except Exception:
        return None, None
    origin = f"{manager_name}_order_{order_idn}.{extension}"

    prefix = uuid4().hex[:8] + str(int(datetime.now().timestamp()))
    fs_name = prefix + origin
    return origin, fs_name


def helper_m_order_processed(user: User, o_id: int, manager_id: int, f_manager_id: int = None) -> Response:
    status = settings.ERROR
    message = ''

    stage = request.form.get("stage", -1, int)
    category = request.form.get("category", 'all')
    filtered_manager_id = request.args.get('filtered_manager_id', None, int)

    if not stage or stage not in settings.OrderStage.CHECK_TUPLE:
        message = f"Invalid stage: {stage}"
        logger.error(message)
        return jsonify({'htmlresponse': None, 'status': status, 'message': message})
    if not category or (category != 'all' and category not in settings.CATEGORIES_UPLOAD):
        message = f" Invalid category: {category}"
        logger.error(message)
        return jsonify({'htmlresponse': None, 'status': status, 'message': message})

    order_stmt = text("""
                    SELECT o.id as id,
                        o.order_idn as order_idn,
                        o.processing_info as processing_info,
                        o.stage as stage,
                        orf.id as of_id,
                        orf.file_system_name as file_system_name,
                        orf.file_link as file_link
                    FROM public.orders o 
                    LEFT JOIN public.order_files orf ON o.id=orf.order_id
                    WHERE o.id=:o_id AND o.manager_id=:manager_id AND o.to_delete != True;
                  """).bindparams(o_id=o_id, manager_id=manager_id)
    order_info = db.session.execute(order_stmt).fetchone()

    if not order_info:
        message = settings.Messages.ORDER_MANAGER_PROCESSED_ABS_ERROR
        return jsonify({'htmlresponse': None, 'status': status, 'message': message})
    if not order_info.file_system_name and not order_info.file_link:
        message = settings.Messages.ORDER_MANAGER_PROCESSED_ABS_FILE_ERROR
        return jsonify({'htmlresponse': None, 'status': status, 'message': message})
    elif order_info.file_system_name:
        # check order file
        check_of_status, check_of_message = check_order_file(order_file_name=order_info.file_system_name, o_id=o_id)
        if order_info.file_system_name and not check_of_status:
            return jsonify({'htmlresponse': None, 'status': status, 'message': check_of_message})
    if not order_info.processing_info:
        message = settings.Messages.ORDER_MANAGER_PROCESSED_ABS_PROCESSING_INFO
        return jsonify({'htmlresponse': None, 'status': status, 'message': message})
    if user.id != manager_id and user.role not in [settings.SUPER_USER, settings.SUPER_MANAGER, settings.MARKINERIS_ADMIN_USER]:
        message = settings.Messages.STRANGE_REQUESTS
        return jsonify({'htmlresponse': None, 'status': status, 'message': message})

    dt_manager = datetime.now()
    stmt = text("""
               UPDATE public.orders 
               SET stage_setter_name=:stage_setter_name, stage=:stage, m_finished=:m_finished
               WHERE id=:o_id; 
               """).bindparams(o_id=o_id, stage_setter_name=user.login_name, stage=settings.OrderStage.MANAGER_PROCESSED, m_finished=dt_manager )
    try:
        db.session.execute(stmt)
        db.session.commit()
        message = settings.Messages.ORDER_MANAGER_PROCESSED.format(order_idn=order_info.order_idn)
        status = settings.SUCCESS
        update_orders = helper_get_manager_orders(user=user, filtered_manager_id=filtered_manager_id,
                                                  category=category, stage=stage)

        return jsonify({'htmlresponse': render_template(
            'crm_mod_v1/crmm/updated_stages/orders_{stage}.html'.format(stage=stage), **locals()),
            'quantity': len(update_orders), 'status': status, 'message': message})
    except IntegrityError:
        db.session.rollback()
        message = settings.Messages.ORDER_MANAGER_PROCESSED_ERROR
        logger.error(message)
        return jsonify({'htmlresponse': None, 'status': status, 'message': message})


# push to problem-solved stage
def helper_m_order_ps(user: User, o_id: int, manager_id: int) -> Response:
    status = settings.ERROR
    message = ''

    stage = request.form.get("stage", -1, int)
    category = request.form.get("category", 'all')
    filtered_manager_id = request.args.get('filtered_manager_id', None, int)

    if not stage or stage not in settings.OrderStage.CHECK_TUPLE:
        message = f"Invalid stage: {stage}"
        logger.error(message)
        return jsonify({'htmlresponse': None, 'status': status, 'message': message})
    if not category or (category != 'all' and category not in settings.CATEGORIES_UPLOAD):
        message = f" Invalid category: {category}"
        logger.error(message)
        return jsonify({'htmlresponse': None, 'status': status, 'message': message})

    order_stmt = text("""
                    SELECT o.id as id,
                        o.stage as stage,
                        o.user_id as user_id,
                        o.order_idn as order_idn,
                        o.processing_info as processing_info,
                        orf.id as of_id,
                        orf.file_system_name as file_system_name,
                        orf.file_link as file_link
                    FROM public.orders o 
                    LEFT JOIN public.order_files orf ON o.id=orf.order_id
                    WHERE o.id=:o_id AND o.manager_id=:manager_id AND o.to_delete != True;
                  """).bindparams(o_id=o_id, manager_id=manager_id)
    order_info = db.session.execute(order_stmt).fetchone()

    if not order_info:
        message = settings.Messages.ORDER_MANAGER_PS_ABS_ERROR
        return jsonify({'htmlresponse': None, 'status': status, 'message': message})
    if not order_info.file_system_name and not order_info.file_link:
        message = settings.Messages.ORDER_MANAGER_PROCESSED_ABS_FILE_ERROR
        return jsonify({'htmlresponse': None, 'status': status, 'message': message})
    elif order_info.file_system_name:
        # check order file
        check_of_status, check_of_message = check_order_file(order_file_name=order_info.file_system_name, o_id=o_id)
        if order_info.file_system_name and not check_of_status:
            return jsonify({'htmlresponse': None, 'status': status, 'message': check_of_message})
    if not order_info.processing_info:
        message = settings.Messages.ORDER_MANAGER_PROCESSED_ABS_PROCESSING_INFO
        return jsonify({'htmlresponse': None, 'status': status, 'message': message})
    if user.id != manager_id and user.role not in [settings.SUPER_USER, settings.SUPER_MANAGER, settings.MARKINERIS_ADMIN_USER]:
        message = settings.Messages.STRANGE_REQUESTS
        return jsonify({'htmlresponse': None, 'status': status, 'message': message})

    dt_manager = datetime.now()
    stmt = text("""
                   UPDATE public.orders 
                   SET stage_setter_name=:stage_setter_name, stage=:stage, m_finished=:m_finished
                   WHERE id=:o_id;
               """).bindparams(o_id=o_id, stage_setter_name=user.login_name, stage=settings.OrderStage.MANAGER_SOLVED, m_finished=dt_manager)
    try:
        db.session.execute(stmt)
        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        message = settings.Messages.ORDER_MANAGER_PROCESSED_ERROR
        logger.error(message)
        return jsonify({'htmlresponse': None, 'status': status, 'message': message})

    else:
        helper_send_user_order_tg_notify(user_id=order_info.user_id, order_idn=order_info.order_idn,
                                         order_stage=settings.OrderStage.MANAGER_SOLVED)

    message = settings.Messages.ORDER_MANAGER_PS.format(order_idn=order_info.order_idn)
    status = settings.SUCCESS
    update_orders = helper_get_manager_orders(user=user, filtered_manager_id=filtered_manager_id,
                                              category=category, stage=stage)
    return jsonify({'htmlresponse': render_template(
        'crm_mod_v1/crmm/updated_stages/orders_{stage}.html'.format(stage=stage), **locals()),
        'quantity': len(update_orders), 'status': status, 'message': message})


def helper_m_order_bp(user: User, o_id: int, manager_id: int) -> Response:
    status = settings.ERROR
    message = ''

    stage = request.form.get("stage", -1, int)
    category = request.form.get("category", 'all')
    filtered_manager_id = request.args.get('filtered_manager_id', None, int)

    if not stage or stage not in settings.OrderStage.CHECK_TUPLE:
        message = f"Invalid stage: {stage}"
        logger.error(message)
        return jsonify({'htmlresponse': None, 'status': status, 'message': message})
    if not category or (category != 'all' and category not in settings.CATEGORIES_UPLOAD):
        message = f" Invalid category: {category}"
        logger.error(message)
        return jsonify({'htmlresponse': None, 'status': status, 'message': message})

    order_stmt = text("""
                    SELECT o.id as id,
                        o.user_id as user_id,
                        o.order_idn as order_idn,
                        o.stage as stage
                    FROM public.orders o 
                    LEFT JOIN public.order_files orf ON o.id=orf.order_id
                    WHERE o.id=:o_id AND o.manager_id=:manager_id AND o.to_delete != True;
                  """).bindparams(o_id=o_id, manager_id=manager_id)
    order_info = db.session.execute(order_stmt).fetchone()

    if not order_info:
        message = settings.Messages.ORDER_MANAGER_PS_ABS_ERROR
        return jsonify({'htmlresponse': None, 'status': status, 'message': message})

    if user.role not in [settings.SUPER_USER, settings.SUPER_MANAGER] or order_info.stage not in [settings.OrderStage.MANAGER_PROCESSED, settings.OrderStage.MANAGER_SOLVED, settings.OrderStage.SENT]:
        flash(message=settings.Messages.STRANGE_REQUESTS, category='error')
        return redirect(url_for('crm_d.agents')) if user.role not in [settings.MANAGER_USER, settings.SUPER_MANAGER] \
            else redirect(url_for('crm_d.managers'))

    stmt = text(f"""UPDATE public.orders 
                    SET stage=:stage, cp_created=NULL, sent_at=NULL, m_finished=NULL
                    WHERE id=:o_id; 
               """).bindparams(o_id=o_id, stage=settings.OrderStage.MANAGER_START)
    try:
        db.session.execute(stmt)
        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        message = settings.Messages.ORDER_MANAGER_BP_ERROR
        logger.error(message)
        return jsonify({'htmlresponse': None, 'status': status, 'message': message})
    else:
        helper_send_user_order_tg_notify(user_id=order_info.user_id, order_idn=order_info.order_idn,
                                         order_stage=settings.OrderStage.MANAGER_START)

    message = settings.Messages.ORDER_MANAGER_BP.format(order_idn=order_info.order_idn)
    update_orders = helper_get_manager_orders(user=user, filtered_manager_id=filtered_manager_id,
                                              stage=stage, category=category)
    status = settings.SUCCESS
    return jsonify({'htmlresponse': render_template(
        'crm_mod_v1/crmm/updated_stages/orders_{stage}.html'.format(stage=stage), **locals()),
        'quantity': len(update_orders), 'status': status, 'message': message})


def helper_a_order_bp(user: User, o_id: int, manager_id: int, f_manager_id: int = None) -> Response:
    status = 'danger'
    message = ''

    stage = request.form.get("stage", -1, int)
    category = request.form.get("category", 'all')

    if not stage or stage not in settings.OrderStage.CHECK_TUPLE:
        mes = f"{message} Invalid stage: {stage}"
        logger.error(mes)
        return jsonify({'htmlresponse': None, 'status': status, 'message': mes})
    if not category or (category != 'all' and category not in settings.CATEGORIES_UPLOAD):
        mes = f"{message} Invalid category: {category}"
        logger.error(mes)
        return jsonify({'htmlresponse': None, 'status': status, 'message': mes})

    order_stmt = text(f"""
                    SELECT o.id as id,
                        o.user_id as user_id,
                        o.order_idn as order_idn,
                        o.stage as stage
                    FROM public.orders o 
                    LEFT JOIN public.order_files orf ON o.id=orf.order_id
                    WHERE o.id=:o_id AND o.manager_id=:manager_id AND o.to_delete != True;
                  """).bindparams(o_id=o_id, manager_id=manager_id)
    order_info = db.session.execute(order_stmt).fetchone()

    if not order_info:
        message = settings.Messages.ORDER_MANAGER_PS_ABS_ERROR
        return jsonify({'status': status, 'message': message})

    # todo: КТО МОЖЕТ ВОЗВРАЩАТЬ ЗАКАЗ МЕНЕДЖЕРАМ И ЧТО ВОЗВРАЩАТЬ JSON ИЛИ РЕДИРЕКТ
    if (user.role not in [settings.SUPER_USER, settings.SUPER_MANAGER, settings.MARKINERIS_ADMIN_USER, settings.ADMIN_USER]
            or order_info.stage not in [settings.OrderStage.MANAGER_PROCESSED, settings.OrderStage.MANAGER_SOLVED, settings.OrderStage.SENT]):
        return redirect(url_for('crm_d.agents')) if user.role not in [settings.MANAGER_USER, settings.SUPER_MANAGER]\
            else redirect(url_for('crm_d.managers', filtered_manager_id=f_manager_id))

    stmt = text(f"""UPDATE public.orders 
                    SET stage={settings.OrderStage.MANAGER_START}, cp_created=NULL, sent_at=NULL, m_finished=NULL
                    WHERE id=:o_id; 
               """).bindparams(o_id=o_id)
    try:
        db.session.execute(stmt)
        db.session.commit()
        status = settings.SUCCESS
        message = settings.Messages.ORDER_MANAGER_BP.format(order_idn=order_info.order_idn)
    except IntegrityError:
        db.session.rollback()
        message = settings.Messages.ORDER_MANAGER_BP_ERROR
        logger.error(message)
        return jsonify({'status': status, 'message': message})

    else:
        helper_send_user_order_tg_notify(user_id=order_info.user_id, order_idn=order_info.order_idn,
                                         order_stage=settings.OrderStage.MANAGER_START)

    update_orders = helper_get_agent_stage_orders(stage=stage, category=category, user=current_user)

    status = settings.SUCCESS
    message = settings.Messages.ORDER_CHANGE_STAGE_SUCCESS
    return jsonify({'htmlresponse': render_template(
        'crm_mod_v1/crma/updated_stages/orders_{stage}.html'.format(stage=stage), **locals()),
                    'quantity': len(update_orders), 'status': status, 'message': message})


def helper_attach_file(manager: str, manager_id: int, o_id: int) -> Response:
    status = settings.ERROR
    message = ''
    htmlresponse_file = ''
    htmlresponse_footer = ''
    order_stmt = text(f"""
                        SELECT o.id as id,
                            o.order_idn as order_idn,
                            o.stage as stage,
                            orf.id as of_id,
                            orf.file_system_name as file_system_name
                        FROM public.orders o 
                        LEFT JOIN public.order_files orf ON o.id=orf.order_id
                        WHERE o.id=:o_id AND o.manager_id=:manager_id AND o.to_delete != True;
                      """).bindparams(o_id=o_id, manager_id=manager_id)
    order_info = db.session.execute(order_stmt).fetchone()

    if not order_info:
        message = settings.Messages.ORDER_ATTACH_FILE_ABS_ERROR
        return jsonify({'htmlresponse_file': htmlresponse_file,
                        'htmlresponse_footer': htmlresponse_footer,
                        'status': status, 'message': message})

    file = request.files.get('order_file', '')

    check, check_file_message = helper_check_attached_file(order_file=file, order_idn=order_info.order_idn)
    if not check:
        message = check_file_message
        return jsonify({'htmlresponse_file': htmlresponse_file,
                        'htmlresponse_footer': htmlresponse_footer,
                        'status': status, 'message': message})

    s3_service = get_s3_service()

    of_id = order_info.of_id
    ofs_name = order_info.file_system_name

    try:
        if ofs_name and ofs_name in s3_service.list_objects(settings.MINIO_CRM_BUCKET_NAME):
            s3_service.remove_object(object_name=ofs_name, bucket_name=settings.MINIO_CRM_BUCKET_NAME)
    except Exception:
        logger.exception("Ошибка при удалении файла из хранилища")
        message = "Ошибка при удалении файла из хранилища, попробуйте позже."
        return jsonify({'htmlresponse_file': htmlresponse_file,
                        'htmlresponse_footer': htmlresponse_footer,
                        'status': status, 'message': message})

    filename = secure_filename(filename=file.filename)
    origin, fs_name = helper_create_filename(order_idn=order_info.order_idn, manager_name=manager, filename=filename)

    if not fs_name:
        message = settings.Messages.CRM_FILENAME_ERROR,
        return jsonify({'htmlresponse_file': htmlresponse_file,
                        'htmlresponse_footer': htmlresponse_footer,
                        'status': status, 'message': message})

    # insert data
    stmt = text(f"""UPDATE public.order_files 
                 SET origin_name='{origin}', file_system_name='{fs_name}', file_link='', order_id=:o_id 
                 WHERE id={of_id}
                """ if of_id else f"""
                   INSERT INTO public.order_files (origin_name, file_system_name, file_link, order_id)
                   VALUES ('{origin}', '{fs_name}', '', :o_id);
               """).bindparams(o_id=o_id)

    try:
        if file:
            try:
                s3_service.upload_file(
                    file_data=file.stream,
                    object_name=fs_name,
                    bucket_name=settings.MINIO_CRM_BUCKET_NAME,
                )
            except EmptyFileToUploadError:
                message = f"{settings.Messages.ORDER_ATTACH_FILE_ERROR} Переданный файл пуст"
                logger.error(message)
                return jsonify({'htmlresponse_file': htmlresponse_file,
                                'htmlresponse_footer': htmlresponse_footer,
                                'status': status, 'message': message})

        db.session.execute(stmt)
        db.session.commit()

        status = settings.SUCCESS
        message = settings.Messages.ORDER_ATTACH_FILE.format(order_idn=order_info.order_idn)

        stage = request.args.get('stage', 0, int)

        htmlresponse_file = render_template('crm_mod_v1/crmm/manager_file_block.html', **locals())
        htmlresponse_footer = render_template('crm_mod_v1/crmm/manager_footer_btn_block.html', **locals())
    except IntegrityError as ie:
        db.session.rollback()
        message = settings.Messages.ORDER_ATTACH_FILE_ERROR
        logger.error(message + str(ie))
    except Exception as e:
        message = settings.Messages.ORDER_ATTACH_FILE_ERROR
        logger.error(message + str(e))

    return jsonify({'htmlresponse_file': htmlresponse_file,
                    'htmlresponse_footer': htmlresponse_footer,
                    'status': status, 'message': message})


def helper_attach_of_link(manager: str, manager_id: int, o_id: int) -> Response:
    status = settings.ERROR
    message = ''
    htmlresponse_file = ''
    htmlresponse_footer = ''

    order_stmt = f"""
                        SELECT o.id as id,
                            o.order_idn as order_idn,
                            o.stage as stage,
                            orf.id as of_id,
                            orf.file_system_name as file_system_name
                        FROM public.orders o 
                        LEFT JOIN public.order_files orf ON o.id=orf.order_id
                        WHERE o.id={o_id} AND o.manager_id={manager_id} AND o.to_delete != True;
                      """
    order_info = db.session.execute(text(order_stmt)).fetchone()

    if not order_info:
        message = settings.Messages.ORDER_ATTACH_FILE_ABS_ERROR
        return jsonify({'htmlresponse_file': htmlresponse_file,
                        'htmlresponse_footer': htmlresponse_footer,
                        'status': status, 'message': message})

    file_link = request.form.get('of_link', '').replace('--', '')

    of_id = order_info.of_id
    ofs_name = order_info.file_system_name
    try:
        s3_service = get_s3_service()
        if ofs_name and ofs_name in s3_service.list_objects(settings.MINIO_CRM_BUCKET_NAME):
            s3_service.remove_object(object_name=ofs_name, bucket_name=settings.MINIO_CRM_BUCKET_NAME)
    except Exception:
        logger.exception("Ошибка при удалении файла из хранилища")
        message = "Ошибка при удалении файла из хранилища, попробуйте позже."
        return jsonify({'htmlresponse_file': htmlresponse_file,
                        'htmlresponse_footer': htmlresponse_footer,
                        'status': status, 'message': message})

    # insert data
    stmt = f"""UPDATE public.order_files 
                 SET origin_name='', file_system_name='', file_link='{file_link}', order_id={o_id} 
                 WHERE id={of_id}
                """ if of_id else f"""
                   INSERT INTO public.order_files (origin_name, file_system_name, file_link, order_id)
                   VALUES ('', '', '{file_link}', {o_id});
               """

    try:
        db.session.execute(text(stmt))
        db.session.commit()
        status = settings.SUCCESS
        message = settings.Messages.ORDER_ATTACH_FILE_LINK.format(order_idn=order_info.order_idn)

        stage = request.args.get('stage', 0, int)
        htmlresponse_file = render_template('crm_mod_v1/crmm/manager_file_block.html', **locals())
        htmlresponse_footer = render_template('crm_mod_v1/crmm/manager_footer_btn_block.html', **locals())
    except IntegrityError as e:
        db.session.rollback()
        message = settings.Messages.ORDER_ATTACH_FILE_LINK_ERROR
        logger.error(f"{message} {e}")

    return {'htmlresponse_file': htmlresponse_file,
            'htmlresponse_footer': htmlresponse_footer,
            'status': status, 'message': message}


def helper_download_file(manager_id: int, o_id: int, user_type: str) -> Response:
    order_stmt = f"""
        SELECT 
            o.id AS id,
            o.stage AS stage,
            orf.id AS of_id,
            orf.origin_name AS origin_name,
            orf.file_system_name AS file_system_name,
            CASE 
                WHEN a.login_name IS NOT NULL THEN a.login_name 
                ELSE u.login_name 
            END AS agent_name
        FROM public.orders o 
        LEFT JOIN public.order_files orf ON o.id = orf.order_id
        LEFT JOIN public.users u ON o.user_id = u.id
        LEFT JOIN public.users a ON u.admin_parent_id = a.id
        WHERE o.id = :o_id 
          AND o.manager_id = :manager_id 
          AND o.to_delete != TRUE
        LIMIT 1;
    """

    order_info = db.session.execute(
        text(order_stmt),
        {"o_id": o_id, "manager_id": manager_id}
    ).fetchone()

    if not order_info:
        flash(message=settings.Messages.ORDER_DOWNLOAD_FILE_ABS_ERROR, category='error')
        return redirect(url_for(f'crm_d.{user_type}'))

    # Проверка доступа для администратора
    if current_user.role == settings.ADMIN_USER:
        if order_info.agent_name != current_user.login_name:
            flash(message="Недостаточно прав для скачивания этого файла.", category='error')
            return redirect(url_for(f'crm_d.{user_type}'))

    o_name, fs_name = order_info.origin_name, order_info.file_system_name

    if not check_order_file(order_file_name=fs_name, o_id=o_id):
        return redirect(url_for(f'crm_d.{user_type}'))

    return download_file_from_minio(
        object_name=fs_name,
        bucket_name=settings.MINIO_CRM_BUCKET_NAME,
        download_name=o_name
    )


def helper_delete_order_file(manager_id: int, o_id: int) -> Response:
    status = settings.ERROR
    message = ''
    htmlresponse_file = ''
    htmlresponse_footer = ''

    order_stmt = f"""
                        SELECT o.id as id,
                            o.order_idn as order_idn,
                            o.stage as stage,
                            orf.id as of_id,
                            orf.file_system_name as file_system_name,
                            managers.login_name as manager
                        FROM public.orders o 
                        LEFT JOIN public.order_files orf ON o.id=orf.order_id
                        LEFT JOIN public.users managers ON o.manager_id = managers.id
                        WHERE o.id={o_id} AND o.manager_id={manager_id} AND o.to_delete != True;
                      """
    order_info = db.session.execute(text(order_stmt)).fetchone()

    if not order_info:
        message = settings.Messages.ORDER_DELETE_FILE_ABS_ERROR
        return jsonify({'htmlresponse_file': htmlresponse_file,
                        'htmlresponse_footer': htmlresponse_footer,
                        'status': status, 'message': message})

    of_id = order_info.of_id
    ofs_name = order_info.file_system_name

    try:
        s3_service = get_s3_service()
        if ofs_name and ofs_name in s3_service.list_objects(settings.MINIO_CRM_BUCKET_NAME):
            s3_service.remove_object(object_name=ofs_name, bucket_name=settings.MINIO_CRM_BUCKET_NAME)
    except Exception:
        logger.exception("Ошибка при удалении файла из хранилища")
        message = "Ошибка при удалении файла из хранилища, попробуйте позже."
        return jsonify({'htmlresponse_file': htmlresponse_file,
                        'htmlresponse_footer': htmlresponse_footer,
                        'status': status, 'message': message})

    stmt = f"DELETE FROM public.order_files pof WHERE pof.id={of_id}"

    try:
        db.session.execute(text(stmt))
        db.session.commit()
        stage = request.args.get('stage', 0, int)
        delete_flag = True
        message = settings.Messages.ORDER_DELETE_FILE.format(order_idn=order_info.order_idn)
        status = settings.SUCCESS
        htmlresponse_file = render_template('crm_mod_v1/crmm/manager_file_block.html', **locals())
        htmlresponse_footer = render_template('crm_mod_v1/crmm/manager_footer_btn_block.html', **locals())
    except IntegrityError:
        db.session.rollback()
        message = settings.Messages.ORDER_DELETE_FILE_ERROR
        logger.error(message)

    return jsonify({'htmlresponse_file': htmlresponse_file,
                    'htmlresponse_footer': htmlresponse_footer,
                    'status': status, 'message': message})


def helper_change_manager(manager_id: int, o_id: int) -> Response:
    status = settings.ERROR

    order_stmt = f"""
                            SELECT o.id as id,
                                o.order_idn as order_idn,
                                o.stage as stage,
                                o.manager_id as manager_id
                            FROM public.orders o 
                            LEFT JOIN public.order_files orf ON o.id=orf.order_id
                            WHERE o.id={o_id} AND o.manager_id={manager_id} AND o.to_delete != True;
                          """
    order_info = db.session.execute(text(order_stmt)).fetchone()

    if not order_info:
        message = settings.Messages.ORDER_MANAGER_CHANGE_ABS_ERROR
        return jsonify(dict(status=status, message=message))

    new_manager_id = int(request.form.get('operator_id')) if request.form.get('operator_id') else None

    managers_ids = (User.query.with_entities(User.id).
                    filter((User.role == settings.MANAGER_USER) | (User.role == settings.SUPER_MANAGER)).all())

    if (new_manager_id, ) not in managers_ids:
        message = settings.Messages.ORDER_MANAGER_CHANGE_ABS_ERROR

    else:
        stmt = (text("UPDATE public.orders SET manager_id=:new_manager_id WHERE id=:o_id;")
                .bindparams(new_manager_id=new_manager_id, o_id=o_id))
        try:
            db.session.execute(stmt)
            db.session.commit()
            status = settings.SUCCESS
            message = settings.Messages.ORDER_MANAGER_CHANGE
        except IntegrityError:
            db.session.rollback()
            message = settings.Messages.ORDER_MANAGER_CHANGE_ERROR
            logger.error(settings.Messages.ORDER_MANAGER_CHANGE_ERROR)
        except Exception as e:
            db.session.rollback()
            message = settings.Messages.ORDER_MANAGER_CHANGE_ERROR
            logger.error(settings.Messages.ORDER_MANAGER_CHANGE_ERROR + str(e))
    return jsonify(dict(status=status, message=message))


def helper_cancel_order(user: User, o_id: int, cancel_comment: str):
    status = settings.ERROR

    stmt_get_agent = "SELECT a.admin_parent_id FROM public.users a WHERE a.id  = (SELECT o.user_id FROM public.orders o WHERE o.id=:o_id LIMIT 1)"
    order_stmt = text(f"""
                    SELECT o.id as id,
                        o.user_id as user_id,
                        o.order_idn as order_idn,
                        o.payment as payment,
                        o.transaction_id as transaction_id,
                        ({stmt_get_agent}) as agent_id,
                        orf.id as of_id,
                        orf.file_system_name as file_system_name
                    FROM public.orders o 
                    LEFT JOIN public.order_files orf ON o.id=orf.order_id
                    WHERE o.id=:o_id AND o.to_delete != True;
                  """).bindparams(o_id=o_id)
    order_info = db.session.execute(order_stmt).fetchone()
    # check for order exist and admin correct
    if not order_info or ((user.id != order_info.agent_id and user.id != order_info.user_id) and user.role != settings.SUPER_USER):
        flash(message=settings.Messages.STRANGE_REQUESTS, category='error')
        message = settings.Messages.STRANGE_REQUESTS
        return jsonify({'status': status, 'message': message})

    # delete rows from db and delete file from syst
    of_delete_remove(order_info=order_info, o_id=o_id)

    # update order stage
    dt_agent = datetime.now()
    order_query = text(f"""
               UPDATE public.orders 
               SET payment=False,
                   stage={settings.OrderStage.CANCELLED},
                   comment_cancel='{cancel_comment}',
                   cc_created='{dt_agent}'
               WHERE id=:o_id 
            """).bindparams(o_id=o_id)

    try:
        db.session.execute(order_query)

        if order_info.payment:
            # make restore balance and cancel userTransaction and update orders_stats
            h_cancel_order_process_payment(order_idn=order_info.order_idn,
                                           user_id=order_info.user_id)

        db.session.commit()
        status = settings.SUCCESS
        message = settings.Messages.ORDER_CANCEL.format(order_idn=order_info.order_idn)
    except IntegrityError as ie:
        db.session.rollback()
        message = settings.Messages.ORDER_CANCEL_ERROR
        logger.error(f"{settings.Messages.ORDER_CANCEL_ERROR} {ie}")
    except Exception as e:
        db.session.rollback()
        message = settings.Messages.ORDER_CANCEL_ERROR
        logger.error(str(e))
    else:
        helper_send_user_order_tg_notify(user_id=order_info.user_id, order_idn=order_info.order_idn,
                                         order_stage=settings.OrderStage.CANCELLED)
    return jsonify({'status': status, 'message': message})


def helper_change_agent_stage(o_id: int, stage: int, user: User):

    stmt_get_agent = "SELECT a.admin_parent_id FROM public.users a  WHERE a.id  = (SELECT o.user_id FROM public.orders o WHERE o.id=:o_id LIMIT 1)"

    order_stmt = f"""
                        SELECT o.id as id,
                            o.category as category,
                            o.company_type as company_type,
                            o.company_name as company_name,
                            o.company_idn as company_idn,
                            o.order_idn as order_idn,
                            o.created_at as created_at,
                            o.user_id as user_id,
                            o.transaction_id as transaction_id,
                            ut.op_cost as op_cost,
                            o.manager_id as manager_id,
                            o.comment_problem as comment_problem,
                            o.cp_created as cp_created,
                            o.m_started as m_started,
                            o.m_finished as m_finished,
                            o.crm_created_at as crm_created_at,
                            o.sent_at as sent_at,
                            o.stage_setter_name as stage_setter_name,
                            o.payment as payment,
                            o.to_delete as to_delete,
                            o.processing_info as processing_info,
                            ({stmt_get_agent}) as agent_id,
                            orf.id as of_id,
                            orf.file_system_name as file_system_name
                        FROM public.orders o 
                        LEFT JOIN public.order_files orf ON o.id=orf.order_id
                        LEFT JOIN public.user_transactions ut ON o.transaction_id=ut.id
                        WHERE o.id=:o_id AND o.to_delete != True;
                      """
    order_info = db.session.execute(text(order_stmt).bindparams(o_id=o_id)).fetchone()

    if not order_info:
        flash(message=settings.Messages.STRANGE_REQUESTS, category='error')
        return redirect(url_for('crm_d.agents'))
    # check for order exist and admin correct
    # ordinary user change state check for his admin
    user_order_agent_check = (order_info.agent_id and user.id != order_info.agent_id)
    # agent user change state check for his admin
    agent_order_agent_check = (not order_info.agent_id and user.id != order_info.user_id)

    if stage not in settings.OrderStage.CHECK_TUPLE or \
            ((user_order_agent_check or agent_order_agent_check) and user.role != settings.SUPER_USER):
        flash(message=settings.Messages.STRANGE_REQUESTS, category='error')
        return redirect(url_for('crm_d.agents'))
    # update order stage
    dt_agent = datetime.now()
    additional_stmt = ''
    match stage:
        case settings.OrderStage.POOL:
            if user.is_at2:
                # count all not paid orders and compare with balance
                balance_check, balance_message = helper_get_at2_pending_balance(admin_id=user.id,
                                                                                price_id=user.price_id,
                                                                                balance=user.balance,
                                                                                trust_limit=user.trust_limit)
                if not balance_check:
                    flash(message=balance_message, category='warning')
                    return redirect(url_for('crm_d.agents'))
            additional_stmt += f", p_started='{dt_agent}'"
            crm_os_status, crm_os_messsage = helper_crm_process_order_stats(o_id=o_id, order_info=order_info,
                                                                            stage=stage, additional_stmt=additional_stmt)
            flash(message=crm_os_messsage, category='success' if crm_os_status else 'danger')
            return redirect(url_for('crm_d.agents'))
        case settings.OrderStage.SENT:
            additional_stmt += f", sent_at='{dt_agent}'"
        case settings.OrderStage.CRM_PROCESSED:
            additional_stmt += f", closed_at='{dt_agent}', processed={True}"

            if not order_info.payment:
                flash(message=settings.Messages.ORDER_PROCESSED_NOT_PAID, category='error')
                logger.error(settings.Messages.ORDER_PROCESSED_NOT_PAID)
                return redirect(url_for('crm_d.agents'))

    stmt = f"""
                   UPDATE public.orders 
                   SET stage={stage}
                   {additional_stmt}
                   WHERE id={o_id} 
                """
    try:
        db.session.execute(text(stmt))
        db.session.commit()
        flash(message=settings.Messages.ORDER_STAGE_CHANGE)
    except IntegrityError:
        flash(message=settings.Messages.ORDER_STAGE_CHANGE_ERROR, category='error')
        db.session.rollback()
        logger.error(settings.Messages.ORDER_STAGE_CHANGE_ERROR)
    else:
        # sending user notification
        if stage == settings.OrderStage.SENT:
            helper_send_user_order_tg_notify(user_id=order_info.user_id, order_idn=order_info.order_idn,
                                             order_stage=stage)
    return redirect(url_for('crm_d.agents'))


def helper_change_agent_stage_bck(o_id: int, stage: int, user: User) -> tuple[bool, str]:

    stmt_get_agent = f"SELECT a.admin_parent_id FROM public.users a  WHERE a.id  = (SELECT o.user_id FROM public.orders o WHERE o.id=:o_id LIMIT 1)"

    order_stmt = f"""
                        SELECT o.id as id,
                            o.category as category,
                            o.company_type as company_type,
                            o.company_name as company_name,
                            o.company_idn as company_idn,
                            o.order_idn as order_idn,
                            o.created_at as created_at,
                            o.user_id as user_id,
                            o.transaction_id as transaction_id,
                            ut.op_cost as op_cost,
                            o.manager_id as manager_id,
                            o.comment_problem as comment_problem,
                            o.cp_created as cp_created,
                            o.m_started as m_started,
                            o.m_finished as m_finished,
                            o.crm_created_at as crm_created_at,
                            o.sent_at as sent_at,
                            o.stage_setter_name as stage_setter_name,
                            o.payment as payment,
                            o.to_delete as to_delete,
                            o.processing_info as processing_info,
                            ({stmt_get_agent}) as agent_id,
                            orf.id as of_id,
                            orf.file_system_name as file_system_name
                        FROM public.orders o 
                        LEFT JOIN public.order_files orf ON o.id=orf.order_id
                        LEFT JOIN public.user_transactions ut ON o.transaction_id=ut.id
                        WHERE o.id={o_id} AND o.to_delete != True;
                      """
    order_info = db.session.execute(text(order_stmt).bindparams(o_id=o_id)).fetchone()
    if not order_info:
        return False, settings.Messages.STRANGE_REQUESTS
    # check for order exist and admin correct
    # ordinary user change state check for his admin
    user_order_agent_check = (order_info.agent_id and user.id != order_info.agent_id)
    # agent user change state check for his admin
    agent_order_agent_check = (not order_info.agent_id and user.id != order_info.user_id)

    if stage not in settings.OrderStage.CHECK_TUPLE  or \
            ((user_order_agent_check or agent_order_agent_check) and user.role != settings.SUPER_USER):
        return False, settings.Messages.STRANGE_REQUESTS
    # update order stage
    dt_agent = datetime.now()
    additional_stmt = ''
    match stage:
        case settings.OrderStage.POOL:
            if user.is_at2:
                # count all not paid orders and compare with balance
                balance_check, balance_message = helper_get_at2_pending_balance(admin_id=user.id,
                                                                                price_id=user.price_id,
                                                                                balance=user.balance,
                                                                                trust_limit=user.trust_limit)
                if not balance_check:
                    return False, balance_message

            additional_stmt += f", p_started='{dt_agent}'"
            return helper_crm_process_order_stats(o_id=o_id, order_info=order_info, stage=stage,
                                                  additional_stmt=additional_stmt)

        case settings.OrderStage.SENT:
            additional_stmt += f", sent_at='{dt_agent}'"
        case settings.OrderStage.CRM_PROCESSED:
            additional_stmt += f", closed_at='{dt_agent}', processed={True}"

            if not order_info.payment:
                logger.error(settings.Messages.ORDER_PROCESSED_NOT_PAID)
                return False, settings.Messages.ORDER_PROCESSED_NOT_PAID

    stmt = f"""
                   UPDATE public.orders 
                   SET stage={stage}
                   {additional_stmt}
                   WHERE id={o_id} 
                """
    try:
        db.session.execute(text(stmt))
        db.session.commit()
        status = True
        message = settings.Messages.ORDER_STAGE_CHANGE
    except IntegrityError:
        db.session.rollback()
        logger.error(settings.Messages.ORDER_STAGE_CHANGE_ERROR)
        status = False
        message = settings.Messages.ORDER_STAGE_CHANGE_ERROR
    else:
        # sending user notification
        if stage == settings.OrderStage.SENT:
            helper_send_user_order_tg_notify(user_id=order_info.user_id, order_idn=order_info.order_idn,
                                             order_stage=stage)
    return status, message


def helper_crm_process_order_stats(o_id: int, order_info, stage: int, additional_stmt: str) -> Response:
    stmt = f"""
                                      UPDATE public.orders 
                                      SET stage={stage}
                                      {additional_stmt}
                                      WHERE id={o_id} 
                                   """
    try:
        db.session.execute(text(stmt))
        db.session.commit()  # not sure

        row_count, mark_count = get_rows_marks(o_id=o_id, category=order_info.category)

        # Create the INSERT statement with ON CONFLICT DO NOTHING
        stmt = insert(OrderStat).values(
            category=order_info.category,
            company_idn=order_info.company_idn,
            company_type=order_info.company_type,
            company_name=order_info.company_name,
            order_idn=order_info.order_idn,
            rows_count=row_count,
            marks_count=mark_count,
            op_cost=order_info.op_cost,
            created_at=order_info.created_at,
            comment_problem=order_info.comment_problem,
            cp_created=order_info.cp_created,
            m_started=order_info.m_started,
            m_finished=order_info.m_finished,
            crm_created_at=order_info.crm_created_at,
            sent_at=order_info.sent_at,
            stage_setter_name=order_info.stage_setter_name,
            manager_id=order_info.manager_id,
            user_id=order_info.user_id,
            transaction_id=order_info.transaction_id
        )

        # Apply ON CONFLICT DO NOTHING
        stmt = stmt.on_conflict_do_nothing()

        db.session.execute(stmt)
        db.session.commit()
        message = settings.Messages.ORDER_STAGE_CHANGE
    except IntegrityError:
        message = settings.Messages.ORDER_STAGE_CHANGE_ERROR
        db.session.rollback()
        logger.error(settings.Messages.ORDER_STAGE_CHANGE_ERROR)
        return False, message
    else:
        helper_send_user_order_tg_notify(user_id=order_info.user_id, order_idn=order_info.order_idn,
                                         order_stage=settings.OrderStage.POOL)
    return True, message


def of_delete_remove(order_info: Order, o_id: int) -> None:
    # check if we got a file in pur folder
    try:
        s3_service = get_s3_service()
        if order_info.file_system_name and order_info.file_system_name in s3_service.list_objects(settings.MINIO_CRM_BUCKET_NAME):
            s3_service.remove_object(object_name=order_info.file_system_name, bucket_name=settings.MINIO_CRM_BUCKET_NAME)
    except Exception:
        logger.exception(f"Ошибка при удалении файла из хранилища. Заказ {order_info.id}")

    # delete order file info in db
    if order_info.of_id:
        stmt = f"DELETE FROM public.order_files pof WHERE pof.order_id={o_id}"
        try:
            db.session.execute(text(stmt))
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            logger.error(e)


def helpers_problem_order(problem_order: Order, problem_comment: str, with_check: bool = False) -> str:
    try:
        problem_order.stage = settings.OrderStage.MANAGER_PROBLEM
        problem_order.external_problem = True
        problem_order.comment_problem = problem_comment
        problem_order.cp_created = datetime.now()
        problem_order.m_finished = None
        if with_check:
            delete_stmt = f"""
                           DELETE from public.order_files WHERE order_id={problem_order.id};
                           """
            db.session.execute(text(delete_stmt))
        db.session.commit()
        message = settings.Messages.ORDER_PROBLEM
    except IntegrityError:
        db.session.rollback()
        message = settings.Messages.ORDER_PROBLEM_ERROR
        logger.error(message)
    else:
        helper_send_user_order_tg_notify(user_id=problem_order.user_id, order_idn=problem_order.order_idn,
                                         order_stage=settings.OrderStage.MANAGER_PROBLEM)
        MarkinerisInform.send_message_tg.delay(order_idn=problem_order.order_idn, problem_order_flag=True)

    return message


def helpers_problem_order_response(user: User, o_id: int) -> Response:
    status = settings.ERROR
    message = ''
    htmlresponse = ''

    stage = request.form.get("stage", -1, int)
    category = request.form.get("category", 'all')
    filtered_manager_id = request.args.get('filtered_manager_id', None, int)

    if not stage or stage not in settings.OrderStage.CHECK_TUPLE:
        mes = f"{message} Invalid stage: {stage}"
        logger.error(mes)
        return jsonify({'htmlresponse': htmlresponse, 'status': status, 'message': mes})
    if not category or (category != 'all' and category not in settings.CATEGORIES_UPLOAD):
        mes = f"{message} Invalid category: {category}"
        logger.error(mes)
        return jsonify({'htmlresponse': htmlresponse, 'status': status, 'message': mes})

    problem_comment = request.form.get("problem_order_comment", '').replace("--", '').replace("#", '')
    problem_order = Order.query.get(o_id)

    if not o_id or not problem_order:
        message = settings.Messages.EMPTY_ORDER
        return jsonify({'htmlresponse': htmlresponse, 'status': status, 'message': message})
    status = False
    try:
        problem_order.stage = settings.OrderStage.MANAGER_PROBLEM
        problem_order.external_problem = True
        problem_order.comment_problem = problem_comment
        problem_order.cp_created = datetime.now()
        problem_order.m_finished = None
        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        message = settings.Messages.ORDER_PROBLEM_ERROR
        logger.error(message)
        return jsonify({'htmlresponse': htmlresponse, 'status': status, 'message': message})
    else:
        helper_send_user_order_tg_notify(user_id=problem_order.user_id, order_idn=problem_order.order_idn,
                                         order_stage=settings.OrderStage.MANAGER_PROBLEM)
        MarkinerisInform.send_message_tg.delay(order_idn=problem_order.order_idn, problem_order_flag=True)
    message = settings.Messages.ORDER_PROBLEM.format(order_idn=problem_order.order_idn)
    status = settings.SUCCESS
    update_orders = helper_get_manager_orders(user=user, filtered_manager_id=filtered_manager_id,
                                              category=category, stage=stage)

    return jsonify({'htmlresponse': render_template(
            'crm_mod_v1/crmm/updated_stages/orders_{stage}.html'.format(stage=stage), **locals()),
            'quantity': len(update_orders), 'status': status, 'message': message})


def helpers_ceps_order(o_id: int, ep: int, executor: str):
    status = 'danger'
    message = settings.Messages.NO_SUCH_ORDER_CRM
    try:

        order_info = db.session.execute(text("SELECT o.id from public.orders o WHERE o.id=:o_id AND o.to_delete != True;").bindparams(o_id=o_id)).fetchone()
        if not order_info:
            return jsonify({'status': status, 'message': message})
        ep = True if ep == 1 else False
        query = text("UPDATE public.orders SET external_problem=:ep WHERE id=:o_id;").bindparams(o_id=o_id, ep=ep)

        db.session.execute(query)
        db.session.commit()

        status = 'success'
        message = settings.Messages.ORDER_CEPS_SUCCESS
        html_block = """<span class="badge bg-solved text-white" title="Заказ без внешних проблем">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-clipboard-check" viewBox="0 0 16 16">
                                      <path fill-rule="evenodd" d="M10.854 7.146a.5.5 0 0 1 0 .708l-3 3a.5.5 0 0 1-.708 0l-1.5-1.5a.5.5 0 1 1 .708-.708L7.5 9.793l2.646-2.647a.5.5 0 0 1 .708 0"></path>
                                      <path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1z"></path>
                                      <path d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5zm-3-1A1.5 1.5 0 0 0 5 1.5v1A1.5 1.5 0 0 0 6.5 4h3A1.5 1.5 0 0 0 11 2.5v-1A1.5 1.5 0 0 0 9.5 0z"></path>
                                    </svg>
                                </span>""" if executor == 'agent' else """<span class="badge bg-error" title="Оператор поставил флаг внешней проблемы заказа, Нажмите если проблема устранена" 
                                                >
                                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-person-lock" viewBox="0 0 16 16">
                                                  <path d="M11 5a3 3 0 1 1-6 0 3 3 0 0 1 6 0M8 7a2 2 0 1 0 0-4 2 2 0 0 0 0 4m0 5.996V14H3s-1 0-1-1 1-4 6-4q.845.002 1.544.107a4.5 4.5 0 0 0-.803.918A11 11 0 0 0 8 10c-2.29 0-3.516.68-4.168 1.332-.678.678-.83 1.418-.832 1.664zM9 13a1 1 0 0 1 1-1v-1a2 2 0 1 1 4 0v1a1 1 0 0 1 1 1v2a1 1 0 0 1-1 1h-4a1 1 0 0 1-1-1zm3-3a1 1 0 0 0-1 1v1h2v-1a1 1 0 0 0-1-1"/>
                                                </svg>
                                            </span>"""
        return jsonify({'status': status, 'message': message, 'html_block': html_block})
    except Exception as e:
        db.session.rollback()
        logger.error(f"{settings.Messages.ORDER_CEPS_ERROR} {e}")
        return jsonify({'status': status, 'message': message})


def helpers_m_take_order(user: User, o_id: int) -> Response:
    status = settings.ERROR
    message = settings.Messages.ORDER_CHANGE_STAGE_ERROR
    # attempt to decrease sql queries
    stage = request.form.get("stage", -1, int)
    category = request.form.get("category", 'all')
    filtered_manager_id = request.args.get('filtered_manager_id', None, int)

    if not stage or stage not in settings.OrderStage.CHECK_TUPLE:
        mes = f"{message} Invalid stage: {stage}"
        logger.error(mes)
        return jsonify({'htmlresponse': None, 'status': status, 'message': mes})
    if not category or (category != 'all' and category not in settings.CATEGORIES_UPLOAD):
        mes = f"{message} Invalid category: {category}"
        logger.error(mes)
        return jsonify({'htmlresponse': None, 'status': status, 'message': mes})

    order_id = (Order.query.with_entities(Order.id, Order.stage).filter_by(id=o_id, stage=settings.OrderStage.POOL)
                .filter(~Order.to_delete).first())

    if not order_id:
        message = settings.Messages.ORDER_MANAGER_TAKE_ABS_ERROR
        return jsonify({'htmlresponse': None, 'status': status, 'message': message})

    if user.role == settings.MANAGER_USER:
        o_stmt = f"""
                    SELECT COUNT(co.id) as orders_count FROM public.orders co WHERE co.manager_id={user.id} AND co.stage < {settings.OrderStage.SENT}; 
               """
        o_count = db.session.execute(text(o_stmt)).fetchone().orders_count

        po_stmt = f"""
                            SELECT COUNT(co.id) as orders_count FROM public.orders co WHERE co.manager_id={user.id} AND co.stage = {settings.OrderStage.MANAGER_PROBLEM}; 
                       """
        po_count = db.session.execute(text(po_stmt)).fetchone().orders_count

        limits = helper_get_limits()
        mo_limit, po_limit = limits.mo_limit, limits.po_limit

        if o_count >= mo_limit or po_count >= po_limit:
            message = f'{settings.Messages.ORDERS_MANAGER_LIMIT} <br>Всего взято заказов: {o_count}, допуск({mo_limit}) <br>Всего проблемных заказов {po_count}, допуск({po_limit})'
            return jsonify({'htmlresponse': None, 'status': status, 'message': message})

    dt_manager = datetime.now()
    stmt = f"""
                   UPDATE public.orders 
                   SET manager_id={user.id}, stage={settings.OrderStage.MANAGER_START}, m_started='{dt_manager}'
                   WHERE id={o_id} 
               """
    try:
        db.session.execute(text(stmt))
        db.session.commit()

        update_orders = helper_get_manager_orders(user=user, filtered_manager_id=filtered_manager_id,
                                                  category=category, stage=stage)

        status = settings.SUCCESS
        message = settings.Messages.ORDER_MANAGER_TAKE
        return jsonify({'htmlresponse': render_template(
            'crm_mod_v1/crmm/updated_stages/orders_{stage}.html'.format(stage=stage), **locals()),
                        'quantity': len(update_orders), 'status': status, 'message': message})
    except IntegrityError:
        db.session.rollback()
        message = settings.Messages.ORDER_MANAGER_TAKE_ERROR
        logger.error(settings.Messages.ORDER_MANAGER_TAKE_ERROR)

        return jsonify({'status': status, 'message': message})


def check_order_file(order_file_name: str, o_id: int) -> tuple[bool, str]:

    try:
        s3_service = get_s3_service()
        list_objects = s3_service.list_objects(bucket_name=settings.MINIO_CRM_BUCKET_NAME)
    except Exception as e:
        logger.exception("Ошибка при получении списка объектов из хранилища")
        list_objects = []

    if order_file_name not in list_objects:
        problem_order = Order.query.get(o_id)
        message = settings.Messages.ORDER_FILE_ABS_ERROR + helpers_problem_order(problem_order=problem_order, problem_comment=settings.Messages.ORDER_FILE_ABS_ERROR, with_check=True)
        return False, message
    return True, ''


def helper_clean_oco() -> Response:
    try:
        dt_co = date.today() - timedelta(days=settings.OrderStage.DAYS_CONTENT)

        stmt = f"UPDATE public.orders SET to_delete=True " \
               f"WHERE stage={settings.OrderStage.CANCELLED} AND cc_created<'{dt_co}' AND to_delete != True"

        db.session.execute(text(stmt))
        db.session.commit()

        flash(message=settings.Messages.OCO_REMOVED)
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.OCO_REMOVED_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)

    return redirect(url_for('crm_uoc.index'))


def helper_change_manager_limit(limit_param: str) -> Response:

    if limit_param in settings.OrderStage.PS_DICT:

        db_param = settings.OrderStage.PS_DICT.get(limit_param).get('db_param')
        helper_proc_change_mlimit(ps_param=limit_param, db_param=db_param)

    else:
        flash(message=f'{settings.Messages.LIMIT_ERROR}')

    return redirect(url_for('crm_uoc.index'))


def helper_change_auto_order_pool() -> Response:
    ap_rows = request.form.get('ap_rows', '').replace('--', '')
    ap_marks = request.form.get('ap_marks', '').replace('--', '')
    if (ap_rows.isdigit() and ap_marks.isdigit()) and \
            (settings.OrderStage.PS_DICT.get('ap_rows').get('min_limit') <= int(ap_rows) <=
             settings.OrderStage.PS_DICT.get('ap_rows').get('max_limit')) and \
            (settings.OrderStage.PS_DICT.get('ap_marks').get('min_limit') <= int(ap_marks) <=
             settings.OrderStage.PS_DICT.get('ap_marks').get('max_limit')):

        try:
            stmt = text("""
                        INSERT INTO public.server_params (id, auto_pool_rows, auto_pool_marks)
                        VALUES(1,:ap_rows, :ap_marks)
                        ON CONFLICT(id) DO UPDATE SET auto_pool_rows = :ap_rows, auto_pool_marks = :ap_marks;
                       """).bindparams(ap_rows=ap_rows, ap_marks=ap_marks)
            db.session.execute(stmt)
            db.session.commit()
            flash(message=settings.Messages.LIMIT_SUCCESS + ' крайних значений количества строк и количества этикеток для автоматического перевода заказа после оформления в ПУЛ фирмы.')
        except IntegrityError:
            db.session.rollback()
            flash(message=settings.Messages.LIMIT_ERROR)
            logger.error(settings.Messages.LIMIT_ERROR)

    else:
        flash(message=settings.Messages.LIMIT_INPUT_ERROR)
    return redirect(url_for('crm_uoc.index'))


def helper_proc_change_mlimit(ps_param: str, db_param) -> None:

    ps_form_param = request.form.get(ps_param, '').replace('--', '')
    if ps_form_param.isdigit() and \
            settings.OrderStage.PS_DICT.get(ps_param).get('min_limit') <= int(ps_form_param) <= \
            settings.OrderStage.PS_DICT.get(ps_param).get('max_limit'):

        if ps_param == settings.OrderStage.PO_LIMIT:
            mo_limit = helper_get_limits().mo_limit
            if int(ps_form_param) > mo_limit:
                flash(message=f"{settings.Messages.PO_LIMIT_EXCCED_MO} {ps_form_param} > {mo_limit}")
                return
        try:
            stmt = f"""
                            INSERT INTO public.server_params (id, {db_param})
                            VALUES(1,{ps_form_param})
                            ON CONFLICT(id) DO UPDATE SET {db_param} = {ps_form_param};
                           """
            db.session.execute(text(stmt))
            db.session.commit()
            flash(message=settings.Messages.LIMIT_SUCCESS)
        except IntegrityError:
            db.session.rollback()
            flash(message=settings.Messages.LIMIT_ERROR)
            logger.error(settings.Messages.LIMIT_ERROR)

    else:
        flash(message=settings.Messages.LIMIT_INPUT_ERROR)


def helpers_move_orders_to_processed() -> Response:
    status = 'danger'
    closed_at = datetime.now()
    date_compare = date.today() - timedelta(days=settings.OrderStage.DAYS_SENT_CONTENT)
    stmt = text(f"""
               UPDATE public.orders 
               SET stage=:new_stage,
                   closed_at=:closed_at, processed={True}
               WHERE stage=:stage
                AND sent_at < :date_compare' AND payment=True AND to_delete != True; 
            """).bindparams(
        new_stage=settings.OrderStage.CRM_PROCESSED,
        closed_at=closed_at,
        stage=settings.OrderStage.SENT,
        date_compare=date_compare
    )
    try:
        db.session.execute(stmt)
        db.session.commit()
        status = settings.SUCCESS
        message = settings.Messages.OS_CHANGE_SUCCESS \
            .format(stage_from=settings.OrderStage.STAGES[settings.OrderStage.SENT][1],
                    stage_to=settings.OrderStage.STAGES[settings.OrderStage.CRM_PROCESSED][1])
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.OSR_CHANGE_ERROR} {e}"
        logger.error(message)

    return jsonify({'status': status, 'message': message})


# todo
def helpers_bck_change_orders_stage() -> Response:
    def _get_stages() ->tuple[bool, int, int]:
        stage_from = request.form.get('stage_from', -1, int)
        stage_to = request.form.get('stage_to', -1, int)
        if (stage_from, stage_to) in settings.OrderStage.CHECK_CHANGING_STAGES:
            return True, stage_from, stage_to,
        else:
            return False, -1, -1,

    status = 'danger'

    check, stage_from, stage_to = _get_stages()
    if not check:
        message = settings.Messages.STRANGE_REQUESTS
        return jsonify({'status': status, 'message': message})

    stmt = text("""
                   UPDATE public.orders 
                   SET stage=:stage_to,
                   WHERE stage=:stage AND payment=False AND o.to_delete != True; 
                """).bindparams(stage_to=stage_to, stage=settings.OrderStage.SENT)
    try:
        db.session.execute(stmt)
        db.session.commit()

        status = settings.SUCCESS
        message = settings.Messages.OS_CHANGE_SUCCESS.format(stage_from=settings.OrderStage.STAGES[stage_from][1],
                                                             stage_to=settings.OrderStage.STAGES[stage_to][1])
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.OS_CHANGE_STAGE_ERROR} {e}"
        logger.error(message)

    return jsonify({'status': status, 'message': message})


def check_manager_orders(u_id: int) -> int:

    stmt = f"SELECT COUNT(*) FROM public.orders o " \
           f"WHERE o.manager_id={u_id} and o.stage<{settings.OrderStage.SENT} AND o.to_delete != True;"

    res = db.session.execute(text(stmt)).fetchone()[0]
    return res


def h_get_agent_order_info(search_order_idn):
    date_compare = date.today() - timedelta(days=settings.OrderStage.DAYS_SEARCH_CONTENT)
    conditional_stmt = f"((o.stage>{settings.OrderStage.CREATING} AND o.stage!={settings.OrderStage.TELEGRAM_PROCESSED} AND o.stage!={settings.OrderStage.CANCELLED} AND o.stage!={settings.OrderStage.CRM_PROCESSED}) OR ((o.stage={settings.OrderStage.CANCELLED} AND o.cc_created  > '{date_compare}') OR (o.stage={settings.OrderStage.CRM_PROCESSED} AND o.closed_at > '{date_compare}')))"
    stmt_get_manager = f"(select managers.login_name from public.users managers where managers.id=o.manager_id)"
    additional_stmt = """
                                         o.comment_problem as comment_problem,
                                         o.comment_cancel as comment_cancel,
                                         o.cp_created as cp_created,
                                         o.cc_created as cc_created,
                                         o.crm_created_at as crm_created_at,
                                         o.p_started as p_started,
                                         o.m_started as m_started,
                                         o.m_finished as m_finished,
                                         o.sent_at as sent_at,
                                         o.closed_at as closed_at,
                                      """
    stmt_get_agent = f"CASE WHEN MAX(a.login_name) IS NOT NULL THEN MAX(a.login_name) ELSE u.login_name end"
    agent_condition = ''
    if current_user.role != settings.SUPER_USER:
        admin_id = current_user.id
        stmt_users = f"""SELECT users.id AS users_id
                         FROM users
                         WHERE users.admin_parent_id = {admin_id} OR users.id = {admin_id}
                    """
        agent_condition = f"u.id in ({stmt_users}) AND"
    stmt_search_order = text(f"""
                                  SELECT 
                                      u.client_code as client_code,
                                      {stmt_get_agent} as agent_name ,
                                      u.login_name as login_name, 
                                      u.phone as phone, 
                                      u.email as email, 
                                      o.id as id,
                                      o.stage as stage,
                                      o.payment as payment,
                                      o.order_idn as order_idn,
                                      o.category as category,
                                      o.company_type as company_type,
                                      o.company_name as company_name,
                                      o.company_idn as company_idn,
                                      o.external_problem as external_problem,
                                      o.edo_type as edo_type,
                                      o.mark_type as mark_type,
                                      o.user_comment as user_comment,
                                      o.has_new_tnveds as has_new_tnveds,
                                      o.manager_id as manager_id,
                                      o.crm_created_at as crm_created_at,
                                      o.to_delete as to_delete,
                                      o.processing_info as processing_info,
                                      MAX(orf.origin_name) as order_file,
                                      MAX(orf.file_link) as order_file_link,
                                      {stmt_get_manager} as manager,
                                      o.stage_setter_name as stage_setter_name,
                                      {additional_stmt}
                                      COUNT(o.id) as row_count,
                                      {SQLQueryCategoriesAll.get_stmt(field='subcategory')} as subcategory,
                                      {SQLQueryCategoriesAll.get_stmt(field='declar_doc')} as declar_doc,
                                      {SQLQueryCategoriesAll.get_stmt(field='marks_count')} as pos_count
                                  FROM public.users u
                                      JOIN public.orders o ON o.user_id = u.id  
                                      LEFT JOIN public.users a ON u.admin_parent_id = a.id  
                                      LEFT JOIN public.order_files orf ON o.id=orf.order_id 
                                      {SQLQueryCategoriesAll.get_joins()} 
                                  WHERE  {agent_condition}{conditional_stmt} AND o.order_idn=:search_order_idn
                                  GROUP BY u.id, o.id, o.crm_created_at
                                  ORDER BY o.crm_created_at
                                   """).bindparams(search_order_idn=search_order_idn)

    order_info = db.session.execute(stmt_search_order).fetchone()
    return order_info


def h_get_manager_order_info(user: User, search_order_idn: str):
    manager_id = user.id
    additional_stmt = """
                                o.comment_problem as comment_problem,
                                o.comment_cancel as comment_cancel,
                                o.p_started as p_started,
                                o.cp_created as cp_created,
                                o.cc_created as cc_created,
                                o.m_started as m_started,
                                o.m_finished as m_finished,
                             """

    conditional_stmt_common = f"(o.stage!={settings.OrderStage.POOL} AND o.stage>{settings.OrderStage.CREATING} AND o.stage<={settings.OrderStage.MANAGER_SOLVED} AND o.stage!={settings.OrderStage.CRM_PROCESSED})"

    stmt_get_manager = f"(select login_name from public.users managers where managers.id=o.manager_id)"

    if user.role not in [settings.SUPER_USER, settings.SUPER_MANAGER, ]:
        conditional_stmt = f"(({conditional_stmt_common} AND o.manager_id={manager_id}) OR o.stage={settings.OrderStage.POOL})"

        stmt_get_agent = f"CASE WHEN MAX(a.login_name) IS NOT NULL THEN MAX(a.login_name) ELSE u.login_name end"
        stmt_orders = text(f"""SELECT u.client_code as client_code,
                                     ({stmt_get_agent})  as agent_name ,
                                     u.login_name as login_name, 
                                     u.phone as phone, 
                                     u.email as email, 
                                     o.id as id,
                                     o.stage as stage,
                                     o.payment as payment,
                                     o.order_idn as order_idn,
                                     o.category as category,
                                     o.crm_created_at as crm_created_at,
                                     o.company_type as company_type,
                                     o.company_name as company_name,
                                     o.company_idn as company_idn,
                                     o.external_problem as external_problem,
                                     o.edo_type as edo_type,
                                     o.mark_type as mark_type,
                                     o.user_comment as user_comment,
                                     o.has_new_tnveds as has_new_tnveds,
                                     o.to_delete as to_delete,
                                     o.processing_info as processing_info,
                                     MAX(orf.origin_name) as order_file,
                                     MAX(orf.file_link) as order_file_link,
                                     o.manager_id as manager_id,
                                     {stmt_get_manager} as manager,
                                     o.stage_setter_name as stage_setter_name,
                                     {additional_stmt}
                                     COUNT(o.id) as row_count,
                                     {SQLQueryCategoriesAll.get_stmt(field='subcategory')} as subcategory,
                                     {SQLQueryCategoriesAll.get_stmt(field='declar_doc')} as declar_doc,
                                     {SQLQueryCategoriesAll.get_stmt(field='marks_count')} as pos_count
                                 FROM public.users u
                                     JOIN public.orders o ON o.user_id = u.id
                                     LEFT JOIN public.users a ON u.admin_parent_id = a.id   
                                     LEFT JOIN public.order_files orf ON o.id=orf.order_id
                                     {SQLQueryCategoriesAll.get_joins()} 
                               WHERE o.order_idn=:search_order_idn AND {conditional_stmt}
                               GROUP BY u.id, o.id, o.crm_created_at
                               ORDER BY o.crm_created_at
                              """).bindparams(search_order_idn=search_order_idn)
    else:
        conditional_stmt = f"({conditional_stmt_common} OR o.stage={settings.OrderStage.POOL})"

        stmt_get_agent = f"CASE WHEN MAX(a.login_name) IS NOT NULL THEN MAX(a.login_name) ELSE u.login_name end"
        stmt_orders = text(f"""
                                  SELECT 
                                      u.client_code as client_code,
                                      ({stmt_get_agent})  as agent_name ,
                                      u.login_name as login_name, 
                                      u.phone as phone, 
                                      u.email as email, 
                                      o.id as id,
                                      o.stage as stage,
                                      o.payment as payment,
                                      o.order_idn as order_idn,
                                      o.category as category,
                                      o.crm_created_at as crm_created_at,
                                      o.company_type as company_type,
                                      o.company_name as company_name,
                                      o.company_idn as company_idn,
                                      o.external_problem as external_problem,
                                      o.edo_type as edo_type,
                                      o.mark_type as mark_type,
                                      o.to_delete as to_delete,
                                      o.user_comment as user_comment,
                                      o.has_new_tnveds as has_new_tnveds,
                                      o.to_delete as to_delete,
                                      o.processing_info as processing_info,
                                      MAX(orf.origin_name) as order_file,
                                      MAX(orf.file_link) as order_file_link,
                                      o.manager_id as manager_id,
                                      {stmt_get_manager} as manager,
                                      o.stage_setter_name as stage_setter_name,
                                      {additional_stmt}
                                      COUNT(o.id) as row_count,
                                      {SQLQueryCategoriesAll.get_stmt(field='subcategory')} as subcategory,
                                      {SQLQueryCategoriesAll.get_stmt(field='declar_doc')} as declar_doc,
                                  {SQLQueryCategoriesAll.get_stmt(field='marks_count')} as pos_count
                                  FROM public.users u
                                      JOIN public.orders o ON o.user_id = u.id
                                      LEFT JOIN public.users a ON u.admin_parent_id = a.id   
                                      LEFT JOIN public.order_files orf ON o.id=orf.order_id
                                      {SQLQueryCategoriesAll.get_joins()}
                                  WHERE  {conditional_stmt} AND o.order_idn=:search_order_idn
                                  GROUP BY u.id, o.id, o.crm_created_at
                                  ORDER BY o.crm_created_at
                                   """).bindparams(search_order_idn=search_order_idn)

    order_info = db.session.execute(stmt_orders).fetchone()
    return order_info


def helper_search_crma_order() -> Response:
    status = 'danger'

    search_order_idn = request.form.get('search_order_idn', '')
    if not search_order_idn:
        message = settings.Messages.CRM_SEARCH_ORDER_ERROR.format(comment='Введен пустой заказ!')
        return jsonify({'status': status, 'message': message})
    order_info = h_get_agent_order_info(search_order_idn=search_order_idn,)
    if not order_info:
        message = settings.Messages.CRM_SEARCH_ORDER_ERROR.format(comment=f"Либо заказ отсутствует, либо отменен и готов и старше {settings.OrderStage.DAYS_SEARCH_CONTENT} дней!")
        return jsonify({'status': status, 'message': message})

    status = settings.SUCCESS
    ps_limit_qry = ServerParam.query.get(1)
    problem_order_time_limit = ps_limit_qry.crm_manager_ps_limit if ps_limit_qry and ps_limit_qry.crm_manager_ps_limit \
        else settings.OrderStage.DEFAULT_PS_LIMIT
    cur_time = datetime.now()

    htmlresponse = ''
    update_orders = [order_info, ]
    match order_info.stage:
        case settings.OrderStage.NEW:
            htmlresponse = render_template(f'crm_mod_v1/crma/updated_stages/crma_search_1.html', **locals())
        case settings.OrderStage.POOL:
            htmlresponse = render_template(f'crm_mod_v1/crma/updated_stages/crma_search_2.html', **locals())
        case settings.OrderStage.MANAGER_START:
            htmlresponse = render_template(f'crm_mod_v1/crma/updated_stages/crma_search_3.html', **locals())
        case settings.OrderStage.MANAGER_PROCESSED:
            htmlresponse = render_template(f'crm_mod_v1/crma/updated_stages/crma_search_5.html', **locals())
        case settings.OrderStage.MANAGER_PROBLEM:
            htmlresponse = render_template(f'crm_mod_v1/crma/updated_stages/crma_search_6.html', **locals())
        case settings.OrderStage.MANAGER_SOLVED:
            htmlresponse = render_template(f'crm_mod_v1/crma/updated_stages/crma_search_7.html', **locals())
        case settings.OrderStage.SENT:
            htmlresponse = render_template(f'crm_mod_v1/crma/updated_stages/crma_search_8.html', **locals())
        case settings.OrderStage.CANCELLED:
            htmlresponse = render_template(f'crm_mod_v1/crma/updated_stages/crma_search_9.html', **locals())
        case settings.OrderStage.CRM_PROCESSED:
            htmlresponse = render_template(f'crm_mod_v1/crma/updated_stages/crma_search_10.html', **locals())
    return jsonify({'htmlresponse': htmlresponse, 'status': status})


def helper_search_crmm_order() -> Response:
    status = 'danger'

    search_order_idn = request.form.get('search_order_idn', '')
    filtered_manager_id = None

    if not search_order_idn:
        message = settings.Messages.CRM_SEARCH_ORDER_ERROR.format(comment='Введен пустой заказ!')
        return jsonify({'status': status, 'message': message})

    order_info = h_get_manager_order_info(user=current_user, search_order_idn=search_order_idn)

    if not order_info:
        message = settings.Messages.CRM_SEARCH_ORDER_ERROR.format(comment=f"Либо заказ отсутствует, либо отправлен!")
        return jsonify({'status': status, 'message': message})

    status = settings.SUCCESS
    ps_limit_qry = ServerParam.query.get(1)
    problem_order_time_limit = ps_limit_qry.crm_manager_ps_limit if ps_limit_qry and ps_limit_qry.crm_manager_ps_limit \
        else settings.OrderStage.DEFAULT_PS_LIMIT
    cur_time = datetime.now()

    htmlresponse = ''
    update_orders = [order_info, ]
    match order_info.stage:
        case settings.OrderStage.POOL:
            htmlresponse = render_template(f'crm_mod_v1/crmm/updated_stages/crmm_search_2.html', **locals())
        case settings.OrderStage.MANAGER_START:
            htmlresponse = render_template(f'crm_mod_v1/crmm/updated_stages/crmm_search_3.html', **locals())
        case settings.OrderStage.MANAGER_PROCESSED:
            htmlresponse = render_template(f'crm_mod_v1/crmm/updated_stages/crmm_search_5.html', **locals())
        case settings.OrderStage.MANAGER_PROBLEM:
            htmlresponse = render_template(f'crm_mod_v1/crmm/updated_stages/crmm_search_6.html', **locals())
        case settings.OrderStage.MANAGER_SOLVED:
            htmlresponse = render_template(f'crm_mod_v1/crmm/updated_stages/crmm_search_7.html', **locals())

    return jsonify({'htmlresponse': htmlresponse, 'status': status})


def helper_get_processing_order_info() -> Response:
    status = 'danger'

    order_id = request.args.get("order_id", type=int)
    if not order_id:
        message = 'Ошибка- не указан номер заказа!'
        return jsonify({'status': status, 'message': message})

    order_info = Order.query.with_entities(Order.processing_info, Order.order_idn).filter(Order.id == order_id).first()
    if not order_info:
        message = 'Ошибка- заказ не найден, обратитесь к администратору.'
        return jsonify({'status': status, 'message': message})

    status = 'success'
    companies_operators = [c.as_option() for c in CompaniesOperators]

    if order_info:
        status = "success"
    else:
        message = "Данные по организации не установлены"

    htmlresponse = render_template(f'crm_mod_v1/helpers/modals/modal_order_process_info.html', **locals())

    return jsonify({'status': status, 'htmlresponse': htmlresponse})


def helper_update_processing_order_info() -> tuple[Response, int]:
    data = request.get_json()

    order_id = data.get("order_id")
    company = data.get("company")
    upd_number = data.get("upd_number")
    if not all([order_id, company, upd_number]):
        return jsonify({
            "status": "error",
            "message": "Все поля обязательны к заполнению"
        }), 400

    order = Order.query.get(order_id)
    if current_user.role == settings.MANAGER_USER and order.manager_id != current_user.id:
        return jsonify({
            "status": "error",
            "message": "Этот заказ закреплен за другим оператором"
        }), 404
    if not order:
        return jsonify({
            "status": "error",
            "message": "Заказ не найден"
        }), 404

    try:

        order.processing_info = f"{company} <br> УПД: {upd_number}"
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": f"Информация по заказу № {order.order_idn} обновлена",
            "order_idn": order.order_idn,
            "processing_info": order.processing_info
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.exception('Ошибка обновления информации по организации проводящей заказ: ')
        return jsonify({
            "status": "error",
            "message": f"Ошибка при обновлении: {str(e)}"
        }), 500


def h_set_dynamic_jobs(minutes: int) -> bool:
    conn = Redis.from_url(settings.REDIS_CONN)
    queue_dynamic = Queue(settings.RQ_DYNSCHEDULER_QUEUE_NAME, connection=conn)
    scheduler_dynamic = Scheduler(queue=queue_dynamic, connection=queue_dynamic.connection)
    try:
        new_cron_string = settings.OrderStage.minutes_to_cron(minutes=minutes)

        for job in scheduler_dynamic.get_jobs():
            # scheduler_dynamic.cancel(job)
            job.delete()

        scheduler_dynamic.cron(
            new_cron_string,
            func=helpers_crm_mpo_so_task,
            on_success=on_success_periodic_task,
            on_failure=on_failure_periodic_task,
            queue_name=settings.RQ_DYNSCHEDULER_QUEUE_NAME
        )

        return True
    except Exception as e:
        logger.error(str(e))
        return False


def helpers_crm_mpo_so_task():
    """
    scheduler tasks change order stage from manager processed to sent
    :return:
    """
    status = 'error'
    sent_at = datetime.now()

    # get orders and user_ids for tg notification
    orders_users = [o for o in Order.query.with_entities(Order.id,
                                                         Order.order_idn,
                                                         Order.user_id)
                                          .filter_by(stage=settings.OrderStage.MANAGER_PROCESSED)
                    .filter(~Order.to_delete).all()]
    if not orders_users:
        return {'status': status,
                'message': settings.Messages.OS_CHANGE_EMPTY.format(stage_from=settings.OrderStage.
                                                                    STAGES[settings.OrderStage.MANAGER_PROCESSED][1],
                                                                    stage_to=settings.OrderStage.
                                                                    STAGES[settings.OrderStage.SENT][1])}
    stmt = text("""
                     UPDATE public.orders 
                     SET stage=:new_stage,
                         sent_at=:sent_at
                     WHERE stage=:stage AND to_delete != True; 
                  """).bindparams(new_stage=settings.OrderStage.SENT, sent_at=sent_at, stage=settings.OrderStage.MANAGER_PROCESSED)

    try:
        db.session.execute(stmt)
        db.session.commit()
        status = 'success'
        message = settings.Messages.OS_CHANGE_SUCCESS \
            .format(stage_from=settings.OrderStage.STAGES[settings.OrderStage.MANAGER_PROCESSED][1],
                    stage_to=settings.OrderStage.STAGES[settings.OrderStage.SENT][1])
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.OSR_CHANGE_ERROR} {e}"
        logger.error(message)
    else:
        helper_suotls(users_orders=orders_users, order_stage=settings.OrderStage.SENT)
    return {'status': status, 'message': message}


def helper_change_auto_order_sent() -> Response:
    as_minutes = request.form.get('as_minutes', '').replace('--', '')
    if (as_minutes.isdigit() and as_minutes.isdigit()) and \
            (settings.OrderStage.PS_DICT.get('as_minutes').get('min_limit') <= int(as_minutes) <=
             settings.OrderStage.PS_DICT.get('as_minutes').get('max_limit')):
        try:
            if not h_set_dynamic_jobs(minutes=int(as_minutes)):
                raise Exception(settings.Messages.LIMIT_DYN_SCH_ERROR)

            stmt = text(f"""
                        INSERT INTO public.server_params (id, auto_sent_minutes)
                        VALUES(1,:as_minutes)
                        ON CONFLICT(id) DO UPDATE SET auto_sent_minutes = :as_minutes;
                       """).bindparams(as_minutes=as_minutes)
            db.session.execute(stmt)
            db.session.commit()
            flash(message=settings.Messages.LIMIT_SUCCESS + ' количества минут для автоматического перевода заказов из Операторы готово в Агенты Отправлено.')
        except Exception as e:
            db.session.rollback()
            flash(message=settings.Messages.LIMIT_ERROR, category='error')
            logger.error(f"settings.Messages.LIMIT_ERROR {e}")

    else:
        flash(message=settings.Messages.LIMIT_INPUT_ERROR, category='error')
    return redirect(url_for('crm_uoc.index'))


def helper_auto_problem_cancel_order():
    """
    scheduler tasks change order stage from manager problem to cancel
    """

    current_date = datetime.now()
    date_compare = current_date - timedelta(hours=settings.OrderStage.AUTO_HOURS_CP, minutes=settings.OrderStage.AUTO_MINUTES_CP)
    orders_stmt = f"""
                    SELECT o.id as id,
                        o.user_id as user_id,
                        o.order_idn as order_idn,
                        o.payment as payment,
                        o.transaction_id as transaction_id,
                        orf.id as of_id,
                        orf.file_system_name as file_system_name,
                        o.cp_created as cp_created
                    FROM public.orders o 
                    LEFT JOIN public.order_files orf ON o.id=orf.order_id
                    WHERE o.stage={settings.OrderStage.MANAGER_PROBLEM}
                     AND o.cp_created < '{date_compare}' AND o.to_delete != True;
                  """

    orders_info = db.session.execute(text(orders_stmt)).fetchall()
    # check for order exist and admin correct
    if not orders_info:
        logger.info(settings.OrderStage.APCO_NOORDERS)
        return jsonify({'status': 'error', 'message': settings.OrderStage.APCO_NOORDERS})

    for order in orders_info:
        # delete rows from db and delete file from syst
        of_delete_remove(order_info=order, o_id=order.id)

        # update order stage

        order_query = text(f"""
                   UPDATE public.orders 
                   SET payment=False,
                       stage={settings.OrderStage.CANCELLED},
                       comment_cancel='{settings.OrderStage.APCO_MESSAGE} решения вопроса',
                       cc_created='{current_date}'
                   WHERE id=:o_id 
                """).bindparams(o_id=order.id)

        try:
            db.session.execute(order_query)

            if order.payment:
                # make restore balance and cancel userTransaction and update orders_stats
                h_cancel_order_process_payment(order_idn=order.order_idn,
                                               user_id=order.user_id)

            db.session.commit()

        except IntegrityError as ie:
            db.session.rollback()
            logger.error(f"{settings.Messages.ORDER_CANCEL_ERROR} {ie}")

        except Exception as e:
            db.session.rollback()
            logger.error(str(e))

        else:
            helper_send_user_order_tg_notify(user_id=order.user_id, order_idn=order.order_idn,
                                             order_stage=settings.OrderStage.CANCELLED)

    return jsonify({'status': 'success', 'message': settings.OrderStage.APCO_SUCCESS})


def helper_auto_new_cancel_order():
    """
    scheduler tasks change order stage from manager problem to cancel
    """

    current_date = datetime.now()
    date_compare = current_date - timedelta(days=7)
    orders_stmt = f"""
                    SELECT o.id as id,
                        o.user_id as user_id,
                        o.order_idn as order_idn,
                        o.payment as payment,
                        o.transaction_id as transaction_id,
                        orf.id as of_id,
                        orf.file_system_name as file_system_name,
                        o.cp_created as cp_created
                    FROM public.orders o 
                    LEFT JOIN public.order_files orf ON o.id=orf.order_id
                    WHERE o.stage={settings.OrderStage.NEW}
                     AND o.crm_created_at < '{date_compare}' AND o.to_delete != True;
                  """

    orders_info = db.session.execute(text(orders_stmt)).fetchall()
    # check for order exist and admin correct
    if not orders_info:
        logger.info(settings.OrderStage.APCO_NOORDERS)
        return jsonify({'status': 'error', 'message': settings.OrderStage.APCO_NOORDERS})

    for order in orders_info:
        # delete rows from db and delete file from syst
        of_delete_remove(order_info=order, o_id=order.id)

        # update order stage
        order_query = text(f"""
                   UPDATE public.orders 
                   SET payment=False,
                       stage={settings.OrderStage.CANCELLED},
                       comment_cancel='{settings.OrderStage.APCO_MESSAGE}',
                       cc_created='{current_date}'
                   WHERE id=:o_id 
                """).bindparams(o_id=order.id)

        try:
            db.session.execute(order_query)

            if order.payment:
                # make restore balance and cancel userTransaction and update orders_stats
                h_cancel_order_process_payment(order_idn=order.order_idn,
                                               user_id=order.user_id)

            db.session.commit()

        except IntegrityError as ie:
            db.session.rollback()
            logger.error(f"{settings.Messages.ORDER_CANCEL_ERROR} {ie}")

        except Exception as e:
            db.session.rollback()
            logger.error(str(e))

        else:
            helper_send_user_order_tg_notify(user_id=order.user_id, order_idn=order.order_idn,
                                             order_stage=settings.OrderStage.CANCELLED)

    return jsonify({'status': 'success', 'message': settings.OrderStage.APCO_SUCCESS})


def helper_crm_preload(o_id: int):
    order_info = (Order.query.with_entities(Order.category, Order.stage, Order.order_idn, Order.user_id)
                  .filter(Order.id == o_id).filter(~Order.to_delete).first())
    if not order_info:
        flash(message=settings.Messages.NO_SUCH_ORDER, category='error')
        return redirect(url_for(f'crm_d.agents'))

    stage, category, order_idn, user_id = order_info.stage, order_info.category, order_info.order_idn, order_info.user_id
    category_process_name = settings.CATEGORIES_DICT.get(order_info.category)
    stage_name = settings.OrderStage.STAGES[stage][1]

    orders, company_type, company_name, company_idn, \
        edo_type, edo_id, mark_type, trademark, orders_pos_count, pos_count, \
        total_price, price_exist, subcategory = orders_list_common(category=category, user=User.query.get(user_id), o_id=o_id, stage=order_info.stage)

    if not orders:
        flash(message=settings.Messages.NO_SUCH_ORDER, category='error')
        return redirect(url_for(f'crm_d.agents'))

    start_list, page, per_page, offset, pagination, order_list = crm_orders_common_preload(category=category,
                                                                                           company_idn=company_idn,
                                                                                           orders_list=orders,)

    return render_template('crm_mod_v1/preload/crm_preload.html', **locals())


def helper_categories_counter(all_cards: list | tuple) -> dict:
    all_cards_proc = list(filter(lambda x: x.stage < 8, all_cards))
    categories: tuple = ('одежда', 'обувь', 'белье', 'парфюм', 'носки и прочее')
    categories_counter: dict = {'all': len(all_cards_proc)}
    for cat in categories:
        categories_counter.update({cat: sum(1 for card in all_cards_proc if card.category == cat)})

    return categories_counter
