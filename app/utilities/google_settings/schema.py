from collections import namedtuple


OrderRow = namedtuple('OrderRow', ('date_value, order_idn, partner_code, login_name, company_name,'
                                   ' phone, marks_count, rows_count, category, price, status, agent_type'))

TransactionRow = namedtuple('TransactionRow', 'u_id, tr_id, is_at2, transaction_price')

PromoRow = namedtuple('PromoRow', 'date_value, login_name, service_account, promo_code, promo_summ')

RuznakRow = namedtuple('RuznakRow',
                       'date_value, company_composed, marks_count, rows_count, category, transaction_price, final_price,'
                       ' partner_code, order_idn')

# from typing import List, Optional
# from datetime import datetime
# from pydantic import BaseModel
#
#
# class OrderRow(BaseModel):
#     date_value: str = datetime.now().strftime("%d.%m.%Y %H:%M")
#     order_idn: Optional[str] = None
#     partner_code: Optional[str] = None
#     login_name: Optional[str] = None
#     company_name: Optional[str] = None
#     phone: Optional[str] = None
#     rows_count: Optional[int] = None
#     marks_count: Optional[int] = None
#     category: Optional[str] = None
#     price: Optional[int] = None
#     status: str = "Оплачен"
#     agent_type: str = "Обычный агент"
#
#
# class DataList(BaseModel):
#     orders: List[OrderRow]
