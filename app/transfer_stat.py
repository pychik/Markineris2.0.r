import io
import logging as logger
import os
import psycopg2

from collections import namedtuple
from functools import wraps
from psycopg2.extensions import cursor as p_cursor
from time import time
from urllib.parse import urlparse


logger.basicConfig(level=logger.INFO,
                   format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
                   datefmt='%Y-%m-%d %H:%M:%S',)


def time_count(func):
    @wraps(func)
    def wrapper(*args, **kw):
        t_start = time()
        result = func(*args, **kw)
        res = f"{func.__name__}, :  {time() - t_start}"
        logger.info(msg=res)
        return result
    return wrapper


def process_db_path() -> dict:
    default_database_path = 'postgres://admin:password@localhost:5432/multiorders'
    database_path = os.getenv('DATABASE_URL', default_database_path)
    if database_path.startswith("postgres"):
        database_path = database_path.replace("postgres://", "postgresql://", 1)
    parsed = urlparse(url=database_path)
    dsn = {
        'dbname': parsed.path[1:],
        'user': parsed.username,
        'password': parsed.password,
        'host': parsed.hostname,
        'port': 5432,
        'options': '-c search_path=content',
    }
    return dsn


dsn = process_db_path()

OrderObject = namedtuple('OrderObject', 'user_id orderd_id category pos_count order_pos_count')


class OrdersGetter:
    def __init__(self, cursor: p_cursor):
        self.cursor = cursor

    def get_shoes(self) -> list:
        self.cursor.execute("""
            SELECT public.orders.category, public.orders.company_idn, public.orders.company_type, public.orders.company_name,
                   public.orders.user_id, public.orders.order_idn, public.orders.created_at,
                    COUNT(shoes_quantity_sizes.quantity), SUM(public.shoes.box_quantity*public.shoes_quantity_sizes.quantity)
                       FROM public.orders 
                           JOIN public.shoes ON public.orders.id = public.shoes.order_id
                           JOIN  public.shoes_quantity_sizes ON public.shoes.id= public.shoes_quantity_sizes.shoe_id
                       WHERE public.orders.category='обувь' AND public.orders.processed=True
                       GROUP BY public.orders.id
                       ORDER BY public.orders.user_id """)

        shoe_orders = self.cursor.fetchall()
        # shoe_orders = 1000* shoe_orders
        # from uuid import uuid4
        # shoe_orders = list(map(lambda x: (x[0], x[1], x[2], x[3], x[4], str(uuid4()), x[6], x[7] , x[8], ), shoe_orders))

        logger.info(msg=f"got {len(shoe_orders)} shoe orders. processing...")
        # logger.info(msg=f"1st row -  {shoe_orders[0]}")

        return shoe_orders

    def get_clothes(self) -> list:
        self.cursor.execute("""
        SELECT public.orders.category, public.orders.company_idn, public.orders.company_type,
            public.orders.company_name, public.orders.user_id, public.orders.order_idn, public.orders.created_at,
            COUNT(cl_quantity_sizes.quantity), SUM(public.clothes.box_quantity*public.cl_quantity_sizes.quantity)
               FROM public.orders 
                   JOIN public.clothes ON public.orders.id = public.clothes.order_id
                   JOIN  public.cl_quantity_sizes ON public.clothes.id=public.cl_quantity_sizes.cl_id
               WHERE public.orders.category='одежда' AND public.orders.processed=True
               GROUP BY public.orders.id
               ORDER BY public.orders.user_id """)

        clothes_orders = self.cursor.fetchall()
        logger.info(msg=f"got {len(clothes_orders)} clothes orders. processing...")
        logger.info(msg=f"1st row -  {clothes_orders}")

        return clothes_orders

    def get_linen(self) -> list:
        self.cursor.execute("""
        SELECT public.orders.category, public.orders.company_idn, public.orders.company_type,
            public.orders.company_name, public.orders.user_id, public.orders.order_idn, public.orders.created_at,
            COUNT(linen_quantity_sizes.quantity), SUM(public.linen.box_quantity*public.linen_quantity_sizes.quantity)
               FROM public.orders 
                   JOIN public.linen ON public.orders.id = public.linen.order_id
                   JOIN  public.linen_quantity_sizes ON public.linen.id=public.linen_quantity_sizes.lin_id
               WHERE public.orders.category='белье' AND public.orders.processed=True
               GROUP BY public.orders.id
               ORDER BY public.orders.user_id """)

        linen_orders = self.cursor.fetchall()

        logger.info(msg=f"got {len(linen_orders)} linen orders. processing...")
        # logger.info(msg=f"1st row -  {linen_orders[0]}")

        return linen_orders

    def get_parfum(self) -> list:
        self.cursor.execute("""
        SELECT public.orders.category, public.orders.company_idn, public.orders.company_type,
            public.orders.company_name, public.orders.user_id, public.orders.order_idn, public.orders.created_at,
            COUNT(parfum.quantity), SUM(parfum.quantity)
            
               FROM public.orders 
                   JOIN public.parfum ON public.orders.id = public.parfum.order_id
               WHERE public.orders.category='парфюм' AND public.orders.processed=True
               GROUP BY public.orders.id
               ORDER BY public.orders.user_id """)

        parfum_orders = self.cursor.fetchall()

        logger.info(msg=f"got {len(parfum_orders)} parfum orders. processing...")
        # logger.info(msg=f"1st rows -  {parfum_orders[0]}")

        return parfum_orders


def put_orders(cursor: p_cursor, cat_orders: list) -> None:
    args = ','.join(cursor.mogrify("(%s, %s, %s, %s, %s, %s, %s, %s, %s)", item).decode()
                    for item in cat_orders)

    cursor.execute(f"""
        INSERT into public.orders_stats (category, company_idn, company_type,
                                         company_name, user_id, order_idn, created_at, rows_count, marks_count)
               VALUES {args} ON CONFLICT DO NOTHING;
               """)


@time_count
def main(cursor: p_cursor) -> None:
    og =OrdersGetter(cursor=cursor)
    shoe_orders = og.get_shoes()
    clothes_orders = og.get_clothes()
    linen_orders = og.get_linen()
    parfum_orders = og.get_parfum()
    put_orders(cursor=cursor, cat_orders=shoe_orders)
    put_orders(cursor=cursor, cat_orders=clothes_orders)
    put_orders(cursor=cursor, cat_orders=linen_orders)
    put_orders(cursor=cursor, cat_orders=parfum_orders)


def add_shoes(cursor: p_cursor, order_id: int, quantity: int = 3500) -> None:
    cursor.execute("""
                            SELECT * FROM public.orders WHERE category='обувь' ORDER BY  public.orders.id DESC LIMIT 1""")
    res = cursor.fetchall()

    shoe_order_vals = [
        f"('БАЛЕТКИ', 0, 'КИТАЙ', 0, 'SARM_4', 'S_325', 0, 'БЕЛЫЙ', 'ВОЙЛОК', 'ВОЙЛОК', 'ВОЙЛОК', 'Мужские', {order_id}, False, '123456789121')"
        for _ in range(quantity)]
    args = ','.join(shoe_order_vals)
    cursor.execute(f"""
                    INSERT into public.shoes (type, article_price, country, tax, trademark, article, box_quantity, color,
                                              material_top, material_lining, material_bottom, gender, order_id, 
                                              with_packages, tnved_code)
                           VALUES {args} ON CONFLICT DO NOTHING;
                           """)


# ram and apache tests
# watch -n 5 free -m
# ab -n5000 -C session=eJwlzjsOwjAMANC7ZGZwHMeOe5nK-CNYWzoh7g4S7wTv3fY68ny07XVceWv7M9rWYib71ConDOIk5w6VLjhIchiZOBjKWlZUipLWQRJQF9E0EpMyM1gy2XuJky1RNOwwIKaHa0dUn2uwCciywZPTNPhOodF-kevM47_p7fMFzs8vGQ.ZCBG-A.ZV6ZW9cWJjyyYF6KB7XcVzZXRag http://192.168.0.112:5005/shoes


if __name__ == "__main__":

    with psycopg2.connect(**dsn) as conn, conn.cursor() as cursor:
        cursor.execute("""SELECT id FROM public.users order by id""")
        res_ids = map(lambda x: x[0], cursor.fetchall())
        print(*list(res_ids))
        main(cursor=cursor)
