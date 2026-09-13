from logger import logger

from config import settings
from models import Clothes, Cosmetics, Toys


def get_subcategory(order_id: int, category: str) -> str | None:
    try:
        match category:
            case settings.Clothes.CATEGORY:
                return Clothes.query.filter(
                        Clothes.order_id == order_id).first().subcategory
            case settings.Cosmetics.CATEGORY:
                cosmetics = Cosmetics.query.filter(Cosmetics.order_id == order_id).first()
                return cosmetics.subcategory if cosmetics else None
            case settings.Toys.CATEGORY:
                toys = Toys.query.filter(Toys.order_id == order_id).first()
                return toys.subcategory if toys else None
            case _:
                return None
    except Exception:
        logger.exception(f'Ошибка подкатегории {order_id=}, {category=}')
        return None
