from datetime import date, datetime, timedelta
from os import listdir as o_listdir
from os import path as o_path
from os import remove as o_remove
from redis import Redis
from rq import Queue
from rq_scheduler.scheduler import Scheduler
from uuid import uuid4

from flask import jsonify, redirect, render_template, request, Response, flash, url_for, send_from_directory
from flask_login import current_user
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from typing import Optional
from werkzeug.utils import secure_filename

from config import settings
from logger import logger
from models import User, Order, OrderStat, db, ServerParam
from redis_queue.callbacks import on_success_periodic_task, on_failure_periodic_task
from utilities.helpers.h_tg_notify import helper_send_user_order_tg_notify, helper_suotls
from utilities.saving_uts import get_rows_marks
from utilities.support import helper_get_at2_pending_balance, helper_get_limits
from utilities.telegram import MarkinerisInform


def helper_get_agent_orders(user: User) -> list:
# def helper_get_agent_orders() -> list:

    date_compare = date.today() - timedelta(days=settings.OrderStage.DAYS_CONTENT)
    conditional_stmt = f"((o.stage>{settings.OrderStage.CREATING} AND o.stage!={settings.OrderStage.TELEGRAM_PROCESSED} AND o.stage!={settings.OrderStage.CANCELLED} AND o.stage!={settings.OrderStage.CRM_PROCESSED}) OR ((o.stage={settings.OrderStage.CANCELLED} AND o.cc_created  > '{date_compare}') OR (o.stage={settings.OrderStage.CRM_PROCESSED} AND o.closed_at > '{date_compare}')))"
    stmt_get_manager = f"(select managers.login_name from public.users managers where managers.id=o.manager_id)"
    additional_stmt = """
                                 o.comment_problem as comment_problem,
                                 o.comment_cancel as comment_cancel,
                                 o.cp_created as cp_created,
                                 o.cc_created as cc_created,
                                 o.crm_created_at as crm_created_at,
                                 o.m_started as m_started,
                                 o.m_finished as m_finished,
                                 o.sent_at as sent_at,
                                 o.closed_at as closed_at,
                              """
    if user.role != settings.SUPER_USER:
        admin_id = user.id

        stmt_get_agent = f"SELECT public.users.login_name from public.users where public.users.id={admin_id}"
        stmt_users = f"""SELECT users.id AS users_id
                         FROM users
                         WHERE users.admin_parent_id = {admin_id} OR users.id = {admin_id}
                    """

        stmt_orders = f"""
                              SELECT u.client_code as client_code,
                                  ({stmt_get_agent})  as agent_name ,
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
                                  MAX(orf.origin_name) as order_file,
                                  MAX(orf.file_link) as order_file_link,
                                  {stmt_get_manager} as manager,
                                  o.stage_setter_name as stage_setter_name,
                                  {additional_stmt}
                                  COUNT(o.id) as row_count,
                                  COUNT(coalesce(sh.rd_date, cl.rd_date, l.rd_date, p.rd_date)) as declar_doc,
                                  SUM(coalesce(sh.box_quantity*sh_qs.quantity, cl.box_quantity*cl_qs.quantity, l.box_quantity*l_qs.quantity, p.quantity)) as pos_count
                              FROM public.users u
                                  JOIN public.orders o ON o.user_id = u.id
                                  LEFT JOIN public.order_files orf ON o.id=orf.order_id
                                  LEFT JOIN public.shoes sh ON o.id = sh.order_id
                                  LEFT JOIN public.shoes_quantity_sizes sh_qs ON sh.id = sh_qs.shoe_id
                                  LEFT JOIN public.clothes  cl ON o.id = cl.order_id
                                  LEFT JOIN public.cl_quantity_sizes cl_qs ON cl.id = cl_qs.cl_id
                                  LEFT JOIN public.linen l ON o.id = l.order_id
                                  LEFT JOIN public.linen_quantity_sizes l_qs ON l.id = l_qs.lin_id
                                  LEFT JOIN public.parfum p ON o.id = p.order_id
                        WHERE u.id in({stmt_users}) AND {conditional_stmt}
                        GROUP BY u.id, o.id, o,crm_created_at
                        ORDER BY o.crm_created_at ASC 
                       """
    else:
        # stmt_get_agent = f"SELECT a.login_name FROM public.users a  WHERE ((a.id=u.admin_parent_id and (a.role='{settings.ADMIN_USER}' or a.role='{settings.SUPER_USER}')) OR (a.id=u.id and (a.role='{settings.ADMIN_USER}' or a.role='{settings.SUPER_USER}')))"
        stmt_get_agent = f"CASE WHEN MAX(a.login_name) IS NOT NULL THEN MAX(a.login_name) ELSE u.login_name end"
        stmt_orders = f"""
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
                                  MAX(orf.origin_name) as order_file,
                                  MAX(orf.file_link) as order_file_link,
                                  {stmt_get_manager} as manager,
                                  o.stage_setter_name as stage_setter_name,
                                  {additional_stmt}
                                  COUNT(o.id) as row_count,
                                  COUNT(coalesce(sh.rd_date, cl.rd_date, l.rd_date, p.rd_date)) as declar_doc,
                                  SUM(coalesce(sh.box_quantity*sh_qs.quantity, cl.box_quantity*cl_qs.quantity, l.box_quantity*l_qs.quantity, p.quantity)) as pos_count
                              FROM public.users u
                                  JOIN public.orders o ON o.user_id = u.id  
                                  LEFT JOIN public.users a ON u.admin_parent_id = a.id  
                                  LEFT JOIN public.order_files orf ON o.id=orf.order_id 
                                  LEFT JOIN public.shoes sh ON o.id = sh.order_id
                                  LEFT JOIN public.shoes_quantity_sizes sh_qs ON sh.id = sh_qs.shoe_id 
                                  LEFT JOIN public.clothes  cl ON o.id = cl.order_id
                                  LEFT JOIN public.cl_quantity_sizes cl_qs ON cl.id = cl_qs.cl_id
                                  LEFT JOIN public.linen l ON o.id = l.order_id
                                  LEFT JOIN public.linen_quantity_sizes l_qs ON l.id = l_qs.lin_id
                                  LEFT JOIN public.parfum p ON o.id = p.order_id 
                              WHERE  {conditional_stmt}
                              GROUP BY u.id, o.id, o.crm_created_at
                              ORDER BY o.crm_created_at ASC
                               """

    res = db.session.execute(text(stmt_orders))
    return res.fetchall()


def helper_get_manager_orders(user: User, filtered_manager_id: int = None) -> tuple:
    manager_id = user.id
    additional_stmt = """
                            o.comment_problem as comment_problem,
                            o.comment_cancel as comment_cancel,
                            o.cp_created as cp_created,
                            o.cc_created as cc_created,
                            o.m_started as m_started,
                            o.m_finished as m_finished,
                         """

    conditional_stmt_common = f"(o.stage!={settings.OrderStage.POOL} AND o.stage>{settings.OrderStage.CREATING} AND o.stage<={settings.OrderStage.MANAGER_SOLVED} AND o.stage!={settings.OrderStage.CRM_PROCESSED})"

    stmt_get_manager = f"(select login_name from public.users managers where managers.id=o.manager_id)"

    if user.role not in [settings.SUPER_USER, settings.SUPER_MANAGER, ]:
        # conditional_stmt = f"o.stage={settings.OrderStage.POOL}" if pool else conditional_stmt_common + f" AND o.manager_id={manager_id}"
        conditional_stmt = f"({conditional_stmt_common} AND o.manager_id={manager_id}) OR o.stage={settings.OrderStage.POOL}"

        # stmt_get_agent = f"CASE WHEN MAX(a.login_name) IS NOT NULL THEN MAX(a.login_name) ELSE u.login_name end"
        stmt_orders = f"""
                             SELECT u.client_code as client_code,
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
                                 MAX(orf.origin_name) as order_file,
                                 MAX(orf.file_link) as order_file_link,
                                 o.manager_id as manager_id,
                                 {stmt_get_manager} as manager,
                                 o.stage_setter_name as stage_setter_name,
                                 {additional_stmt}
                                 COUNT(o.id) as row_count,
                                 COUNT(coalesce(sh.rd_date, cl.rd_date, l.rd_date, p.rd_date)) as declar_doc,
                                 SUM(coalesce(sh.box_quantity*sh_qs.quantity, cl.box_quantity*cl_qs.quantity, l.box_quantity*l_qs.quantity, p.quantity)) as pos_count
                             FROM public.users u
                                 JOIN public.orders o ON o.user_id = u.id
                                 LEFT JOIN public.users a ON u.admin_parent_id = a.id   
                                 LEFT JOIN public.order_files orf ON o.id=orf.order_id
                                 LEFT JOIN public.shoes sh ON o.id = sh.order_id
                                 LEFT JOIN public.shoes_quantity_sizes sh_qs ON sh.id = sh_qs.shoe_id 
                                 LEFT JOIN public.clothes  cl ON o.id = cl.order_id
                                 LEFT JOIN public.cl_quantity_sizes cl_qs ON cl.id = cl_qs.cl_id
                                 LEFT JOIN public.linen l ON o.id = l.order_id
                                 LEFT JOIN public.linen_quantity_sizes l_qs ON l.id = l_qs.lin_id
                                 LEFT JOIN public.parfum p ON o.id = p.order_id 
                           WHERE {conditional_stmt}
                           GROUP BY u.id, o.id, o.crm_created_at
                           ORDER BY o.crm_created_at ASC
                          """
    else:
        manager_condition = f" AND o.manager_id={filtered_manager_id}" if filtered_manager_id else ""
        conditional_stmt = f"({conditional_stmt_common}{manager_condition} OR o.stage={settings.OrderStage.POOL})"

        # stmt_get_agent = f"CASE WHEN MAX(a.login_name) IS NOT NULL THEN MAX(a.login_name) ELSE u.login_name end"
        stmt_orders = f"""
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
                                  o.crm_created_at as crm_created_at,
                                  o.company_type as company_type,
                                  o.company_name as company_name,
                                  o.company_idn as company_idn,
                                  o.external_problem as external_problem,
                                  o.edo_type as edo_type,
                                  o.mark_type as mark_type,
                                  o.user_comment as user_comment,
                                  o.has_new_tnveds as has_new_tnveds,
                                  MAX(orf.origin_name) as order_file,
                                  MAX(orf.file_link) as order_file_link,
                                  o.manager_id as manager_id,
                                  {stmt_get_manager} as manager,
                                  o.stage_setter_name as stage_setter_name,
                                  {additional_stmt}
                                  COUNT(o.id) as row_count,
                                  COUNT(coalesce(sh.rd_date, cl.rd_date, l.rd_date, p.rd_date)) as declar_doc,
                                  SUM(coalesce(sh.box_quantity*sh_qs.quantity, cl.box_quantity*cl_qs.quantity, l.box_quantity*l_qs.quantity, p.quantity)) as pos_count
                              FROM public.users u
                                  JOIN public.orders o ON o.user_id = u.id
                                  LEFT JOIN public.users a ON u.admin_parent_id = a.id   
                                  LEFT JOIN public.order_files orf ON o.id=orf.order_id
                                  LEFT JOIN public.shoes sh ON o.id = sh.order_id
                                  LEFT JOIN public.shoes_quantity_sizes sh_qs ON sh.id = sh_qs.shoe_id 
                                  LEFT JOIN public.clothes  cl ON o.id = cl.order_id
                                  LEFT JOIN public.cl_quantity_sizes cl_qs ON cl.id = cl_qs.cl_id
                                  LEFT JOIN public.linen l ON o.id = l.order_id
                                  LEFT JOIN public.linen_quantity_sizes l_qs ON l.id = l_qs.lin_id
                                  LEFT JOIN public.parfum p ON o.id = p.order_id 
                              WHERE  {conditional_stmt}
                              GROUP BY u.id, o.id, o.crm_created_at
                              ORDER BY o.crm_created_at ASC
                               """
    res = db.session.execute(text(stmt_orders))
    return res.fetchall()


def helper_check_extension(filename: str) -> bool:
    return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in settings.CRM_ALLOWED_EXTENSIONS


def helper_create_filename(o_id: int, manager_name: str, filename: str) -> tuple[Optional[str], Optional[str]]:
    try:
        extension = filename.rsplit('.')[1]
    except Exception:
        return None, None
    origin = f"{manager_name}_order_{o_id}.{extension}"

    prefix = uuid4().hex[:8] + str(int(datetime.now().timestamp()))
    fs_name = prefix + origin
    return origin, fs_name


def helper_m_order_processed(user: User, o_id: int, manager_id: int, f_manager_id: int = None) -> Response:

    order_stmt = text(f"""
                    SELECT o.id as id,
                        o.stage as stage,
                        orf.id as of_id,
                        orf.file_system_name as file_system_name,
                        orf.file_link as file_link
                    FROM public.orders o 
                    LEFT JOIN public.order_files orf ON o.id=orf.order_id
                    WHERE o.id=:o_id AND o.manager_id=:manager_id;
                  """).bindparams(o_id=o_id, manager_id=manager_id)
    order_info = db.session.execute(order_stmt).fetchone()

    if not order_info:
        flash(message=settings.Messages.ORDER_MANAGER_PROCESSED_ABS_ERROR, category='error')
        return redirect(url_for('crm_d.managers'))
    if not order_info.file_system_name and not order_info.file_link:
        flash(message=settings.Messages.ORDER_MANAGER_PROCESSED_ABS_FILE_ERROR, category='error')
        return redirect(url_for('crm_d.managers'))
    if order_info.file_system_name and not check_order_file(order_file_name=order_info.file_system_name, o_id=o_id):
        return redirect(url_for(f'crm_d.managers'))

    if user.id != manager_id and user.role not in [settings.SUPER_USER, settings.SUPER_MANAGER]:
        flash(message=settings.Messages.STRANGE_REQUESTS, category='error')
        return redirect(url_for('crm_d.managers'))
    dt_manager = datetime.now()
    stmt = text(f"""
               UPDATE public.orders 
               SET stage_setter_name='{user.login_name}', stage={settings.OrderStage.MANAGER_PROCESSED}, m_finished='{dt_manager}'
               WHERE id=:o_id; 
               """).bindparams(o_id=o_id)
    try:
        db.session.execute(stmt)
        db.session.commit()
        flash(message=settings.Messages.ORDER_MANAGER_PROCESSED)
    except IntegrityError:
        db.session.rollback()
        flash(message=settings.Messages.ORDER_MANAGER_PROCESSED_ERROR)
        logger.error(settings.Messages.ORDER_MANAGER_PROCESSED_ERROR)

    return redirect(url_for('crm_d.managers', filtered_manager_id=f_manager_id))


# push to problem-solved stage
def helper_m_order_ps(user: User, o_id: int, manager_id: int, f_manager_id: int = None) -> Response:
    order_stmt = text(f"""
                    SELECT o.id as id,
                        o.stage as stage,
                        o.user_id as user_id,
                        o.order_idn as order_idn,
                        orf.id as of_id,
                        orf.file_system_name as file_system_name,
                        orf.file_link as file_link
                    FROM public.orders o 
                    LEFT JOIN public.order_files orf ON o.id=orf.order_id
                    WHERE o.id=:o_id AND o.manager_id=:manager_id;
                  """).bindparams(o_id=o_id, manager_id=manager_id)
    order_info = db.session.execute(order_stmt).fetchone()

    if not order_info:
        flash(message=settings.Messages.ORDER_MANAGER_PS_ABS_ERROR, category='error')
        return redirect(url_for('crm_d.managers'))
    if not order_info.file_system_name and not order_info.file_link:
        flash(message=settings.Messages.ORDER_MANAGER_PROCESSED_ABS_FILE_ERROR, category='error')
        return redirect(url_for('crm_d.managers'))
    if order_info.file_system_name and not check_order_file(order_file_name=order_info.file_system_name, o_id=o_id):
        return redirect(url_for(f'crm_d.managers'))
    if user.id != manager_id and user.role not in [settings.SUPER_USER, settings.SUPER_MANAGER]:
        flash(message=settings.Messages.STRANGE_REQUESTS, category='error')
        return redirect(url_for('crm_d.managers'))
    dt_manager = datetime.now()
    stmt = text(f"""
                   UPDATE public.orders 
                   SET stage_setter_name='{user.login_name}', stage={settings.OrderStage.MANAGER_SOLVED}, m_finished='{dt_manager}'
                   WHERE id=:o_id;
               """).bindparams(o_id=o_id)
    try:
        db.session.execute(stmt)
        db.session.commit()
        flash(message=settings.Messages.ORDER_MANAGER_PS)
    except IntegrityError:
        db.session.rollback()
        flash(message=settings.Messages.ORDER_MANAGER_PROCESSED_ERROR)
        logger.error(settings.Messages.ORDER_MANAGER_PROCESSED_ERROR)
    else:
        helper_send_user_order_tg_notify(user_id=order_info.user_id, order_idn=order_info.order_idn,
                                         order_stage=settings.OrderStage.MANAGER_SOLVED)
    return redirect(url_for('crm_d.managers', filtered_manager_id=f_manager_id))


def helper_m_order_bp(user: User, o_id: int, manager_id: int, f_manager_id: int = None) -> Response:
    order_stmt = text(f"""
                    SELECT o.id as id,
                        o.user_id as user_id,
                        o.order_idn as order_idn,
                        o.stage as stage
                    FROM public.orders o 
                    LEFT JOIN public.order_files orf ON o.id=orf.order_id
                    WHERE o.id=:o_id AND o.manager_id=:manager_id;
                  """).bindparams(o_id=o_id, manager_id=manager_id)
    order_info = db.session.execute(order_stmt).fetchone()

    if not order_info:
        flash(message=settings.Messages.ORDER_MANAGER_PS_ABS_ERROR, category='error')
        return redirect(url_for('crm_d.agents')) if user.role not in [settings.MANAGER_USER, settings.SUPER_MANAGER] \
            else redirect(url_for('crm_d.managers'))

    if user.role not in [settings.SUPER_USER, settings.SUPER_MANAGER] or order_info.stage not in [settings.OrderStage.MANAGER_PROCESSED, settings.OrderStage.MANAGER_SOLVED]:
        flash(message=settings.Messages.STRANGE_REQUESTS, category='error')
        return redirect(url_for('crm_d.agents')) if user.role not in [settings.MANAGER_USER, settings.SUPER_MANAGER] \
            else redirect(url_for('crm_d.managers'))

    stmt = text(f"""UPDATE public.orders 
                    SET stage={settings.OrderStage.MANAGER_START}, cp_created=NULL, sent_at=NULL, m_finished=NULL
                    WHERE id=:o_id; 
               """).bindparams(o_id=o_id)
    try:
        db.session.execute(stmt)
        db.session.commit()
        flash(message=settings.Messages.ORDER_MANAGER_BP)
    except IntegrityError:
        db.session.rollback()
        flash(message=settings.Messages.ORDER_MANAGER_BP_ERROR)
        logger.error(settings.Messages.ORDER_MANAGER_BP_ERROR)
    else:
        helper_send_user_order_tg_notify(user_id=order_info.user_id, order_idn=order_info.order_idn,
                                         order_stage=settings.OrderStage.MANAGER_START)
    return redirect(url_for('crm_d.agents')) if user.role not in [settings.MANAGER_USER, settings.SUPER_MANAGER]\
        else redirect(url_for('crm_d.managers', filtered_manager_id=f_manager_id))


def helper_attach_file(manager: str, manager_id: int, o_id: int) -> Response:
    order_stmt = text(f"""
                        SELECT o.id as id,
                            o.stage as stage,
                            orf.id as of_id,
                            orf.file_system_name as file_system_name
                        FROM public.orders o 
                        LEFT JOIN public.order_files orf ON o.id=orf.order_id
                        WHERE o.id=:o_id AND o.manager_id=:manager_id;
                      """).bindparams(o_id=o_id, manager_id=manager_id)
    order_info = db.session.execute(order_stmt).fetchone()

    if not order_info:
        flash(message=settings.Messages.ORDER_ATTACH_FILE_ABS_ERROR, category='error')
        return redirect(url_for('crm_d.managers'))

    file = request.files.get('order_file', '')

    if file.filename == '' or not helper_check_extension(filename=file.filename):
        flash(message=f'{settings.Messages.ORDER_MANAGER_FEXT} {file.filename}', category='error')
        return redirect(url_for('crm_d.managers'))
    # not correct- make file read if you want to save file to disk
    # file_size = len(file.read())
    #
    # if file_size > settings.OrderStage.MAX_ORDER_FILE_SIZE:
    #     flash(message=f'{settings.Messages.ORDER_ATTACH_FILE_EXCEED_ERROR} {file_size} bytes', category='error')
    #     return redirect(url_for('crm_d.managers'))

    of_id = order_info.of_id
    ofs_name = order_info.file_system_name
    if ofs_name and ofs_name in o_listdir(path=settings.DOWNLOAD_DIR_CRM):
        o_remove(settings.DOWNLOAD_DIR_CRM + order_info.file_system_name)

    filename = secure_filename(filename=file.filename)
    origin, fs_name = helper_create_filename(o_id=o_id, manager_name=manager, filename=filename)

    if not fs_name:
        flash(message=settings.Messages.CRM_FILENAME_ERROR, category='error')
        return redirect(url_for('crm_d.managers'))

    # insert data
    stmt = text(f"""UPDATE public.order_files 
                 SET origin_name='{origin}', file_system_name='{fs_name}', file_link='', order_id=:o_id 
                 WHERE id={of_id}
                """ if of_id else f"""
                   INSERT INTO public.order_files (origin_name, file_system_name, file_link, order_id)
                   VALUES ('{origin}', '{fs_name}', '', :o_id);
               """).bindparams(o_id=o_id)

    try:
        db.session.execute(stmt)
        db.session.commit()
        flash(message=settings.Messages.ORDER_ATTACH_FILE)
    except IntegrityError as ie:
        db.session.rollback()
        flash(message=settings.Messages.ORDER_ATTACH_FILE_ERROR, category='error')
        logger.error(settings.Messages.ORDER_ATTACH_FILE_ERROR + str(ie))
    except Exception as e:
        flash(message=settings.Messages.ORDER_ATTACH_FILE_ERROR, category='error')
        logger.error(settings.Messages.ORDER_ATTACH_FILE_ERROR + str(e))
        return redirect(url_for('crm_d.managers'))
    if file:
        file.save(dst=o_path.join(settings.DOWNLOAD_DIR_CRM, fs_name))

    return redirect(url_for('crm_d.managers'))


def helper_attach_of_link(manager: str, manager_id: int, o_id: int) -> Response:
    order_stmt = f"""
                        SELECT o.id as id,
                            o.stage as stage,
                            orf.id as of_id,
                            orf.file_system_name as file_system_name
                        FROM public.orders o 
                        LEFT JOIN public.order_files orf ON o.id=orf.order_id
                        WHERE o.id={o_id} AND o.manager_id={manager_id};
                      """
    order_info = db.session.execute(text(order_stmt)).fetchone()

    if not order_info:
        flash(message=settings.Messages.ORDER_ATTACH_FILE_ABS_ERROR, category='error')
        return redirect(url_for('crm_d.managers'))

    file_link = request.form.get('of_link', '').replace('--', '')

    of_id = order_info.of_id
    ofs_name = order_info.file_system_name
    if ofs_name and ofs_name in o_listdir(path=settings.DOWNLOAD_DIR_CRM):
        o_remove(settings.DOWNLOAD_DIR_CRM + order_info.file_system_name)

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
        flash(message=settings.Messages.ORDER_ATTACH_FILE_LINK)
    except IntegrityError as e:
        db.session.rollback()
        message = f"{settings.Messages.ORDER_ATTACH_FILE_LINK_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)

    return redirect(url_for('crm_d.managers'))


def helper_download_file(manager_id: int, o_id: int, user_type: str) -> Response:
    order_stmt = f"""
                        SELECT o.id as id,
                            o.stage as stage,
                            orf.id as of_id,
                            orf.origin_name as origin_name,
                            orf.file_system_name as file_system_name
                        FROM public.orders o 
                        LEFT JOIN public.order_files orf ON o.id=orf.order_id
                        WHERE o.id={o_id} AND o.manager_id={manager_id};
                      """
    order_info = db.session.execute(text(order_stmt)).fetchone()

    if not order_info:
        flash(message=settings.Messages.ORDER_DOWNLOAD_FILE_ABS_ERROR, category='error')
        return redirect(url_for(f'crm_d.{user_type}'))
    o_name, fs_name = order_info.origin_name, order_info.file_system_name

    if not check_order_file(order_file_name=order_info.file_system_name, o_id=o_id):
        return redirect(url_for(f'crm_d.{user_type}'))
    return send_from_directory(directory=settings.DOWNLOAD_DIR_CRM, path=fs_name, download_name=o_name)


def helper_delete_order_file(manager_id: int, o_id: int) -> Response:

    order_stmt = f"""
                        SELECT o.id as id,
                            o.stage as stage,
                            orf.id as of_id,
                            orf.file_system_name as file_system_name
                        FROM public.orders o 
                        LEFT JOIN public.order_files orf ON o.id=orf.order_id
                        WHERE o.id={o_id} AND o.manager_id={manager_id};
                      """
    order_info = db.session.execute(text(order_stmt)).fetchone()

    if not order_info:
        flash(message=settings.Messages.ORDER_DELETE_FILE_ABS_ERROR, category='error')
        return redirect(url_for('crm_d.managers'))

    of_id = order_info.of_id
    ofs_name = order_info.file_system_name
    if ofs_name and ofs_name in o_listdir(path=settings.DOWNLOAD_DIR_CRM):
        o_remove(settings.DOWNLOAD_DIR_CRM + order_info.file_system_name)

    stmt = f"DELETE FROM public.order_files pof WHERE pof.id={of_id}"

    try:
        db.session.execute(text(stmt))
        db.session.commit()
        flash(message=settings.Messages.ORDER_DELETE_FILE)
    except IntegrityError:
        db.session.rollback()
        flash(message=settings.Messages.ORDER_DELETE_FILE_ERROR, category='error')
        logger.error(settings.Messages.ORDER_DELETE_FILE_ERROR)

    return redirect(url_for('crm_d.managers'))


def helper_change_manager(manager_id: int, o_id: int) -> Response:
    order_stmt = f"""
                            SELECT o.id as id,
                                o.stage as stage,
                                o.manager_id as manager_id
                                
                            FROM public.orders o 
                            LEFT JOIN public.order_files orf ON o.id=orf.order_id
                            WHERE o.id={o_id} AND o.manager_id={manager_id};
                          """
    order_info = db.session.execute(text(order_stmt)).fetchone()

    if not order_info:
        flash(message=settings.Messages.ORDER_MANAGER_CHANGE_ABS_ERROR, category='error')
        return redirect(url_for('crm_d.managers'))

    new_manager_id = int(request.form.get('operator_id')) if request.form.get('operator_id') else None

    managers_ids = (User.query.with_entities(User.id).
                    filter((User.role == settings.MANAGER_USER) | (User.role == settings.SUPER_MANAGER)).all())

    if (new_manager_id, ) not in managers_ids:
        # print(managers_ids)
        flash(message=settings.Messages.ORDER_MANAGER_CHANGE_ABS_ERROR, category='error')

    else:
        stmt = (text("UPDATE public.orders SET manager_id=:new_manager_id WHERE id=:o_id;")
                .bindparams(new_manager_id=new_manager_id, o_id=o_id))
        try:
            db.session.execute(stmt)
            db.session.commit()
            flash(message=settings.Messages.ORDER_MANAGER_CHANGE)
        except IntegrityError:
            flash(message=settings.Messages.ORDER_MANAGER_CHANGE_ERROR, category='error')
            logger.error(settings.Messages.ORDER_MANAGER_CHANGE_ERROR)

    return redirect(url_for('crm_d.managers'))


def helper_cancel_order(user: User, o_id: int, cancel_comment: str):
    stmt_get_agent = f"SELECT a.admin_parent_id FROM public.users a WHERE a.id  = (SELECT o.user_id FROM public.orders o WHERE o.id={o_id} LIMIT 1)"
    order_stmt = f"""
                    SELECT o.id as id,
                        o.user_id as user_id,
                        o.order_idn as order_idn,
                        ({stmt_get_agent}) as agent_id,
                        orf.id as of_id,
                        orf.file_system_name as file_system_name
                    FROM public.orders o 
                    LEFT JOIN public.order_files orf ON o.id=orf.order_id
                    WHERE o.id={o_id};
                  """
    order_info = db.session.execute(text(order_stmt)).fetchone()
    # check for order exist and admin correct
    if not order_info or (((user.id != order_info.agent_id and user.id != order_info.user_id) and user.role != settings.SUPER_USER)):
        flash(message=settings.Messages.STRANGE_REQUESTS, category='error')
        return redirect(url_for('crm_d.agents'))

    # delete rows from db and delete file from syst
    of_delete_remove(order_info=order_info, o_id=o_id)

    # update order stage
    dt_agent = datetime.now()
    stmt = f"""
               UPDATE public.orders 
               SET stage={settings.OrderStage.CANCELLED},
                   comment_cancel='{cancel_comment}',
                   cc_created='{dt_agent}'
               WHERE id={o_id} 
            """
    try:
        db.session.execute(text(stmt))
        db.session.commit()
        flash(message=settings.Messages.ORDER_CANCEL)
    except IntegrityError:
        db.session.rollback()
        flash(message=settings.Messages.ORDER_CANCEL_ERROR)
        logger.error(settings.Messages.ORDER_CANCEL_ERROR)
    else:
        helper_send_user_order_tg_notify(user_id=order_info.user_id, order_idn=order_info.order_idn,
                                         order_stage=settings.OrderStage.CANCELLED)
    return redirect(url_for('crm_d.agents'))


def helper_change_agent_stage(o_id: int, stage: int, user: User):

    stmt_get_agent = f"SELECT a.admin_parent_id FROM public.users a  WHERE a.id  = (SELECT o.user_id FROM public.orders o WHERE o.id={o_id} LIMIT 1)"

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
                            ({stmt_get_agent}) as agent_id,
                            orf.id as of_id,
                            orf.file_system_name as file_system_name
                        FROM public.orders o 
                        LEFT JOIN public.order_files orf ON o.id=orf.order_id
                        LEFT JOIN public.user_transactions ut ON o.transaction_id=ut.id
                        WHERE o.id={o_id};
                      """
    order_info = db.session.execute(text(order_stmt)).fetchone()

    # check for order exist and admin correct
    # ordinary user change state check for his admin
    user_order_agent_check = (order_info.agent_id and user.id != order_info.agent_id)
    # agent user change state check for his admin
    agent_order_agent_check = (not order_info.agent_id and user.id != order_info.user_id)

    # (((order_info.agent_id and user.id != order_info.agent_id) or (
    #             not order_info.agent_id and order_info.user_id != user.id)) and user.role != settings.SUPER_USER)
    if stage not in settings.OrderStage.CHECK_TUPLE or not order_info or \
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
                if not helper_get_at2_pending_balance(admin_id=user.id, price_id=user.price_id, balance=user.balance,
                                                      trust_limit=user.trust_limit):
                    return redirect(url_for('crm_d.agents'))

            return helper_crm_process_order_stats(o_id=o_id, order_info=order_info,
                                                  stage=stage, additional_stmt=additional_stmt)
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


def helper_crm_process_order_stats(o_id: int, order_info, stage: int, additional_stmt: str) -> Response:
    stmt = f"""
                                      UPDATE public.orders 
                                      SET stage={stage}
                                      {additional_stmt}
                                      WHERE id={o_id} 
                                   """
    try:
        db.session.execute(text(stmt))
        db.session.commit()

        row_count, mark_count = get_rows_marks(o_id=o_id, category=order_info.category)

        # new_stat = OrderStat(category=order_info.category, company_idn=order_info.company_idn,
        #                      company_type=order_info.company_type,
        #                      company_name=order_info.company_name, order_idn=order_info.order_idn,
        #                      rows_count=row_count, marks_count=mark_count, op_cost=order_info.op_cost,
        #                      created_at=order_info.created_at,
        #                      comment_problem=order_info.comment_problem, cp_created=order_info.cp_created,
        #                      m_started=order_info.m_started, m_finished=order_info.m_finished,
        #                      crm_created_at=order_info.crm_created_at, sent_at=order_info.sent_at,
        #                      stage_setter_name=order_info.stage_setter_name,
        #                      manager_id=order_info.manager_id, user_id=order_info.user_id,
        #                      transaction_id=order_info.transaction_id)
        #                      # closed_at = datetime.now(),
        # db.session.add(new_stat)

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
        flash(message=settings.Messages.ORDER_STAGE_CHANGE)
    except IntegrityError:
        flash(message=settings.Messages.ORDER_STAGE_CHANGE_ERROR, category='error')
        db.session.rollback()
        logger.error(settings.Messages.ORDER_STAGE_CHANGE_ERROR)
    else:
        helper_send_user_order_tg_notify(user_id=order_info.user_id, order_idn=order_info.order_idn,
                                         order_stage=settings.OrderStage.POOL)
    return redirect(url_for('crm_d.agents'))


def of_delete_remove(order_info: Order, o_id: int) -> None:
    # check if we got a file in pur folder
    if order_info.file_system_name and order_info.file_system_name in o_listdir(path=settings.DOWNLOAD_DIR_CRM):
        o_remove(settings.DOWNLOAD_DIR_CRM + order_info.file_system_name)
    # delete order file info in db
    if order_info.of_id:
        stmt = f"DELETE FROM public.order_files pof WHERE pof.order_id={o_id}"
        try:
            db.session.execute(text(stmt))
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            logger.error(e)


def helpers_problem_order(problem_order: Order, problem_comment: str, with_check: bool = False) -> None:
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
        flash(message=settings.Messages.ORDER_PROBLEM)
    except IntegrityError:
        db.session.rollback()
        flash(message=settings.Messages.ORDER_PROBLEM_ERROR, category='error')
        logger.error(settings.Messages.ORDER_PROBLEM_ERROR)
    else:
        helper_send_user_order_tg_notify(user_id=problem_order.user_id, order_idn=problem_order.order_idn,
                                         order_stage=settings.OrderStage.MANAGER_PROBLEM)
        MarkinerisInform.send_message_tg.delay(order_idn=problem_order.order_idn, problem_order_flag=True)


def helpers_ceps_order(o_id: int, ep: int):
    status = 'danger'
    message = settings.Messages.NO_SUCH_ORDER_CRM
    try:

        order_info = db.session.execute(text("SELECT id from public.orders WHERE id=:o_id;").bindparams(o_id=o_id)).fetchone()
        if not order_info:
            return jsonify({'status': status, 'message': message})
        ep = True if ep == 1 else False
        query = text("UPDATE public.orders SET external_problem=:ep WHERE id=:o_id;").bindparams(o_id=o_id, ep=ep)

        db.session.execute(query)
        db.session.commit()

        status = 'success'
        message = settings.Messages.ORDER_CEPS_SUCCESS
        return jsonify({'status': status, 'message': message})
    except Exception as e:
        db.session.rollback()
        logger.error(f"{settings.Messages.ORDER_CEPS_ERROR} {e}")
        return jsonify({'status': status, 'message': message})


def helpers_m_take_order(user: User, o_id: int) -> Response:
    order_id = Order.query.with_entities(Order.id, Order.stage).filter_by(id=o_id, stage=settings.OrderStage.POOL).first()

    if not order_id:
        flash(message=settings.Messages.ORDER_MANAGER_TAKE_ABS_ERROR, category='error')
        return redirect(url_for('crm_d.managers'))

    if user.role == settings.MANAGER_USER:
        stmt = f"""
                    SELECT COUNT(co.id) as orders_count FROM public.orders co WHERE co.manager_id={user.id} AND co.stage < {settings.OrderStage.SENT}; 
               """
        order_count = db.session.execute(text(stmt)).fetchone().orders_count

        if order_count >= settings.OrderStage.MANAGER_ORDERS_LIMIT:
            flash(message=f'{settings.Messages.ORDERS_MANAGER_LIMIT} Всего: {order_count}', category='error')
            return redirect(url_for('crm_d.managers'))

    dt_manager = datetime.now()
    stmt = f"""
                   UPDATE public.orders 
                   SET manager_id={user.id}, stage={settings.OrderStage.MANAGER_START}, m_started='{dt_manager}'
                   WHERE id={o_id} 
               """
    try:
        db.session.execute(text(stmt))
        db.session.commit()
        flash(message=settings.Messages.ORDER_MANAGER_TAKE)
    except IntegrityError:
        db.session.rollback()
        flash(message=settings.Messages.ORDER_MANAGER_TAKE_ERROR)
        logger.error(settings.Messages.ORDER_MANAGER_TAKE_ERROR)

    return redirect(url_for('crm_d.managers'))


def check_order_file(order_file_name: str, o_id: int) -> bool:
    if order_file_name not in o_listdir(path=settings.DOWNLOAD_DIR_CRM):
        problem_order = Order.query.get(o_id)
        flash(message=settings.Messages.ORDER_FILE_ABS_ERROR, category='error')
        helpers_problem_order(problem_order=problem_order, problem_comment=settings.Messages.ORDER_FILE_ABS_ERROR, with_check=True)
        return False
    return True


def helper_clean_oco() -> Response:
    try:
        dt_co = date.today() - timedelta(days=settings.OrderStage.DAYS_CONTENT)

        stmt = f"DELETE FROM public.orders pof " \
               f"WHERE pof.stage={settings.OrderStage.CANCELLED} AND pof.cc_created<'{dt_co}'"

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
            stmt = text(f"""
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
               SET stage={settings.OrderStage.CRM_PROCESSED},
                   closed_at='{closed_at}', processed={True}
               WHERE stage={settings.OrderStage.SENT} AND sent_at < '{date_compare}' AND payment=True; 
            """)
    try:
        db.session.execute(stmt)
        db.session.commit()
        status = 'success'
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

    stmt = text(f"""
                   UPDATE public.orders 
                   SET stage={stage_to},
                   WHERE stage={settings.OrderStage.SENT} AND payment=False; 
                """)
    try:
        db.session.execute(stmt)
        db.session.commit()

        status = 'success'
        message = settings.Messages.OS_CHANGE_SUCCESS.format(stage_from=settings.OrderStage.STAGES[stage_from][1],
                                                             stage_to=settings.OrderStage.STAGES[stage_to][1])
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.OS_CHANGE_STAGE_ERROR} {e}"
        logger.error(message)

    return jsonify({'status': status, 'message': message})


def check_manager_orders(u_id: int) -> int:

    stmt = f"SELECT COUNT(*) FROM public.orders o " \
           f"WHERE o.manager_id={u_id} and o.stage<{settings.OrderStage.SENT};"

    res = db.session.execute(text(stmt)).fetchone()[0]
    return res


def h_get_agent_order_info(search_order_idn):
    date_compare = date.today() - timedelta(days=settings.OrderStage.DAYS_CONTENT)
    conditional_stmt = f"((o.stage>{settings.OrderStage.CREATING} AND o.stage!={settings.OrderStage.TELEGRAM_PROCESSED} AND o.stage!={settings.OrderStage.CANCELLED} AND o.stage!={settings.OrderStage.CRM_PROCESSED}) OR ((o.stage={settings.OrderStage.CANCELLED} AND o.cc_created  > '{date_compare}') OR (o.stage={settings.OrderStage.CRM_PROCESSED} AND o.closed_at > '{date_compare}')))"
    stmt_get_manager = f"(select managers.login_name from public.users managers where managers.id=o.manager_id)"
    additional_stmt = """
                                         o.comment_problem as comment_problem,
                                         o.comment_cancel as comment_cancel,
                                         o.cp_created as cp_created,
                                         o.cc_created as cc_created,
                                         o.crm_created_at as crm_created_at,
                                         o.m_started as m_started,
                                         o.m_finished as m_finished,
                                         o.sent_at as sent_at,
                                         o.closed_at as closed_at,
                                      """
    stmt_get_agent = f"CASE WHEN MAX(a.login_name) IS NOT NULL THEN MAX(a.login_name) ELSE u.login_name end"
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
                                      MAX(orf.origin_name) as order_file,
                                      MAX(orf.file_link) as order_file_link,
                                      {stmt_get_manager} as manager,
                                      o.stage_setter_name as stage_setter_name,
                                      {additional_stmt}
                                      COUNT(o.id) as row_count,
                                      COUNT(coalesce(sh.rd_date, cl.rd_date, l.rd_date, p.rd_date)) as declar_doc,
                                      SUM(coalesce(sh.box_quantity*sh_qs.quantity, cl.box_quantity*cl_qs.quantity, l.box_quantity*l_qs.quantity, p.quantity)) as pos_count
                                  FROM public.users u
                                      JOIN public.orders o ON o.user_id = u.id  
                                      LEFT JOIN public.users a ON u.admin_parent_id = a.id  
                                      LEFT JOIN public.order_files orf ON o.id=orf.order_id 
                                      LEFT JOIN public.shoes sh ON o.id = sh.order_id
                                      LEFT JOIN public.shoes_quantity_sizes sh_qs ON sh.id = sh_qs.shoe_id 
                                      LEFT JOIN public.clothes  cl ON o.id = cl.order_id
                                      LEFT JOIN public.cl_quantity_sizes cl_qs ON cl.id = cl_qs.cl_id
                                      LEFT JOIN public.linen l ON o.id = l.order_id
                                      LEFT JOIN public.linen_quantity_sizes l_qs ON l.id = l_qs.lin_id
                                      LEFT JOIN public.parfum p ON o.id = p.order_id 
                                  WHERE  {conditional_stmt} AND o.order_idn=:search_order_idn
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
                                o.cp_created as cp_created,
                                o.cc_created as cc_created,
                                o.m_started as m_started,
                                o.m_finished as m_finished,
                             """

    conditional_stmt_common = f"(o.stage!={settings.OrderStage.POOL} AND o.stage>{settings.OrderStage.CREATING} AND o.stage<={settings.OrderStage.MANAGER_SOLVED} AND o.stage!={settings.OrderStage.CRM_PROCESSED})"

    stmt_get_manager = f"(select login_name from public.users managers where managers.id=o.manager_id)"

    if user.role not in [settings.SUPER_USER, settings.SUPER_MANAGER, ]:
        # conditional_stmt = f"o.stage={settings.OrderStage.POOL}" if pool else conditional_stmt_common + f" AND o.manager_id={manager_id}"
        conditional_stmt = f"(({conditional_stmt_common} AND o.manager_id={manager_id}) OR o.stage={settings.OrderStage.POOL})"

        # stmt_get_agent = f"SELECT a.login_name FROM public.users a  WHERE ((a.id=u.admin_parent_id and (a.role='{settings.ADMIN_USER}' or a.role='{settings.SUPER_USER}')) OR (a.id=u.id and (a.role='{settings.ADMIN_USER}' or a.role='{settings.SUPER_USER}')))"
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
                                     MAX(orf.origin_name) as order_file,
                                     MAX(orf.file_link) as order_file_link,
                                     o.manager_id as manager_id,
                                     {stmt_get_manager} as manager,
                                     o.stage_setter_name as stage_setter_name,
                                     {additional_stmt}
                                     COUNT(o.id) as row_count,
                                     COUNT(coalesce(sh.rd_date, cl.rd_date, l.rd_date, p.rd_date)) as declar_doc,
                                     SUM(coalesce(sh.box_quantity*sh_qs.quantity, cl.box_quantity*cl_qs.quantity, l.box_quantity*l_qs.quantity, p.quantity)) as pos_count
                                 FROM public.users u
                                     JOIN public.orders o ON o.user_id = u.id
                                     LEFT JOIN public.users a ON u.admin_parent_id = a.id   
                                     LEFT JOIN public.order_files orf ON o.id=orf.order_id
                                     LEFT JOIN public.shoes sh ON o.id = sh.order_id
                                     LEFT JOIN public.shoes_quantity_sizes sh_qs ON sh.id = sh_qs.shoe_id 
                                     LEFT JOIN public.clothes  cl ON o.id = cl.order_id
                                     LEFT JOIN public.cl_quantity_sizes cl_qs ON cl.id = cl_qs.cl_id
                                     LEFT JOIN public.linen l ON o.id = l.order_id
                                     LEFT JOIN public.linen_quantity_sizes l_qs ON l.id = l_qs.lin_id
                                     LEFT JOIN public.parfum p ON o.id = p.order_id 
                               WHERE o.order_idn=:search_order_idn AND {conditional_stmt}
                               GROUP BY u.id, o.id, o.crm_created_at
                               ORDER BY o.crm_created_at
                              """).bindparams(search_order_idn=search_order_idn)
    else:
        # manager_condition = f" AND o.manager_id={filtered_manager_id}" if filtered_manager_id else ""
        # conditional_stmt = f"({conditional_stmt_common}{manager_condition} OR o.stage={settings.OrderStage.POOL})"
        conditional_stmt = f"({conditional_stmt_common} OR o.stage={settings.OrderStage.POOL})"

        # stmt_get_agent = f"SELECT a.login_name FROM public.users a  WHERE ((a.id=u.admin_parent_id and (a.role='{settings.ADMIN_USER}' or a.role='{settings.SUPER_USER}')) OR (a.id=u.id and (a.role='{settings.ADMIN_USER}' or a.role='{settings.SUPER_USER}')))"
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
                                      o.user_comment as user_comment,
                                      o.has_new_tnveds as has_new_tnveds,
                                      MAX(orf.origin_name) as order_file,
                                      MAX(orf.file_link) as order_file_link,
                                      o.manager_id as manager_id,
                                      {stmt_get_manager} as manager,
                                      o.stage_setter_name as stage_setter_name,
                                      {additional_stmt}
                                      COUNT(o.id) as row_count,
                                      COUNT(coalesce(sh.rd_date, cl.rd_date, l.rd_date, p.rd_date)) as declar_doc,
                                      SUM(coalesce(sh.box_quantity*sh_qs.quantity, cl.box_quantity*cl_qs.quantity, l.box_quantity*l_qs.quantity, p.quantity)) as pos_count
                                  FROM public.users u
                                      JOIN public.orders o ON o.user_id = u.id
                                      LEFT JOIN public.users a ON u.admin_parent_id = a.id   
                                      LEFT JOIN public.order_files orf ON o.id=orf.order_id
                                      LEFT JOIN public.shoes sh ON o.id = sh.order_id
                                      LEFT JOIN public.shoes_quantity_sizes sh_qs ON sh.id = sh_qs.shoe_id 
                                      LEFT JOIN public.clothes  cl ON o.id = cl.order_id
                                      LEFT JOIN public.cl_quantity_sizes cl_qs ON cl.id = cl_qs.cl_id
                                      LEFT JOIN public.linen l ON o.id = l.order_id
                                      LEFT JOIN public.linen_quantity_sizes l_qs ON l.id = l_qs.lin_id
                                      LEFT JOIN public.parfum p ON o.id = p.order_id 
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
        message = settings.Messages.CRM_SEARCH_ORDER_ERROR.format(comment=f"Либо заказ отсутствует, либо отменен и готов и старше {settings.OrderStage.DAYS_CONTENT} дней!")
        return jsonify({'status': status, 'message': message})

    status = 'success'
    ps_limit_qry = ServerParam.query.get(1)
    problem_order_time_limit = ps_limit_qry.crm_manager_ps_limit if ps_limit_qry and ps_limit_qry.crm_manager_ps_limit \
        else settings.OrderStage.DEFAULT_PS_LIMIT
    cur_time = datetime.now()
    match order_info.stage:
        case settings.OrderStage.NEW:
            new_orders = [order_info, ]
            htmlresponse = render_template(f'crm/crma/crma_1.html', **locals())
        case settings.OrderStage.POOL:
            pool_orders = [order_info, ]
            htmlresponse = render_template(f'crm/crma/crma_2.html', **locals())
        case settings.OrderStage.MANAGER_START:
            m_start_orders = [order_info, ]
            htmlresponse = render_template(f'crm/crma/crma_3.html', **locals())
        case settings.OrderStage.MANAGER_PROCESSED:
            m_processed_orders = [order_info, ]
            htmlresponse = render_template(f'crm/crma/crma_5.html', **locals())
        case settings.OrderStage.MANAGER_PROBLEM:
            m_problem_orders = [order_info, ]
            htmlresponse = render_template(f'crm/crma/crma_6.html', **locals())
        case settings.OrderStage.MANAGER_SOLVED:
            m_solved_orders = [order_info, ]
            htmlresponse = render_template(f'crm/crma/crma_7.html', **locals())
        case settings.OrderStage.SENT:
            sent_orders = [order_info, ]
            htmlresponse = render_template(f'crm/crma/crma_8.html', **locals())
        case settings.OrderStage.CANCELLED:
            cancelled_orders = [order_info, ]
            htmlresponse = render_template(f'crm/crma/crma_9.html', **locals())
        case settings.OrderStage.CRM_PROCESSED:
            crm_processed_orders = [order_info, ]
            htmlresponse = render_template(f'crm/crma/crma_10.html', **locals())
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

    status = 'success'
    ps_limit_qry = ServerParam.query.get(1)
    problem_order_time_limit = ps_limit_qry.crm_manager_ps_limit if ps_limit_qry and ps_limit_qry.crm_manager_ps_limit \
        else settings.OrderStage.DEFAULT_PS_LIMIT
    cur_time = datetime.now()

    htmlresponse = ''
    match order_info.stage:
        case settings.OrderStage.POOL:
            pool_orders = [order_info, ]
            htmlresponse = render_template(f'crm/crmm/crmm_1.html', **locals())
        case settings.OrderStage.MANAGER_START:
            m_start_orders = [order_info, ]
            htmlresponse = render_template(f'crm/crmm/crmm_2.html', **locals())
        case settings.OrderStage.MANAGER_PROCESSED:
            m_processed_orders = [order_info, ]
            htmlresponse = render_template(f'crm/crmm/crmm_4.html', **locals())
        case settings.OrderStage.MANAGER_PROBLEM:
            m_problem_orders = [order_info, ]
            htmlresponse = render_template(f'crm/crmm/crmm_5.html', **locals())
        case settings.OrderStage.MANAGER_SOLVED:
            m_solved_orders = [order_info, ]
            htmlresponse = render_template(f'crm/crmm/crmm_6.html', **locals())

    return jsonify({'htmlresponse': htmlresponse, 'status': status})


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
                                          .filter_by(stage=settings.OrderStage.MANAGER_PROCESSED).all()]
    if not orders_users:
        return {'status': status,
                'message': settings.Messages.OS_CHANGE_EMPTY.format(stage_from=settings.OrderStage.
                                                                    STAGES[settings.OrderStage.MANAGER_PROCESSED][1],
                                                                    stage_to=settings.OrderStage.
                                                                    STAGES[settings.OrderStage.SENT][1])}
    stmt = text(f"""
                     UPDATE public.orders 
                     SET stage={settings.OrderStage.SENT},
                         sent_at='{sent_at}'
                     WHERE stage={settings.OrderStage.MANAGER_PROCESSED}; 
                  """)
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
