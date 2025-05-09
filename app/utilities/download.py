import zipfile
from abc import ABC
from copy import copy
from datetime import datetime
from io import BytesIO
from typing import Generator, Optional, Union

from flask import flash, redirect, Response, send_file, url_for
from pandas import DataFrame
from xlsxwriter import Workbook
from xlsxwriter.worksheet import Worksheet

from config import settings
from models import Order, db, User
from .categories_data.subcategories_data import ClothesSubcategories, Category
from .abstract import ProcessorInterface
from .support import order_count, helper_paginate_data, check_leather
from .categories_data.underwear_data import UNDERWEAR_DEC_DICT, UNDERWEAR_TNVEDS
from .categories_data.subcategories_logic import get_subcategory
from .telegram import TelegramProcessor


class OrdersProcessor(ProcessorInterface, ABC):
    def __init__(self, category: str, company_idn: str, orders_list: list, flag_046: bool = False) -> None:
        (self._orders_list,
         self._orders_list_outer,
         self._orders_list_inner) = self.prepare_ext_data(orders_list=orders_list, flag_046=flag_046)

        self.company_idn = company_idn
        self.path = ''
        self.category = category
        self.start_data = []
        self.additional_info = []
        self.flag_046 = flag_046

    @property
    def orders_list(self) -> list:
        return self._orders_list

    @property
    def orders_list_outer(self) -> list:
        return self._orders_list_outer

    @property
    def orders_list_inner(self) -> list:
        return self._orders_list_inner

    @staticmethod
    def archive_excels(excel_files: list[tuple[BytesIO, str]], filename: str) -> tuple[BytesIO, str]:
        """
        Takes a list of tuples containing BytesIO Excel files and their respective filenames,
        and returns a BytesIO object of a zip archive containing these files.
        """

        # Create a BytesIO object for the zip archive
        archive = BytesIO()
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zip_archive:
            for file_obj, f_name in excel_files:
                file_obj.seek(0)
                zip_archive.writestr(f_name, file_obj.read())

        archive.seek(0)
        return archive, filename

    @staticmethod
    def prepare_batches(orders_divided: list, batch_size=400):
        """
        Делит каждый список в `orders_divided` на батчи и добавляет индекс к имени файла.

        :param orders_divided: Список кортежей (список данных, имя файла).
        :param batch_size: Размер батча (по умолчанию 400).
        :return: Список кортежей (имя файла с индексом, данные батча).
        """
        for data_list, file_name in orders_divided:
            for batch_index, i in enumerate(range(0, len(data_list), batch_size), start=1):
                start_index = i + 1
                end_index = min(i + batch_size, len(data_list))
                batch_indexed_name = f"{batch_index}_{file_name}_{start_index}-{end_index}.xlsx"
                batch_data = data_list[i:i + batch_size]
                yield batch_data, batch_indexed_name

    def excel_add_worksheet_data(self, company_idn: str, company_name: str, company_type: str, edo_type: str,
                                 edo_id: str, mark_type: str,
                                 user_name: str, user_phone: str, user_email: str, partner: str) -> None:
        # self.additional_info = [[user_name, user_phone, user_email],
        self.additional_info = [[user_name, ],
                                ['Код партнера', partner],
                                [company_type, company_name, company_idn],
                                [edo_type, edo_id],
                                ['Тип этикетки', mark_type],
                                ]

    def process_to_excel(self, list_of_orders: Generator) -> list[tuple[BytesIO, str],]:

        """
            receives list of orders in sequence
            :param list_of_orders: (self._orders_list_outer, name),
                                   (self._orders_list_inner, name),
            return excel table and it's name
        """
        res_tables = []
        for el in list_of_orders:
            if not el[0]:
                continue
            output = BytesIO()
            workbook = Workbook(output)
            worksheet_1 = workbook.add_worksheet(name=self.company_idn)
            worksheet_2 = workbook.add_worksheet(name=settings.SHEET_NAME_2)

            # Some data we want to write to the worksheet.
            main_data = self.excel_start_data_ext(category=self.category, flag_046=self.flag_046)
            main_data.extend(el[0])
            OrdersProcessor.add_to_excel(worksheet=worksheet_1, data=main_data, row=0, col=0)

            df_dict = {}

            df_dict["df1"] = DataFrame(main_data)
            OrdersProcessor.add_to_excel(worksheet=worksheet_2, data=self.additional_info, row=0, col=0)
            df_dict["df2"] = DataFrame(self.additional_info)

            OrdersProcessor.adjusting_df(df=df_dict["df1"], worksheet=worksheet_1) if not self.flag_046 else None
            OrdersProcessor.adjusting_df(df=df_dict["df2"], worksheet=worksheet_2)
            workbook.close()
            df_dict.clear()

            output.name = el[1]
            output.seek(0)
            output.flush()
            res_tables.append((output, output.name,))
        return res_tables

    @staticmethod
    def get_filename(order_num: int, category: str, pos_count: int, count: int,
                     partner_code: str, company_type: str, company_name: str, flag_046: bool = False) -> str:
        table_format = '029_' if not flag_046 else '046_'
        name = f"{table_format}{order_num} {partner_code} {category} {company_type} " \
               f"{company_name.split(' ')[0] if len(company_name.split(' ')) > 1 else company_name} {pos_count}-{count}"
        # return f"{name}.xlsx"
        return f"{name}.zip"

    @staticmethod
    def set_styles(workbook: Workbook,  worksheet: Worksheet, row: int):
        little_format = workbook.add_format({'font_size': 6, 'text_wrap': 'true'})
        for i in range(2, row+1):
            worksheet.set_row(row=i, cell_format=little_format)

    @staticmethod
    def add_to_excel(worksheet: Worksheet, data: Optional[Union[tuple, list]], row: int, col: int) -> None:
        col_n = copy(col)
        for data_row in data:
            for data_cell in data_row:
                worksheet.write(row, col, data_cell)
                col += 1
            col = col_n
            row += 1

    @staticmethod
    def excel_start_data(category: str):
        res = []
        if category == settings.Shoes.CATEGORY:
            res = copy(settings.Shoes.START)
        if category == settings.Linen.CATEGORY:
            res = copy(settings.Linen.START)
        if category == settings.Parfum.CATEGORY:
            res = copy(settings.Parfum.START)
        if category == settings.Clothes.CATEGORY:
            res = copy(settings.Clothes.START)
        return res

    @staticmethod
    def excel_start_data_ext(category: str,  flag_046: bool = False):
        res = []
        if category == settings.Shoes.CATEGORY:
            res = copy(settings.Shoes.START_EXT_046) if flag_046 else copy(settings.Shoes.START_EXT)
        if category == settings.Linen.CATEGORY:
            res = copy(settings.Linen.START_EXT)
        if category == settings.Parfum.CATEGORY:
            res = copy(settings.Parfum.START_EXT)
        if category == settings.Clothes.CATEGORY:
            res = copy(settings.Clothes.START_EXT_046) if flag_046 else copy(settings.Clothes.START_EXT)
        if category == settings.Socks.CATEGORY:
            res = copy(settings.Socks.START_EXT_046) if flag_046 else copy(settings.Socks.START_EXT)
        return res

    @staticmethod
    def adjusting_df(df: DataFrame, worksheet: Worksheet):
        for idx, col in enumerate(df):  # loop through all columns
            series = df[col]
            max_len = max((
                series.astype(str).map(len).max(),  # len of largest item
                len(str(series.name))  # len of column name/header
            )) + 1  # adding a little extra space
            worksheet.set_column(idx, idx, max_len)

    def make_file(self, order_num: int, category: str, pos_count: int, orders_pos_count: int,
                  c_partner_code: str, company_type: str, company_name: str, company_idn: str, edo_type: str,
                  edo_id: str, mark_type: str, c_name: str, c_phone: str, c_email: str, ) -> tuple[BytesIO, str]:
        self.path = self.get_filename(order_num=order_num, category=category,
                                      pos_count=pos_count, count=orders_pos_count,
                                      partner_code=c_partner_code, company_type=company_type,
                                      company_name=company_name, flag_046=self.flag_046)
        self.excel_add_worksheet_data(company_idn=company_idn, company_name=company_name,
                                      company_type=company_type,
                                      edo_type=edo_type, edo_id=edo_id, mark_type=mark_type,
                                      user_name=c_name, user_phone=c_phone,
                                      user_email=c_email, partner=c_partner_code)

        excel_files = self.process_to_excel(list_of_orders=OrdersProcessor
                                            .prepare_batches(orders_divided=[(self.orders_list_outer, "ВВЕЗЕН"),
                                                                             (self.orders_list_inner, "РФ_ВНУТР")]))

        return OrdersProcessor.archive_excels(excel_files=excel_files, filename=self.path)

    @staticmethod
    def eatp(value: str, field_type: str) -> str:
        """
        empty_article_trademark_process
        Обрабатывает входное значение в зависимости от типа поля.

        :param value: Входное значение (строка).
        :param field_type: Тип поля ('article' или 'trademark').
        :return: Преобразованное значение в зависимости от условий.
        """
        match field_type:
            case "article" if value == "БЕЗ АРТИКУЛА":
                return ""
            case "trademark" if value == "БЕЗ ТОВАРНОГО ЗНАКА":
                return ""
            case "article":
                return "арт. " + value
            case _:
                return value


class ShoesProcessor(OrdersProcessor):

    @staticmethod
    def prepare_ext_data(orders_list: list, flag_046: bool = False) -> tuple[list, list, list, ]:
        res_list_common = []
        res_list_outer = []
        res_list_inner = []

        actual_date = datetime.now().strftime('%d.%m.%Y')
        for el in orders_list:

            tnved = ShoesProcessor.get_tnved(material=el.material_top, gender=el.gender) \
                if not el.tnved_code else el.tnved_code
            declar_doc = f"{el.rd_type[0]} {el.rd_name} от {el.rd_date.strftime('%d.%m.%Y')}" if el.rd_date else ''
            for sq in el.sizes_quantities:
                full_name = f'{el.type} {el.gender} {OrdersProcessor.eatp(value=el.trademark, field_type="trademark")} ' \
                            f'{OrdersProcessor.eatp(value=el.article, field_type="article")} цвет. {el.color} р.{sq.size}'

                temp_list = [tnved[:4], full_name,
                             el.trademark, "Артикул", el.article,
                             el.type, el.color, sq.size, el.material_top,
                             el.material_lining, el.material_bottom, tnved, '', '',
                             el.article_price, el.tax, el.box_quantity * sq.quantity, el.box_quantity,
                             sq.quantity, el.country, declar_doc,
                             ] if not flag_046 else \
                    ['', '', '', el.article, actual_date, full_name, el.trademark, '',
                     settings.COUNTRIES_CODES.get(el.country), settings.Shoes.TYPES_CODES.get(el.type), el.material_top,
                             el.material_lining, el.material_bottom, el.color, settings.Shoes.SIZES_CODES.get(sq.size),
                     '' if sq.size in settings.Shoes.SIZES_ND else sq.size, tnved, '', sq.quantity, declar_doc, ]

                res_list_common.append(temp_list)
                if el.country.upper() in settings.COUNTRIES_INNER:
                    res_list_inner.append(temp_list)
                else:
                    res_list_outer.append(temp_list)

        return res_list_common, res_list_outer, res_list_inner

    @staticmethod
    def get_tnved(material: str, gender: str) -> str:
        tnved_tuple = settings.Shoes.TNVED_CODE
        if material in settings.Shoes.SHOE_NL and gender == settings.Shoes.GENDERS[1]:
            return tnved_tuple[2]
        if material in settings.Shoes.SHOE_NL:
            return tnved_tuple[1]

        if material in settings.Shoes.SHOE_AL:
            return tnved_tuple[0]
        if material in settings.Shoes.SHOE_OT:
            return tnved_tuple[3]
        else:
            return tnved_tuple[0]


class LinenProcessor(OrdersProcessor):

    @staticmethod
    def prepare_ext_data(orders_list: list, flag_046: bool = False) -> tuple[list, list, list]:
        res_list_common = []
        res_list_outer = []
        res_list_inner = []

        for el in orders_list:
            tnved = settings.Linen.TNVED_CODE if not el.tnved_code else el.tnved_code
            declar_doc = f"{el.rd_type[0]} {el.rd_name} от {el.rd_date.strftime('%d.%m.%Y')}" if el.rd_date else ''
            table_type = el.type if el.type != 'КОМПЛЕКТ ПОСТЕЛЬНОГО БЕЛЬЯ' else 'КОМПЛЕКТ'
            for sq in el.sizes_quantities:
                if el.with_packages == 'да':
                    full_name = f'Комплект {el.type} {OrdersProcessor.eatp(value=el.trademark, field_type="trademark")} {sq.quantity} шт. ' \
                                f'{OrdersProcessor.eatp(value=el.article, field_type="article")} цвет {el.color}, р.{sq.size} {sq.unit}'
                    fin_quantity = el.box_quantity
                else:
                    full_name = f'{el.type} {OrdersProcessor.eatp(value=el.trademark, field_type="trademark")} ' \
                                f'{OrdersProcessor.eatp(value=el.article, field_type="article")} цвет {el.color}, р.{sq.size} {sq.unit}'
                    fin_quantity = sq.quantity * el.box_quantity
                temp_list = [tnved[:4], full_name,
                             el.trademark, "Артикул", el.article,
                             table_type, el.color, el.customer_age, el.textile_type, el.content, sq.size,
                             tnved, settings.Linen.NUMBER_STANDART, '', '', el.article_price, el.tax,
                             fin_quantity, '', '', el.country, declar_doc, ]
                res_list_common.append(temp_list)
                if el.country.upper() in settings.COUNTRIES_INNER:
                    res_list_inner.append(temp_list)
                else:
                    res_list_outer.append(temp_list)

        return res_list_common, res_list_outer, res_list_inner


class ParfumProcessor(OrdersProcessor):

    @staticmethod
    def prepare_ext_data(orders_list: list, flag_046: bool = False) -> tuple[list, list, list]:
        res_list_common = []
        res_list_outer = []
        res_list_inner = []

        for el in orders_list:
            if el.with_packages == 'да':
                full_name = f'Набор {el.type} {OrdersProcessor.eatp(value=el.trademark, field_type="trademark")} {el.quantity} шт., ' \
                            f'{el.volume} {el.volume_type}'
                fin_quantity = el.box_quantity
            else:
                full_name = f'{el.type} {OrdersProcessor.eatp(value=el.trademark, field_type="trademark")} , ' \
                            f'{el.volume} {el.volume_type}'
                fin_quantity = el.quantity

            tnved = ParfumProcessor.get_tnved(parfum_type=el.type) if not el.tnved_code else el.tnved_code
            declar_doc = f"{el.rd_type[0]} {el.rd_name} от {el.rd_date.strftime('%d.%m.%Y')}" if el.rd_date else ''
            temp_list = [tnved[:4], full_name,
                         el.trademark, el.volume_type, el.volume,
                         el.package_type, el.material_package, el.type,
                         tnved, settings.Parfum.NUMBER_STANDART,
                         settings.Parfum.STATUS, '',
                         el.article_price, el.tax, fin_quantity, '', '', el.country,
                         declar_doc, ]
            res_list_common.append(temp_list)
            if el.country.upper() in settings.COUNTRIES_INNER:
                res_list_inner.append(temp_list)
            else:
                res_list_outer.append(temp_list)

        return res_list_common, res_list_outer, res_list_inner

    @staticmethod
    def get_tnved(parfum_type: str) -> str:
        tnved_tuple = settings.Parfum.TNVED_CODE
        parfum_list = settings.Parfum.TYPES
        if parfum_type in parfum_list[:6]:
            return tnved_tuple[0]
        else:
            return tnved_tuple[1]


class ClothesProcessor(OrdersProcessor):

    @staticmethod
    def prepare_ext_data(orders_list: list, flag_046: bool = False) -> tuple[list, list, list]:
        res_list_common = []
        res_list_outer = []
        res_list_inner = []
        actual_date = datetime.now().strftime('%d.%m.%Y')
        for el in orders_list:
            #     if not el.tnved_code else el.tnved_code
            tnved = el.tnved_code
            fc_tnved = tnved if (tnved not in settings.Clothes.TNVED_ALL or tnved == '4304000000'
                                 or tnved[:4] in settings.Clothes.FULL_TNVED_4DIGIT_LIST) \
                else tnved[:4]
            # fc_tnved = tnved if tnved == '4304000000' else tnved[:4]

            declar_doc = f"{el.rd_type[0]} {el.rd_name} от {el.rd_date.strftime('%d.%m.%Y')}" \
                if all([el.rd_date, el.rd_type, el.rd_name]) else ''
            for sq in el.sizes_quantities:

                gender_dec = ClothesProcessor.get_gender_dec(clothes_type=el.type, gender=el.gender, subcategory=el.subcategory)
                gender = ClothesProcessor.get_gender(gender=el.gender) if not flag_046 \
                    else ClothesProcessor.get_gender_046(gender=el.gender)
                full_name = f'{el.type} {gender_dec} ' \
                            f'{OrdersProcessor.eatp(value=el.trademark, field_type="trademark")} {OrdersProcessor.eatp(value=el.article, field_type="article")} цвет {el.color} р. {sq.size}'

                temp_list = [fc_tnved, full_name,
                             el.trademark, 'Артикул', el.article, el.type, el.color, gender, sq.size_type, sq.size,
                             el.content, tnved, settings.Clothes.NUMBER_STANDART,
                             '', '', el.article_price, el.tax, sq.quantity * el.box_quantity, '', '', el.country,
                             declar_doc, ] if not flag_046 else \
                            ['', '', el.article, actual_date, full_name, el.trademark, settings.COUNTRIES_CODES.get(el.country), '',
                             '', settings.Clothes.TYPES_CODES.get(el.type), '', tnved,
                             settings.Clothes.SYZE_TYPES_CODES.get(sq.size_type), sq.size, '', el.color, '', gender,
                             el.content, 'НЕТ', 'ДА', 'НЕТ', 'НЕТ', 'НЕТ', '', 'НЕТ', '', '', '',
                             sq.quantity * el.box_quantity, declar_doc, ]
                res_list_common.append(temp_list)
                if el.country.upper() in settings.COUNTRIES_INNER:
                    res_list_inner.append(temp_list)
                else:
                    res_list_outer.append(temp_list)

        return res_list_common, res_list_outer, res_list_inner

    @staticmethod
    def get_tnved(clothes_type: str, gender: str, content: str) -> str:
        tnved_tuple = settings.Clothes.TNVED_CODE
        leather = check_leather(content)
        upper_clothes = settings.Clothes.UPPER_TYPES
        gender_list = settings.Clothes.GENDERS
        tnved = tnved_tuple[3]
        if leather:
            tnved = tnved_tuple[0]
        elif clothes_type in upper_clothes:
            tnved = tnved_tuple[3]
        elif gender == gender_list[1]:
            tnved = tnved_tuple[1]
        elif gender == gender_list[0] or gender == gender_list[2] or gender == gender_list[3]:
            tnved = tnved_tuple[2]

        return tnved

    @staticmethod
    def get_gender_dec(clothes_type: str, gender: str, subcategory: str) -> Optional[str]:
        match subcategory:
            case ClothesSubcategories.underwear.value:
                declination_dict = UNDERWEAR_DEC_DICT
            case _:
                declination_dict = settings.Clothes.DEC

        if declination_dict.get(clothes_type):
            return declination_dict.get(clothes_type).get(gender)
        else:
            return ''

    @staticmethod
    def get_gender(gender: str) -> Optional[str]:
        gender_value = gender.capitalize()
        return settings.Clothes.GENDERS_ORDER.get(gender_value)

    @staticmethod
    def get_gender_046(gender: str) -> Optional[str]:
        gender_value = gender.capitalize()
        return settings.Clothes.GENDERS_ORDER_046.get(gender_value)


class SocksProcessor(OrdersProcessor):

    @staticmethod
    def prepare_ext_data(orders_list: list, flag_046: bool = False) -> tuple[list, list, list]:
        res_list_common = []
        res_list_outer = []
        res_list_inner = []

        actual_date = datetime.now().strftime('%d.%m.%Y')
        for el in orders_list:
            #     if not el.tnved_code else el.tnved_code
            tnved = el.tnved_code

            # fc_tnved = tnved if tnved == '4304000000' else tnved[:4]

            declar_doc = f"{el.rd_type[0]} {el.rd_name} от {el.rd_date.strftime('%d.%m.%Y')}" \
                if all([el.rd_date, el.rd_type, el.rd_name]) else ''
            for sq in el.sizes_quantities:

                gender_dec = SocksProcessor.get_gender_dec(clothes_type=el.type, gender=el.gender)
                gender = SocksProcessor.get_gender(gender=el.gender) if not flag_046 \
                    else SocksProcessor.get_gender_046(gender=el.gender)
                full_name = f'{el.type} {gender_dec} ' \
                            f'{OrdersProcessor.eatp(value=el.trademark, field_type="trademark")} {OrdersProcessor.eatp(value=el.article, field_type="article")} цвет {el.color} р. {sq.size}'

                temp_list = [tnved, full_name,
                             el.trademark, 'Артикул', el.article, el.type, el.color, gender, sq.size_type, sq.size,
                             el.content, tnved, settings.Clothes.NUMBER_STANDART,
                             '', '', el.article_price, el.tax, sq.quantity * el.box_quantity, '', '', el.country,
                             declar_doc, ] if not flag_046 else \
                            ['', '', el.article, actual_date, full_name, el.trademark, settings.COUNTRIES_CODES.get(el.country), '',
                             '', settings.Socks.TYPES_CODES.get(el.type), '', tnved,
                             settings.Socks.SYZE_TYPES_CODES.get(sq.size_type), sq.size, '', el.color, '', gender,
                             el.content, 'НЕТ', 'ДА', 'НЕТ', 'НЕТ', 'НЕТ', '', 'НЕТ', '', '', '',
                             sq.quantity * el.box_quantity, declar_doc, ]
                res_list_common.append(temp_list)
                if el.country.upper() in settings.COUNTRIES_INNER:
                    res_list_inner.append(temp_list)
                else:
                    res_list_outer.append(temp_list)

        return res_list_common, res_list_outer, res_list_inner

    @staticmethod
    def get_gender_dec(clothes_type: str, gender: str) -> Optional[str]:
        declination_dict = settings.Socks.DEC
        return declination_dict.get('socks').get(gender)


    @staticmethod
    def get_gender(gender: str) -> Optional[str]:
        gender_value = gender.capitalize()
        #same genders as in clothes
        return settings.Clothes.GENDERS_ORDER.get(gender_value)

    @staticmethod
    def get_gender_046(gender: str) -> Optional[str]:
        # same genders as in clothes
        gender_value = gender.capitalize()
        return settings.Clothes.GENDERS_ORDER_046.get(gender_value)


# not used currently
def orders_list_get(model: db.Model) -> Optional[Union[tuple, list]]:
    order_list = [o for o in model]
    if order_list:
        return order_list
    else:
        return None, None


def get_download_info(o_id, user: User, flag_046: bool = False) -> Union[Response, tuple]:
    category_name_excel = ''  # for filename if we got subcategory

    order = Order.query.filter(Order.id == o_id, ~Order.to_delete).first()
    if not order:
        flash(message=settings.Messages.EMPTY_ORDER, category='error')
        # return redirect(url_for('main.enter'))
        return (None,) * 12

    order_num = order.order_idn
    company_idn = order.company_idn
    company_type = order.company_type
    company_name = order.company_name
    edo_type = order.edo_type
    edo_id = order.edo_id
    mark_type = order.mark_type
    c_name = user.login_name
    c_phone = user.phone
    c_email = user.email
    if not user.partners:
        c_partner_code = settings.NO_PARTNER_CODE
    else:
        c_partner_code = user.partners[0].code if user.role != settings.SUPER_USER else settings.SU_PARTNER

    if order.category == settings.Shoes.CATEGORY:
        order_list = order.shoes
        if not order_list:
            flash(message=settings.Messages.EMPTY_ORDER, category='error')

            return (None,) * 12  # say hi hardcode

        category = settings.Shoes.CATEGORY
        rd_exist, quantity_list_raw, pos_count, orders_pos_count = order_count(category=category, order_list=order_list)

        op = ShoesProcessor(category=settings.Shoes.CATEGORY, company_idn=company_idn, orders_list=order_list,
                            flag_046=flag_046)
    elif order.category == settings.Clothes.CATEGORY:
        # order_list, old_tnved, new_tnved = helper_get_clothes_divided_list(order_id=o_id,)
        order_list = order.clothes
        if not order_list:
            flash(message=settings.Messages.EMPTY_ORDER, category='error')

            return (None,) * 12

        category = settings.Clothes.CATEGORY
        rd_exist, quantity_list_raw, pos_count, orders_pos_count = order_count(category=category, order_list=order_list)

        from utilities.support import get_subcategory
        subcategory = get_subcategory(order_id=o_id, category=settings.Clothes.CATEGORY)

        category_name_excel = settings.SUB_CATEGORIES_DICT.get(subcategory) if subcategory in ClothesSubcategories.__members__  and subcategory != ClothesSubcategories.common.value else category

        op = ClothesProcessor(category=category, company_idn=company_idn, orders_list=order_list, flag_046=flag_046)

    elif order.category == settings.Socks.CATEGORY:
        # order_list, old_tnved, new_tnved = helper_get_clothes_divided_list(order_id=o_id,)
        order_list = order.socks
        if not order_list:
            flash(message=settings.Messages.EMPTY_ORDER, category='error')

            return (None,) * 12

        category = settings.Socks.CATEGORY
        rd_exist, quantity_list_raw, pos_count, orders_pos_count = order_count(category=category, order_list=order_list)

        op = SocksProcessor(category=category, company_idn=company_idn, orders_list=order_list, flag_046=flag_046)

    elif order.category == settings.Linen.CATEGORY:
        order_list = order.linen
        if not order_list:
            flash(message=settings.Messages.EMPTY_ORDER, category='error')

            return (None,) * 12

        category = settings.Linen.CATEGORY
        rd_exist, quantity_list_raw, pos_count, orders_pos_count = order_count(category=category, order_list=order_list)

        op = LinenProcessor(category=category, company_idn=company_idn, orders_list=order_list)
    elif order.category == settings.Parfum.CATEGORY:
        order_list = order.parfum
        pos_count = len(order_list)
        if not order_list:
            flash(message=settings.Messages.EMPTY_ORDER, category='error')

            return (None,) * 12

        rd_exist = True if [el.rd_type for el in order_list if el.rd_type] else False
        orders_pos_count = sum([el.quantity for el in order_list])
        category = settings.Parfum.CATEGORY
        op = ParfumProcessor(category=category, company_idn=company_idn, orders_list=order_list)

    else:
        flash(message=settings.Messages.CATEGORY_UNKNOWN_ERROR, category='error')

        return (None,) * 12

    category_name_excel = category if not category_name_excel else category_name_excel
    files_list = op.make_file(order_num=order_num, category=category_name_excel, pos_count=pos_count, orders_pos_count=orders_pos_count,
                              c_partner_code=c_partner_code, company_type=company_type, company_name=company_name,
                              company_idn=company_idn, edo_type=edo_type, edo_id=edo_id, mark_type=mark_type,
                              c_name=c_name, c_phone=c_phone, c_email=c_email)

    return rd_exist, company_idn, company_type, company_name, edo_type, edo_id, \
        mark_type, pos_count, orders_pos_count, category, \
        c_partner_code, files_list


# todo decompose common methods

def orders_download_common(user: User, o_id: int, flag_046: bool = False):

    rd_exist, company_idn, company_type, company_name, edo_type, edo_id, \
        mark_type, pos_count, orders_pos_count, category, \
        c_partner_code, files_list = get_download_info(o_id=o_id, user=user, flag_046=flag_046)
    if not mark_type:
        return redirect(url_for('main.index'))

    return send_file(files_list[0], download_name=files_list[1], as_attachment=True)


def orders_process_send_order(o_id: int, user: User, order_comment: str, order_idn: str,
                              su_exec_order_name: str = None,
                              flag_046: bool = False) -> bool:
    # if user.role == settings.ORD_USER and user.admin_parent_id:
    #     order_num = User.query.filter_by(id=user.admin_parent_id).order_by(desc(User.id)).first().admin_order_num
    #
    # elif user.role in [settings.ADMIN_USER, settings.SUPER_USER]:
    #     order_num = user.admin_order_num
    # else:
    #     flash(message=settings.Messages.TELEGRAM_SEND_ERROR, category='error')
    #     return False

    if user.is_at2:
        telegram_raw = user.telegram
        telegram_id = telegram_raw[0].channel_id if telegram_raw else settings.Telegram.TELEGRAM_MAIN_GROUP_ID
    else:
        telegram_id = settings.Telegram.TELEGRAM_MAIN_GROUP_ID

    rd_exist, company_idn, company_type, company_name, \
        edo_type, edo_id, mark_type, \
        pos_count,  orders_pos_count, \
        category,  p_code, files_list = get_download_info(o_id=o_id, user=user,
                                                          flag_046=flag_046)
    if not files_list:
        flash(message=settings.Messages.CATEGORY_UNKNOWN_ERROR, category='error')
        return False

    admin_user = User.query.filter_by(id=user.admin_parent_id).first() if user.role == settings.ORD_USER else user
    message = TelegramProcessor.make_message_tg(user=user, admin_user=admin_user if admin_user else None,
                                                order_comment=order_comment, company_idn=company_idn,
                                                company_type=company_type, company_name=company_name,
                                                edo_type=edo_type, edo_id=edo_id, mark_type=mark_type,
                                                pos_count=pos_count, orders_pos_count=orders_pos_count,
                                                su_exec_order_name=su_exec_order_name, reports_quantity=len(files_list),
                                                rd_exist=rd_exist, tg_order_num=order_idn
                                                )

    TelegramProcessor.send_message_tg(
        message=message,
        group_id=telegram_id,
        files_list=files_list,
    ) if user.admin_parent_id != 2\
        else TelegramProcessor.send_message_text(message=message, chat_id=telegram_id)
    # если клиент ruznak то не отправляем файл

    return True


def upload_errors_file(error_list: list) -> BytesIO:
    buf_error_list = map(lambda x: f"{x}\n".encode(), error_list)
    output = BytesIO()
    for e in buf_error_list:
        output.write(e)

    output.seek(0)
    return output


def orders_common_preload(category: str, company_idn: str, orders_list: list) -> tuple:
    start_list, res_list = [], []

    if category == settings.Shoes.CATEGORY:
        # start_list = copy(settings.Shoes.START_RELOAD)
        start_list = copy(settings.Shoes.START_CRM_PRELOAD)
        sp = ShoesProcessor(company_idn=company_idn, category=category, orders_list=orders_list)
        res_list_raw = sp.orders_list
        # res_list = list(map(lambda x: x[:12] + x[14:], res_list_raw))
        res_list = list(map(lambda x: x[1:11] + x[14:], res_list_raw))
    elif category == settings.Clothes.CATEGORY:
        # start_list = copy(settings.Clothes.START_PRELOAD)
        start_list = copy(settings.Clothes.START_CRM_PRELOAD)
        cp = ClothesProcessor(company_idn=company_idn, category=category, orders_list=orders_list)
        res_list_raw = cp.orders_list
        # res_list = list(map(lambda x: x[:12] + x[15:18] + x[20:], res_list_raw))
        res_list = list(map(lambda x: x[1:11] + x[15:18] + x[20:], res_list_raw))
    elif category == settings.Socks.CATEGORY:
        start_list = copy(settings.Socks.START_PRELOAD)
        cp = SocksProcessor(company_idn=company_idn, category=category, orders_list=orders_list)
        res_list_raw = cp.orders_list
        res_list = list(map(lambda x: x[:12] + x[15:18] + x[20:], res_list_raw))
    elif category == settings.Linen.CATEGORY:
        # start_list = copy(settings.Linen.START_PRELOAD)
        start_list = copy(settings.Linen.START_CRM_PRELOAD)
        lp = LinenProcessor(company_idn=company_idn, category=category, orders_list=orders_list)
        res_list_raw = lp.orders_list
        # res_list = list(map(lambda x: x[:12] + x[15:18] + x[20:], res_list_raw))
        res_list = list(map(lambda x: x[1:11] + x[15:18] + x[20:], res_list_raw))
    elif category == settings.Parfum.CATEGORY:
        # start_list = copy(settings.Parfum.START_PRELOAD)
        start_list = copy(settings.Parfum.START_CRM_PRELOAD)
        p_proc = ParfumProcessor(company_idn=company_idn, category=category, orders_list=orders_list)
        res_list_raw = p_proc.orders_list
        # res_list = list(map(lambda x: x[:9] + x[12:15] + x[17:], res_list_raw))
        res_list = list(map(lambda x: x[1:8] + x[12:15] + x[17:], res_list_raw))

    page, per_page, offset, pagination, order_list = helper_paginate_data(data=res_list,
                                                                          per_page=settings.PAGINATION_PER_PAGE_PRELOAD)
    return start_list, page, per_page, offset, pagination, order_list


# temoporary double code for preload because of table specifics
def crm_orders_common_preload(category: str, company_idn: str, orders_list: list) -> tuple:
    start_list, res_list = [], []

    if category == settings.Shoes.CATEGORY:
        start_list = copy(settings.Shoes.START_CRM_PRELOAD)
        sp = ShoesProcessor(company_idn=company_idn, category=category, orders_list=orders_list)
        res_list_raw = sp.orders_list
        res_list = list(map(lambda x: x[1:11] + x[14:], res_list_raw))
        # res_list = list(map(lambda x: x[:12] + x[14:], res_list_raw))
    elif category == settings.Clothes.CATEGORY:
        start_list = copy(settings.Clothes.START_CRM_PRELOAD)
        cp = ClothesProcessor(company_idn=company_idn, category=category, orders_list=orders_list)
        res_list_raw = cp.orders_list
        res_list = list(map(lambda x: x[1:11] + x[15:18] + x[20:], res_list_raw))
    elif category == settings.Linen.CATEGORY:
        start_list = copy(settings.Linen.START_CRM_PRELOAD)
        lp = LinenProcessor(company_idn=company_idn, category=category, orders_list=orders_list)
        res_list_raw = lp.orders_list
        res_list = list(map(lambda x: x[1:11] + x[15:18] + x[20:], res_list_raw))
    elif category == settings.Parfum.CATEGORY:
        start_list = copy(settings.Parfum.START_CRM_PRELOAD)
        p_proc = ParfumProcessor(company_idn=company_idn, category=category, orders_list=orders_list)
        res_list_raw = p_proc.orders_list
        res_list = list(map(lambda x: x[1:8] + x[12:15] + x[17:], res_list_raw))

    page, per_page, offset, pagination, order_list = helper_paginate_data(data=res_list,
                                                                          per_page=settings.PAGINATION_PER_PAGE_PRELOAD,
                                                                          css_framework='bootstrap4')
    return start_list, page, per_page, offset, pagination, order_list
