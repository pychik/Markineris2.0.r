from copy import copy
from typing import Optional, Union

from pandas import isna

from config import settings
from utilities.check_tnved import TnvedChecker
from utilities.download import ClothesProcessor
from utilities.upload_order.upload_common import empty_value, val_error_start, UploadCategory


class ValidateClothesMixin:
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
    def _article(value: str, row_num: int, col: str) -> Optional[str]:
        return None

    @staticmethod
    @empty_value
    def _type(value: str, row_num: int, col: str, pos: int, order_list: list) -> Optional[Union[list, str]]:
        # value is shoe_type
        type_value = value.upper()
        order_list[row_num - settings.Clothes.UPLOAD_STANDART_ROW][pos] = type_value
        if type_value not in settings.Clothes.TYPES:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Clothes.UPLOAD_TYPE_ERROR}"

    @staticmethod
    @empty_value
    def _color(value: str, row_num: int, col: str, pos: int, order_list: list) -> Optional[str]:
        color_value = value.upper()
        order_list[row_num - settings.Shoes.UPLOAD_STANDART_ROW][pos] = color_value
        # value is shoe_color
        if color_value not in settings.Shoes.COLORS:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Shoes.UPLOAD_COLOR_ERROR}"

    @staticmethod
    @empty_value
    def _size_type(value: str, row_num: int, col: str, pos: int, order_list: list) -> Optional[str]:
        # temporary comments
        corrected_value = value.strip().replace(' ', '')

        if corrected_value not in settings.Clothes.SIZE_TYPES_ALL:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Clothes.UPLOAD_SIZE_TYPE_ERROR}"

    @staticmethod
    @empty_value
    def _size(value: str, row_num: int, col: str, pos: int, order_list: list) -> Optional[str]:
        corrected_value = value.strip().replace(' ', '')
        order_list[row_num - settings.Clothes.UPLOAD_STANDART_ROW][pos] = corrected_value

        if corrected_value not in settings.Clothes.SIZES:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Clothes.UPLOAD_SIZE_ERROR}"

    @staticmethod
    def _content(order_list: list, cloth_material: str, row_num: int, col: str, pos: int,
                 ) -> Optional[str]:
        # cols I J
        if not cloth_material or not isinstance(cloth_material, str):
            return f"{val_error_start(row_num=row_num, col=col)} " \
                   f"{settings.Messages.UPLOAD_NOT_STR_VALUE_ERROR}"
        if len(cloth_material) <= 1:
            return f"{val_error_start(row_num=row_num, col=col)} " \
                   f"{settings.Messages.UPLOAD_EMPTY_VALUE_ERROR}"

        order_list[row_num - settings.Clothes.UPLOAD_STANDART_ROW][pos] = cloth_material.capitalize()
        return None

    @staticmethod
    def _tnved(order_list: list, clothes_type: str, gender: str, content: str,
               value: str, row_num: int, col: str, pos: int = 8) -> Optional[str]:
        # value is tnved
        value.replace('.0', '')

        value.strip()
        if value == 'nan' or isna(value) or len(value) < 1:
            tnved = ClothesProcessor.get_tnved(clothes_type=clothes_type, gender=gender, content=content)

            order_list[row_num - settings.Clothes.UPLOAD_STANDART_ROW][pos] = tnved

            return None

        tc = TnvedChecker(category=settings.Clothes.CATEGORY_PROCESS, tnved_code=value)
        result_status, answer = tc.tnved_parse()
        if result_status != 5:
            return f"{val_error_start(row_num=row_num, col=col)} {answer}." \
                   f"{settings.Messages.UPLOAD_TNVED_ERROR}"

    @staticmethod
    @empty_value
    def _gender(value: str, row_num: int, col: str) -> Optional[str]:
        # value is gender

        if value not in settings.Clothes.GENDERS:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Clothes.UPLOAD_GENDER_ERROR}"

    @staticmethod
    @empty_value
    def _quantity(value: str, row_num: int, col: str) -> Optional[str]:
        # value is quantity
        if not value.isdigit() or int(value) > settings.Clothes.MAX_QUANTITY:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Shoes.UPLOAD_QUANTITY_ERROR}"

    @staticmethod
    @empty_value
    def _country(value: str, row_num: int, col: str, pos: int, order_list: list) -> Optional[str]:
        # value is shoe_country
        country_value = value.upper()
        order_list[row_num - settings.Shoes.UPLOAD_STANDART_ROW][pos] = country_value
        if value not in settings.COUNTRIES_LIST:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Shoes.UPLOAD_COUNTRY_ERROR}"


class UploadClothes(UploadCategory):

    def get_article_info(self):
        if self.type_upload == settings.Upload.STANDART:
            return self.get_article_info_standart()

    def get_article_info_standart(self) -> tuple:
        # import all in df with clearing empty rows
        try:
            process_df = self.df.iloc[5:settings.ORDER_LIMIT_UPLOAD_ARTICLES, [2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]]\
                .dropna(how='all').astype(str)

            res_list = list(process_df.values.tolist())
            if len(res_list) > settings.ORDER_LIMIT_ARTICLES:
                return (settings.ORDER_LIMIT_ARTICLES, len(res_list),), None

            vs = UploadClothes.ValidateStandart()
            return vs.full_validate_standart(order_list=res_list)
        except IndexError:
            return None, None

    class ValidateStandart(ValidateClothesMixin):

        def full_validate_standart(self, order_list):
            errors_list = []
            error_rows = self.check_rows_cols(order_list=order_list)
            errors_list.append(error_rows) if error_rows is not None else None
            row_num = copy(settings.Clothes.UPLOAD_STANDART_ROW)

            for data_group in order_list:

                trademark_error = self._trademark(value=data_group[0].strip(), row_num=row_num, col='C')
                article_error = self._article(value=data_group[1].strip(), row_num=row_num, col='E')
                type_error = self._type(value=data_group[2].strip(), row_num=row_num, col='F',
                                        pos=2, order_list=order_list)

                color_error = self._color(value=data_group[3].strip(), row_num=row_num, col='G', pos=3,
                                          order_list=order_list)
                gender_error = self._gender(value=data_group[4].strip(), row_num=row_num, col='H')
                size_type_error = self._size_type(value=data_group[5].strip(), row_num=row_num, col='I', pos=5,
                                                  order_list=order_list)
                size_error = self._size(value=data_group[6].strip(), row_num=row_num, col='J', pos=6,
                                        order_list=order_list)
                content_error = self._content(order_list=order_list, cloth_material=data_group[7].strip(),
                                              row_num=row_num, col='K', pos=7)
                tnved_error = self._tnved(order_list=order_list, clothes_type=data_group[2].strip(),
                                          gender=data_group[4].strip(), content=data_group[7].strip(),
                                          value=data_group[8].strip(), row_num=row_num, col='L', pos=8)
                quantity_error = self._quantity(value=data_group[9].strip(), row_num=row_num, col='M')
                country_error = self._country(value=data_group[10].strip(), row_num=row_num, col='N',
                                              pos=10, order_list=order_list)

                error_tuple = (trademark_error, article_error, type_error, color_error, size_type_error, size_error,
                               content_error, tnved_error, gender_error, quantity_error, country_error)
                for e in error_tuple:
                    errors_list.append(e) if e is not None else None

                row_num += 1

            return order_list, errors_list
