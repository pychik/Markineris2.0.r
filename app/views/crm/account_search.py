"""Поиск активных заказов по email для суперадминистратора и модераторов."""
import re

from flask import jsonify, render_template, request
from sqlalchemy import text

from config import settings
from models import db
from utilities.order_log import CRM_STAGE_LABELS
from utilities.sql_categories_aggregations import SQLQueryCategoriesAll


def account_search_stages(user):
    if getattr(user, "is_at2", False) or user.role not in (settings.SUPER_USER, settings.MARKINERIS_ADMIN_USER):
        return ()
    stages = (
        settings.OrderStage.NEW, settings.OrderStage.POOL,
        settings.OrderStage.MANAGER_START, settings.OrderStage.MANAGER_EDO,
        settings.OrderStage.MANAGER_PROBLEM, settings.OrderStage.MANAGER_SOLVED,
    )
    return stages


def get_orders_by_account(user, value):
    stages = account_search_stages(user)
    if not stages:
        return []
    query = text(f"""
        SELECT o.id, o.order_idn, o.stage, o.category, o.payment,
               o.user_comment, o.processing_info, o.is_moderation,
               COALESCE(o.crm_created_at, o.created_at) AS crm_created_at,
               o.company_type, o.company_name, o.company_idn,
               MAX(managers.login_name) AS manager,
               {SQLQueryCategoriesAll.get_stmt(field='subcategory')} AS subcategory,
               {SQLQueryCategoriesAll.get_stmt(field='rows_count')} AS row_count,
               {SQLQueryCategoriesAll.get_stmt(field='marks_count')} AS pos_count,
               {SQLQueryCategoriesAll.get_stmt(field='declar_doc')} AS declar_doc,
               {SQLQueryCategoriesAll.get_stmt(field='is_rf_order')} AS is_rf_order,
               {SQLQueryCategoriesAll.get_stmt(field='has_children')} AS has_children
        FROM public.users u
        JOIN public.orders o ON o.user_id = u.id
        LEFT JOIN public.users managers ON managers.id = o.manager_id
        {SQLQueryCategoriesAll.get_joins()}
        WHERE LOWER(u.email) = LOWER(:account)
          AND o.stage IN ({','.join(str(stage) for stage in stages)})
          AND o.to_delete IS NOT TRUE
        GROUP BY o.id
        ORDER BY o.stage, crm_created_at, o.id
    """)
    params = {"account": value}
    return db.session.execute(query, params).fetchall()


def search_orders_by_account(user):
    stages = account_search_stages(user)
    if not stages:
        return jsonify(status="danger", message="Недостаточно прав для поиска."), 403
    value = (request.form.get("account") or "").strip()
    if len(value) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
        return jsonify(status="warning", message="Введите полный email пользователя."), 400

    orders = get_orders_by_account(user, value)
    groups = [
        {"stage": stage, "label": "Отправлены фирме" if stage == settings.OrderStage.POOL else CRM_STAGE_LABELS[stage],
         "orders": [order for order in orders if order.stage == stage]}
        for stage in stages
    ]
    html = render_template("crm_mod_v1/helpers/account_search_results.html",
                           groups=groups, account=value, total=len(orders))
    return jsonify(status="success", htmlresponse=html)
