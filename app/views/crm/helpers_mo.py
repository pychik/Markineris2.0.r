# multi operations helpers
from datetime import datetime
from flask import flash, jsonify, url_for
from sqlalchemy import text, update, null
from sqlalchemy.sql import bindparam
from sqlalchemy.exc import IntegrityError

from config import settings
from logger import logger
from models import db, Order, OrderStat
from utilities.support import helper_send_user_order_tg_notify


def h_all_new_multi_pool():
    """
        makes bulk update of all NEW orders to POOL with creating Or updating order_stats
        Notifies all users about there orders
    :return:
    """
    status = 'danger'

    all_new_orders_stmt = text("""SELECT o.id as id, o.category as category, o.company_idn as company_idn, 
                          o.stage as stage, o.company_type as company_type, o.company_name, o.order_idn,
                          o.payment as payment, MAX(ut.op_cost) as op_cost, 
                          COUNT(coalesce(sh.id, cl.id, sk.id, l.id, p.id)) as rows_count, 
                          SUM(coalesce(sh.box_quantity*sh_qs.quantity, cl.box_quantity*cl_qs.quantity, sk.box_quantity*sk_qs.quantity, l.box_quantity*l_qs.quantity, p.quantity)) as marks_count,
                          o.created_at as created_at, 
                          o.crm_created_at as crm_created_at,
                          o.user_id as user_id, o.transaction_id
                    FROM public.orders o
                           LEFT join public.user_transactions ut on ut.id=o.transaction_id  
                           LEFT JOIN public.shoes sh ON o.id = sh.order_id
                           LEFT JOIN public.shoes_quantity_sizes sh_qs ON sh.id = sh_qs.shoe_id 
                           LEFT JOIN public.clothes  cl ON o.id = cl.order_id
                           LEFT JOIN public.cl_quantity_sizes cl_qs ON cl.id = cl_qs.cl_id
                           LEFT JOIN public.socks sk ON o.id = sk.order_id
                           LEFT JOIN public.socks_quantity_sizes sk_qs ON sk.id = sk_qs.socks_id
                           LEFT JOIN public.linen l ON o.id = l.order_id
                           LEFT JOIN public.linen_quantity_sizes l_qs ON l.id = l_qs.lin_id
                           LEFT JOIN public.parfum p ON o.id = p.order_id 
                    WHERE o.stage = :stage AND (o.processed = null or o.processed=false) AND o.to_delete != True 
                    GROUP BY o.id, o.category, o.company_idn, o.company_type, o.company_name, o.order_idn, o.stage,
                     o.created_at, o.crm_created_at, o.user_id, o.payment, ut.op_cost, o.transaction_id
                    order by o.created_at
    """).bindparams(stage=settings.OrderStage.NEW)

    all_new_orders = [o for o in db.session.execute(all_new_orders_stmt).fetchall()]
    if not all_new_orders:
        status = 'warning'
        message = settings.Messages.ORDER_STAGE_CHANGE_EMPTY
        return jsonify({'status': status, 'message': message})

    dt_pool = datetime.now()
    bulk_array = [{"o_id": o.id, "stage": settings.OrderStage.POOL, 'p_started': f'{dt_pool}'} for o in all_new_orders]
    update_orders_stmt = update(Order).where(Order.id == bindparam('o_id')).values(stage=bindparam('stage'))

    # Executing the update operation in bulk

    # db.session.execute(update(Order), bulk_array)
    try:
        db.session.execute(update_orders_stmt, bulk_array)
        # db.session.execute(update(Order), bulk_array)
        # for o in all_new_orders:
        #     db.session.execute(
        #         update(Order)
        #         .where(Order.id == o.id)
        #         .values(stage=o.stage)
        #     )
        db.session.commit()

        orders_stats_stmt = h_create_multi_os_stmt(orders=all_new_orders)
        db.session.execute(orders_stats_stmt)
        db.session.commit()

        status = 'success'
        message = f"{settings.Messages.ORDER_STAGE_MULTI_CHANGE} из Новых в ПУЛ фирмы"

    except Exception as e:
        message = settings.Messages.ORDER_STAGE_CHANGE_ERROR
        db.session.rollback()
        logger.error(f"{settings.Messages.ORDER_STAGE_CHANGE_ERROR}{e}")

    else:
        for o in all_new_orders:
            helper_send_user_order_tg_notify(user_id=o.user_id, order_idn=o.order_idn,
                                             order_stage=settings.OrderStage.POOL)
    return jsonify({'status': status, 'message': message})


def h_create_multi_os_stmt(orders: list) -> str:
    """
     creates stm for upserting OrderStats
    :param orders:
    :return:
    """
    stmt = "INSERT INTO public.orders_stats (category, company_idn, company_type, company_name, order_idn, rows_count, "\
           "marks_count, op_cost, created_at, crm_created_at, user_id, transaction_id, saved_at) VALUES "
    first = True
    saved_at = datetime.now()
    for order_info in orders:
        if first:
            first = False
            prefix = ''
        else:
            prefix = ', '
        op_cost = order_info.op_cost if order_info.op_cost else null()
        transaction_id = order_info.transaction_id if order_info.transaction_id else null()

        stmt += f"{prefix}('{order_info.category}', '{order_info.company_idn}', '{order_info.company_type}', " \
                f"'{order_info.company_name}', '{order_info.order_idn}', {order_info.rows_count}, {order_info.marks_count}, " \
                f"{op_cost}, '{order_info.created_at}'," \
                f" '{order_info.crm_created_at}', {order_info.user_id}, {transaction_id}, '{saved_at}')"
    stmt += "ON CONFLICT DO NOTHING; "
    return stmt
