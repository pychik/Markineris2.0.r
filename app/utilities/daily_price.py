from sqlalchemy import text, TextClause

from config import settings
from models import db, Price, User


def get_cocmd(user_id: int, price_id: int, order_id: str | None = None,
              start_stage: int = settings.OrderStage.NEW) -> dict:
    """
    get_current_orders_cost_marks_data
    1. get all not paid orders for User in sorted by crm_created order asc
    2. gets first 2 distinct company_idn that can summarize their marks for counting
    3. compares company_idn of User order and makes calculating

    :return:
    result dict consists of pc, lpc , report_data, current_order dicts
    pc dict with orders, company_idns, marks_count for prior companies
    lpc is a list of less prior company_idns dictionaries that contain
        order_idns: list, marks_count: int, op_cost: Decimal for less prior companies
    report_data sum marks count(smc), sum count orders(sco), ao_price(all_orders price sum = marks_count*price)
    current_order consists of cost_type, new_idn_flag(if order with company_idn is already in pc or lpc), order_idn, order_op_cost, order_cost, order_marks_count for cases if order_idn is not None
    """
    unpaid_orders = db.session.execute(get_unpaid_orders_stmt(u_id=user_id, o_id=order_id,
                                                              start_stage=start_stage)).fetchall()

    # get idns distinct from unpaid_orders ORDERED by crm_created_at
    company_idns = [row.company_idn for row in
                    db.session.execute(get_unpaid_company_idns_stmt(u_id=user_id, o_id=order_id)).fetchall()]

    current_order_info = next((order for order in unpaid_orders if order.id == order_id), None) if order_id else {}

    pc_idns = company_idns[:2]  # prior_company_idns
    lpc_idns = company_idns[2:]  # less_prior_company_idns

    result = {'pc': {'order_idns': [], 'company_idns': [], 'marks_count': 0, 'op_cost': 0},
              'lpc': [],
              'report_data': {'smc': 0, 'sco': 0},
              'current_order': {}}
    result['report_data']['smc'] = sum(o.marks_count for o in unpaid_orders)
    result['report_data']['sco'] = len(unpaid_orders)

    if len(company_idns) <= 2:
        # pc_marks_count = sum(
        #     list(map(lambda x: x.marks_count if x.company_idn in pc_idns else 0, unpaid_orders)))
        pc_marks_count = sum(o.marks_count for o in unpaid_orders if o.company_idn in pc_idns)
        pc_op_cost = helper_get_user_price(price_id=price_id, pos_count=pc_marks_count)
        result['pc']['order_idns'] = [o.order_idn for o in unpaid_orders if o.company_idn in pc_idns]
        result['pc']['company_idns'] = pc_idns
        result['pc']['marks_count'] = pc_marks_count
        result['pc']['op_cost'] = pc_op_cost
        if current_order_info and current_order_info.company_idn in pc_idns:
            result['current_order'] = {
                'cost_type': 'pmc',
                'new_idn': False,
                'order_id': order_id,
                'op_cost': pc_op_cost,
                'order_cost': pc_op_cost * current_order_info.marks_count,
                'marks_count': current_order_info.marks_count
            }
    else:
        pc_marks_count = sum(o.marks_count for o in unpaid_orders if o.company_idn in pc_idns)
        pc_op_cost = helper_get_user_price(price_id=price_id, pos_count=pc_marks_count)
        result['pc']['order_idns'] = [o.order_idn for o in unpaid_orders if o.company_idn in pc_idns]
        result['pc']['company_idns'] = pc_idns
        result['pc']['marks_count'] = pc_marks_count
        result['pc']['op_cost'] = pc_op_cost
        result['current_order'] = {
            'cost_type': 'pc',
            'new_idn': False,
            'order_id': order_id,
            'op_cost': pc_op_cost,
            'order_cost': pc_op_cost * current_order_info.marks_count,
            'marks_count': current_order_info.marks_count
        } if order_id and (current_order_info and current_order_info.company_idn in pc_idns) else {}

        for lpc in lpc_idns:
            order_idns = [o.order_idn for o in unpaid_orders if o.company_idn == lpc]
            # lpc_marks_count = sum(list(map(lambda x: x.marks_count if x.company_idn == lpc else 0, unpaid_orders)))
            lpc_marks_count = sum(o.marks_count for o in unpaid_orders if o.company_idn == lpc)
            lpc_op_cost = helper_get_user_price(price_id=price_id, pos_count=lpc_marks_count)
            lpc_data = {'company_idn': lpc,
                        'order_idns': order_idns,
                        'lpc_marks_count': lpc_marks_count,
                        'lpc_op_cost': lpc_op_cost}
            result['lpc'].append(lpc_data)
            if current_order_info and current_order_info.company_idn == lpc:
                result['current_order'] = {
                    'cost_type': 'lpc',
                    'new_idn': False,
                    'order_id': order_id,
                    'op_cost': lpc_op_cost,
                    'order_cost': lpc_op_cost * current_order_info.marks_count,
                    'marks_count': current_order_info.marks_count
                }
    if current_order_info and not result['current_order']:
        new_op_cost = helper_get_user_price(price_id=price_id, pos_count=current_order_info.marks_count)
        result['current_order'] = {
            'cost_type': 'lpc',
            'new_idn': True,
            'order_id': order_id,
            'op_cost': new_op_cost,
            'order_cost': new_op_cost * current_order_info.marks_count,
            'marks_count': current_order_info.marks_count
        }

    result['report_data']['ao_price'] = round(result['pc']['marks_count'] * result['pc']['op_cost'], 2) + sum(round(lpc['lpc_marks_count'] * lpc['lpc_op_cost'], 2) for lpc in result['lpc'])
    return result


def get_unpaid_company_idns_stmt(u_id: int, o_id: int = None) -> TextClause:
    order_id_stmt = f" OR o.id={o_id}" if o_id else " "
    return text(f"""SELECT sub.company_idn, sub.crm_created_at
                    FROM (
                        SELECT DISTINCT ON (o.company_idn)
                            o.company_idn as company_idn,
                            o.crm_created_at as crm_created_at
                        FROM public.users u
                        JOIN public.orders AS o ON o.user_id = u.id
                        WHERE u.id=:u_id AND o.payment != True AND o.to_delete != True 
                          AND (o.stage>={settings.OrderStage.NEW}
                          AND o.stage != {settings.OrderStage.CANCELLED}{order_id_stmt})
                        ORDER BY o.company_idn, o.crm_created_at ASC
                    ) sub
                 ORDER BY sub.crm_created_at ASC;
                 """).bindparams(u_id=u_id)


def get_unpaid_orders_stmt(u_id: int, o_id: int = None, start_stage: int = settings.OrderStage.NEW) -> TextClause:
    order_id_stmt = f" OR o.id={o_id}" if o_id else " "
    return text(f"""SELECT o.id as id,
                                    o.payment as payment,
                                    o.order_idn as order_idn,
                                    o.category as category,
                                    o.company_idn as company_idn,
                                    o.crm_created_at as crm_created_at,
                                    SUM(coalesce(sh.box_quantity*sh_qs.quantity, cl.box_quantity*cl_qs.quantity, l.box_quantity*l_qs.quantity, p.quantity)) as marks_count
                              FROM public.users u
                                  JOIN public.orders o ON o.user_id = u.id  
                                  LEFT JOIN public.users a ON u.admin_parent_id = a.id  
                                  LEFT JOIN public.shoes sh ON o.id = sh.order_id
                                  LEFT JOIN public.shoes_quantity_sizes sh_qs ON sh.id = sh_qs.shoe_id 
                                  LEFT JOIN public.clothes  cl ON o.id = cl.order_id
                                  LEFT JOIN public.cl_quantity_sizes cl_qs ON cl.id = cl_qs.cl_id
                                  LEFT JOIN public.linen l ON o.id = l.order_id
                                  LEFT JOIN public.linen_quantity_sizes l_qs ON l.id = l_qs.lin_id
                                  LEFT JOIN public.parfum p ON o.id = p.order_id 
                                  LEFT JOIN public.users managers ON o.manager_id = managers.id
                              WHERE u.id=:u_id AND o.payment != True AND o.to_delete != True 
                                AND (o.stage>={start_stage} 
                                AND o.stage!={settings.OrderStage.CANCELLED}{order_id_stmt})
                              GROUP BY  o.id, o.crm_created_at
                              ORDER BY o.crm_created_at ASC
                             """).bindparams(u_id=u_id)


def helper_get_user_price(price_id: int | None, pos_count: int) -> int:

    index = helper_find_price_index(target=pos_count)
    if not price_id:
        up = settings.Prices.BASIC_PRICES
        index += 1 if index != -1 else 0
    else:
        up = Price.query.filter_by(id=price_id).first()
        up = (up.price_1, up.price_2, up.price_3, up.price_4, up.price_5, )
    return up[index]


def helper_find_price_index(target: int) -> int:
    quant_list = list(filter(lambda x: target <= x, settings.Prices.RANGES))
    if quant_list:
        index = settings.Prices.RANGES.index(quant_list[0])
    else:
        index = -1
    return index

# test values
# 7825504770
# 7838360491
# 7841086802
# 7826133705
