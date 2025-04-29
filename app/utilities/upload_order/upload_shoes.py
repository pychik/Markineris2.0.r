from copy import copy
from datetime import datetime
from flask_login import current_user
from typing import Optional, Union

from numpy import nan
from pandas import isna

from config import settings
from logger import logger
from utilities.check_tnved import TnvedChecker
from utilities.download import ShoesProcessor
from utilities.support import upload_divide_sizes_quantities
from utilities.upload_order.upload_common import empty_value, val_error_start, UploadCategory


class ValidateShoesMixin:
    @staticmethod
    def _check_rows_cols(order_list: list) -> Optional[str]:
        row_error = None
        if len(order_list) < 1:
            row_error = settings.Messages.UPLOAD_EMPTY_FILE_ERROR
        if len(order_list) > settings.ORDER_LIMIT_ARTICLES:
            row_error = f"Превышен лимит строк {settings.ORDER_LIMIT_ARTICLES}."
        return row_error

    @staticmethod
    def _trademark(value: str, row_num: int, col: str, pos: int, order_list: list) -> Optional[str]:
        if not value or value == 'nan' or isna(value) \
                or len(value) < 1:
            order_list[row_num - settings.Shoes.UPLOAD_STANDART_ROW][pos] = 'БЕЗ ТОВАРНОГО ЗНАКА'
        return

    @staticmethod
    def _article(value: str, row_num: int, col: str, pos: int, order_list: list) -> Optional[str]:
        if not value or value == 'nan' or isna(value) \
                or len(value) < 1:
            order_list[row_num - settings.Shoes.UPLOAD_STANDART_ROW][pos] = 'БЕЗ АРТИКУЛА'
        return

    @staticmethod
    @empty_value
    def _shoe_type(value: str, row_num: int, col: str, pos: int, order_list: list) -> Optional[Union[list, str]]:
        # value is shoe_type
        type_value = value.upper()
        order_list[row_num - settings.Shoes.UPLOAD_STANDART_ROW][pos] = type_value
        if type_value not in settings.Shoes.TYPES:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Shoes.UPLOAD_TYPE_ERROR}"

    @staticmethod
    @empty_value
    def _color(value: str, row_num: int, col: str, pos: int, order_list: list) -> Optional[str]:
        color_value = value.upper()
        order_list[row_num - settings.Shoes.UPLOAD_STANDART_ROW][pos] = color_value
        # value is shoe_color
        if len(value) > 100:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Shoes.UPLOAD_COLOR_ERROR}"

    @staticmethod
    @empty_value
    def _size(value: str, row_num: int, col: str, pos: int, order_list: list) -> Optional[str]:
        corrected_value = value.strip().replace(' ', '')
        order_list[row_num - settings.Shoes.UPLOAD_STANDART_ROW][pos] = corrected_value

        if corrected_value not in settings.Shoes.SIZES_ALL:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Shoes.UPLOAD_SIZE_ERROR}"

    @staticmethod
    @empty_value
    def _sizes_quantities(value: str, row_num: int, col: str) -> tuple[Optional[str], int]:
        sizes, quantities = upload_divide_sizes_quantities(value=value)
        pos_quantity = len(sizes)
        if not sizes:
            return f"{val_error_start(row_num=row_num, col=col)}" \
                   f" {settings.Shoes.UPLOAD_SIZES_QUANTITIES_DATA_INPUT_ERROR}", 0
        if pos_quantity != len(quantities):
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Shoes.UPLOAD_SIZES_QUANTITIES_LEN_ERROR}", \
                pos_quantity

        # value is shoe_size
        size_check = all(map(lambda x: x in settings.Shoes.SIZES, sizes))
        quantity_check = all(map(lambda x: x.isdigit(), quantities))

        if not size_check or not quantity_check:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Shoes.UPLOAD_SIZES_QUANTITIES_ERROR}",\
                pos_quantity
        return None, pos_quantity

    @staticmethod
    def _material(order_list: list, shoe_material: str, row_num: int, col: str, pos: int,
                 bottom: bool = False) -> Optional[str]:
        # cols I J
        if not shoe_material or not isinstance(shoe_material, str):
            return f"{val_error_start(row_num=row_num, col=col)} " \
                   f"{settings.Messages.UPLOAD_NOT_STR_VALUE_ERROR}"
        if len(shoe_material) <= 1:
            return f"{val_error_start(row_num=row_num, col=col)} " \
                   f"{settings.Messages.UPLOAD_EMPTY_VALUE_ERROR}"

        if bottom:
            check_list = copy(settings.Shoes.MATERIALS_BOTTOM)
        else:
            check_list = copy(settings.Shoes.MATERIALS_UP_LINEN)

        if shoe_material in check_list:
            return None

        # check material with lower first letter and capitalize in our check_list
        elif shoe_material in settings.Shoes.MATERIALS_CORRECT.keys():

            order_list[row_num - settings.Shoes.UPLOAD_STANDART_ROW][pos] = settings.Shoes.MATERIALS_CORRECT. \
                get(shoe_material)
            return None
        else:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Shoes.UPLOAD_MATERIAL_ERROR}"

    @staticmethod
    def _tnved(order_list: list, material_up: str, gender: str,
              value: str, row_num: int, col: str, pos: int = 8) -> Optional[str]:
        # value is tnved
        value.replace('.0', '')

        value.strip()
        if value == 'nan' or isna(value) or len(value) < 1:
            tnved = ShoesProcessor.get_tnved(material=material_up.strip(),
                                             gender=gender.strip())

            order_list[row_num - settings.Shoes.UPLOAD_STANDART_ROW][pos] = tnved

            return None

        tc = TnvedChecker(category=settings.Shoes.CATEGORY_PROCESS, tnved_code=value)
        result_status, answer = tc.tnved_parse()
        if result_status != 5:
            return f"{val_error_start(row_num=row_num, col=col)} {answer}." \
                   f"{settings.Messages.UPLOAD_TNVED_ERROR}"

    @staticmethod
    @empty_value
    def _gender(value: str, row_num: int, col: str, order_list: list, pos: int = 9) -> Optional[str]:

        if value.capitalize() in settings.Shoes.GENDERS:
            order_list[row_num - settings.Shoes.UPLOAD_STANDART_ROW][pos] = value.capitalize()
        else:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Shoes.UPLOAD_GENDER_ERROR}"

    @staticmethod
    @empty_value
    def _quantity(value: str, row_num: int, col: str) -> Optional[str]:
        # value is quantity
        if not value.isdigit() or int(value) > settings.Shoes.MAX_QUANTITY or int(value) < settings.Shoes.MIN_QUANTITY:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Shoes.UPLOAD_QUANTITY_ERROR}"

    @staticmethod
    @empty_value
    def _country(value: str, row_num: int, col: str, pos: int, order_list: list) -> Optional[str]:
        # value is shoe_country
        country_value = value.upper()
        order_list[row_num - settings.Shoes.UPLOAD_STANDART_ROW][pos] = country_value
        if country_value not in settings.COUNTRIES_LIST:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Shoes.UPLOAD_COUNTRY_ERROR}"

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
        try:
            res = datetime.strptime(value.strip(), "%d.%m.%Y")
        except ValueError:
            res = False
        if not res:
            return f"{val_error_start(row_num=row_num, col=col)} {settings.Messages.UPLOAD_RD_DATE_ERROR}"

    @staticmethod
    def _rd_general(list_values: list, rz_gender_condition: bool, gender: str, row_num: int,
                    order_list: list, cols: tuple) -> Optional[tuple]:
        res = len(list(filter(lambda x: x is None or x == 'nan' or len(x) == 0, list_values)))
        for i in range(12, 15):
            order_list[row_num - settings.Clothes.UPLOAD_STANDART_ROW][i] = \
                order_list[row_num - settings.Clothes.UPLOAD_STANDART_ROW][i].replace('nan', '')
        if res != 0 and rz_gender_condition:
            return (val_error_start(row_num=row_num) + ' ' +
                    settings.Messages.UPLOAD_RD_GENERAL_REQUIRED_ERROR.format(gender=gender),
                    None, None, None)
        elif res == 0:
            rd_type_error = ValidateShoesMixin._rd_type(value=list_values[0].strip(), row_num=row_num, col=cols[0],
                                                        pos=12, order_list=order_list)
            rd_name_error = ValidateShoesMixin._rd_name(value=list_values[1].strip(), row_num=row_num, col=cols[1])
            rd_date_error = ValidateShoesMixin._rd_date(value=list_values[2].strip(), row_num=row_num, col=cols[2])
            return None, rd_type_error, rd_name_error, rd_date_error
        elif 0 < res < 3:
            return f"{val_error_start(row_num=row_num)} {settings.Messages.UPLOAD_RD_GENERAL_ERROR}", None, None, None
        else:
            return (None,) * 4

    # @staticmethod
    # def _rd_general(list_values: list, row_num: int, order_list: list, cols: tuple) -> Optional[tuple]:
    #     res = len(list(filter(lambda x: x is None or x == 'nan' or len(x) == 0, list_values)))
    #     for i in range(12, 15):
    #         order_list[row_num - settings.Shoes.UPLOAD_STANDART_ROW][i] = \
    #             order_list[row_num - settings.Shoes.UPLOAD_STANDART_ROW][i].replace('nan', '')
    #
    #     if res == 0:
    #         rd_type_error = ValidateShoesMixin._rd_type(value=list_values[0].strip(), row_num=row_num, col=cols[0],
    #                                                     pos=12, order_list=order_list)
    #         rd_name_error = ValidateShoesMixin._rd_name(value=list_values[1].strip(), row_num=row_num, col=cols[1])
    #         rd_date_error = ValidateShoesMixin._rd_date(value=list_values[2].strip(), row_num=row_num, col=cols[2])
    #         return None, rd_type_error, rd_name_error, rd_date_error
    #     elif 0 < res < 3:
    #         return f"{val_error_start(row_num=row_num)} {settings.Messages.UPLOAD_RD_GENERAL_ERROR}", None, None, None
    #     else:
    #         return (None,) * 4


class UploadShoes(UploadCategory):

    def get_article_info(self):
        if self.type_upload == settings.Upload.STANDART:
            return self.get_article_info_standart()
        if self.type_upload == settings.Upload.EXTENDED:
            return self.get_article_info_extended()

    def get_article_info_standart(self) -> tuple:
        # import all in df with clearing empty rows
        try:
            if self.df.iloc[4, 5] != 'выберите ВИД ОБУВИ из выпадающего списка или со второго листа (справочник)':
                raise IndexError
            process_df = self.df.iloc[5:settings.ORDER_LIMIT_UPLOAD_ARTICLES, [2, 4, 5, 6, 7, 8, 9, 10, 11, 14, 16, 19, 20, 21, 22]]\
                .dropna(how='all').astype(str)

            res_list = list(process_df.values.tolist())
            if len(res_list) > settings.ORDER_LIMIT_ARTICLES:
                return (settings.ORDER_LIMIT_ARTICLES, len(res_list),), None

            vs = UploadShoes.ValidateStandart()
            return vs.full_validate_standart(order_list=res_list)
        except IndexError as e:
            logger.error(e)
            return None, None

    def get_article_info_extended(self) -> tuple:
        # import all in df with clearing empty rows
        try:
            if self.df.iloc[4, 0] != 'Указывайте конкретный артикул вашего Изделия. Заполнять обязательно. Если артикула на изделии нет то укажите любой произвольный':
                raise IndexError
            df_raw = self.df.iloc[5:settings.ORDER_LIMIT_UPLOAD_ARTICLES, [0, 2, 3, 4, 5, 6, 7, 9, 11, 12, 15, 16, 17, 18, 19]]  # .replace('0', nan, inplace=True)
            df_raw.replace('0', nan, inplace=True)
            df_raw.replace(0, nan, inplace=True)

            process_df = df_raw.dropna(how='all').astype(str)

            res_list = list(process_df.values.tolist())

            ve = UploadShoes.ValidateExtended()

            return ve.full_validate_extended(order_list=res_list)

        except IndexError as e:
            logger.error(e)
            return None, None

    class ValidateStandart(ValidateShoesMixin):

        def full_validate_standart(self, order_list):
            errors_list = []
            error_rows = self._check_rows_cols(order_list=order_list)
            errors_list.append(error_rows) if error_rows is not None else None
            row_num = copy(settings.Shoes.UPLOAD_STANDART_ROW)
            rz_condition = ((current_user.role == 'ordinary_user' and current_user.admin_parent_id == 2)
                            or current_user.id == 2)
            for data_group in order_list:
                # set condition for declar documents required
                gender = data_group[9].strip()

                gender_condition = gender not in settings.RZ_GENDERS_RD_LIST
                rz_gender_condition = rz_condition and gender_condition

                trademark_error = self._trademark(value=data_group[0].strip(), row_num=row_num, col='C', pos=0,
                                                  order_list=order_list)
                article_error = self._article(value=data_group[1].strip(), row_num=row_num, col='E', pos=1,
                                              order_list=order_list)
                type_error = self._shoe_type(value=data_group[2].strip(), row_num=row_num, col='F',
                                             pos=2, order_list=order_list)

                color_error = self._color(value=data_group[3].strip(), row_num=row_num, col='G', pos=3,
                                          order_list=order_list)
                size_error = self._size(value=data_group[4].strip(), row_num=row_num, col='H', pos=4,
                                        order_list=order_list)
                mt_error = self._material(order_list=order_list, shoe_material=data_group[5].strip(),
                                          row_num=row_num, col='I', pos=5)
                ml_error = self._material(order_list=order_list, shoe_material=data_group[6].strip(),
                                          row_num=row_num, col='J', pos=6)
                mb_error = self._material(order_list=order_list, shoe_material=data_group[7].strip(),
                                          row_num=row_num, col='K', pos=7, bottom=True)
                tnved_error = self._tnved(order_list=order_list, material_up=data_group[5].strip(),
                                          gender=gender,
                                          value=data_group[8].strip(), row_num=row_num, col='L', pos=8)
                gender_error = self._gender(value=gender, row_num=row_num, col='O', pos=9,
                                            order_list=order_list)
                quantity_error = self._quantity(value=data_group[10].strip(), row_num=row_num, col='Q')
                country_error = self._country(value=data_group[11].strip(), row_num=row_num, col='T',
                                              pos=11, order_list=order_list)

                rd_general_error, rd_type_error, \
                    rd_name_error, rd_date_error = self._rd_general(list_values=data_group[12:15],
                                                                    rz_gender_condition=rz_gender_condition,
                                                                    gender=gender,
                                                                    row_num=row_num, order_list=order_list,
                                                                    cols=('U', 'V', 'W',))
                error_tuple = (trademark_error, article_error, type_error, color_error, size_error, mt_error, ml_error,
                               mb_error, tnved_error, gender_error, quantity_error, country_error, rd_general_error,
                               rd_type_error, rd_name_error, rd_date_error)
                for e in error_tuple:
                    errors_list.append(e) if e is not None else None

                row_num += 1
            return order_list, errors_list

    class ValidateExtended(ValidateShoesMixin):

        def full_validate_extended(self, order_list: list):
            errors_list = []
            error_rows = self._check_rows_cols(order_list=order_list)
            errors_list.append(error_rows) if error_rows is not None else None
            row_num = copy(settings.Shoes.UPLOAD_STANDART_ROW)
            rz_condition = ((current_user.role == 'ordinary_user' and current_user.admin_parent_id == 2)
                            or current_user.id == 2)
            pos_count = 0
            for data_group in order_list:
                # set condition for declar documents required
                gender = data_group[11].strip()

                gender_condition = gender not in settings.RZ_GENDERS_RD_LIST
                rz_gender_condition = rz_condition and gender_condition

                article_error = self._article(value=data_group[1].strip(), row_num=row_num, col='A', pos=0,
                                              order_list=order_list)
                trademark_error = self._trademark(value=data_group[0].strip(), row_num=row_num, col='C', pos=1,
                                                  order_list=order_list)

                type_error = self._shoe_type(value=data_group[2].strip(), row_num=row_num, col='D',
                                             pos=2, order_list=order_list)

                mt_error = self._material(order_list=order_list, shoe_material=data_group[3].strip(),
                                          row_num=row_num, col='E', pos=3)
                ml_error = self._material(order_list=order_list, shoe_material=data_group[4].strip(),
                                          row_num=row_num, col='F', pos=4)
                mb_error = self._material(order_list=order_list, shoe_material=data_group[5].strip(),
                                          row_num=row_num, col='G', pos=5, bottom=True)
                color_error = self._color(value=data_group[6].strip(), row_num=row_num, col='H', pos=6,
                                          order_list=order_list)

                bq_error = self._quantity(value=data_group[7].strip(), row_num=row_num, col='J')

                size_quantity_error, pos_quantity = self._sizes_quantities(value=data_group[8].strip(), row_num=row_num, col='L')

                country_error = self._country(value=data_group[9].strip(), row_num=row_num, col='M',
                                              pos=9, order_list=order_list)

                tnved_error = self._tnved(order_list=order_list, material_up=data_group[3].strip(),
                                          gender=gender,
                                          value=data_group[10].strip(), row_num=row_num, col='P', pos=10)

                gender_error = self._gender(value=gender, row_num=row_num, col='Q', pos=11,
                                            order_list=order_list)

                rd_general_error, rd_type_error, \
                    rd_name_error, rd_date_error = self._rd_general(list_values=data_group[12:15],
                                                                    rz_gender_condition=rz_gender_condition,
                                                                    gender=gender,
                                                                    row_num=row_num, order_list=order_list,
                                                                    cols=('R', 'S', 'T',))

                error_tuple = (article_error, trademark_error, type_error, mt_error, ml_error, mb_error,
                               color_error, bq_error, size_quantity_error, country_error, tnved_error,
                               gender_error, rd_general_error, rd_type_error, rd_name_error, rd_date_error)

                for e in error_tuple:
                    errors_list.append(e) if e is not None else None

                row_num += 1
                pos_count += pos_quantity

            if pos_count > settings.ORDER_LIMIT_ARTICLES:
                return (settings.ORDER_LIMIT_ARTICLES, pos_count,), None
            return order_list, errors_list
