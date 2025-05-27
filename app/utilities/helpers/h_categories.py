from typing import Union

from flask import Response, jsonify, request, render_template, url_for
from sqlalchemy import desc

from config import settings
from models import db, Order, User, Shoe


def h_shoe_sba(o_id: int) -> Response:
    search_query = request.form.get('query', '').replace("--", "")
    if search_query:
        order_list = Shoe.query.filter(Shoe.order_id == o_id, Shoe.article.ilike(f"%{search_query}%"))\
            .order_by(desc(Shoe.id)).limit(settings.PAGINATION_PER_PAGE).all()
        numrows = len(order_list)

    else:
        numrows = 0
        order_list = ''

    return jsonify({'htmlresponse': render_template('helpers/shoes/response_shoes_sba.html', o_id=o_id, order_list=order_list,

                                                    numrows=numrows)})


def h_category_sba(u_id: int, o_id: int, model_c: db.Model, category: str) -> Response:
    numrows = 0
    order_list = ''
    if Order.query.with_entities(Order.id).filter(Order.user_id == u_id, Order.id == o_id, ~Order.to_delete).first():
        search_query = request.form.get('query', '').replace("--", "")
        if search_query:
            order_list = model_c.query.filter(model_c.order_id == o_id, model_c.article.ilike(f"%{search_query}%"))\
                .order_by(desc(model_c.id)).limit(settings.PAGINATION_PER_PAGE).all()

            numrows = len(order_list)

    return jsonify({'htmlresponse': render_template(f'helpers/{category}/response_{category}_sba.html', o_id=o_id, order_list=order_list,
                                                    numrows=numrows)})


def h_category_trademark_sba(u_id: int, o_id: int, model_c: db.Model, category: str) -> Response:
    numrows = 0
    order_list = ''
    if Order.query.with_entities(Order.id).filter(Order.user_id == u_id, Order.id == o_id, ~Order.to_delete).first():
        search_query = request.form.get('query', '').replace("--", "")
        if search_query:
            order_list = model_c.query.filter(model_c.order_id == o_id, model_c.trademark.ilike(f"%{search_query}%"))\
                .order_by(desc(model_c.id)).limit(settings.PAGINATION_PER_PAGE).all()

            numrows = len(order_list)

    return jsonify({'htmlresponse': render_template(f'helpers/{category}/response_{category}_sba.html', o_id=o_id, order_list=order_list,
                                                    numrows=numrows)})


def order_table_update(user: User, o_id: int, category: str, jsonify_flag: bool = True, has_aggr: bool = False) -> Union[Response, dict]:
    from utilities.support import orders_list_common, helper_paginate_data
    order, orders, company_type, company_name, company_idn, \
        edo_type, edo_id, mark_type, trademark, orders_pos_count, pos_count, \
        total_price, price_exist, subcategory = orders_list_common(category=category, user=user, o_id=o_id)
    category_process_name = settings.CATEGORIES_DICT[category]
    has_aggr = order.has_aggr
    link = f'javascript:{category_process_name}_update_table(\'' + url_for(f'{category_process_name}.index', o_id=o_id,
                                                        update_flag=1) + \
           '?page={0}\');'
    page, per_page, offset, pagination, order_list = helper_paginate_data(data=orders, href=link)

    return jsonify({'htmlresponse': render_template(f'helpers/{category_process_name}/response_{category_process_name}_table.html', **locals()),
                    'status': 'success', 'orders_pos_count': orders_pos_count, 'pos_count': pos_count}) \
        if jsonify_flag else {'htmlresponse': render_template(f'helpers/{category_process_name}/response_{category_process_name}_table.html', **locals()),
                              'orders_pos_count': orders_pos_count, 'pos_count': pos_count}
