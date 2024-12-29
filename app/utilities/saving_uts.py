from datetime import datetime
from functools import wraps
from time import time
from typing import Optional

from flask import flash
from sqlalchemy.sql import desc, text

from config import settings
from logger import logger
from models import User, Order, Shoe, ShoeQuantitySize, Socks, SocksQuantitySize, Linen, LinenQuantitySize, Parfum, \
    Clothes, ClothesQuantitySize, db


def time_count(func):
    @wraps(func)
    def wrapper(*args, **kw):
        t_start = time()
        result = func(*args, **kw)
        res = f"{func.__name__}, :  {time() - t_start}"
        logger.info(res)
        return result
    return wrapper


def process_input_str(value: str) -> str:
    return value.replace("\"", '').replace("\'", '').replace(":", '').replace("?", '').strip()


def save_shoes(order: Order, form_dict: dict, sizes_quantities: list) -> Order:
    rd_date = datetime.strptime(form_dict.get("rd_date"), '%d.%m.%Y').date() if form_dict.get("rd_date") else None
    new_shoe_order = Shoe(trademark=process_input_str(form_dict.get("trademark")),
                          article=process_input_str(form_dict.get("article")), type=form_dict.get("type"),
                          color=form_dict.get("color"), box_quantity=form_dict.get("box_quantity"),
                          material_top=form_dict.get("material_top"),
                          material_lining=form_dict.get("material_lining"),
                          material_bottom=form_dict.get("material_bottom"),
                          gender=form_dict.get("gender"), country=form_dict.get("country"),
                          with_packages=True if form_dict.get("with_packages") == "True" else False,
                          tnved_code=form_dict.get("tnved_code"), article_price=form_dict.get("article_price"),
                          tax=form_dict.get("tax"), rd_type=form_dict.get("rd_type"),
                          rd_name=form_dict.get("rd_name").replace('№', ''),
                          rd_date=rd_date)

    extend_sq = (ShoeQuantitySize(size=el[0], quantity=el[1]) for el in sizes_quantities)
    new_shoe_order.sizes_quantities.extend(extend_sq)
    order.shoes.append(new_shoe_order)

    return order


def save_clothes(order: Order, form_dict: dict, sizes_quantities: list) -> Order:
    rd_date = datetime.strptime(form_dict.get("rd_date"), '%d.%m.%Y').date() if form_dict.get("rd_date") else None
    new_clothes_order = Clothes(trademark=process_input_str(form_dict.get("trademark")),
                                article=process_input_str(form_dict.get("article")),
                                type=form_dict.get("type"),
                                color=form_dict.get("color"),
                                content=form_dict.get("content")[:101], box_quantity=form_dict.get("box_quantity"),
                                gender=form_dict.get("gender"), country=form_dict.get("country"),
                                tnved_code=form_dict.get("tnved_code"), article_price=form_dict.get("article_price"),
                                tax=form_dict.get("tax"), rd_type=form_dict.get("rd_type"),
                                rd_name=form_dict.get("rd_name").replace('№', ''),
                                rd_date=rd_date)

    extend_sq = (ClothesQuantitySize(size=el[0], quantity=el[1],
                                     size_type=el[2] if el[0] != settings.Clothes.UNITE_SIZE_VALUE
                                     else settings.Clothes.DEFAULT_SIZE_TYPE) for el in sizes_quantities)
    new_clothes_order.sizes_quantities.extend(extend_sq)
    order.clothes.append(new_clothes_order)
    return order


def save_socks(order: Order, form_dict: dict, sizes_quantities: list) -> Order:
    rd_date = datetime.strptime(form_dict.get("rd_date"), '%d.%m.%Y').date() if form_dict.get("rd_date") else None
    new_socks_order = Socks(trademark=process_input_str(form_dict.get("trademark")),
                              article=process_input_str(form_dict.get("article")),
                              type=form_dict.get("type"),
                              color=form_dict.get("color"),
                              content=form_dict.get("content")[:101], box_quantity=form_dict.get("box_quantity"),
                              gender=form_dict.get("gender"), country=form_dict.get("country"),
                              tnved_code=form_dict.get("tnved_code"), article_price=form_dict.get("article_price"),
                              tax=form_dict.get("tax"), rd_type=form_dict.get("rd_type"),
                              rd_name=form_dict.get("rd_name").replace('№', ''),
                              rd_date=rd_date)
    extend_sq = (SocksQuantitySize(size=el[0], quantity=el[1],
                                   size_type=el[2] if el[0] != settings.Socks.UNITE_SIZE_VALUE
                                     else settings.Socks.DEFAULT_SIZE_TYPE) for el in sizes_quantities)
    new_socks_order.sizes_quantities.extend(extend_sq)
    order.socks.append(new_socks_order)
    return order


def save_linen(order: Order, form_dict: dict, sizes_quantities: list) -> Order:
    # with_p = form_dict.get("with_packages")
    with_p = "False"
    rd_date = datetime.strptime(form_dict.get("rd_date"), '%d.%m.%Y').date() if form_dict.get("rd_date") else None
    new_linen_order = Linen(trademark=process_input_str(form_dict.get("trademark")),
                            article=process_input_str(form_dict.get("article")),
                            type=form_dict.get("type"),
                            color=form_dict.get("color"),
                            with_packages='да' if form_dict.get("with_packages") == "True" else 'нет',
                            box_quantity=form_dict.get("box_quantity"),
                            customer_age=form_dict.get("customer_age"), textile_type=form_dict.get("textile_type"),
                            content=form_dict.get("content"), country=form_dict.get("country"),
                            tnved_code=form_dict.get("tnved_code"), article_price=form_dict.get("article_price"),
                            tax=form_dict.get("tax"), rd_type=form_dict.get("rd_type"),
                            rd_name=form_dict.get("rd_name").replace('№', ''),
                            rd_date=rd_date)

    if with_p == "True":
        max_sq = max(sizes_quantities, key=lambda x: int(x[0].split('*')[0] * int(x[0].split('*')[1])))
        append_sq = LinenQuantitySize(size=max_sq[0], quantity=max_sq[1])
        new_linen_order.sizes_quantities.append(append_sq)

    else:
        extend_sq = (LinenQuantitySize(size=el[0], quantity=el[1]) for el in sizes_quantities)
        new_linen_order.sizes_quantities.extend(extend_sq)

    order.linen.append(new_linen_order)
    return order


def save_parfum(order: Order, form_dict: dict) -> Order:
    with_p = form_dict.get("with_packages")
    rd_date = datetime.strptime(form_dict.get("rd_date"), '%d.%m.%Y').date() if form_dict.get("rd_date") else None
    new_parfum_order = Parfum(trademark=process_input_str(form_dict.get("trademark")),
                              volume_type=form_dict.get("volume_type"),
                              volume=form_dict.get("volume"), package_type=form_dict.get("package_type"),
                              material_package=form_dict.get("material_package"), type=form_dict.get("type"),
                              with_packages='да' if form_dict.get("with_packages") == "True" else 'нет',
                              box_quantity=form_dict.get("box_quantity"),
                              quantity=form_dict.get("quantity"), country=form_dict.get("country"),
                              tnved_code=form_dict.get("tnved_code"), article_price=form_dict.get("article_price"),
                              tax=form_dict.get("tax"), rd_type=form_dict.get("rd_type"),
                              rd_name=form_dict.get("rd_name").replace('№', ''),
                              rd_date=rd_date)

    order.parfum.append(new_parfum_order)
    return order


def common_save_db(order: Order, form_dict: dict, category: str, sizes_quantities: list = None) -> Order:
    tnved_code_raw = form_dict.get("tnved_code")

    form_dict.update({"tnved_code": tnved_code_raw if tnved_code_raw else ''})

    for k in form_dict:
        form_dict[k] = form_dict[k].replace('--', '')

    match category:
        case settings.Shoes.CATEGORY:
            order = save_shoes(order=order, form_dict=form_dict, sizes_quantities=sizes_quantities)
        case settings.Clothes.CATEGORY:
            order = save_clothes(order=order, form_dict=form_dict, sizes_quantities=sizes_quantities)
        case settings.Socks.CATEGORY:
            order = save_socks(order=order, form_dict=form_dict, sizes_quantities=sizes_quantities)
        case settings.Linen.CATEGORY:
            order = save_linen(order=order, form_dict=form_dict, sizes_quantities=sizes_quantities)
        case settings.Parfum.CATEGORY:
            order = save_parfum(order=order, form_dict=form_dict)
    return order


def common_save_copy_order(u_id: int, user: User, category: str, order: Order) -> Optional[int]:

    try:

        new_order = Order(company_type=order.company_type, company_name=order.company_name,
                          edo_type=order.edo_type, edo_id=order.edo_id,
                          company_idn=order.company_idn, mark_type=order.mark_type,
                          category=order.category, processed=False)

        match category:
            case settings.Shoes.CATEGORY:
                new_order = save_copy_order_shoes(order_category_list=order.shoes, new_order=new_order)
            case settings.Clothes.CATEGORY:
                new_order = save_copy_order_clothes(order_category_list=order.clothes, new_order=new_order)
            case settings.Socks.CATEGORY:
                new_order = save_copy_order_socks(order_category_list=order.socks, new_order=new_order)
            case settings.Linen.CATEGORY:
                new_order = save_copy_order_linen(order_category_list=order.linen, new_order=new_order)
            case settings.Parfum.CATEGORY:
                new_order = save_copy_order_parfum(order_category_list=order.parfum, new_order=new_order)

        user.orders.append(new_order)
        db.session.commit()

        return Order.query.with_entities(Order.id).filter_by(user_id=u_id).order_by(desc(Order.id)).first().id
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.ORDER_ADD_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)

        return None


def save_copy_order_shoes(order_category_list: list[Shoe], new_order: Order) -> Order:
    new_order.shoes.extend(Shoe(trademark=shoe.trademark,
                                article=shoe.article, type=shoe.type,
                                color=shoe.color, box_quantity=shoe.box_quantity,
                                material_top=shoe.material_top,
                                material_lining=shoe.material_lining,
                                material_bottom=shoe.material_bottom,
                                gender=shoe.gender, country=shoe.country,
                                with_packages=shoe.with_packages,
                                tnved_code=shoe.tnved_code, article_price=shoe.article_price,
                                tax=shoe.tax, rd_type=shoe.rd_type, rd_name=shoe.rd_name.replace('№', ''),
                                rd_date=shoe.rd_date,
                                sizes_quantities=list((ShoeQuantitySize(size=sq.size, quantity=sq.quantity)
                                                                    for sq in shoe.sizes_quantities)))
                           for shoe in order_category_list)
    return new_order


def save_copy_order_clothes(order_category_list: list[Clothes], new_order: Order) -> Order:
    new_order.clothes.extend(Clothes(trademark=clothes.trademark,
                                     article=clothes.article, type=clothes.type,
                                     color=clothes.color, content=clothes.content,
                                     box_quantity=clothes.box_quantity,
                                     gender=clothes.gender, country=clothes.country,
                                     tnved_code=clothes.tnved_code, article_price=clothes.article_price,
                                     tax=clothes.tax, rd_type=clothes.rd_type, rd_name=clothes.rd_name.replace('№', ''),
                                     rd_date=clothes.rd_date,
                                     sizes_quantities=list((ClothesQuantitySize(size=sq.size, quantity=sq.quantity, size_type=sq.size_type)
                                                            for sq in clothes.sizes_quantities)))
                             for clothes in order_category_list)
    return new_order


def save_copy_order_socks(order_category_list: list[Socks], new_order: Order) -> Order:
    new_order.socks.extend(Socks(trademark=sock.trademark,
                                     article=sock.article, type=sock.type,
                                     color=sock.color, content=sock.content,
                                     box_quantity=sock.box_quantity,
                                     gender=sock.gender, country=sock.country,
                                     tnved_code=sock.tnved_code, article_price=sock.article_price,
                                     tax=sock.tax, rd_type=sock.rd_type, rd_name=sock.rd_name.replace('№', ''),
                                     rd_date=sock.rd_date,
                                 sizes_quantities=list(
                                     (SocksQuantitySize(size=sq.size, quantity=sq.quantity, size_type=sq.size_type)
                                      for sq in sock.sizes_quantities)))
                             for sock in order_category_list)
    return new_order


def save_copy_order_linen(order_category_list: list[Linen], new_order: Order) -> Order:
    new_order.linen.extend(Linen(trademark=linen.trademark,
                                 article=linen.article, type=linen.type,
                                 color=linen.color, with_packages=linen.with_packages,
                                 box_quantity=linen.box_quantity,
                                 customer_age=linen.customer_age, textile_type=linen.textile_type,
                                 content=linen.content,
                                 country=linen.country,
                                 tnved_code=linen.tnved_code, article_price=linen.article_price,
                                 tax=linen.tax, rd_type=linen.rd_type, rd_name=linen.rd_name.replace('№', ''),
                                 rd_date=linen.rd_date,
                                 sizes_quantities=list((LinenQuantitySize(size=sq.size, quantity=sq.quantity)
                                                        for sq in linen.sizes_quantities)))
                           for linen in order_category_list)

    return new_order


def save_copy_order_parfum(order_category_list: list[Parfum], new_order: Order) -> Order:

    new_order.parfum.extend((Parfum(trademark=parfum.trademark,
                            volume_type=parfum.volume_type,
                            volume=parfum.volume, package_type=parfum.package_type,
                            material_package=parfum.material_package, type=parfum.type,
                            with_packages=parfum.with_packages, box_quantity=parfum.box_quantity,
                            quantity=parfum.quantity,
                            country=parfum.country,
                            tnved_code=parfum.tnved_code, article_price=parfum.article_price,
                            tax=parfum.tax, rd_type=parfum.rd_type, rd_name=parfum.rd_name.replace('№', ''), rd_date=parfum.rd_date)
                             for parfum in order_category_list))
    return new_order


def get_rows_marks(o_id: int, category: str) -> tuple[int, int]:
    match category:
        case settings.Shoes.CATEGORY:
            res = db.session.execute(text(f"""
                SELECT COUNT(shoes_quantity_sizes.quantity),
                 SUM(public.shoes.box_quantity*public.shoes_quantity_sizes.quantity)
                       FROM public.orders 
                           JOIN public.shoes ON public.orders.id = public.shoes.order_id
                           JOIN  public.shoes_quantity_sizes ON public.shoes.id= public.shoes_quantity_sizes.shoe_id
                       WHERE public.orders.category=:category AND public.orders.id=:o_id
                       GROUP BY public.orders.id
                       """).bindparams(category=settings.Shoes.CATEGORY, o_id=o_id))
            row_count, mark_count = res.fetchall()[0]
        case settings.Clothes.CATEGORY:
            res = db.session.execute(text("""
                SELECT COUNT(cl_quantity_sizes.quantity),
                 SUM(public.clothes.box_quantity*public.cl_quantity_sizes.quantity)
                   FROM public.orders 
                       JOIN public.clothes ON public.orders.id = public.clothes.order_id
                       JOIN  public.cl_quantity_sizes ON public.clothes.id=public.cl_quantity_sizes.cl_id
                   WHERE public.orders.category=:category AND public.orders.id=:o_id
                   GROUP BY public.orders.id
                   """).bindparams(category=settings.Clothes.CATEGORY, o_id=o_id))
            row_count, mark_count = res.fetchall()[0]
        case settings.Socks.CATEGORY:
            res = db.session.execute(text(f"""
                        SELECT COUNT(public.socks_quantity_sizes.quantity),
                         SUM(public.socks.box_quantity*public.socks_quantity_sizes.quantity)
                           FROM public.orders 
                               JOIN public.socks ON public.orders.id = public.socks.order_id
                               JOIN  public.socks_quantity_sizes ON public.socks.id=public.socks_quantity_sizes.socks_id
                           WHERE public.orders.category='{settings.Socks.CATEGORY}' AND public.orders.id={o_id}
                           GROUP BY public.orders.id
                           """))
            row_count, mark_count = res.fetchall()[0]
        case settings.Linen.CATEGORY:
            res = db.session.execute(text("""
                SELECT COUNT(linen_quantity_sizes.quantity),
                    SUM(public.linen.box_quantity*public.linen_quantity_sizes.quantity)
                    FROM public.orders 
                      JOIN public.linen ON public.orders.id = public.linen.order_id
                      JOIN  public.linen_quantity_sizes ON public.linen.id=public.linen_quantity_sizes.lin_id
                    WHERE public.orders.category=:category AND public.orders.id=:o_id
                    GROUP BY public.orders.id
                    """).bindparams(category=settings.Linen.CATEGORY, o_id=o_id))
            row_count, mark_count = res.fetchall()[0]
        case settings.Parfum.CATEGORY:
            res = db.session.execute(text("""
                SELECT COUNT(parfum.quantity), SUM(parfum.quantity)
                    FROM public.orders 
                        JOIN public.parfum ON public.orders.id = public.parfum.order_id
                    WHERE public.orders.category=:category AND public.orders.id=:o_id
                    GROUP BY public.orders.id
                    """).bindparams(category=settings.Parfum.CATEGORY, o_id=o_id))
            row_count, mark_count = res.fetchall()[0]

        case _:
            row_count, mark_count = 0, 0
    return row_count, mark_count


def get_delete_stmts(category: str, o_id: int) -> list:
    stmts = []
    match category:
        case settings.Shoes.CATEGORY:
            stmt1 = f"""DELETE FROM public.shoes_quantity_sizes AS sqs
                                        USING public.shoes AS sh
                                        WHERE sqs.shoe_id = sh.id AND sh.order_id = {o_id}
                                    """
            stmt2 = f"""DELETE FROM public.shoes AS sh

                                        WHERE sh.order_id = {o_id}
                                        """
            stmt3 = f"""DELETE FROM public.orders AS o WHERE o.id={o_id}"""

            stmts.extend((stmt1, stmt2, stmt3))

        case settings.Clothes.CATEGORY:
            stmt1 = f"""DELETE FROM public.cl_quantity_sizes AS cqs
                                                USING public.clothes AS cl, public.orders AS o
                                                WHERE cqs.cl_id = cl.id AND cl.order_id={o_id}
                                            """
            stmt2 = f"""DELETE FROM public.clothes AS cl
                                                USING public.orders AS o
                                                WHERE cl.order_id={o_id}
                                                """
            stmt3 = f"""DELETE FROM public.orders AS o WHERE o.id = {o_id}"""
            stmts.extend((stmt1, stmt2, stmt3))
        case settings.Socks.CATEGORY:
            stmt1 = f"""DELETE FROM public.socks_quantity_sizes AS sqs
                                                        USING public.socks AS sk, public.orders AS o
                                                        WHERE sqs.socks_id = sk.id AND sk.order_id={o_id}
                                                    """
            stmt2 = f"""DELETE FROM public.socks AS sk
                                                        USING public.orders AS o
                                                        WHERE sk.order_id={o_id}
                                                        """
            stmt3 = f"""DELETE FROM public.orders AS o WHERE o.id = {o_id}"""
            stmts.extend((stmt1, stmt2, stmt3))
        case settings.Linen.CATEGORY:
            stmt1 = f"""DELETE FROM public.linen_quantity_sizes AS lqs
                                                USING public.linen AS ln, public.orders AS o
                                                WHERE lqs.lin_id=ln.id AND ln.order_id={o_id}
                                            """
            stmt2 = f"""DELETE FROM public.linen AS ln
                                                USING public.orders AS o
                                                WHERE ln.order_id={o_id}
                                                """
            stmt3 = f"""DELETE FROM public.orders AS o WHERE o.id={o_id}"""
            stmts.extend((stmt1, stmt2, stmt3))
        case settings.Parfum.CATEGORY:
            stmt1 = f"""DELETE FROM public.parfum AS pm
                                                USING public.orders AS o
                                                WHERE pm.order_id={o_id}
                                                """
            stmt2 = f"""DELETE FROM public.orders AS o WHERE o.id={o_id}"""
            stmts.extend((stmt1, stmt2))
        case _:
            flash(message=settings.Messages.ORDER_DELETE_ERROR)
            raise Exception
    return stmts


def get_delete_pos_stmts(category: str, m_id: int) -> str:
    stmt = ""
    match category:
        case settings.Shoes.CATEGORY:
            stmt = f"DELETE FROM public.shoes WHERE public.shoes.id={m_id}"
        case settings.Clothes.CATEGORY:
            stmt = f"DELETE FROM public.clothes WHERE public.clothes.id={m_id}"
        case settings.Socks.CATEGORY:
            stmt = f"DELETE FROM public.socks AS sm WHERE sm.id={m_id}"
        case settings.Linen.CATEGORY:
            stmt = f"DELETE FROM public.linen WHERE public.linen.id={m_id}"
        case settings.Parfum.CATEGORY:
            stmt = f"DELETE FROM public.parfum AS pm WHERE pm.id={m_id}"
        case _:
            flash(message=settings.Messages.ORDER_DELETE_ERROR)
            raise Exception
    return stmt


def helper_check_partner_codes_admin(partner_id: int, admin_id: int) -> tuple[bool, Optional[str]]:
    try:
        res = db.session.execute(text("""
                                    SELECT 
                                        u.login_name as admin,
                                        up.user_id as up_user_id
                                        FROM public.users u
                                        LEFT JOIN  public.users_partners up on up.user_id=u.id
                                        WHERE u.id=:admin_id
                                        GROUP BY u.id, up.user_id, up.partner_code_id
                                        HAVING up.partner_code_id=:partner_id
                                        ORDER BY u.id DESC
                                 """).bindparams(admin_id=admin_id, partner_id=partner_id)).fetchone()

        if res:
            return True, res.admin
        else:
            return False, ''
    except Exception as e:
        logger.error(
            "Произошло исключение при проверке партнер кодов агента"
            f"\nОшибка {e}"
        )
        return False, ''


def get_sql_admin_partner_codes(u_id: int) -> Optional[list]:
    res = db.session.execute(text(f"""
                            SELECT partner_codes.id, partner_codes.code, users_partners.partner_code_id, users.login_name 
                            FROM users
                             JOIN users_partners ON users_partners.user_id=users.id
                             JOIN partner_codes on partner_codes.id=users_partners.partner_code_id
                            WHERE users.id={u_id}; 
                            """)).fetchall()
    return res
