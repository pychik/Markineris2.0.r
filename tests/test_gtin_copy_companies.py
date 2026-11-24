"""Copy guard uses the live conductor catalog and runs before creating an order."""
import ast
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]


class CopyCompanyTests(unittest.TestCase):
    def setUp(self):
        self.options = Mock(return_value=[{'value': 'g:AVRORA'}])
        self.ns = {'company_options': self.options}
        tree = ast.parse((ROOT / 'app/utilities/gtin_orders.py').read_text())
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                    and n.name == 'validate_order_copy_companies')
        exec(compile(ast.Module(body=[node], type_ignores=[]), 'gtin_orders.py', 'exec'), self.ns)
        self.validate = self.ns['validate_order_copy_companies']

    def test_current_company_allowed_and_live_catalog_respected(self):
        order = NS(is_gtin_order=True, processing_company_key='g:AVRORA')
        self.validate(order, [])
        self.options.return_value = []
        with self.assertRaisesRegex(ValueError, 'Честный ЗНАК'):
            self.validate(order, [])

    def test_retired_and_missing_order_company_blocked(self):
        for key in ['g:MIRAT', 'g:TURKIN', None, '']:
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.validate(NS(is_gtin_order=True, processing_company_key=key), [])

    def test_positions_and_sizes_checked_even_without_order_flag(self):
        for key in ['g:MIRAT', 'g:TURKIN', None]:
            item = NS(gtin='04640735105562', gtin_company_key=key)
            for positions in [[item], [NS(sizes_quantities=[item])]]:
                with self.subTest(key=key, positions=positions), self.assertRaises(ValueError):
                    self.validate(NS(is_gtin_order=False), positions)
        self.validate(NS(), [NS(gtin='04640735105562', gtin_company_key='g:AVRORA')])

    def test_non_gtin_and_product_card_orders_keep_existing_behavior(self):
        self.validate(NS(), [NS(gtin=None, gtin_company_key=None)])
        self.validate(NS(is_moderation=True, is_gtin_order=True), [NS(gtin_company_key='pc:1')])

    def test_guard_failure_prevents_order_creation_and_commit(self):
        tree = ast.parse((ROOT / 'app/utilities/saving_uts.py').read_text())
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'common_save_copy_order')
        settings = NS(**{name: NS(CATEGORY=name) for name in
                        ['Shoes', 'Clothes', 'Socks', 'Linen', 'Parfum', 'Cosmetics', 'Toys']},
                      Messages=NS(ORDER_ADD_ERROR='Ошибка'))
        db, model, flash = Mock(), Mock(), Mock()
        ns = dict(self.ns, settings=settings, db=db, Order=model, flash=flash, logger=Mock())
        module = ast.parse('from __future__ import annotations')
        module.body.append(node)
        exec(compile(module, 'saving_uts.py', 'exec'), ns)
        order = NS(is_gtin_order=True, processing_company_key='g:MIRAT', shoes=[])
        self.assertIsNone(ns['common_save_copy_order'](1, NS(), 'Shoes', order))
        model.assert_not_called()
        db.session.commit.assert_not_called()
        db.session.rollback.assert_called_once()
        self.assertIn('Честный ЗНАК', flash.call_args.kwargs['message'])


if __name__ == '__main__':
    unittest.main()
