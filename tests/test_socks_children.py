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
    CHILDREN_AGE_SIZES, CHILDREN_INTERNATIONAL, FOOT_LENGTH_SIZE_TYPE, FOOT_LENGTH_SIZES,
    normalize_socks_size, parse_socks_children, socks_size_for_export, validate_socks_age,
    validate_socks_sizes,
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
            CHILDREN_AGE_SIZES=CHILDREN_AGE_SIZES, validate_socks_age=validate_socks_age))

    def test_ages_keep_values_in_both_export_formats(self):
        expected = [(str(year), 'years') for year in range(1, 15)] + [
            ('0-3', 'month'), ('3-6', 'month'), ('6-9', 'month'),
            ('1-2', 'years'), ('2-3', 'years'), ('3-4', 'years'), ('1-3', 'years'),
            ('1,5', 'years'), ('4-5', 'years'), ('6-7', 'years'), ('8-9', 'years'), ('10-12', 'years')]
        for age, kind in expected:
            with self.subTest(age=age):
                self.assertEqual(self.get_type(age, kind), kind)
                validate_socks_sizes([(age, 2, kind)], True, 'Унисекс')
                exported = f'{age} years' if kind == 'years' else age
                self.assertEqual(socks_size_for_export(age, kind), (exported, 'МЕЖДУНАРОДНЫЙ'))
                self.assertEqual(socks_size_for_export(age, kind, True), (exported, 'МЕЖДУНАРОДНЫЙ'))
        self.assertEqual(normalize_socks_size('1.5', 'years'), '1,5')
        self.assertEqual(normalize_socks_size('12.0', 'МЕЖДУНАРОДНЫЙ'), '12')
        self.assertEqual(normalize_socks_size('2-3 years', 'years'), '2-3')

    def test_new_grids_are_available_only_in_their_mode(self):
        expected = [str(n) for n in range(6, 29, 2)] + [f'{n}-{n+2}' for n in range(6, 27, 2)]
        self.assertEqual(list(CHILDREN_INTERNATIONAL), expected)
        child_grid = self.settings.Socks.SIZE_ALL_DICT['Детск.']
        for kind in ['РОССИЯ', 'МЕЖДУНАРОДНЫЙ']:
            self.assertEqual([entry[0] for entry in child_grid[kind]], expected)
            for size in expected:
                validate_socks_sizes([(size, 1, kind)], True, 'Без указания пола')
                self.assertTrue(parse_socks_children('', '', kind, size))
                with self.assertRaises(SizeTypeException):
                    validate_socks_sizes([(size, 1, kind)], False, 'Без указания пола')
        self.assertEqual(list(FOOT_LENGTH_SIZES), [f'{n}-{n+2}' for n in range(6, 32)])
        for gender in ['Жен.', 'Муж.', 'Унисекс', 'Без указания пола']:
            self.assertEqual([entry[0] for entry in self.settings.Socks.SIZE_ALL_DICT[gender][FOOT_LENGTH_SIZE_TYPE]],
                             list(FOOT_LENGTH_SIZES))
        self.assertNotIn(FOOT_LENGTH_SIZE_TYPE, child_grid)
        for size in FOOT_LENGTH_SIZES:
            self.assertFalse(parse_socks_children('', '', FOOT_LENGTH_SIZE_TYPE, size))
            validate_socks_sizes([(size, 1, FOOT_LENGTH_SIZE_TYPE)], False, 'Унисекс')
            with self.assertRaises(SizeTypeException):
                validate_socks_sizes([(size, 1, FOOT_LENGTH_SIZE_TYPE)], True, 'Без указания пола')
        for size in ['5-7', '32-34', '6-9', '23', '23-25 см']:
            with self.assertRaises(SizeTypeException):
                validate_socks_sizes([(size, 1, FOOT_LENGTH_SIZE_TYPE)], False, 'Унисекс')

    def test_server_rejects_mixed_grids_and_unknown_ages(self):
        for size, kind, child, gender in [
            ('0-3', 'month', False, 'Жен.'), ('1,5', 'years', False, 'Унисекс'),
            ('12', 'МЕЖДУНАРОДНЫЙ', False, 'Муж.'), ('12', 'РОССИЯ', False, 'Муж.'),
            ('XL', 'МЕЖДУНАРОДНЫЙ', True, 'Муж.'), ('25', 'РОССИЯ', True, 'Унисекс'),
            ('0-3', 'years', True, 'Детск.'), ('2-3', 'month', True, 'Детск.'),
            ('25', 'РОССИЯ', False, 'Детск.'),
            ('15', 'years', True, 'Без указания пола'), ('4-6', 'years', True, 'Без указания пола'),
            ('30', 'МЕЖДУНАРОДНЫЙ', True, 'Без указания пола'),
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
        self.assertFalse(parse_socks_children('', 'Без указания пола', 'МЕЖДУНАРОДНЫЙ', 'ONE SIZE'))
        self.assertTrue(parse_socks_children('Да', 'Без указания пола', 'МЕЖДУНАРОДНЫЙ', 'ONE SIZE'))
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
            ('14 years', 'МЕЖДУНАРОДНЫЙ', 'years', '14'), ('1-3 years', '', 'years', '1-3'),
            ('0-3', 'МЕЖДУНАРОДНЫЙ', 'month', '0-3'), ('3-6', '', 'month', '3-6'),
            ('31-33', 'длина стопы', 'ДЛИНА СТОПЫ', '31-33'),
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

    def test_saved_position_validator_checks_sizes_and_country(self):
        country_error = ''
        ns = dict(validate_socks_sizes=validate_socks_sizes, SizeTypeException=SizeTypeException,
                  _check_country_by_rd=lambda item: country_error)
        load_node('app/utilities/helpers/helpers_checks.py', '_append_err', ns)
        check = load_node('app/utilities/helpers/helpers_checks.py', '_check_socks_compatibility', ns)
        item = NS(is_children=False, gender='Унисекс',
                  sizes_quantities=[NS(size='31-33', size_type=FOOT_LENGTH_SIZE_TYPE, quantity=1)])
        self.assertFalse(check(item))
        item.is_children = True
        self.assertIn('только для взрослых', check(item))
        country_error = 'Ошибка страны'
        self.assertTrue(check(item).startswith('Ошибка страны; '))
        item.sizes_quantities = [NS(size='2-3', size_type='years', quantity=1)]
        self.assertEqual(check(item), country_error)
        country_error = ''
        self.assertFalse(check(item))

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
        self.settings.Socks.__dict__.update(TYPES=['НОСКИ'], GENDERS=['Унисекс', 'Детск.', 'Без указания пола'],
                                            MAX_QUANTITY=100000, MIN_QUANTITY=1)
        self.settings.Clothes = NS(UPLOAD_STANDART_ROW=7)
        self.settings.ORDER_LIMIT_ARTICLES = 1600
        self.settings.Messages = NS(UPLOAD_EMPTY_FILE_ERROR='empty')
        self.settings.RZ_GENDERS_RD_LIST = ['Унисекс', 'Детск.', 'Без указания пола']
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
                for kind, size, flag in [('years', '1.5', 'Да'), ('МЕЖДУНАРОДНЫЙ', '6', ''),
                                          ('РОССИЯ', '25', 'Нет'), ('РОССИЯ', '28', ''),
                                          ('МЕЖДУНАРОДНЫЙ', '1-3 years', ''),
                                          ('МЕЖДУНАРОДНЫЙ', '0-3', ''),
                                          ('ДЛИНА СТОПЫ', '6-8', ''),
                                          ('МЕЖДУНАРОДНЫЙ', 'ONE SIZE', 'Да'),
                                          ('МЕЖДУНАРОДНЫЙ', 'ONE SIZE', '')]]
        validated, errors = upload.ValidateStandart().full_validate_standart(rows)
        self.assertEqual(errors, [])
        modes = [True, True, False, True, True, True, False, True, False]
        self.assertEqual([row[14] for row in validated], ['yes' if child else 'no' for child in modes])
        self.assertEqual(validated[0][5:7], ['years', '1,5'])
        self.assertEqual(validated[4][5:7], ['years', '1-3'])
        self.assertEqual(validated[5][5:7], ['month', '0-3'])
        self.assertEqual([row[4] for row in validated], ['Без указания пола' if child else 'Унисекс' for child in modes])
        self.settings.Socks.CATEGORY = 'socks'
        ns.update(Socks=lambda **kw: NS(sizes_quantities=[], **kw), SocksQuantitySize=lambda **kw: NS(**kw),
                  append_or_merge_position=lambda items, item, *args: items.append(item))
        save = load_node('app/utilities/upload_order/upload_saving_uts.py', 'upload_socks_st', ns)
        for row in validated:
            row.append(100)
        order = NS(socks=[])
        save(validated, order)
        self.assertEqual([item.is_children for item in order.socks], modes)
        self.assertEqual([item.weight_grams for item in order.socks], [100] * len(modes))
        self.assertEqual(order.socks[0].sizes_quantities[0].size, '1,5')
        for kind, size, flag in [('ДЛИНА СТОПЫ', '6-8', 'Да'), ('ДЛИНА СТОПЫ', '32-34', ''),
                                 ('РОССИЯ', '28', 'Нет'), ('years', '15', '')]:
            with self.subTest(kind=kind, size=size, flag=flag):
                invalid = [['Бренд', 'A1', 'НОСКИ', 'БЕЛЫЙ', 'Унисекс', kind, size,
                            'Хлопок', '6115950000', '2', 'РОССИЯ', '', '', '', flag]]
                _, errors = upload.ValidateStandart().full_validate_standart(invalid)
                self.assertTrue(errors)

    def test_workbook_flag_dropdown_types_and_age_reference(self):
        from contextlib import closing
        from openpyxl import load_workbook
        from openpyxl.formula.translate import Translator

        ns = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        path = ROOT/'app/download_dir/system_files/носки_по каждому размеру.xlsx'
        with ZipFile(path) as book:
            data = ET.fromstring(book.read('xl/worksheets/sheet1.xml'))
        validations = {v.get('sqref'): v.findtext('m:formula1', namespaces=ns) for v in data.findall('.//m:dataValidation', ns)}
        self.assertEqual(validations['S7:S1045'], 'Справочники!$G$2:$G$3')
        self.assertEqual(validations['I7:I1045'], 'Справочники!$D$2:$D$6')
        with closing(load_workbook(path, read_only=True)) as book:
            data, catalog, reference = book.worksheets[:3]
            self.assertEqual(data['S1'].value, 'Детский товар')
            self.assertEqual([catalog[coord].value for coord in ['D4', 'D5', 'G2', 'G3']],
                             ['month', 'years', 'Да', 'Нет'])
            self.assertEqual(catalog['D6'].value, FOOT_LENGTH_SIZE_TYPE)
            entries = list(reference.iter_rows(min_row=2, min_col=7, max_col=10, values_only=True))
            for kind, values in [('РОССИЯ', CHILDREN_INTERNATIONAL), ('МЕЖДУНАРОДНЫЙ', CHILDREN_INTERNATIONAL),
                                 *CHILDREN_AGE_SIZES.items()]:
                actual = [size for mode, entry_kind, size, _ in entries
                          if mode == 'Детский' and entry_kind == kind and size != 'ONE SIZE']
                self.assertEqual(actual, list(values))
            self.assertEqual([size for _, kind, size, _ in entries if kind == FOOT_LENGTH_SIZE_TYPE],
                             list(FOOT_LENGTH_SIZES))
            self.assertEqual([mode for mode, _, size, _ in entries if size == 'ONE SIZE'],
                             ['Детский', 'Взрослый — любой пол'])
            for name, expected in [('SocksChildNumeric', CHILDREN_INTERNATIONAL),
                                   ('SocksChildMonths', CHILDREN_AGE_SIZES['month'])]:
                sheet, coords = next(book.defined_names[name].destinations)
                self.assertEqual([row[0].value for row in book[sheet][coords]], list(expected))
            first_formula = data['B7'].value
            self.assertEqual(data['B1045'].value,
                             Translator(first_formula, origin='B7').translate_formula('B1045'))
            self.assertTrue(all(row[0].data_type == 'f' for row in data.iter_rows(
                min_row=7, max_row=1045, min_col=2, max_col=2)))
            self.assertTrue(all(row[0].number_format == '@' for row in data.iter_rows(
                min_row=7, max_row=1045, min_col=10, max_col=10)))

    def test_export_regulation_per_position_and_046_preserves_age(self):
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
        self.assertEqual(rows[1][9:11], ['МЕЖДУНАРОДНЫЙ', '1,5 years'])
        self.assertIn('НОСКИ детские', rows[1][2])
        self.assertEqual([row[18] for row in rows], [6, 6])
        self.assertEqual(inner, rows)
        self.assertEqual(outer, [])
        rows, _, _ = export(items, flag_046=True)
        self.assertEqual(rows[1][12:14], ['<1764000037> МЕЖДУНАРОДНЫЙ', '1,5 years'])
        self.assertTrue(rows[1][4].endswith('р. 1,5 years'))
        self.assertNotIn(None, rows[1][12:14])
        for kind, size, child, expected_type, expected_size in [
            ('years', '2-3', True, 'МЕЖДУНАРОДНЫЙ', '2-3 years'),
            ('month', '0-3', True, 'МЕЖДУНАРОДНЫЙ', '0-3'),
            ('МЕЖДУНАРОДНЫЙ', '28', True, 'МЕЖДУНАРОДНЫЙ', '28'),
            ('РОССИЯ', '26-28', True, 'РОССИЯ', '26-28'),
            ('ДЛИНА СТОПЫ', '31-33', False, 'ДЛИНА СТОПЫ', '31-33'),
        ]:
            with self.subTest(kind=kind, size=size):
                item = copy(items[1])
                item.is_children, item.gender = child, 'Без указания пола'
                item.sizes_quantities = [NS(size=size, size_type=kind, quantity=1)]
                rows, _, _ = export([item])
                self.assertEqual(rows[0][9:11], [expected_type, expected_size])
                self.assertEqual('детские' in rows[0][2], child)
                self.assertTrue(rows[0][2].endswith(f'р. {expected_size}'))
                self.assertNotIn('None', rows[0][2])


if __name__ == '__main__':
    unittest.main()
