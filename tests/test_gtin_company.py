"""CRM company assignment: real transactions, access checks and stale modal data."""
import ast
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock

from flask import Flask, current_app, jsonify, render_template, request
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, lazyload, relationship, scoped_session, selectinload, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
Base = declarative_base()


class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)
    order_idn = Column(String, default='1_42')
    category = Column(String, default='одежда')
    is_gtin_order = Column(Boolean, default=True)
    is_moderation = Column(Boolean, default=False)
    to_delete = Column(Boolean, default=False)
    manager_id = Column(Integer, default=10)
    manager_role = Column(String, default='manager')
    user_id = Column(Integer, default=25)
    admin_parent_id = Column(Integer, default=40)
    stage = Column(Integer, default=3)
    processing_company_key = Column(String, default='g:GRENADA')
    processing_company_label = Column(String, default='Гренада')
    upd_number = Column(String, nullable=True)
    processing_info = Column(String, default='')
    clothes = relationship('Position', cascade='all,delete')


class Position(Base):
    __tablename__ = 'positions'
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'))
    gtin = Column(String)
    gtin_company_key = Column(String)
    weight_grams = Column(Integer, default=100)
    sizes_quantities = relationship('Size', cascade='all,delete')


class Size(Base):
    __tablename__ = 'sizes'
    id = Column(Integer, primary_key=True)
    position_id = Column(Integer, ForeignKey('positions.id'))
    gtin = Column(String)
    gtin_company_key = Column(String)
    quantity = Column(Integer, default=5)


def load_functions(path, names, context):
    functions = [node for node in ast.parse(path.read_text()).body
                 if isinstance(node, ast.FunctionDef) and node.name in names]
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), 'exec'), context)


class GtinCompanyTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        self.session = scoped_session(sessionmaker(bind=self.engine))
        Order.query = self.session.query_property()
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.session.remove)
        self.order = Order(clothes=[
            Position(gtin='04640735105562', gtin_company_key='g:GRENADA', sizes_quantities=[Size()]),
            Position(gtin='04640735105579', gtin_company_key='g:GRENADA', sizes_quantities=[
                Size(gtin='04640735105579', gtin_company_key='g:GRENADA')]),
        ])
        self.session.add(self.order)
        self.session.commit()
        self.user = NS(id=10, role='manager')
        self.platinum_access = Mock(return_value=True)
        settings = NS(MANAGER_USER='manager', SUPER_MANAGER='supermanager', SUPER_USER='superuser',
                      MARKINERIS_ADMIN_USER='moderator', ADMIN_USER='admin', OrderStage=NS(POOL=2),
                      CATEGORIES_DICT={'одежда': 'clothes'})
        policy = dict(User=object, settings=settings)
        load_functions(ROOT / 'app/views/crm/helpers.py', {'_can_view_order_desc'}, policy)
        def access(user, order_id):
            row = self.session.get(Order, order_id)
            return policy['_can_view_order_desc'](row, user)
        self.log = Mock()
        self.context = dict(current_user=self.user, settings=settings, Order=Order, db=NS(session=self.session),
                            lazyload=lazyload, selectinload=selectinload, request=request,
                            jsonify=jsonify, render_template=render_template, current_app=current_app,
                            _can_access_gtin_order=access, append_order_log=self.log,
                            split_processing_company_label=lambda label: ((label or '').strip(), ''),
                            company_options=lambda: [dict(value='g:GRENADA', label='Гренада'),
                                                     dict(value='g:AVRORA', label='Аврора')])
        load_functions(ROOT / 'app/views/crm/gtin_company.py', {'gtin_company_has_upd', 'reassign_gtin_company', 'h_gtin_company'}, self.context)
        self.app = Flask(__name__, template_folder=str(ROOT / 'app/templates'))
        self.app.add_url_rule('/managers/orders/<int:order_id>/gtin-company', endpoint='crm_d.gtin_company', view_func=lambda order_id: None)
        self.app.add_url_rule('/managers', endpoint='crm_d.managers', view_func=lambda: None)
        self.app.jinja_env.globals['csrf_token'] = lambda: 'csrf'
        self.app.logger.disabled = True

    def call(self, method='POST', data=None, order_id=None):
        if data is None:
            data = dict(company='g:AVRORA', expected_company='g:GRENADA')
        with self.app.test_request_context(method=method, json=data):
            result = self.context['h_gtin_company'](order_id or self.order.id)
            response, status = result if isinstance(result, tuple) else (result, 200)
            return response.get_json(), status, response.headers

    def test_assignment_updates_all_metadata_and_preserves_goods(self):
        before = [(p.id, p.gtin, p.weight_grams, [(s.id, s.gtin, s.quantity) for s in p.sizes_quantities]) for p in self.order.clothes]
        data, status, _ = self.call()
        self.assertEqual(status, 200)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(self.order.processing_company_key, 'g:AVRORA')
        self.assertEqual(self.order.processing_company_label, 'Аврора')
        self.assertIsNone(self.order.upd_number)
        self.assertEqual(self.order.processing_info, '')
        self.assertTrue(all(p.gtin_company_key == 'g:AVRORA' for p in self.order.clothes))
        self.assertIsNone(self.order.clothes[0].sizes_quantities[0].gtin_company_key)  # Legacy fallback stays valid.
        self.assertEqual(self.order.clothes[1].sizes_quantities[0].gtin_company_key, 'g:AVRORA')
        self.assertEqual(before, [(p.id, p.gtin, p.weight_grams, [(s.id, s.gtin, s.quantity) for s in p.sizes_quantities]) for p in self.order.clothes])
        self.assertIn('Гренада → Аврора', self.log.call_args.args[1])

    def test_same_company_does_not_clear_upd_or_log_a_change(self):
        self.order.upd_number = 'UPD-123'
        self.order.processing_info = 'Гренада <br> УПД: UPD-123'
        self.session.commit()
        result, status, _ = self.call(data=dict(company='g:GRENADA', expected_company='g:GRENADA'))
        self.assertEqual(status, 200)
        self.assertFalse(result['changed'])
        self.assertFalse(result['upd_reset'])
        self.assertEqual(self.order.upd_number, 'UPD-123')
        self.log.assert_not_called()

    def test_stale_modal_unknown_company_and_missing_snapshot_are_rejected(self):
        for payload, expected in [
            (dict(company='g:AVRORA', expected_company='g:OTHER'), 409),
            (dict(company='g:UNKNOWN', expected_company='g:GRENADA'), 400),
            (dict(company='', expected_company='g:GRENADA'), 400),
            (dict(company='g:AVRORA'), 409),
        ]:
            with self.subTest(payload=payload):
                self.assertEqual(self.call(data=payload)[1], expected)
                self.assertEqual(self.order.processing_company_key, 'g:GRENADA')
                self.assertIsNone(self.order.upd_number)
        self.log.assert_not_called()

    def test_only_operator_superoperator_and_superadmin_have_access(self):
        for role in ('manager', 'supermanager', 'superuser'):
            self.user.role = role
            self.assertEqual(self.call(method='GET')[1], 200)
        for role in ('moderator', 'admin', 'ordinary_user', 'm2r_admin', 'markineris_admin'):
            self.user.role = role
            for method in ('GET', 'POST'):
                with self.subTest(role=role, method=method):
                    self.assertEqual(self.call(method=method)[1], 403)
        self.assertEqual(self.order.processing_company_key, 'g:GRENADA')

    def test_other_operator_orders_and_superadmin_assignments_are_respected(self):
        self.user.id = 99
        self.assertEqual(self.call()[1], 403)
        self.order.stage = 2
        self.session.commit()
        self.assertEqual(self.call(method='GET')[1], 200)
        self.user.role = 'supermanager'
        self.order.stage = 3
        self.order.manager_role = 'superuser'
        self.session.commit()
        self.assertEqual(self.call()[1], 403)

    def test_ordinary_moderation_missing_and_deleted_orders_are_rejected(self):
        self.order.is_gtin_order = False
        self.session.commit()
        self.assertEqual(self.call()[1], 400)
        self.order.is_gtin_order = True
        self.order.is_moderation = True
        self.session.commit()
        self.assertEqual(self.call()[1], 400)
        self.order.to_delete = True
        self.session.commit()
        self.assertEqual(self.call()[1], 404)
        self.assertEqual(self.call(order_id=999)[1], 404)

    def test_failed_logging_rolls_back_the_order_positions_and_sizes(self):
        self.log.side_effect = RuntimeError('audit unavailable')
        self.assertEqual(self.call()[1], 500)
        self.assertEqual(self.order.processing_company_key, 'g:GRENADA')
        self.assertIsNone(self.order.upd_number)
        self.assertEqual(self.order.clothes[1].gtin_company_key, 'g:GRENADA')
        self.assertEqual(self.order.clothes[1].sizes_quantities[0].gtin_company_key, 'g:GRENADA')

    def test_pencil_is_only_in_operator_details(self):
        with self.app.test_request_context():
            template = self.app.jinja_env.get_template('crm_mod_v1/helpers/order_description.html')
            def render(role, src='/managers'):
                return template.render(n=self.order, current_user=NS(role=role), src=src,
                                       processing_company_title='Гренада', processing_company_inn='1234567890',
                                       url_for=lambda endpoint, **kwargs: '/managers' if endpoint == 'crm_d.managers' else '#',
                                       user_companies=[])
            for role in ('manager', 'supermanager', 'superuser', 'admin', 'moderator', 'ordinary_user'):
                with self.subTest(role=role):
                    self.assertEqual('data-gtin-company-url' in render(role), role in ('manager', 'supermanager', 'superuser'))
                    self.assertNotIn('data-gtin-company-url', render(role, '/agents'))
            self.order.upd_number = 'UPD-123'
            self.assertIn('data-gtin-company-url', render('superuser'))
            self.order.upd_number = None
            self.order.processing_info = 'Гренада <br> УПД: OLD-123'
            self.assertIn('data-gtin-company-url', render('superuser'))

    def test_company_change_resets_existing_upd_and_legacy_shipping_info(self):
        for role in ('manager', 'supermanager', 'superuser'):
            for number, info in [('UPD-123', ''), (None, 'Гренада <br> УПД: OLD-123')]:
                self.user.role = role
                self.order.processing_company_key = 'g:GRENADA'
                self.order.processing_company_label = 'Гренада'
                self.order.upd_number, self.order.processing_info = number, info
                self.session.commit()
                with self.subTest(role=role, number=number):
                    self.assertEqual(self.call(method='GET')[1], 200)
                    result, status, _ = self.call()
                    self.assertEqual(status, 200)
                    self.assertTrue(result['upd_reset'])
                    self.assertEqual(result['company_key'], 'g:AVRORA')
                    self.assertEqual(result['company_title'], 'Аврора')
                    self.assertEqual(result['upd_number'], '')
                    self.assertEqual(result['processing_info'], '')
                    self.assertIsNone(self.order.upd_number)
                    self.assertEqual(self.order.processing_info, '')
                    self.assertIn('УПД сброшен', self.log.call_args.args[1])

    def save_upd(self, company='g:GRENADA'):
        context = dict(self.context, Response=object, perf_counter=lambda: 0,
                       _processing_order_query=lambda: self.session.query(Order),
                       _can_work_with_order_user=lambda *args: True,
                       CompaniesOperators={'GRENADA': NS(as_option=lambda: ('', 'Гренада')),
                                           'AVRORA': NS(as_option=lambda: ('', 'Аврора'))},
                       _format_processing_info_rows=lambda rows: '<br>'.join(f'{label} <br> УПД: {number}' for label, number in rows),
                       _log_slow_upd_save=Mock(), logger=Mock())
        load_functions(ROOT / 'app/views/crm/helpers.py', {'helper_update_processing_order_info'}, context)
        with self.app.test_request_context(method='POST', json=dict(order_id=self.order.id, company=company, upd_number='UPD-123')):
            response, status = context['helper_update_processing_order_info']()
            return response.get_json(), status

    def test_upd_save_then_company_change_resets_the_saved_upd(self):
        self.assertEqual(self.call(method='GET')[1], 200)
        self.assertEqual(self.save_upd()[1], 200)
        self.assertEqual(self.call()[1], 200)
        self.assertIsNone(self.order.upd_number)
        self.assertEqual(self.order.processing_company_key, 'g:AVRORA')

    def test_company_change_then_stale_upd_save_is_rejected(self):
        self.assertEqual(self.call()[1], 200)
        self.assertEqual(self.save_upd()[1], 400)
        self.assertIsNone(self.order.upd_number)
        self.assertEqual(self.order.processing_company_key, 'g:AVRORA')
        self.assertEqual(self.save_upd(company='g:AVRORA')[1], 200)
        self.assertEqual(self.order.upd_number, 'UPD-123')

    def test_modal_selects_current_company_and_is_not_cached(self):
        data, status, headers = self.call(method='GET')
        self.assertEqual(status, 200)
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertIn('value="g:GRENADA" selected', data['html'])
        self.assertIn('value="g:AVRORA"', data['html'])
        self.assertIn('name="csrf_token"', data['html'])
        self.assertIn('name="expected_company" value="g:GRENADA"', data['html'])


if __name__ == '__main__':
    unittest.main()
