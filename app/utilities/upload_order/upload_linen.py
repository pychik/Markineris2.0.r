from copy import copy
from datetime import datetime
from numpy import nan
from pandas import isna
from typing import Optional, Union

from config import settings
from logger import logger
from utilities.check_tnved import TnvedChecker
from utilities.upload_order.upload_common import empty_value, val_error_start, UploadCategory, handle_upload_exceptions, \
    check_article_value


class ValidateLinenMixin:
    @staticmethod
    def _check_rows_cols(order_list: list) -> Optional[str]:
        row_error = None
        if len(order_list) < 1:
            row_error = settings.Messages.UPLOAD_EMPTY_FILE_ERROR
        if len(order_list) > settings.ORDER_LIMIT_ARTICLES:
            row_error = f"Превышен лимит строк {settings.ORDER_LIMIT_ARTICLES}."
        return row_error

    @staticmethod
    @check_article_value
    def _trademark(value: str, row_num: int, col: str, pos: int, order_list: list) -> Optional[str]:
        if not value or value == 'nan' or isna(value) \
                or len(value) < 1:
            order_list[row_num - settings.Linen.UPLOAD_STANDART_ROW][pos] = 'БЕЗ ТОВАРНОГО ЗНАКА'
        return

    @staticmethod
    @check_article_value
    def _article(value: str, row_num: int, col: str, pos: int, order_list: list) -> Optional[str]:
        if not value or value == 'nan' or isna(value) \
                or len(value) < 1 or value.upper() == 'БЕЗ АРТИКУЛА':
            order_list[row_num - settings.Clothes.UPLOAD_STANDART_ROW][pos] = 'ОТСУТСТВУЕТ'
        return

    @staticmethod
    @empty_value
    def _linen_type(value: str, row_num: int, col: str, pos: int, order_list: list) -> Optional[Union[list, str]]:
        # value is shoe_type
        type_value = value.upper()
        order_list[row_num - settings.Linen.UPLOAD_STANDART_ROW][pos] = type_value
        if type_value not in settings.Linen.TYPES:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Linen.UPLOAD_TYPE_ERROR}"

    @staticmethod
    @empty_value
    def _color(value: str, row_num: int, col: str, pos: int, order_list: list) -> Optional[str]:
        color_value = value.upper()
        order_list[row_num - settings.Linen.UPLOAD_STANDART_ROW][pos] = color_value
        # value is shoe_color
        if color_value not in settings.ALL_COLORS:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Linen.UPLOAD_COLOR_ERROR}"

    @staticmethod
    @empty_value
    def _size(value: str, row_num: int, col: str, pos: int, order_list: list) -> Optional[str]:
        corrected_value = value.strip().replace(' ', '')
        order_list[row_num - settings.Linen.UPLOAD_STANDART_ROW][pos] = corrected_value

        if not corrected_value.isdigit():
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Linen.UPLOAD_SIZE_ERROR}"

    @staticmethod
    def _tnved(order_list: list, value: str, row_num: int, col: str, pos: int = 8) -> Optional[str]:
        # value is tnved
        value.replace('.0', '')

        value.strip()
        if value == 'nan' or isna(value) or len(value) < 1:
            tnved = settings.Linen.TNVED_CODE

            order_list[row_num - settings.Linen.UPLOAD_STANDART_ROW][pos] = tnved

            return None

        tc = TnvedChecker(category=settings.Linen.CATEGORY_PROCESS, tnved_code=value)
        result_status, answer = tc.tnved_parse()
        if result_status != 5:
            return f"{val_error_start(row_num=row_num, col=col)} {answer}." \
                   f"{settings.Messages.UPLOAD_TNVED_ERROR}"

    @staticmethod
    @empty_value
    def _customer_age(value: str, row_num: int, col: str, order_list: list, pos: int = 4) -> Optional[str]:
        customer_age = value.upper()
        if customer_age in settings.Linen.CUSTOMER_AGES:
            order_list[row_num - settings.Linen.UPLOAD_STANDART_ROW][pos] = customer_age
        else:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Linen.UPLOAD_CUSTOMER_AGE_ERROR}"

    @staticmethod
    @empty_value
    def _textyle_type(value: str, row_num: int, col: str, order_list: list, pos: int = 5) -> Optional[str]:
        textyle_type = value.upper()
        if textyle_type in settings.Linen.TEXTILE_TYPES:
            order_list[row_num - settings.Linen.UPLOAD_STANDART_ROW][pos] = textyle_type
        else:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Linen.UPLOAD_TEXTYLE_TYPE_ERROR}"

    @staticmethod
    @empty_value
    def _content(value: str, row_num: int, col: str) -> Optional[str]:
        return None

    @staticmethod
    @empty_value
    def _quantity(value: str, row_num: int, col: str, packages: bool = False) -> Optional[str]:
        # value is quantity

        if not value.isdigit() or int(value) > settings.Linen.MAX_QUANTITY or int(value) < settings.Linen.MIN_QUANTITY:
            message = settings.Linen.UPLOAD_BOX_QUANTITY_ERROR if packages else settings.Linen.UPLOAD_QUANTITY_ERROR
            return f"{val_error_start(row_num=row_num, col=col)} {message}"

    @staticmethod
    @empty_value
    def _country(value: str, row_num: int, col: str, pos: int, order_list: list) -> Optional[str]:
        # value is shoe_country
        country_value = value.upper()
        order_list[row_num - settings.Linen.UPLOAD_STANDART_ROW][pos] = country_value
        if country_value not in settings.COUNTRIES_LIST:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Linen.UPLOAD_COUNTRY_ERROR}"

    @staticmethod
    @empty_value
    def _rd_type(value: str, row_num: int, col: str, pos: int, order_list: list) -> Optional[str]:
        # value is shoe_rd_type
        type_value = value.capitalize()
        order_list[row_num - settings.Linen.UPLOAD_STANDART_ROW][pos] = type_value
        if type_value not in settings.RD_TYPES:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Messages.UPLOAD_RD_TYPE_ERROR}"

    @staticmethod
    @empty_value
    def _rd_name(value: str, row_num: int, col: str) -> Optional[str]:
        return None

    @staticmethod
    @empty_value
    def _rd_date(value: str, row_num: int, col: str) -> Optional[str]:
        error_message = f"{val_error_start(row_num=row_num, col=col)} {settings.Messages.UPLOAD_RD_DATE_ERROR}"
        try:
            res = datetime.strptime(value.strip(), "%d.%m.%Y")
        except ValueError:
            res = False
            logger.error(error_message)
        if not res:
            return error_message

    @staticmethod
    def _rd_general(list_values: list, row_num: int, order_list: list, type_pos: int, cols: tuple) -> Optional[tuple]:
        res = len(list(filter(lambda x: x is None or x == 'nan' or len(x) == 0, list_values)))
        for i in range(type_pos, type_pos + 3):
            order_list[row_num - settings.Linen.UPLOAD_STANDART_ROW][i] = \
                order_list[row_num - settings.Linen.UPLOAD_STANDART_ROW][i].replace('nan', '')

        if res == 0:
            rd_type_error = ValidateLinenMixin._rd_type(value=list_values[0].strip(), row_num=row_num, col=cols[0],
                                                        pos=type_pos, order_list=order_list)
            rd_name_error = ValidateLinenMixin._rd_name(value=list_values[1].strip(), row_num=row_num, col=cols[1])
            rd_date_error = ValidateLinenMixin._rd_date(value=list_values[2].strip(), row_num=row_num, col=cols[2])
            return None, rd_type_error, rd_name_error, rd_date_error
        elif 0 < res < 3:
            return f"{val_error_start(row_num=row_num)} {settings.Messages.UPLOAD_RD_GENERAL_ERROR}", None, None, None
        else:
            return (None,) * 4


class UploadLinen(UploadCategory):

    def get_article_info(self):
        if self.type_upload == settings.Upload.STANDART:
            return self.get_article_info_standart()
        if self.type_upload == settings.Upload.EXTENDED:
            return self.get_article_info_extended()

    @handle_upload_exceptions
    def get_article_info_standart(self) -> tuple:

        if not self.df.iloc[4, 10].startswith('Укажите конкретный размер изделия X'):
            raise IndexError
        process_df = self.df.iloc[5:settings.ORDER_LIMIT_UPLOAD_ARTICLES, [2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]]\
            .dropna(how='all').astype(str)

        res_list = list(process_df.values.tolist())

        if len(res_list) > settings.ORDER_LIMIT_ARTICLES:
            return (settings.ORDER_LIMIT_ARTICLES, len(res_list),), None

        vs = UploadLinen.ValidateStandart()
        return vs.full_validate_standart(order_list=res_list)

    @handle_upload_exceptions
    def get_article_info_extended(self) -> tuple:

        if not self.df.iloc[4, 10].startswith('Укажите самый большой размер изделия в комплетке X'):
            raise IndexError
        df_raw = self.df.iloc[5:settings.ORDER_LIMIT_UPLOAD_ARTICLES, [2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]]  # .replace('0', nan, inplace=True)
        df_raw.replace('0', nan, inplace=True)
        df_raw.replace(0, nan, inplace=True)

        process_df = df_raw.dropna(how='all').astype(str)

        res_list = list(process_df.values.tolist())

        ve = UploadLinen.ValidateExtended()

        return ve.full_validate_extended(order_list=res_list)

    class ValidateStandart(ValidateLinenMixin):

        def full_validate_standart(self, order_list):
            errors_list = []
            error_rows = self._check_rows_cols(order_list=order_list)
            errors_list.append(error_rows) if error_rows is not None else None
            row_num = copy(settings.Linen.UPLOAD_STANDART_ROW)

            for data_group in order_list:
                trademark_error = self._trademark(value=data_group[0].strip(), row_num=row_num, col='C', pos=0,
                                                  order_list=order_list)
                article_error = self._article(value=data_group[1].strip(), row_num=row_num, col='E', pos=1,
                                              order_list=order_list)
                type_error = self._linen_type(value=data_group[2].strip(), row_num=row_num, col='F',
                                              pos=2, order_list=order_list)

                color_error = self._color(value=data_group[3].strip(), row_num=row_num, col='G', pos=3,
                                          order_list=order_list)
                customer_age_error = self._customer_age(value=data_group[4].strip(), row_num=row_num, col='H', pos=4,
                                                        order_list=order_list)
                textile_type_error = self._textyle_type(value=data_group[5].strip(), row_num=row_num, col='I', pos=5,
                                                        order_list=order_list)
                content_type_error = self._content(value=data_group[6].strip(), row_num=row_num, col='J')

                sizeX_error = self._size(value=data_group[7].strip(), row_num=row_num, col='K', pos=7,
                                        order_list=order_list)
                sizeY_error = self._size(value=data_group[8].strip(), row_num=row_num, col='L', pos=8,
                                         order_list=order_list)
                tnved_error = self._tnved(order_list=order_list,
                                          value=data_group[9].strip(), row_num=row_num, col='M', pos=9)
                quantity_error = self._quantity(value=data_group[10].strip(), row_num=row_num, col='N')

                country_error = self._country(value=data_group[11].strip(), row_num=row_num, col='O',
                                              pos=11, order_list=order_list)
                rd_general_error, rd_type_error, \
                    rd_name_error, rd_date_error = self._rd_general(list_values=data_group[12:15],
                                                                    row_num=row_num, order_list=order_list, type_pos=12,
                                                                    cols=('P', 'Q', 'T',))

                error_tuple = (trademark_error, article_error, type_error, color_error, customer_age_error,
                               textile_type_error, content_type_error, sizeX_error, sizeY_error, tnved_error,
                               quantity_error, country_error, rd_general_error, rd_type_error,
                               rd_name_error, rd_date_error)
                for e in error_tuple:
                    errors_list.append(e) if e is not None else None

                row_num += 1

            return order_list, errors_list

    class ValidateExtended(ValidateLinenMixin):

        def full_validate_extended(self, order_list: list):
            errors_list = []
            error_rows = self._check_rows_cols(order_list=order_list)
            errors_list.append(error_rows) if error_rows is not None else None
            row_num = copy(settings.Linen.UPLOAD_STANDART_ROW)

            for data_group in order_list:

                trademark_error = self._trademark(value=data_group[0].strip(), row_num=row_num, col='C', pos=0,
                                                  order_list=order_list)
                article_error = self._article(value=data_group[1].strip(), row_num=row_num, col='E', pos=1,
                                              order_list=order_list)
                type_error = self._linen_type(value=data_group[2].strip(), row_num=row_num, col='F',
                                              pos=2, order_list=order_list)

                color_error = self._color(value=data_group[3].strip(), row_num=row_num, col='G', pos=3,
                                          order_list=order_list)
                customer_age_error = self._customer_age(value=data_group[4].strip(), row_num=row_num, col='H', pos=4,
                                                        order_list=order_list)
                textile_type_error = self._textyle_type(value=data_group[5].strip(), row_num=row_num, col='I', pos=5,
                                                        order_list=order_list)
                content_type_error = self._content(value=data_group[6].strip(), row_num=row_num, col='J')

                sizeX_error = self._size(value=data_group[7].strip(), row_num=row_num, col='K', pos=7,
                                         order_list=order_list)
                sizeY_error = self._size(value=data_group[8].strip(), row_num=row_num, col='L', pos=8,
                                         order_list=order_list)
                tnved_error = self._tnved(order_list=order_list,
                                          value=data_group[9].strip(), row_num=row_num, col='M', pos=9)

                box_quantity_error = self._quantity(value=data_group[10].strip(), row_num=row_num, col='N',
                                                    packages=True)
                quantity_error = self._quantity(value=data_group[11].strip(), row_num=row_num, col='O')
                country_error = self._country(value=data_group[12].strip(), row_num=row_num, col='P',
                                              pos=12, order_list=order_list)
                rd_general_error, rd_type_error, \
                    rd_name_error, rd_date_error = self._rd_general(list_values=data_group[13:16],
                                                                    row_num=row_num, order_list=order_list, type_pos=13,
                                                                    cols=('Q', 'R', 'S',))

                error_tuple = (trademark_error, article_error, type_error, color_error, customer_age_error,
                               textile_type_error, content_type_error, sizeX_error, sizeY_error, tnved_error,
                               box_quantity_error, quantity_error, country_error, rd_general_error, rd_type_error,
                               rd_name_error, rd_date_error)

                for e in error_tuple:
                    errors_list.append(e) if e is not None else None

                row_num += 1

            return order_list, errors_list
