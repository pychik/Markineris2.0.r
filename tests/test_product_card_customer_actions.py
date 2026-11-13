"""Exercise card rendering and weight ownership without starting the database."""
import ast
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1]
HANDLERS = ROOT / 'app/views/main/product_cards/handlers.py'


def load_handler(name, namespace):
    tree = ast.parse(HANDLERS.read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(HANDLERS), 'exec'), namespace)
    return namespace[name]


class CustomerCardActionTests(unittest.TestCase):
    def setUp(self):
        self.settings = NS(ORD_USER='ordinary_user', ADMIN_USER='admin', SUPER_USER='superuser',
                           SUPER_MANAGER='supermanager', MANAGER_USER='manager')
        for category in ('Clothes', 'Socks', 'Shoes', 'Linen', 'Parfum', 'Cosmetics', 'Toys'):
            setattr(self.settings, category, NS(CATEGORY_PROCESS=category.lower()))
        self.settings.RD_DESCRIPTION = ''
        self.settings.RD_TYPES = []
        self.unit = NS(id=7, size='18', size_type='РОССИЯ', weight_grams=None, is_approved=True)
        self.main = NS(sizes_quantities=[self.unit], subcategory='common')
        self.card = NS(id=1, user_id=42, category='clothes', clothes=[self.main],
                       status=NS(value='approved'), data_status='approved',
                       processing_company_label='Компания', created_at=datetime(2026, 9, 13),
                       _all_moderation_units=lambda: [self.unit])
        self.query = Mock()
        for method in ('with_entities', 'filter', 'options', 'filter_by'):
            getattr(self.query, method).return_value = self.query
        self.query.first_or_404.return_value = self.card
        self.query.first.return_value = self.card
        self.model = NS(query=self.query, **{name: Mock() for name in ('id', 'category', 'user_id', 'creator', 'manager', 'clothes')})
        self.ns = dict(settings=self.settings, ProductCard=self.model,
                       ModerationStatus=NS(APPROVED=NS(value='approved'), REJECTED=NS(value='rejected')),
                       current_user=NS(id=42, role='superuser'), jsonify=lambda **kw: kw,
                       _json_error=lambda message, code: (message, code))

    def render_card(self, role, crm=False):
        env = Environment(loader=FileSystemLoader(ROOT / 'app/templates'))
        env.globals['url_for'] = lambda endpoint, **kw: '/' + endpoint
        loader = Mock()
        loader.selectinload.return_value = loader
        self.ns.update(current_user=NS(id=42, role=role),
                       joinedload=lambda *a: loader, selectinload=lambda *a: loader,
                       Clothes=NS(sizes_quantities=Mock()),
                       CATEGORIES_COMMON={'clothes': {'rel_name': 'clothes', 'title': 'Одежда'}},
                       _pc_visible_fields_for_entity=lambda *a: {},
                       card_weight_unit_label=lambda unit: unit.size,
                       MODERATION_STATUS_TITLES={'approved': 'Одобрено'},
                       get_processing_companies=lambda: [],
                       render_template=lambda template, **kw: env.get_template(template).render(**kw))
        return load_handler('h_card_view', self.ns)(1, crm_=crm)['html']

    def test_customer_roles_can_fill_weight_then_add_approved_sizes(self):
        for role in ('ordinary_user', 'admin', 'superuser'):
            with self.subTest(role=role):
                self.unit.weight_grams = None
                html = self.render_card(role)
                self.assertIn('Указать вес', html)
                self.assertNotIn('pc-apply-qty-btn', html)
                self.unit.weight_grams = 150
                html = self.render_card(role)
                self.assertIn('pc-apply-qty-btn', html)
                self.assertIn('Изменить вес', html)

    def test_crm_and_staff_views_do_not_offer_customer_actions(self):
        self.unit.weight_grams = 150
        for role, crm in (('superuser', True), ('manager', True), ('supermanager', True),
                          ('manager', False), ('markineris_admin', False)):
            with self.subTest(role=role, crm=crm):
                html = self.render_card(role, crm)
                self.assertNotIn('pc-apply-qty-btn', html)
                self.assertNotIn('pc-weight-save-btn', html)

    def test_weight_save_keeps_ownership_check_and_allows_customer_roles(self):
        self.ns.update(request=NS(get_json=lambda **kw: {'weights': {'7': '150'}}),
                       parse_unit_weight=int, set_unit_weight=lambda unit, value: setattr(unit, 'weight_grams', value),
                       _log_card_weight_changes=Mock(), db=NS(session=Mock()), SQLAlchemyError=RuntimeError)
        save = load_handler('h_card_weights', self.ns)
        for role in ('ordinary_user', 'admin', 'superuser'):
            with self.subTest(role=role):
                self.ns['current_user'].role = role
                self.assertEqual(save(1)['status'], 'success')
                self.query.filter_by.assert_called_with(id=1, user_id=42)
                self.assertEqual(self.unit.weight_grams, 150)
                self.assertTrue(self.unit.is_approved)
                self.assertEqual(self.card.status.value, 'approved')
        self.query.first.return_value = None
        self.assertEqual(save(1)[1], 404)
        for role in ('manager', 'supermanager', 'markineris_admin'):
            self.ns['current_user'].role = role
            self.assertEqual(save(1)[1], 403)


if __name__ == '__main__':
    unittest.main()
