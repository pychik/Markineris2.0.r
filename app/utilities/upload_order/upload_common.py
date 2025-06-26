from flask import flash
from functools import wraps
from pandas import read_excel, isna

from logger import logger
from config import settings


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


def handle_upload_exceptions(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
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
