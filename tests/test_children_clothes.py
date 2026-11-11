"""Check clothing export and card updates without database or app services."""
import ast
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_function(path, name, namespace, class_name=None):
    tree = ast.parse((ROOT / path).read_text())
    nodes = tree.body
    if class_name:
        nodes = next(n for n in nodes if isinstance(n, ast.ClassDef) and n.name == class_name).body
    node = next(n for n in nodes if isinstance(n, ast.FunctionDef) and n.name == name)
    node.decorator_list = []
    exec(compile(ast.Module(body=[node], type_ignores=[]), path, 'exec'), namespace)
    return namespace[name]


class ChildrenClothesTests(unittest.TestCase):
    def test_mixed_export_uses_regulation_per_position_without_extra_columns(self):
        config = ast.parse((ROOT / 'app/config.py').read_text())
        settings_class = next(n for n in config.body if isinstance(n, ast.ClassDef) and n.name == 'Settings')
        clothes_config = next(n for n in settings_class.body if isinstance(n, ast.ClassDef) and n.name == 'Clothes')
        constants = {n.target.id: ast.literal_eval(n.value) for n in clothes_config.body
                     if isinstance(n, ast.AnnAssign) and n.target.id in ('NUMBER_STANDART', 'CHILDREN_NUMBER_STANDART')}
        processor = NS(placeholder_export_value=lambda value, field: value,
                       eatp=lambda value, field_type: value,
                       normalize_length_width_size_type_for_export=lambda value: value,
                       normalize_length_width_size_for_export=lambda value, kind: value,
                       normalize_export_content=lambda value: value)
        ns = dict(datetime=datetime, settings=NS(Clothes=NS(**constants, TYPES_CODES={'КУРТКА': '1'}, SYZE_TYPES_CODES={'РОССИЯ': '1'}),
                                          COUNTRIES_INNER=('РОССИЯ',), COUNTRIES_CODES={'РОССИЯ': 'RU'}),
                  OrdersProcessor=processor, resolve_clothes_category_code=lambda code: 'test',
                  ClothesProcessor=NS(get_gender_dec=lambda **kwargs: 'женская', get_gender=lambda gender: gender,
                                      get_gender_046=lambda gender: gender))
        export = load_function('app/utilities/download.py', 'prepare_ext_data', ns, 'ClothesProcessor')
        items = [NS(is_children=child, tnved_code='6201900000', trademark='Тест', article='A1',
                    type='КУРТКА', gender='Жен.', subcategory='common', color='ЧЕРНЫЙ', content='ХЛОПОК',
                    box_quantity=1, article_price=100, tax=20, country='РОССИЯ',
                    rd_type=None, rd_name=None, rd_date=None,
                    sizes_quantities=[NS(size='42', size_type='РОССИЯ', quantity=2)]) for child in (False, True)]
        rows, outer, inner = export(items)
        self.assertEqual([len(row) for row in rows], [23, 23])
        self.assertEqual([row[13] for row in rows], [constants['NUMBER_STANDART'], constants['CHILDREN_NUMBER_STANDART']])
        self.assertIn('017/2011', rows[0][13])
        self.assertIn('007/2011', rows[1][13])
        self.assertEqual(inner, rows)
        self.assertEqual(outer, [])
        rows_046, _, _ = export(items, flag_046=True)
        self.assertEqual([len(row) for row in rows_046], [31, 31])
        self.assertEqual(rows_046[0], rows_046[1])
        self.assertEqual(rows_046[0][29], 2)

    def test_card_checkbox_can_be_enabled_and_disabled_when_missing_from_form(self):
        entity = NS(is_children=False)
        ns = dict(ProductCard=object, get_card_entity_for_prefill=lambda card: entity,
                  CARD_FIELDS={'clothes': {'is_children': 'Детская одежда'}},
                  FROZEN_FIELDS={'default': set(), 'single_unit': set()},
                  settings=NS(**{name: NS(CATEGORY_PROCESS=name.lower()) for name in ('Parfum', 'Cosmetics', 'Toys')}))
        update = load_function('app/views/main/product_cards/support.py', 'update_card_allowed_fields', ns)
        changes = load_function('app/views/main/product_cards/support.py', 'get_card_allowed_field_changes', ns)
        card = NS(category='clothes')
        for form, expected in [({'is_children': 'yes'}, True), ({}, False), ({}, False)]:
            with self.subTest(form=form, before=entity.is_children):
                self.assertEqual(changes(card, form), ['Детская одежда'] if entity.is_children != expected else [])
                update(card, form, form)
                self.assertIs(entity.is_children, expected)

    def test_adult_and_children_positions_have_different_merge_keys(self):
        categories = NS(**{name: NS(CATEGORY=name.lower()) for name in ('Shoes', 'Clothes', 'Socks')})
        ns = dict(Any=object, settings=categories, normalize_placeholder_value=lambda value, *args: value,
                  normalize_key_value=lambda value: value, normalize_float_key=lambda value: value,
                  normalize_int_key=lambda value: value, NO_TRADEMARK_PLACEHOLDERS=(), NO_TRADEMARK_VALUE='',
                  NO_ARTICLE_PLACEHOLDERS=(), NO_ARTICLE_VALUE='')
        key = load_function('app/utilities/saving_helpers.py', 'build_position_key', ns)
        item = NS(trademark='Тест', article='A1', tnved_code='6201900000', country='РОССИЯ',
                  rd_type=None, rd_name=None, rd_date=None, article_price=100, tax=20,
                  type='КУРТКА', color='ЧЕРНЫЙ', gender='Жен.', content='ХЛОПОК', subcategory='common')
        adult_key = key(item, 'clothes')
        item.is_children = True
        self.assertNotEqual(adult_key, key(item, 'clothes'))
        item.is_children = False
        self.assertEqual(adult_key, key(item, 'clothes'))


if __name__ == '__main__':
    unittest.main()
