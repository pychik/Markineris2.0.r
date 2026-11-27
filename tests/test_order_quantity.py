"""Order counts must be rejected before creation, persistence, or editing."""
import ast
import importlib.util
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from werkzeug.datastructures import MultiDict

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('order_quantity', ROOT / 'app/utilities/order_quantity.py')
quantity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(quantity)
CATEGORIES = ['clothes', 'socks', 'shoes', 'linen', 'parfum', 'cosmetics', 'toys']
INVALID = ['37.42', '37,42', '', '0', '-1', '+1', '1e2', 'NaN', ' 37 ', '٣٧', '9' * 5000]


def payload(category, value='2', kpb=False):
    fields = [('box_quantity', '1')]
    if category in ['clothes', 'socks', 'shoes']:
        fields += [('size', 'ONE SIZE'), ('quantity', value)]
        if category in ['clothes', 'socks']:
            fields += [('size_type', 'МЕЖДУНАРОДНЫЙ')]
    elif category == 'linen':
        if kpb:
            fields += [('type', 'КПБ'), ('kpb_quantity', '2'), ('linen_set_item_type', 'НАВОЛОЧКА'),
                       ('linen_set_item_sizeX', '50'), ('linen_set_item_sizeY', '70'),
                       ('linen_set_item_sizeUnit', 'см'), ('linen_set_item_quantity', value)]
        else:
            fields += [('sizeX', '50'), ('sizeY', '70'), ('sizeUnit', 'см'), ('quantity', value)]
    else:
        fields += [('quantity', value)]
    return MultiDict(fields)


def subcategories(category):
    if category not in ['clothes', 'cosmetics', 'toys']:
        return ['']
    file = ('app/utilities/categories_data/subcategories_data.py' if category == 'clothes'
            else f'app/views/main/categories/{category}/subcategories/data.py')
    cls = {'clothes': 'ClothesSubcategories', 'cosmetics': 'CosmeticsSubcategories', 'toys': 'ToysSubcategories'}[category]
    tree = ast.parse((ROOT / file).read_text())
    node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls)
    return [n.value.value for n in node.body if isinstance(n, (ast.Assign, ast.AnnAssign))
            and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)]


class OrderQuantityTests(unittest.TestCase):
    def test_invalid_counts_in_every_category(self):
        for category in CATEGORIES:
            for kpb in ([False, True] if category == 'linen' else [False]):
                for value in INVALID:
                    with self.subTest(category=category, kpb=kpb, value=value[:20]), self.assertRaises(ValueError):
                        quantity.validate_order_quantities(payload(category, value, kpb), category, is_kpb=kpb)

    def test_boundaries_and_leading_zeroes(self):
        for category in CATEGORIES:
            for value in ['1', '0002', '50000' if category == 'socks' else '100000000']:
                quantity.validate_order_quantities(payload(category, value), category)
            maximum = 50000 if category == 'socks' else 100000000
            with self.assertRaises(ValueError):
                quantity.validate_order_quantities(payload(category, str(maximum + 1)), category)
        quantity.validate_order_quantities(payload('linen', '5', True), 'linen', is_kpb=True)
        with self.assertRaises(ValueError):
            quantity.validate_order_quantities(payload('linen', '6', True), 'linen', is_kpb=True)

    def test_pack_and_kpb_counts(self):
        for category in CATEGORIES:
            form = payload(category)
            form['box_quantity'] = '37.42'
            with self.assertRaises(ValueError):
                quantity.validate_order_quantities(form, category)
        form = payload('linen', kpb=True)
        form['kpb_quantity'] = '37.42'
        with self.assertRaises(ValueError):
            quantity.validate_order_quantities(form, 'linen', is_kpb=True)

    def test_missing_misaligned_and_later_invalid_rows(self):
        for category in CATEGORIES:
            with self.assertRaises(ValueError):
                quantity.validate_order_quantities(MultiDict(), category)
        form = payload('clothes')
        form.add('size', 'L')
        form.add('size_type', 'МЕЖДУНАРОДНЫЙ')
        with self.assertRaises(ValueError):
            quantity.validate_order_quantities(form, 'clothes')
        form.add('quantity', '37.42')
        with self.assertRaises(ValueError):
            quantity.validate_order_quantities(form, 'clothes')
        form.setlist('quantity', ['2', '3'])
        quantity.validate_order_quantities(form, 'clothes')

    def test_all_subcategories_reject_before_create_add_and_edit(self):
        tree = ast.parse((ROOT / 'app/utilities/support.py').read_text())
        route = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'preprocess_order_category')
        route.returns = None
        route.decorator_list = []
        for arg in route.args.args:
            arg.annotation = None
        route.body = [n for n in route.body if not isinstance(n, ast.ImportFrom)]
        for category in CATEGORIES:
            for subcategory in subcategories(category):
                for o_id, p_id in [(None, None), (1, None), (1, 2)]:
                    with self.subTest(category=category, subcategory=subcategory, o_id=o_id, p_id=p_id):
                        flashes = []
                        settings = NS(CATEGORIES_DICT={c: c for c in CATEGORIES}, Linen=NS(CATEGORY='linen'))
                        ctx = dict(request=NS(form=payload(category, '37.42'), args={'subcategory': subcategory}, view_args={}),
                                   validate_gtin_fields=lambda *a: None, parse_size_gtins=lambda *a: None,
                                   settings=settings, Category=NS(check_subcategory=lambda **k: True),
                                   validate_order_quantities=quantity.validate_order_quantities,
                                   is_linen_kpb_type=lambda value: value == 'КПБ',
                                   jsonify=lambda **k: k, flash=lambda **k: flashes.append(k),
                                   url_for=lambda *a, **k: '/category/', redirect=lambda url: ('redirect', url))
                        exec(compile(ast.Module(body=[route], type_ignores=[]), '<route>', 'exec'), ctx)
                        result = ctx['preprocess_order_category'](o_id, p_id, category)
                        if o_id and not p_id:
                            self.assertEqual(result['status'], 'error')
                            self.assertIn('целое', result['message'])
                        else:
                            self.assertEqual(result, ('redirect', '/category/'))
                            self.assertIn('целое', flashes[0]['message'])
                        # Persistence dependencies are absent: reaching create/edit would fail.


if __name__ == '__main__':
    unittest.main()
