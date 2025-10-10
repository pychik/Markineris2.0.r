import re
from copy import copy
from datetime import datetime
from flask_login import current_user
from pandas import isna
from typing import Optional, Union


from config import settings
from logger import logger
from utilities.check_tnved import TnvedChecker
from utilities.upload_order.upload_common import empty_value, val_error_start, UploadCategory, handle_upload_exceptions, \
    check_article_value


class ValidateSocksMixin:
    @staticmethod
    def check_rows_cols(order_list: list) -> Optional[str]:
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
            order_list[row_num - settings.Socks.UPLOAD_STANDART_ROW][pos] = 'БЕЗ ТОВАРНОГО ЗНАКА'
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
    def _type(value: str, row_num: int, col: str, pos: int, order_list: list) -> Optional[Union[list, str]]:

        type_value = value.upper()
        order_list[row_num - settings.Socks.UPLOAD_STANDART_ROW][pos] = type_value
        if type_value not in settings.Socks.TYPES:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Socks.UPLOAD_TYPE_ERROR}"

    @staticmethod
    @empty_value
    def _color(value: str, row_num: int, col: str, pos: int, order_list: list) -> Optional[str]:
        color_value = value.upper()
        order_list[row_num - settings.Socks.UPLOAD_STANDART_ROW][pos] = color_value
        # value is shoe_color
        if color_value not in settings.ALL_COLORS:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Socks.UPLOAD_COLOR_ERROR}"

    @staticmethod
    def _size_type(size_value: str, row_num: int, pos: int, order_list: list) -> None:
        """
        Утсанавливает тип размера по его значению
            :param size_value: Значение размера (например: 25, S, M-L)
        """

        # allowed_types = ["МЕЖДУНАРОДНЫЙ", "РОССИЯ"]
        #
        # # Проверка что тип размера один из разрешённых
        # if size_type_value not in allowed_types:
        #     return f"{val_error_start(row_num=row_num, col=size_col)} Такого типа размера нет"

        # Если в размере есть латиница — тип должен быть только 'МЕЖДУНАРОДНЫЙ'
        if re.search(r"[A-Za-z]", size_value):
            order_list[row_num - settings.Clothes.UPLOAD_STANDART_ROW][pos] = 'МЕЖДУНАРОДНЫЙ'
        else:
            order_list[row_num - settings.Clothes.UPLOAD_STANDART_ROW][pos] = 'РОССИЯ'


    @staticmethod
    @empty_value
    def _size(value: str, row_num: int, col: str, pos: int, order_list: list) -> Optional[str]:
        order_list[row_num - settings.Socks.UPLOAD_STANDART_ROW][pos] = value

        if len(value) > 100:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Socks.UPLOAD_SIZE_ERROR}"
        # Проверка только латиница, цифры, дефис, точка для дробных
        if not re.fullmatch(r'[A-Za-z0-9.-]{1,8}', value):
            return f"{val_error_start(row_num=row_num, col=col)} Размер должен содержать только латиницу, цифры, дефис и точку для дробных."

    @staticmethod
    def _content(order_list: list, socks_material: str, row_num: int, col: str, pos: int,
                 ) -> Optional[str]:
        # cols I J
        if not socks_material or not isinstance(socks_material, str):
            return f"{val_error_start(row_num=row_num, col=col)} " \
                   f"{settings.Messages.UPLOAD_NOT_STR_VALUE_ERROR}"
        if len(socks_material) <= 1:
            return f"{val_error_start(row_num=row_num, col=col)} " \
                   f"{settings.Messages.UPLOAD_EMPTY_VALUE_ERROR}"

        order_list[row_num - settings.Socks.UPLOAD_STANDART_ROW][pos] = socks_material.capitalize().replace('\n', ' ')
        return

    @staticmethod
    @empty_value
    def _tnved(order_list: list, socks_type: str, value: str, row_num: int, col: str, pos: int = 8) -> Optional[str]:
        # value is tnved
        value = value.replace('.0', '').strip()

        result_status, answer = TnvedChecker.tnved_socks_parse(socks_type=socks_type, tnved_code=value)

        if result_status != 5:
            return f"{val_error_start(row_num=row_num, col=col)} {answer}." \
                   f"{settings.Messages.UPLOAD_TNVED_ERROR}"
        else:
            order_list[row_num - settings.Socks.UPLOAD_STANDART_ROW][pos] = value

    @staticmethod
    @empty_value
    def _gender(value: str, row_num: int, col: str) -> Optional[str]:
        # value is gender

        if value not in settings.Socks.GENDERS:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Socks.UPLOAD_GENDER_ERROR}"

    @staticmethod
    @empty_value
    def _quantity(value: str, row_num: int, col: str) -> Optional[str]:
        # value is quantity
        if not value.isdigit() or int(value) > settings.Socks.MAX_QUANTITY or int(value) < settings.Socks.MIN_QUANTITY:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Socks.UPLOAD_QUANTITY_ERROR}"

    @staticmethod
    @empty_value
    def _country(value: str, row_num: int, col: str, pos: int, order_list: list) -> Optional[str]:
        # value is shoe_country
        country_value = value.upper()
        order_list[row_num - settings.Socks.UPLOAD_STANDART_ROW][pos] = country_value
        if value not in settings.COUNTRIES_LIST:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Socks.UPLOAD_COUNTRY_ERROR}"

    @staticmethod
    @empty_value
    def _rd_type(value: str, row_num: int, col: str, pos: int, order_list: list) -> Optional[str]:
        # value is shoe_rd_type
        type_value = value.capitalize()
        order_list[row_num - settings.Socks.UPLOAD_STANDART_ROW][pos] = type_value
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
    def _rd_general(list_values: list, rz_gender_condition: bool, gender: str, row_num: int, order_list: list,
                    cols: tuple) -> Optional[tuple]:
        res = len(list(filter(lambda x: x is None or x == 'nan' or len(x) == 0, list_values)))
        for i in range(11, 14):
            order_list[row_num - settings.Socks.UPLOAD_STANDART_ROW][i] = \
                order_list[row_num - settings.Socks.UPLOAD_STANDART_ROW][i].replace('nan', '')
        if res != 0 and rz_gender_condition:
            return (val_error_start(row_num=row_num) + ' ' +
                    settings.Messages.UPLOAD_RD_GENERAL_REQUIRED_ERROR.format(gender=gender),
                    None, None, None)
        elif res == 0:
            rd_type_error = ValidateSocksMixin._rd_type(value=list_values[0].strip(), row_num=row_num, col=cols[0],
                                                         pos=11, order_list=order_list)
            rd_name_error = ValidateSocksMixin._rd_name(value=list_values[1].strip(), row_num=row_num, col=cols[1])
            rd_date_error = ValidateSocksMixin._rd_date(value=list_values[2].strip(), row_num=row_num, col=cols[2])
            return None, rd_type_error, rd_name_error, rd_date_error
        elif 0 < res < 3:
            return f"{val_error_start(row_num=row_num)} {settings.Messages.UPLOAD_RD_GENERAL_ERROR}", None, None, None
        else:
            return (None,) * 4


class UploadSocks(UploadCategory):

    def get_article_info(self):
        if self.type_upload == settings.Upload.STANDART:
            return self.get_article_info_standart()

    @handle_upload_exceptions
    def get_article_info_standart(self) -> tuple:
        # import all in df with clearing empty rows

        if self.df.iloc[4, 5] != 'выберите ВИД чулочно носочных изделий из выпадающего списка или со второго листа (справочник)':
            raise IndexError
        process_df = self.df.iloc[5:settings.ORDER_LIMIT_UPLOAD_ARTICLES, [2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, ]]\
            .dropna(how='all').astype(str)

        res_list = list(process_df.values.tolist())
        if len(res_list) > settings.ORDER_LIMIT_ARTICLES:
            return (settings.ORDER_LIMIT_ARTICLES, len(res_list),), None

        vs = UploadSocks.ValidateStandart()
        return vs.full_validate_standart(order_list=res_list)

    class ValidateStandart(ValidateSocksMixin):

        def full_validate_standart(self, order_list):
            errors_list = []
            error_rows = self.check_rows_cols(order_list=order_list)
            errors_list.append(error_rows) if error_rows is not None else None
            row_num = copy(settings.Socks.UPLOAD_STANDART_ROW)
            rz_condition = ((current_user.role == 'ordinary_user' and current_user.admin_parent_id == 2)
                            or current_user.id == 2)
            for data_group in order_list:
                gender = data_group[4].strip()

                gender_condition = gender not in settings.RZ_GENDERS_RD_LIST
                rz_gender_condition = rz_condition and gender_condition
                # print(data_group)
                trademark_error = self._trademark(value=data_group[0].strip(), row_num=row_num, col='C', pos=0,
                                                  order_list=order_list)
                article_error = self._article(value=data_group[1].strip(), row_num=row_num, col='E', pos=1,
                                              order_list=order_list)
                type_error = self._type(value=data_group[2].strip(), row_num=row_num, col='F',
                                        pos=2, order_list=order_list)
                # print(type_error)

                color_error = self._color(value=data_group[3].strip(), row_num=row_num, col='G', pos=3,
                                          order_list=order_list)
                # print(color_error)
                gender_error = self._gender(value=gender, row_num=row_num, col='H')
                # print(gender_error)
                size_type_error = self._size_type(size_value=data_group[6].strip(),
                                                  row_num=row_num, pos=5, order_list=order_list)
                # print(size_type_error)
                size_error = self._size(value=data_group[6].strip(), row_num=row_num, col='J', pos=6,
                                        order_list=order_list)
                # print(size_error)
                content_error = self._content(order_list=order_list, socks_material=data_group[7].strip(),
                                              row_num=row_num, col='K', pos=7)
                # print(content_error)
                tnved_error = self._tnved(order_list=order_list, socks_type=data_group[2].strip(),
                                          value=data_group[8].strip(), row_num=row_num, col='L', pos=8)
                # print(tnved_error)
                quantity_error = self._quantity(value=data_group[9].strip(), row_num=row_num, col='M')
                # print(quantity_error)
                country_error = self._country(value=data_group[10].strip(), row_num=row_num, col='N',
                                              pos=10, order_list=order_list)
                # print(country_error)
                rd_general_error, rd_type_error, \
                    rd_name_error, rd_date_error = self._rd_general(list_values=data_group[11:14],
                                                                    rz_gender_condition=rz_gender_condition,
                                                                    gender=gender,
                                                                    row_num=row_num, order_list=order_list,
                                                                    cols=('O', 'P', 'Q',))
                # print(rd_general_error)
                error_tuple = (trademark_error, article_error, type_error, color_error, size_type_error, size_error,
                               content_error, tnved_error, gender_error, quantity_error, country_error,
                               rd_general_error, rd_type_error, rd_name_error, rd_date_error )
                for e in error_tuple:
                    errors_list.append(e) if e is not None else None

                row_num += 1
            return order_list, errors_list
