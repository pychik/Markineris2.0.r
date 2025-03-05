from logger import logger

from config import settings
from models import Clothes


def get_subcategory(order_id: int, category: str) -> str | None:
    try:
        match category:
            case settings.Clothes.CATEGORY:
                return Clothes.query.filter(
                        Clothes.order_id == order_id).first().subcategory
            case _:
                return None
    except Exception:
        logger.exception(f'Ошибка подкатегории {order_id=}, {category=}')
        return None