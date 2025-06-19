from datetime import datetime
from math import floor as m_floor
from sqlalchemy import text
from uuid import uuid4
from models import db, TransactionStatuses, TransactionTypes
from config import settings


def agent_fee_edit_on_cancel_order(total_order_price: int, admin_info: dict, order_idn: str) -> str:
    admin_id = admin_info.get('admin_id')
    admin_name = admin_info.get('admin_name')
    agent_fee = admin_info.get('agent_fee')

    created_at = datetime.now()
    uuid_postfix = str(uuid4())
    bill_path = f'patch_{admin_name}{uuid_postfix}'

    agent_fee_part = m_floor(total_order_price * agent_fee / 100)

    transaction_agent_commission_stmt = (
        f"""INSERT into public.user_transactions (
                                type, 
                                amount, 
                                status, 
                                transaction_type,
                                agent_fee, 
                                promo_info, 
                                bill_path, 
                                created_at,
                                user_id, 
                                cancel_comment
                            )
                            VALUES(
                                False, 
                                {agent_fee_part}, 
                                {TransactionStatuses.success.value}, 
                                '{TransactionTypes.agent_commission_cancel.value}',
                                {agent_fee},
                                '', 
                                '{bill_path}_{TransactionTypes.agent_commission_cancel.value}', 
                                '{created_at}',
                                {admin_id},
                                'Отменен заказ {order_idn}'
                            );
                            """
    )
    agent_balance_stmt = f"""UPDATE public.users set balance=balance-{agent_fee_part} WHERE id = {admin_id};"""
    agent_balance_and_commission_stmt = transaction_agent_commission_stmt + agent_balance_stmt
    return agent_balance_and_commission_stmt


def get_order_user_context(user_id: int) -> dict:
    """
    Возвращает подробную информацию по пользователю: является ли агентом,
    его роль, админ и др. для дальнейшей логики возврата.
    """
    query = text("""
        SELECT id, is_at2, role, admin_parent_id
        FROM public.users
        WHERE id = :user_id
    """).bindparams(user_id=user_id)

    result = db.session.execute(query).fetchone()
    if not result:
        raise Exception("User not found")

    return dict(result._mapping)


def build_refund_sql_on_order_cancel(order_idn: str, user_info: dict, order_cost: int, op_cost: int) -> str:
    user_id = user_info["id"]
    is_at2 = user_info["is_at2"]
    role = user_info["role"]
    admin_id = user_info["admin_parent_id"]

    created_at = datetime.now()
    bill_path = f'patch_ServerCancel_transaction{uuid4()}'

    sql = ""

    # --- Тип2 агент ---
    if is_at2 and role == settings.ORD_USER:
        sql += f"""
            INSERT INTO public.user_transactions(
                type, amount, op_cost, status, transaction_type, bill_path, created_at, user_id, wo_account_info
            )
            VALUES (
                True, {order_cost}, {op_cost}, {TransactionStatuses.success.value},
                '{TransactionTypes.refund_funds.value}', '{bill_path}', '{created_at}', {admin_id}, '{order_idn}'
            );
            UPDATE public.users SET balance = balance + {order_cost} WHERE id = {admin_id};
        """

    # --- Тип1 агент ---
    elif not is_at2 and role == settings.ORD_USER:

        # 1. Возврат агенту (тип1 клиент)
        sql += f"""
            INSERT INTO public.user_transactions(
                type, amount, op_cost, status, transaction_type, bill_path, created_at, user_id, wo_account_info
            )
            VALUES (
                True, {order_cost}, {op_cost}, {TransactionStatuses.success.value},
                '{TransactionTypes.refund_funds.value}', '{bill_path}', '{created_at}', {user_id}, '{order_idn}'
            );
            UPDATE public.users SET balance = balance + {order_cost} WHERE id = {user_id};
        """

        # 2. Списание комиссии с админа, если у него роль 'admin'
        admin_info = db.session.execute(text("""
            SELECT id as admin_id, agent_fee as agent_fee, login_name as admin_name, role as role
            FROM public.users WHERE id = :admin_id
        """).bindparams(admin_id=admin_id)).fetchone()

        if admin_info and admin_info.role == "admin":
            sql += agent_fee_edit_on_cancel_order(order_cost, dict(admin_info._mapping), order_idn=order_idn)
    # --- Обычный пользователь ---
    else:
        sql += f"""
            INSERT INTO public.user_transactions(
                type, amount, op_cost, status, transaction_type, bill_path, created_at, user_id, wo_account_info
            )
            VALUES (
                True, {order_cost}, {op_cost}, {TransactionStatuses.success.value},
                '{TransactionTypes.refund_funds.value}', '{bill_path}', '{created_at}', {user_id}, '{order_idn}'
            );
            UPDATE public.users SET balance = balance + {order_cost} WHERE id = {user_id};
        """

    # Общие действия
    sql += f"""
        UPDATE public.orders_stats SET op_cost = NULL WHERE order_idn = '{order_idn}';
        UPDATE public.server_params SET balance = balance + {order_cost};
    """

    return sql


def h_cancel_order_process_payment(order_idn: str, user_id: int) -> None:
    # Получение суммы заказа
    oc_query = text("""
        SELECT ROUND(CAST(os.op_cost AS DECIMAL(10,2)) * CAST(os.marks_count AS INTEGER)) AS order_amount,
               os.op_cost as op_cost
        FROM public.orders_stats os
        WHERE order_idn = :order_idn;
    """).bindparams(order_idn=order_idn)

    amount_res = db.session.execute(oc_query).fetchone()
    order_cost, op_cost = (amount_res.order_amount, amount_res.op_cost) if amount_res else (0, 0)

    # Получение контекста пользователя
    user_info = get_order_user_context(user_id)

    # Сбор SQL на основании роли и типа
    refund_sql = build_refund_sql_on_order_cancel(order_idn, user_info, order_cost, op_cost)

    # Выполнение
    db.session.execute(text(refund_sql))

