from copy import copy
from typing import Optional, Union

from pandas import isna

from config import settings
from logger import logger
from utilities.check_tnved import TnvedChecker
from utilities.download import ParfumProcessor
from utilities.upload_order.upload_common import empty_value, val_error_start, UploadCategory


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
    @empty_value
    def _trademark(value: str, row_num: int, col: str) -> Optional[str]:
        return None

    @staticmethod
    @empty_value
    def _parfum_type(value: str, row_num: int, col: str, pos: int, order_list: list) -> Optional[Union[list, str]]:
        # value is shoe_type
        type_value = value.upper()
        order_list[row_num - settings.Parfum.UPLOAD_STANDART_ROW][pos] = type_value
        if type_value not in settings.Parfum.TYPES:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Shoes.UPLOAD_TYPE_ERROR}"

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
        if not value.isdigit() or int(value) > settings.Parfum.MAX_QUANTITY:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Parfum.UPLOAD_QUANTITY_ERROR}"

    @staticmethod
    @empty_value
    def _country(value: str, row_num: int, col: str, pos: int, order_list: list) -> Optional[str]:
        # value is parfum_country
        country_value = value.upper()
        order_list[row_num - settings.Parfum.UPLOAD_STANDART_ROW][pos] = country_value
        if country_value not in settings.COUNTRIES_LIST and value not in settings.COUNTRIES_LIST_C:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Parfum.UPLOAD_COUNTRY_ERROR}"

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


class UploadParfum(UploadCategory):

    def get_article_info(self):
        if self.type_upload == settings.Upload.STANDART:
            return self.get_article_info_standart()
        if self.type_upload == settings.Upload.EXTENDED:
            return self.get_article_info_extended()

    def get_article_info_standart(self) -> tuple:
        # import all in df with clearing empty rows
        try:
            process_df = self.df.iloc[5:settings.ORDER_LIMIT_UPLOAD_ARTICLES, [2, 3, 4, 5, 6, 7, 8, 9, 10]]\
                .dropna(how='all').astype(str)

            res_list = list(process_df.values.tolist())
            if len(res_list) > settings.ORDER_LIMIT_ARTICLES:
                return (settings.ORDER_LIMIT_ARTICLES, len(res_list),), None

            vp = UploadParfum.ValidateParfum()
            return vp.full_validate_standart(order_list=res_list)
        except IndexError as e:
            logger.error(e)
            return None, None

    def get_article_info_extended(self) -> tuple:
        # import all in df with clearing empty rows
        try:
            process_df = self.df.iloc[5:settings.ORDER_LIMIT_UPLOAD_ARTICLES, [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]] \
                             .dropna(how='all').astype(str)

            res_list = list(process_df.values.tolist())
            if len(res_list) > settings.ORDER_LIMIT_ARTICLES:
                return (settings.ORDER_LIMIT_ARTICLES, len(res_list),), None

            vp = UploadParfum.ValidateParfum()
            return vp.full_validate_extended(order_list=res_list)

        except IndexError as e:
            logger.error(e)
            return None, None

    class ValidateParfum(ValidateParfumMixin):

        def full_validate_standart(self, order_list):
            errors_list = []
            error_rows = self.check_rows_cols(order_list=order_list)
            errors_list.append(error_rows) if error_rows is not None else None
            row_num = copy(settings.Shoes.UPLOAD_STANDART_ROW)

            # row, col = 0, 0

            for data_group in order_list:

                trademark_error = self._trademark(value=data_group[0].strip(), row_num=row_num, col='C')
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
                                              pos=8, order_list=order_list)

                tnved_error = self._tnved(value=data_group[6].strip(), parfum_type=data_group[5].strip(),
                                          row_num=row_num, col='I', pos=6, order_list=order_list)

                error_tuple = (trademark_error, volume_type_error, volume_error, package_type_error,
                               material_package_error, type_error, tnved_error, quantity_error, country_error)
                for e in error_tuple:
                    errors_list.append(e) if e is not None else None

                row_num += 1

            return order_list, errors_list

        def full_validate_extended(self, order_list: list):
            errors_list = []
            error_rows = self.check_rows_cols(order_list=order_list)
            errors_list.append(error_rows) if error_rows is not None else None
            row_num = copy(settings.Shoes.UPLOAD_STANDART_ROW)

            # row, col = 0, 0

            for data_group in order_list:

                trademark_error = self._trademark(value=data_group[0].strip(), row_num=row_num, col='C')
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
                                              pos=9, order_list=order_list)

                tnved_error = self._tnved(value=data_group[6].strip(), parfum_type=data_group[5].strip(),
                                          row_num=row_num, col='I', pos=6, order_list=order_list)

                error_tuple = (trademark_error, volume_type_error, volume_error, package_type_error,
                               material_package_error, type_error, tnved_error, box_quantity_error,
                               quantity_error, country_error)
                for e in error_tuple:
                    errors_list.append(e) if e is not None else None

                row_num += 1

            return order_list, errors_list
