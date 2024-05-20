from datetime import datetime
from sqlalchemy import text
from uuid import uuid4
from models import db, UserTransaction
from config import settings


def h_get_user_to_refill_balance(user_id: int) -> int:

    user_info = db.session.execute(text("""SELECT is_at2, role, admin_parent_id from public.users where id=:user_id;""").bindparams(user_id=user_id)).fetchone()
    if not user_info:
        raise Exception
    if user_info.is_at2 and user_info.role == settings.ORD_USER:
        return user_info.admin_parent_id

    return user_id


def h_cancel_order_process_payment(order_idn: int, user_id: int) -> None:
    # order_cost_query
    oc_query = (text("""SELECT ROUND(CAST(os.op_cost AS DECIMAL(10,2)) * CAST(os.marks_count AS INTEGER)) AS order_amount, os.op_cost as op_cost
                            from public.orders_stats os WHERE order_idn=:order_idn;""").
                bindparams(order_idn=order_idn))
    amount_res = db.session.execute(oc_query).fetchone()
    # print(amount_res, order_idn, transaction_id, user_id)
    order_cost, op_cost = (amount_res.order_amount, amount_res.op_cost) if amount_res else (0, 0)

    # checking user or agent is_at2 to refill balance from cancelled transaction
    user_id_refill = h_get_user_to_refill_balance(user_id=user_id)

    # creating patch for unique bill_path
    # uuid_postfix = str(uuid4())
    bill_path = 'patch_ServerCancel_transaction{uuid_postfix}'.format(uuid_postfix=uuid4())

    _created_at = datetime.now()

    combined_query = (text("""INSERT INTO public.user_transactions(type, amount, op_cost, status, bill_path, created_at, user_id, wo_account_info) VALUES (True, :order_cost, :op_cost, :new_transaction_status, :bill_path, :created_at, :user_id_refill, :order_idn) ;
                              UPDATE public.orders_stats SET op_cost=NULL WHERE order_idn=:order_idn;
                              UPDATE public.users SET balance=balance+:order_cost WHERE id=:user_id_refill;
                              UPDATE public.server_params SET balance=balance+:order_cost;""")
                      .bindparams(order_idn=order_idn, new_transaction_status=settings.Transactions.SUCCESS,
                                  bill_path=bill_path, created_at=_created_at, order_cost=order_cost, op_cost=op_cost,
                                  user_id_refill=user_id_refill, ))
    db.session.execute(combined_query)
