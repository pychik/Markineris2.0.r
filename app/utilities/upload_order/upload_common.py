from flask import flash
from flask_login import current_user, logout_user
from functools import wraps
from pandas import read_excel, isna
from typing import Callable

from logger import logger
from models import db
from config import settings
from utilities.exceptions import ArticlesException


def val_error_start(row_num: int, col: str = None):
    return f"Строка {row_num} Столбец {col}" if col else f"Строка {row_num} "


def empty_value(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not kwargs.get('value') or kwargs.get('value') == 'nan' or isna(kwargs.get('value'))\
                or len(kwargs.get('value')) < 1:
            return f"{val_error_start(row_num=kwargs.get('row_num'), col=kwargs.get('col'))} " \
                   f"{settings.Messages.UPLOAD_EMPTY_VALUE_ERROR}"
        elif len(kwargs.get('value')) > settings.UPLOAD_VALUE_LENGTH_LIMIT:
            return f"{val_error_start(row_num=kwargs.get('row_num'), col=kwargs.get('col'))} " \
                   f"{settings.Messages.UPLOAD_VALUE_LIMIT_ERROR}"
        else:
            return func(*args, **kwargs)
    return wrapper


def check_article_value(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(value: str, *args, **kwargs):
        if value:
            lowered = value.lower()
            if any(bad_word in lowered for bad_word in settings.ExceptionOrders.EXCEPTED_ARTICLES):
                raise ArticlesException(f"Обнаружено запрещённое сочетание: '{value}'")
        return func(value, *args, **kwargs)
    return wrapper


def handle_articles_exception(exception):
    logger.error(f"Пользователь {current_user.id} попытался загрузить запрещённый артикул: {exception}")

    current_user.status = False
    db.session.commit()

    logout_user()
    flash(message=f"Вы пытались сделать недопустимое действие, введя в заказе '{exception}' не из указанной категории. Обратитесь к модератору", category="error")
    return None, None


def handle_upload_exceptions(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ArticlesException as ae:
            return handle_articles_exception(ae)
        except IndexError as e:
            logger.error(str(e))
            flash(message=settings.Messages.UPLOAD_FILE_EXTENSION_ERROR, category='error')
            return None, None
        except Exception:
            logger.exception('Исключение обработки загрузки заказа через таблицы')
            return None, None
    return wrapper


class UploadCategory:
    def __init__(self, table_obj, type_upload: str, subcategory: str = None) -> None:
        self.type_upload = type_upload
        self.table_obj = table_obj
        self.subcategory = subcategory
        self.df = self.process_df(table_obj=table_obj, sheet_name=settings.Upload.SHEET_NAME)

    @staticmethod
    def process_df(table_obj, sheet_name: str = settings.Upload.SHEET_NAME):
        return read_excel(table_obj, sheet_name=sheet_name, engine='openpyxl')
