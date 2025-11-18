from sqlalchemy import text
from logger import logger
from models import db


def update_price_set_minus10percent():
    fields = [
        "price_1", "price_2", "price_3", "price_4", "price_5",
        "price_6", "price_7", "price_8", "price_9", "price_10", "price_11"
    ]

    # округление до десятых → ROUND(x, 1)
    set_sql = ", ".join([f"{f} = ROUND({f} * 0.9, 1)" for f in fields])
    sql = f"UPDATE public.prices SET {set_sql};"

    try:
        db.session.execute(text(sql))
        db.session.commit()
    except Exception:
        logger.exception("Price edit exception")
        db.session.rollback()
