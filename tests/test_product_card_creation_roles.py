"""Verify the creation role gate without starting Flask or database services."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ProductCardCreationRoleTests(unittest.TestCase):
    def test_creation_allows_clients_agents_and_superuser_only(self):
        path = ROOT / 'app/views/main/product_cards/handlers.py'
        tree = ast.parse(path.read_text())
        function = next(node for node in tree.body
                        if isinstance(node, ast.FunctionDef) and node.name == 'h_save_product_card')
        # Run the real entry gate; successful requests continue to existing validation.
        gate = ast.FunctionDef(name='gate', args=function.args,
                               body=[function.body[0], ast.Return(value=ast.Constant(value='allowed'))],
                               decorator_list=[])
        ns = {'settings': SimpleNamespace(ORD_USER='ordinary_user', ADMIN_USER='admin', SUPER_USER='superuser'),
              '_json_error': lambda message, code: code}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[gate], type_ignores=[])), str(path), 'exec'), ns)
        for role in ('ordinary_user', 'admin', 'superuser', 'manager', 'supermanager', 'm2r_admin', 'admin_caller'):
            with self.subTest(role=role):
                ns['current_user'] = SimpleNamespace(role=role)
                self.assertEqual(ns['gate'](), 'allowed' if role in ('ordinary_user', 'admin', 'superuser') else 403)


if __name__ == '__main__':
    unittest.main()
