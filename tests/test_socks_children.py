"""Sock forms, imports, merging and exports without a database or app startup."""
import ast
from copy import copy
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace as NS
import re
import sys
import unittest
from zipfile import ZipFile
import xml.etree.ElementTree as ET

from werkzeug.datastructures import MultiDict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
from utilities.exceptions import SizeTypeException
from utilities.socks_children import (
    CHILDREN_AGE_SIZES, normalize_socks_size, parse_socks_children,
    socks_size_for_export, validate_socks_sizes,
)


def load_node(path, name, namespace, class_name=None):
    nodes = ast.parse((ROOT / path).read_text()).body
    if class_name:
        nodes = next(n for n in nodes if isinstance(n, ast.ClassDef) and n.name == class_name).body
    node = next(n for n in nodes if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == name)
    for part in ast.walk(node):
        if isinstance(part, (ast.FunctionDef, ast.ClassDef)):
            part.decorator_list = [d for d in part.decorator_list if isinstance(node, ast.ClassDef)
                                   and isinstance(d, ast.Name) and d.id == 'staticmethod']
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), node], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), path, 'exec'), namespace)
    return namespace[name]


def socks_config():
    from utilities.param_lists import SOCKS_SIZE_TYPES, SOCKS_TYPES_SIZES_DICT, SOCKS_ST_DICT
    return NS(SIZE_TYPES_ALL=SOCKS_SIZE_TYPES, SIZE_ALL_DICT=SOCKS_TYPES_SIZES_DICT,
              SYZE_TYPES_CODES=SOCKS_ST_DICT, UNITE_SIZE_VALUE='ONE SIZE',
              INTERNATIONAL_SIZE_TYPE='МЕЖДУНАРОДНЫЙ', DEFAULT_SIZE_TYPE='РОССИЯ',
              SPECIAL_SIZE_TYPE='ОСОБЫЕ_РАЗМЕРЫ', UPLOAD_STANDART_ROW=7, CATEGORY_PROCESS='socks')


class SocksChildrenTests(unittest.TestCase):
    def setUp(self):
        self.settings = NS(Socks=socks_config())
        self.get_type = load_node('app/utilities/saving_helpers.py', 'get_socks_size_type', dict(
            settings=self.settings, SizeTypeException=SizeTypeException,
            CHILDREN_AGE_SIZES=CHILDREN_AGE_SIZES, normalize_socks_size=normalize_socks_size))

    def test_all_nine_ages_keep_units_and_convert_to_international_for_046(self):
        expected = [('0-3', 'month', '6'), ('3-6', 'month', '8'), ('6-9', 'month', '10'),
                    ('1,5', 'years', '12'), ('2-3', 'years', '14'), ('4-5', 'years', '16'),
                    ('6-7', 'years', '18'), ('8-9', 'years', '20'), ('10-12', 'years', '22')]
        for age, kind, international in expected:
            with self.subTest(age=age):
                self.assertEqual(self.get_type(age, kind), kind)
                validate_socks_sizes([(age, 2, kind)], True, 'Унисекс')
                self.assertEqual(socks_size_for_export(age, kind), (age, kind))
                self.assertEqual(socks_size_for_export(age, kind, True), (international, 'МЕЖДУНАРОДНЫЙ'))
        self.assertEqual(normalize_socks_size('1.5', 'years'), '1,5')
        self.assertEqual(normalize_socks_size('12.0', 'МЕЖДУНАРОДНЫЙ'), '12')

    def test_server_rejects_mixed_grids_and_unknown_ages(self):
        for size, kind, child, gender in [
            ('0-3', 'month', False, 'Жен.'), ('1,5', 'years', False, 'Унисекс'),
            ('12', 'МЕЖДУНАРОДНЫЙ', False, 'Муж.'), ('12', 'РОССИЯ', False, 'Муж.'),
            ('XL', 'МЕЖДУНАРОДНЫЙ', True, 'Муж.'), ('25', 'РОССИЯ', True, 'Унисекс'),
            ('0-3', 'years', True, 'Детск.'), ('2-3', 'month', True, 'Детск.'),
            ('25', 'РОССИЯ', False, 'Детск.'),
        ]:
            with self.subTest(size=size, kind=kind, child=child):
                with self.assertRaises(SizeTypeException):
                    validate_socks_sizes([(size, 1, kind)], child, gender)
        for size, kind in [('25', 'РОССИЯ'), ('S', 'МЕЖДУНАРОДНЫЙ'), ('ONE SIZE', 'МЕЖДУНАРОДНЫЙ')]:
            validate_socks_sizes([(size, 1, kind)], False, 'Жен.')
        validate_socks_sizes([('ONE SIZE', 1, 'МЕЖДУНАРОДНЫЙ'), ('12', 1, 'РОССИЯ')], True, 'Муж.')

    def test_excel_flag_is_explicit_and_old_templates_are_supported(self):
        self.assertTrue(parse_socks_children('', 'Детск.', 'РОССИЯ'))
        self.assertTrue(parse_socks_children('nan', 'Муж.', 'month'))
        self.assertFalse(parse_socks_children('', 'Жен.', 'РОССИЯ'))
        self.assertTrue(parse_socks_children('Да', 'Унисекс', 'МЕЖДУНАРОДНЫЙ'))
        self.assertFalse(parse_socks_children('Нет', 'Детск.', 'years'))
        with self.assertRaises(SizeTypeException):
            parse_socks_children('возможно', 'Унисекс', 'РОССИЯ')

    def test_excel_preserves_explicit_numeric_and_age_types(self):
        ns = dict(settings=self.settings, re=re, get_socks_size_type=self.get_type,
                  normalize_socks_size=normalize_socks_size, SizeTypeException=SizeTypeException,
                  val_error_start=lambda **kw: 'row',)
        get_type = load_node('app/utilities/upload_order/upload_socks.py', '_size_type', ns, 'ValidateSocksMixin')
        get_size = load_node('app/utilities/upload_order/upload_socks.py', '_size', ns, 'ValidateSocksMixin')
        for size, supplied, expected, normalized in [
            ('12', 'МЕЖДУНАРОДНЫЙ', 'МЕЖДУНАРОДНЫЙ', '12'),
            ('0-3', 'MONTH', 'month', '0-3'), ('1.5', 'years', 'years', '1,5'),
            ('25', '', 'РОССИЯ', '25'), ('XL', 'nan', 'МЕЖДУНАРОДНЫЙ', 'XL'),
        ]:
            rows = [[''] * 15]
            rows[0][5] = supplied
            self.assertIsNone(get_type(size, 7, 5, rows))
            self.assertIsNone(get_size(size, 7, 'J', 6, rows))
            self.assertEqual(rows[0][5:7], [expected, normalized])

    def test_card_request_validation_and_decimal_normalization(self):
        settings = NS(**{name: NS(CATEGORY=name.lower(), CATEGORY_PROCESS=name.lower())
                         for name in ['Clothes', 'Socks', 'Shoes', 'Linen', 'Cosmetics', 'Toys']})
        ns = dict(settings=settings, CATEGORIES_COMMON={'socks': {'title': 'socks'}},
                  normalize_socks_size=normalize_socks_size, get_socks_size_type=self.get_type,
                  validate_socks_sizes=validate_socks_sizes)
        parse = load_node('app/views/main/product_cards/support.py', 'parse_sizes_for_category', ns)
        form = MultiDict([('gender', 'Унисекс'), ('is_children', 'yes'),
                          ('size', '1.5'), ('size_type', 'years'), ('quantity', '2')])
        self.assertEqual(parse('socks', form), [('1,5', '2', 'years')])
        del form['is_children']
        with self.assertRaises(SizeTypeException):
            parse('socks', form)
        form['is_children'] = 'yes'
        form.add('size', '2-3')
        with self.assertRaises(ValueError):
            parse('socks', form)

    def test_order_merge_separates_adult_and_child_with_same_article(self):
        ns = dict(Any=object, settings=NS(**{name: NS(CATEGORY=name.lower()) for name in ['Shoes', 'Clothes', 'Socks']}),
                  normalize_placeholder_value=lambda value, *args: value, normalize_key_value=lambda value: value,
                  normalize_float_key=lambda value: value, normalize_int_key=lambda value: value,
                  NO_TRADEMARK_PLACEHOLDERS=(), NO_TRADEMARK_VALUE='', NO_ARTICLE_PLACEHOLDERS=(), NO_ARTICLE_VALUE='')
        key = load_node('app/utilities/saving_helpers.py', 'build_position_key', ns)
        item = NS(trademark='Бренд', article='A1', tnved_code='6115950000', country='РОССИЯ',
                  rd_type=None, rd_name=None, rd_date=None, article_price=0, tax=0, type='НОСКИ',
                  color='БЕЛЫЙ', gender='Унисекс', content='Хлопок', is_children=False)
        adult = key(item, 'socks')
        item.is_children = True
        self.assertNotEqual(adult, key(item, 'socks'))

    def test_save_and_copy_preserve_child_flag_and_age_sizes(self):
        def model(**kwargs):
            kwargs.setdefault('sizes_quantities', [])
            return NS(**kwargs)
        self.settings.Socks.CATEGORY = 'socks'
        ns = dict(datetime=datetime, settings=self.settings, Socks=model, SocksQuantitySize=lambda **kw: NS(**kw),
                  normalize_socks_size=normalize_socks_size, validate_socks_sizes=validate_socks_sizes,
                  get_socks_size_type=self.get_type, normalize_article_placeholder=lambda value: value,
                  normalize_trademark_placeholder=lambda value: value, process_input_str=lambda value: value,
                  rd_name_clean=lambda value: value, validate_gtin_fields=lambda *args: (None, None),
                  append_or_merge_position=lambda items, item, *args, **kw: items.append(item),
                  _check_socks_compatibility=lambda item: None, _copy_pc_approval_flag=lambda *args: False,
                  normalize_length_width_size_value=lambda size, kind: size,
                  normalize_length_width_size_type=lambda kind: kind)
        save = load_node('app/utilities/saving_uts.py', 'save_socks', ns)
        clone = load_node('app/utilities/saving_uts.py', 'save_copy_order_socks', ns)
        form = {'is_children': 'yes', 'gender': 'Унисекс', 'article': 'A1', 'trademark': 'Бренд',
                'weight_grams': 100, 'content': 'Хлопок', 'color': 'БЕЛЫЙ', 'type': 'НОСКИ'}
        order = NS(socks=[])
        save(order, form, [('1.5', '3', 'years')])
        item = order.socks[0]
        self.assertTrue(item.is_children)
        self.assertEqual((item.sizes_quantities[0].size, item.sizes_quantities[0].size_type), ('1,5', 'years'))
        item.sizes_quantities[0].id = 1
        item.fast_order_company_id = None
        copied = NS(socks=[])
        clone([item], copied)
        self.assertTrue(copied.socks[0].is_children)
        self.assertEqual(copied.socks[0].sizes_quantities[0].size_type, 'years')

    def test_card_merge_key_separates_adult_and_child(self):
        entity = NS(article='A1', color='БЕЛЫЙ', is_children=False)
        settings = NS(**{name: NS(CATEGORY_PROCESS=name.lower()) for name in ['Clothes', 'Socks', 'Linen']})
        ns = dict(settings=settings, WEAR_CARD_CATEGORIES={'socks'}, _card_merge_main_entity=lambda card: entity,
                  normalize_article_for_category=lambda category, data: data['article'])
        key = load_node('app/views/main/product_cards/support.py', '_card_merge_key', ns)
        card = NS(category='socks')
        adult = key(card)
        entity.is_children = True
        self.assertNotEqual(key(card), adult)

    def test_excel_reader_keeps_flag_with_row_when_blank_rows_are_removed(self):
        import pandas as pd
        columns = [f'column_{i}' for i in range(19)]
        columns[18] = 'Детский товар'
        df = pd.DataFrame([[None]*19 for _ in range(8)], columns=columns)
        df.iloc[4, 5] = 'выберите ВИД чулочно носочных изделий из выпадающего списка или со второго листа (справочник)'
        df.iloc[5, 2] = 'First'
        df.iloc[7, 2] = 'Second'
        df.iloc[5, 18] = 'Да'
        df.iloc[7, 18] = 'Нет'
        settings = NS(ORDER_LIMIT_UPLOAD_ARTICLES=1607, ORDER_LIMIT_ARTICLES=1600)
        ns = dict(settings=settings, UploadSocks=NS(ValidateStandart=lambda: NS(full_validate_standart=lambda order_list: order_list)))
        read = load_node('app/utilities/upload_order/upload_socks.py', 'get_article_info_standart', ns, 'UploadSocks')
        instance = NS(df=df)
        result = read(instance)
        self.assertEqual(instance.data_row_indexes, [5, 7])
        self.assertEqual([row[14] for row in result], ['Да', 'Нет'])
        instance.df = df.drop(columns='Детский товар')
        self.assertEqual([row[14] for row in read(instance)], ['', ''])

    def test_full_excel_validation_and_save_keep_mode_size_and_weight(self):
        from pandas import isna
        self.settings.Socks.__dict__.update(TYPES=['НОСКИ'], GENDERS=['Унисекс', 'Детск.'],
                                            MAX_QUANTITY=100000, MIN_QUANTITY=1)
        self.settings.Clothes = NS(UPLOAD_STANDART_ROW=7)
        self.settings.ORDER_LIMIT_ARTICLES = 1600
        self.settings.Messages = NS(UPLOAD_EMPTY_FILE_ERROR='empty')
        self.settings.RZ_GENDERS_RD_LIST = ['Унисекс', 'Детск.']
        ns = dict(settings=self.settings, re=re, copy=copy, isna=isna, datetime=datetime,
                  get_socks_size_type=self.get_type, SizeTypeException=SizeTypeException,
                  normalize_socks_size=normalize_socks_size, parse_socks_children=parse_socks_children,
                  validate_socks_sizes=validate_socks_sizes, val_error_start=lambda **kw: 'row',
                  normalize_trademark_placeholder=lambda value: value, normalize_article_placeholder=lambda value: value,
                  is_allowed_color=lambda value: True, is_allowed_country_for_rd=lambda *args: True,
                  TnvedChecker=NS(tnved_socks_parse=lambda **kw: (5, 'ok')), UploadCategory=object,
                  current_user=NS(role='manager', id=3, admin_parent_id=None))
        load_node('app/utilities/upload_order/upload_socks.py', 'ValidateSocksMixin', ns)
        upload = load_node('app/utilities/upload_order/upload_socks.py', 'UploadSocks', ns)
        rows = [['Бренд', 'A1', 'НОСКИ', 'БЕЛЫЙ', 'Унисекс', kind, size,
                 'Хлопок', '6115950000', '2', 'РОССИЯ', '', '', '', flag]
                for kind, size, flag in [('years', '1.5', 'Да'), ('МЕЖДУНАРОДНЫЙ', '6', 'Да'),
                                          ('РОССИЯ', '25', 'Нет')]]
        validated, errors = upload.ValidateStandart().full_validate_standart(rows)
        self.assertEqual(errors, [])
        self.assertEqual([row[14] for row in validated], ['yes', 'yes', 'no'])
        self.assertEqual(validated[0][5:7], ['years', '1,5'])
        self.settings.Socks.CATEGORY = 'socks'
        ns.update(Socks=lambda **kw: NS(sizes_quantities=[], **kw), SocksQuantitySize=lambda **kw: NS(**kw),
                  append_or_merge_position=lambda items, item, *args: items.append(item))
        save = load_node('app/utilities/upload_order/upload_saving_uts.py', 'upload_socks_st', ns)
        for row in validated:
            row.append(100)
        order = NS(socks=[])
        save(validated, order)
        self.assertEqual([item.is_children for item in order.socks], [True, True, False])
        self.assertEqual([item.weight_grams for item in order.socks], [100, 100, 100])
        self.assertEqual(order.socks[0].sizes_quantities[0].size, '1,5')

    def test_workbook_flag_dropdown_types_and_age_reference(self):
        ns = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        with ZipFile(ROOT/'app/download_dir/system_files/носки_по каждому размеру.xlsx') as book:
            data = ET.fromstring(book.read('xl/worksheets/sheet1.xml'))
            catalog = ET.fromstring(book.read('xl/worksheets/sheet2.xml'))
            sizes = ET.fromstring(book.read('xl/worksheets/sheet3.xml'))
        cells = lambda tree: {c.get('r'): ''.join(c.itertext()) for c in tree.findall('.//m:c', ns)}
        self.assertEqual(cells(data)['S1'], 'Детский товар')
        self.assertEqual([cells(catalog)[coord] for coord in ['D4', 'D5', 'G2', 'G3']], ['month', 'years', 'Да', 'Нет'])
        validations = {v.get('sqref'): v.findtext('m:formula1', namespaces=ns) for v in data.findall('.//m:dataValidation', ns)}
        self.assertEqual(validations['S7:S1045'], 'Справочники!$G$2:$G$3')
        self.assertEqual(validations['I7:I1045'], 'Справочники!$D$2:$D$5')
        self.assertEqual([cells(sizes)[f'I{row}'] for row in range(116, 125)],
                         ['0-3', '3-6', '6-9', '1,5', '2-3', '4-5', '6-7', '8-9', '10-12'])

    def test_export_regulation_per_position_and_046_size_conversion(self):
        tree = ast.parse((ROOT/'app/config.py').read_text())
        settings_node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Settings')
        socks = next(n for n in settings_node.body if isinstance(n, ast.ClassDef) and n.name == 'Socks')
        constants = {n.target.id: ast.literal_eval(n.value) for n in socks.body if isinstance(n, ast.AnnAssign)
                     and n.target.id in {'NUMBER_STANDART', 'CHILDREN_NUMBER_STANDART'}}
        self.settings.Socks.__dict__.update(constants, TYPES_CODES={'НОСКИ': 'socks'})
        self.settings.COUNTRIES_INNER = ('РОССИЯ',)
        self.settings.COUNTRIES_CODES = {'РОССИЯ': 'RU'}
        orders = NS(placeholder_export_value=lambda value, field: value, eatp=lambda value, field_type: value,
                    normalize_length_width_size_type_for_export=lambda value: value,
                    normalize_length_width_size_for_export=lambda value, kind: value,
                    normalize_export_content=lambda value: value)
        ns = dict(datetime=datetime, settings=self.settings, OrdersProcessor=orders,
                  SocksProcessor=NS(get_gender_dec=lambda **kw: 'унисекс', get_gender=lambda **kw: 'Унисекс',
                                    get_gender_046=lambda **kw: 'Унисекс'),
                  socks_size_for_export=socks_size_for_export, resolve_clothes_category_code=lambda value: 'test')
        export = load_node('app/utilities/download.py', 'prepare_ext_data', ns, 'SocksProcessor')
        items = [NS(is_children=child, tnved_code='6115950000', trademark='Бренд', article='A1',
                    type='НОСКИ', gender='Унисекс', color='БЕЛЫЙ', content='Хлопок', box_quantity=2,
                    article_price=0, tax=0, country='РОССИЯ', rd_type=None, rd_name=None, rd_date=None,
                    sizes_quantities=[NS(size=size, size_type=kind, quantity=3)])
                 for child, size, kind in [(False, '25', 'РОССИЯ'), (True, '1,5', 'years')]]
        rows, outer, inner = export(items)
        self.assertEqual([len(row) for row in rows], [23, 23])
        self.assertIn('017/2011', rows[0][13])
        self.assertIn('007/2011', rows[1][13])
        self.assertEqual(rows[1][9:11], ['years', '1,5'])
        self.assertEqual([row[18] for row in rows], [6, 6])
        self.assertEqual(inner, rows)
        self.assertEqual(outer, [])
        rows, _, _ = export(items, flag_046=True)
        self.assertEqual(rows[1][12:14], ['<1764000037> МЕЖДУНАРОДНЫЙ', '12'])
        self.assertNotIn(None, rows[1][12:14])


if __name__ == '__main__':
    unittest.main()
