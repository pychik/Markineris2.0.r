"""Exercise reanimation SQL in a disposable PostgreSQL cluster, never the app DB.

Run: python -m unittest discover -s tests -p test_reanimate.py
PostgreSQL server binaries are required for the SQL fixture tests.
"""
import ast
from datetime import datetime
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock

from flask import Flask, request
from sqlalchemy import asc, create_engine, desc, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
USERS = NS(DEFAULT_DAYS_RANGE=30, FILTER_MAX_QUANTITY=30,
           FILTER_DATE_DAYS='Дней', FILTER_DATE_HOURS='Часов', FILTER_DATE_MONTH='Месяцев',
           FILTER_DATE_TYPES=('Часов', 'Дней', 'Месяцев'), FILTER_DATE_DICT={'Дней': 'Дней'})
SETTINGS = NS(Users=USERS, ORD_USER='ordinary_user', PAGINATION_PER_PAGE=50,
              Prices=NS(BASIC_PRICES=[]), REANIMATE_CALL_RESULT={}, REG_SURVEY_STATS_FROM=datetime(2026, 1, 21))


def load_function(path, name, namespace):
    tree = ast.parse((ROOT / path).read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace[name]


def filter_function():
    return load_function('app/utilities/support.py', 'helper_get_filter_users',
                         dict(settings=SETTINGS, request=request))


class FilterAndLoadingTests(unittest.TestCase):
    def test_get_and_excel_share_normalized_filters(self):
        app = Flask(__name__)
        get_filters = filter_function()
        for quantity, expected in [('', 30), ('bad', 30), ('0', 1), ('999', 30), ('12', 12)]:
            with self.subTest(quantity=quantity):
                params = dict(date_quantity=quantity, date_type='Дней', sort_type=0)
                with app.test_request_context('/', query_string=params):
                    shown = get_filters()
                with app.test_request_context('/', method='POST', data=params):
                    exported = get_filters(excel_report=True)
                self.assertEqual(shown, exported)
                self.assertEqual(shown[0], expected)
                self.assertIn('sort_type=0', shown[2])

    def test_initial_shell_does_not_query_client_statistics(self):
        app = Flask(__name__)
        price = NS(id=1, price_code='basic', price_at2=0, created_at=None, query=Mock())
        render = Mock(return_value='shell')
        query_users = Mock(side_effect=AssertionError('Client statistics queried before AJAX'))
        handler = load_function('app/utilities/admin/h_admin_control.py', 'h_bck_reanimate', dict(
            settings=SETTINGS, helper_get_filter_users=filter_function(), request=request,
            url_for=lambda *a, **kw: '/reanimate', render_template=render, Price=price,
            desc=lambda x: x, helper_get_users_reanimate=query_users))
        with app.test_request_context('/'):
            self.assertEqual(handler(), 'shell')
        query_users.assert_not_called()
        self.assertEqual(render.call_args.args[0], 'admin/ra/main_reanimate.html')
        self.assertEqual(render.call_args.kwargs['date_type'], 'Дней')


class CallResultValidationTests(unittest.TestCase):
    def setUp(self):
        from flask import jsonify
        from sqlalchemy.exc import NoResultFound
        self.app = Flask(__name__)
        self.session = Mock()
        self.rec = NS(id=10, user_id=7, updated_at=datetime(2026, 11, 25, 10, 59))
        self.session.execute.return_value.scalar_one.return_value = self.rec
        self.render = Mock(return_value='updated call form')
        get_payload = load_function('app/utilities/admin/helpers.py', 'helper_get_reanimate_call_result', dict(request=request))
        settings = NS(REANIMATE_CALL_RESULT={'недозвон': '#FF9999', 'перезвон': '#FFFF99', 'успех': '#99FF99'})
        self.handler = load_function('app/utilities/admin/h_admin_control.py', 'h_bck_save_call_result', dict(
            helper_get_reanimate_call_result=get_payload, settings=settings, jsonify=jsonify,
            select=Mock(), ReanimateStatus=NS(user_id=Mock()), db=NS(session=self.session),
            datetime=NS(now=lambda: datetime(2026, 11, 25, 10, 59)),
            render_template=self.render, NoResultFound=NoResultFound))

    def test_invalid_results_rejected_before_database_access(self):
        for value in [None, 'unknown', 'Успех', ' успех ', [], {}, 1, False, '<script>']:
            with self.subTest(value=value), self.app.test_request_context('/', method='POST', json={
                    'user_id': 7, 'comment': 'Test', 'call_result': value}):
                response, status = self.handler()
                self.assertEqual(status, 400)
                self.assertEqual(response.get_json()['status'], 'danger')
                self.session.execute.assert_not_called()
                self.session.commit.assert_not_called()

    def test_missing_result_and_invalid_json_shape_rejected(self):
        for payload in [{}, [], ['успех'], 'успех']:
            with self.subTest(payload=payload), self.app.test_request_context('/', method='POST', json=payload):
                response, status = self.handler()
                self.assertEqual(status, 400)
                self.session.execute.assert_not_called()

    def test_all_configured_results_and_explicit_reset_allowed(self):
        for result in ['недозвон', 'перезвон', 'успех', '']:
            with self.subTest(result=result), self.app.test_request_context('/', method='POST', json={
                    'user_id': 7, 'comment': 'Test', 'call_result': result}):
                response = self.handler()
                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.rec.call_result, result)
                self.assertEqual(self.rec.last_call_update, '25.11.2026 10:59')
        self.assertEqual(self.session.commit.call_count, 4)


class ReanimateSQLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        candidates = sorted(Path('/usr/lib/postgresql').glob('*/bin/initdb'), reverse=True)
        initdb = shutil.which('initdb') or (str(candidates[0]) if candidates else None)
        if not initdb or os.geteuid() == 0:
            raise unittest.SkipTest('PostgreSQL binaries and an unprivileged user are required')
        cls.temp = tempfile.TemporaryDirectory(prefix='reanimate-test-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.data = str(Path(cls.temp.name) / 'data')
        cls.pg_ctl = str(Path(initdb).with_name('pg_ctl'))
        subprocess.run([initdb, '-D', cls.data, '-A', 'trust', '--no-locale', '-E', 'UTF8'],
                       check=True, capture_output=True)
        subprocess.run([cls.pg_ctl, '-D', cls.data, '-l', str(Path(cls.temp.name) / 'pg.log'),
                        '-o', f"-F -k {cls.temp.name} -p 55479 -c listen_addresses=''", '-w', 'start'],
                       check=True, capture_output=True)
        cls.addClassCleanup(lambda: subprocess.run(
            [cls.pg_ctl, '-D', cls.data, '-m', 'immediate', '-w', 'stop'], capture_output=True, check=True))
        cls.engine = create_engine(URL.create('postgresql+psycopg2', username=os.environ.get('USER'),
                                              database='postgres', query={'host': cls.temp.name, 'port': '55479'}))
        cls.addClassCleanup(cls.engine.dispose)
        price_columns = ', '.join(f'price_{i} NUMERIC' for i in range(1, 12))
        with cls.engine.begin() as c:
            for ddl in [
                'CREATE TABLE users (id INT PRIMARY KEY, login_name TEXT, phone TEXT, balance INT, email TEXT, role TEXT, status BOOLEAN, admin_parent_id INT, price_id INT, client_code TEXT, created_at TIMESTAMP)',
                f'CREATE TABLE prices (id INT, price_code TEXT, {price_columns}, price_at2 NUMERIC)',
                'CREATE TABLE orders_stats (user_id INT, marks_count INT, rows_count INT, op_cost NUMERIC, saved_at TIMESTAMP, created_at TIMESTAMP, transaction_id INT)',
                'CREATE TABLE user_transactions (id INT, user_id INT, amount INT, status INT, type BOOLEAN, transaction_type TEXT, created_at TIMESTAMP)',
                'CREATE TABLE users_partners (user_id INT, partner_code_id INT)',
                'CREATE TABLE partner_codes (id INT, code TEXT)',
                'CREATE TABLE reanimate_status (user_id INT, comment TEXT, call_result TEXT, updated_at TIMESTAMP)',
                'CREATE TABLE user_registration_surveys (user_id INT, source TEXT, created_at TIMESTAMP, user_agent TEXT, ip TEXT)',
            ]:
                c.execute(text(ddl))

    def setUp(self):
        self.session = Session(self.engine)
        self.addCleanup(self.session.close)
        self.addCleanup(self.session.rollback)
        for id_, name, parent, role in [(1, 'Beta', 10, 'ordinary_user'), (2, 'Alpha', 11, 'ordinary_user'),
                                        (3, 'Recent', 10, 'ordinary_user'), (10, 'Agent', None, 'admin')]:
            self.session.execute(text("INSERT INTO users (id, login_name, admin_parent_id, role) VALUES (:id, :name, :parent, :role)"),
                                 dict(id=id_, name=name, parent=parent, role=role))
        self.session.execute(text("""INSERT INTO orders_stats VALUES
            (1, 100, 2, 999, CURRENT_DATE - INTERVAL '60 days', CURRENT_DATE - INTERVAL '65 days', 101),
            (1, 200, 3, NULL, CURRENT_DATE - INTERVAL '50 days', CURRENT_DATE - INTERVAL '55 days', 101),
            (3, 10, 1, 5, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 102)"""))
        for id_, uid, amount, status, direction, kind in [
            (101, 1, 1001, 2, False, 'order_payment'),  # One payment covers two orders.
            (102, 1, 5000, 0, False, 'order_payment'),
            (103, 1, 5000, 1, False, 'order_payment'),
            (104, 1, 2000, 2, True, 'refill_balance'),
            (105, 1, 300, 2, True, 'promo'),
            (106, 1, 900, 2, True, 'refund_funds'),
            (107, 10, 700, 2, False, 'users_order_payment'),  # Agent balance, not client's.
            (108, 1, 400, 2, False, 'buy_marka_coins'),
            (109, 1, 600, 2, False, 'promo'),
            (110, 1, 600, 2, False, 'refill_balance'),
        ]:
            self.session.execute(text('INSERT INTO user_transactions VALUES (:id, :uid, :amount, :status, :direction, :kind, CURRENT_TIMESTAMP)'),
                                 dict(id=id_, uid=uid, amount=amount, status=status, direction=direction, kind=kind))
        types = NS(**{v: NS(value=v) for v in ['refill_balance', 'promo', 'order_payment', 'users_order_payment']})
        self.query = load_function('app/utilities/admin/helpers.py', 'helper_get_users_reanimate', dict(
            settings=SETTINGS, db=NS(session=self.session), asc=asc, desc=desc, text=text,
            TransactionTypes=types, TransactionStatuses=NS(success=NS(value=2))))

    def test_transactions_are_counted_once_without_cutoff_or_cancelled_payments(self):
        rows = self.query(30, 'Дней', 1)
        self.assertEqual([r.login_name for r in rows], ['Alpha', 'Beta'])
        beta = rows[1]
        self.assertEqual(beta.orders_count, 2)
        self.assertEqual(beta.total_marks_count, 300)
        self.assertEqual(beta.total_rows_count, 5)
        self.assertEqual(beta.total_write_off, 1001)
        self.assertEqual(beta.total_refill, 2000)
        self.assertEqual(beta.total_promo_used, 300)
        self.assertEqual(beta.avg_check, 501)
        self.assertEqual(rows[0].avg_check, 0)

    def test_agent_scope_and_descending_login(self):
        self.assertEqual([r.login_name for r in self.query(30, 'Дней', 0)], ['Beta', 'Alpha'])
        self.assertEqual([r.id for r in self.query(30, 'Дней', 1, u_id=10)], [1])

    def test_filter_units_and_zero_history(self):
        for unit in ['Часов', 'Дней', 'Месяцев']:
            rows = self.query(1, unit, 1)
            self.assertNotIn(3, [r.id for r in rows])
            alpha = next(r for r in rows if r.id == 2)
            self.assertEqual((alpha.orders_count, alpha.total_refill, alpha.total_write_off), (0, 0, 0))


if __name__ == '__main__':
    unittest.main()
