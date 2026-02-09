from copy import copy
from datetime import datetime

from pandas import isna

from typing import Optional, Union

from config import settings
from logger import logger
from utilities.check_tnved import TnvedChecker
from utilities.download import ParfumProcessor
from utilities.upload_order.upload_common import empty_value, val_error_start, UploadCategory, handle_upload_exceptions, \
    check_article_value


class ValidateParfumMixin:
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
            order_list[row_num - settings.Parfum.UPLOAD_STANDART_ROW][pos] = 'БЕЗ ТОВАРНОГО ЗНАКА'
        return

    @staticmethod
    @empty_value
    def _parfum_type(value: str, row_num: int, col: str, pos: int, order_list: list) -> Optional[Union[list, str]]:
        # value is shoe_type
        type_value = value.upper()
        order_list[row_num - settings.Parfum.UPLOAD_STANDART_ROW][pos] = type_value
        if type_value not in settings.Parfum.TYPES:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Parfum.UPLOAD_TYPE_ERROR}"

    @staticmethod
    @empty_value
    def _package_type(value: str, row_num: int, col: str, pos: int, order_list: list) -> Optional[Union[list, str]]:
        # value is shoe_type
        type_value = value.upper()
        order_list[row_num - settings.Parfum.UPLOAD_STANDART_ROW][pos] = type_value
        if type_value not in settings.Parfum.PACKAGE_TYPES:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Parfum.UPLOAD_PACKAGE_TYPE_ERROR}"

    @staticmethod
    @empty_value
    def _material_package(value: str, row_num: int, col: str, pos: int, order_list: list) -> Optional[Union[list, str]]:
        # value is shoe_type
        type_value = value.upper()
        order_list[row_num - settings.Parfum.UPLOAD_STANDART_ROW][pos] = type_value
        if type_value not in settings.Parfum.MATERIAL_PACKAGES:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Parfum.UPLOAD_MATERIAL_PACKAGE_TYPE_ERROR}"

    @staticmethod
    def _tnved(order_list: list, parfum_type: str,
              value: str, row_num: int, col: str, pos: int = 8) -> Optional[str]:
        # value is tnved
        value.replace('.0', '')

        value.strip()

        if value == 'nan' or isna(value) or len(value) < 1:
            tnved = ParfumProcessor.get_tnved(parfum_type=parfum_type.strip())

            order_list[row_num - settings.Parfum.UPLOAD_STANDART_ROW][pos] = tnved

            return None

        tc = TnvedChecker(category=settings.Parfum.CATEGORY_PROCESS, tnved_code=value)
        result_status, answer = tc.tnved_parse()
        if result_status != 5:
            return f"{val_error_start(row_num=row_num, col=col)} {answer}." \
                   f"{settings.Messages.UPLOAD_TNVED_ERROR}"

    @staticmethod
    @empty_value
    def _quantity(value: str, row_num: int, col: str) -> Optional[str]:
        # value is quantity
        if not value.isdigit() or int(value) > settings.Parfum.MAX_QUANTITY or int(value) < settings.Parfum.MIN_QUANTITY:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Parfum.UPLOAD_QUANTITY_ERROR}"

    @staticmethod
    @empty_value
    def _country(value: str, row_num: int, col: str, pos: int, order_list: list, has_rd: bool = False) -> Optional[str]:
        """
        Если есть хоть одно поле РД -> страна проверяется по общему списку COUNTRIES_LIST.
        Если РД нет -> страна проверяется по спец-списку PARFUM_COUNTRIES_RD и при ошибке
        возвращаем список допустимых стран.
        """
        country_value = value.upper().strip()
        order_list[row_num - settings.Parfum.UPLOAD_STANDART_ROW][pos] = country_value

        if has_rd:
            allowed = settings.COUNTRIES_LIST
            if country_value not in allowed:
                return f"{val_error_start(row_num=row_num, col=col)} {settings.Parfum.UPLOAD_COUNTRY_ERROR}"
        else:
            allowed = settings.PARFUM_COUNTRIES_RD
            if country_value not in allowed:
                return (
                    f"{val_error_start(row_num=row_num, col=col)} {settings.Parfum.UPLOAD_COUNTRY_ERROR} "
                    f"Допустимые страны без РД: {allowed}"
                )

    @staticmethod
    @empty_value
    def _volume(value: str, row_num: int, col: str) -> Optional[str]:
        # value is quantity
        if not value.isdigit() or int(value) > settings.Parfum.MAX_VOLUME:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Parfum.UPLOAD_VOLUME_ERROR}"

    @staticmethod
    @empty_value
    def _volume_type(value: str, row_num: int, col: str) -> Optional[str]:
        # value is volume_type
        if value not in settings.Parfum.VOLUMES:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Parfum.UPLOAD_VOLUME_TYPE_ERROR}"

    @staticmethod
    @empty_value
    def _rd_type(value: str, row_num: int, col: str, pos: int, order_list: list) -> Optional[str]:
        # value is shoe_rd_type
        type_value = value.capitalize()
        order_list[row_num - settings.Shoes.UPLOAD_STANDART_ROW][pos] = type_value
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
            rd_type_error = ValidateParfumMixin._rd_type(value=list_values[0].strip(), row_num=row_num, col=cols[0],
                                                        pos=type_pos, order_list=order_list)
            rd_name_error = ValidateParfumMixin._rd_name(value=list_values[1].strip(), row_num=row_num, col=cols[1])
            rd_date_error = ValidateParfumMixin._rd_date(value=list_values[2].strip(), row_num=row_num, col=cols[2])
            return None, rd_type_error, rd_name_error, rd_date_error
        elif 0 < res < 3:
            return f"{val_error_start(row_num=row_num)} {settings.Messages.UPLOAD_RD_GENERAL_ERROR}", None, None, None
        else:
            return (None,) * 4


class UploadParfum(UploadCategory):

    def get_article_info(self):
        if self.type_upload == settings.Upload.STANDART:
            return self.get_article_info_standart()
        if self.type_upload == settings.Upload.EXTENDED:
            return self.get_article_info_extended()

    @handle_upload_exceptions
    def get_article_info_standart(self) -> tuple:

        if self.df.iloc[4, 9] != 'Укажите кол-во позиций':
            raise IndexError
        process_df = self.df.iloc[5:settings.ORDER_LIMIT_UPLOAD_ARTICLES, [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]]\
            .dropna(how='all').astype(str)

        res_list = list(process_df.values.tolist())
        if len(res_list) > settings.ORDER_LIMIT_ARTICLES:
            return (settings.ORDER_LIMIT_ARTICLES, len(res_list),), None

        vp = UploadParfum.ValidateParfum()
        return vp.full_validate_standart(order_list=res_list)

    @handle_upload_exceptions
    def get_article_info_extended(self) -> tuple:

        if self.df.iloc[4, 9] != 'Введите количество наборов':
            raise IndexError
        process_df = self.df.iloc[5:settings.ORDER_LIMIT_UPLOAD_ARTICLES, [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]] \
                         .dropna(how='all').astype(str)

        res_list = list(process_df.values.tolist())
        if len(res_list) > settings.ORDER_LIMIT_ARTICLES:
            return (settings.ORDER_LIMIT_ARTICLES, len(res_list),), None

        vp = UploadParfum.ValidateParfum()
        return vp.full_validate_extended(order_list=res_list)

    class ValidateParfum(ValidateParfumMixin):

        def full_validate_standart(self, order_list):
            errors_list = []
            error_rows = self.check_rows_cols(order_list=order_list)
            errors_list.append(error_rows) if error_rows is not None else None
            row_num = copy(settings.Shoes.UPLOAD_STANDART_ROW)

            for data_group in order_list:
                rd_values = [x.strip() for x in data_group[9:12]]
                has_rd = any(v not in ("", "nan", "None") for v in rd_values)
                trademark_error = self._trademark(value=data_group[0].strip(), row_num=row_num, col='C', pos=0,
                                                  order_list=order_list)
                # trademark_error = self._trademark(value=data_group[0].strip(), row_num=row_num, col='C')
                volume_type_error = self._volume_type(value=data_group[1].strip(), row_num=row_num, col='D')
                volume_error = self._volume(value=data_group[2].strip(), row_num=row_num, col='E')
                package_type_error = self._package_type(value=data_group[3].strip(), row_num=row_num, col='F',
                                                        pos=3, order_list=order_list)
                material_package_error = self._material_package(value=data_group[4].strip(), row_num=row_num, col='G',
                                                                pos=4, order_list=order_list)
                type_error = self._parfum_type(value=data_group[5].strip(), row_num=row_num, col='H',
                                               pos=5, order_list=order_list)
                quantity_error = self._quantity(value=data_group[7].strip(), row_num=row_num, col='J')
                country_error = self._country(value=data_group[8].strip(), row_num=row_num, col='K',
                                              pos=8, order_list=order_list, has_rd=has_rd)

                tnved_error = self._tnved(value=data_group[6].strip(), parfum_type=data_group[5].strip(),
                                          row_num=row_num, col='I', pos=6, order_list=order_list)

                rd_general_error, rd_type_error, \
                    rd_name_error, rd_date_error = self._rd_general(list_values=rd_values,
                                                                    row_num=row_num, order_list=order_list,
                                                                    type_pos=9, cols=('L', 'M', 'N',))

                error_tuple = (trademark_error, volume_type_error, volume_error, package_type_error,
                               material_package_error, type_error, tnved_error, quantity_error, country_error,
                               rd_general_error, rd_type_error, rd_name_error, rd_date_error)
                for e in error_tuple:
                    errors_list.append(e) if e is not None else None

                row_num += 1

            return order_list, errors_list

        def full_validate_extended(self, order_list: list):
            errors_list = []
            error_rows = self.check_rows_cols(order_list=order_list)
            errors_list.append(error_rows) if error_rows is not None else None
            row_num = copy(settings.Shoes.UPLOAD_STANDART_ROW)

            for data_group in order_list:
                rd_values = [x.strip() for x in data_group[10:13]]
                has_rd = any(v not in ("", "nan", "None") for v in rd_values)
                # trademark_error = self._trademark(value=data_group[0].strip(), row_num=row_num, col='C')
                trademark_error = self._trademark(value=data_group[0].strip(), row_num=row_num, col='C', pos=0,
                                                  order_list=order_list)
                volume_type_error = self._volume_type(value=data_group[1].strip(), row_num=row_num, col='D')
                volume_error = self._volume(value=data_group[2].strip(), row_num=row_num, col='E')
                package_type_error = self._package_type(value=data_group[3].strip(), row_num=row_num, col='F',
                                                        pos=3, order_list=order_list)
                material_package_error = self._material_package(value=data_group[4].strip(), row_num=row_num, col='G',
                                                                pos=4, order_list=order_list)
                type_error = self._parfum_type(value=data_group[5].strip(), row_num=row_num, col='H',
                                               pos=5, order_list=order_list)
                box_quantity_error = self._quantity(value=data_group[7].strip(), row_num=row_num, col='J')
                quantity_error = self._quantity(value=data_group[8].strip(), row_num=row_num, col='K')
                country_error = self._country(value=data_group[9].strip(), row_num=row_num, col='L',
                                              pos=9, order_list=order_list, has_rd=has_rd)

                tnved_error = self._tnved(value=data_group[6].strip(), parfum_type=data_group[5].strip(),
                                          row_num=row_num, col='I', pos=6, order_list=order_list)

                rd_general_error, rd_type_error, \
                    rd_name_error, rd_date_error = self._rd_general(list_values=data_group[10:13],
                                                                    row_num=row_num, order_list=order_list,
                                                                    type_pos=10, cols=('M', 'N', 'O',))

                error_tuple = (trademark_error, volume_type_error, volume_error, package_type_error,
                               material_package_error, type_error, tnved_error, box_quantity_error,
                               quantity_error, country_error, rd_general_error, rd_type_error,
                               rd_name_error, rd_date_error)
                for e in error_tuple:
                    errors_list.append(e) if e is not None else None

                row_num += 1

            return order_list, errors_list
