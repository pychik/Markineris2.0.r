"""Run the report SQL against fixture tables, including lifetime-first selection."""
import importlib.util
import re
from dataclasses import replace
from datetime import date, datetime
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from flask import Flask
from jinja2 import Environment, FileSystemLoader, select_autoescape
from openpyxl import load_workbook
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('first_order_report', ROOT / 'app/utilities/admin/first_order_report.py')
report = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = report
spec.loader.exec_module(report)


class FirstOrderReportTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine('sqlite://')
        self.connection = engine.connect()
        self.addCleanup(engine.dispose)
        self.addCleanup(self.connection.close)
        self.connection.execute(text("ATTACH DATABASE ':memory:' AS public"))
        for ddl in (
            'CREATE TABLE public.users (id INTEGER PRIMARY KEY, login_name TEXT, created_at TIMESTAMP, email TEXT, phone TEXT, admin_parent_id INTEGER, role TEXT, balance INTEGER)',
            'CREATE TABLE public.orders_stats (id INTEGER PRIMARY KEY, user_id INTEGER, created_at TIMESTAMP, crm_created_at TIMESTAMP)',
        ):
            self.connection.execute(text(ddl))
        users = [
            (1, 'October registration', '2026-10-03', 'ordinary_user', 100),
            (2, 'Already ordered', '2026-09-01', 'ordinary_user', 100),
            (3, 'Last day', '2026-11-01', 'ordinary_user', None),
            (4, 'No orders', '2026-11-01', 'ordinary_user', None),
            (5, 'Draft in October', '2026-10-20', 'ordinary_user', None),
            (6, 'Legacy date', '2026-10-20', 'ordinary_user', None),
            (7, 'Staff', '2026-10-01', 'manager', None),
            (8, 'December first', '2026-10-01', 'ordinary_user', None),
            (100, 'Agent Alpha', '2026-01-01', 'admin', None),
        ]
        for user_id, login, registered, role, agent in users:
            self.connection.execute(text('INSERT INTO public.users VALUES (:id, :login, :registered, :email, :phone, :agent, :role, :balance)'),
                                    dict(id=user_id, login=login, registered=registered + ' 00:00:00',
                                         email=f'user{user_id}@example.com', phone='+79991234567', agent=agent, role=role, balance=-150 if user_id == 1 else 400))
        orders = [
            (1, '2026-10-31 23:00:00', '2026-11-01 00:00:00'),
            (1, '2026-11-02 12:00:00', '2026-11-02 12:01:00'),
            (1, '2026-12-01 00:00:00', '2026-12-01 00:00:00'),
            (2, '2026-10-01 00:00:00', '2026-10-01 00:00:00'),
            (2, '2026-11-10 00:00:00', '2026-11-10 00:00:00'),
            (3, '2026-11-30 23:59:59', '2026-11-30 23:59:59'),
            (5, '2026-10-25 00:00:00', '2026-11-15 00:00:00'),
            (6, '2026-11-15 00:00:00', None),
            (7, '2026-11-15 00:00:00', '2026-11-15 00:00:00'),
            (8, '2026-11-15 00:00:00', '2026-12-01 00:00:00'),
        ]
        for index, (user_id, created, submitted) in enumerate(orders, 1):
            self.connection.execute(text('INSERT INTO public.orders_stats VALUES (:id, :user_id, :created, :submitted)'),
                                    dict(id=index, user_id=user_id, created=created, submitted=submitted))
        self.session = Session(bind=self.connection)
        self.addCleanup(self.session.close)
        self.params = report.parse_report_params(dict(date_from='2026-11-01', date_to='2026-11-30'))

    def load(self, params=None, **kwargs):
        return report.load_report(self.session, params or self.params, 'ordinary_user', **kwargs)

    def test_first_order_is_lifetime_first_and_registration_is_not_filtered(self):
        rows, totals, _, _ = self.load()
        self.assertEqual([r['user_id'] for r in rows], [3, 5, 6, 1])
        self.assertEqual(dict(totals), dict(users_count=4, orders_count=5))
        october = next(row for row in rows if row['user_id'] == 1)
        self.assertTrue(october['registered_at'].startswith('2026-10'))
        self.assertTrue(october['first_order_at'].startswith('2026-11-01'))
        self.assertEqual(october['orders_count'], 2)
        self.assertEqual(october['balance'], -150)
        self.assertEqual(october['agent_name'], 'Agent Alpha')
        self.assertIsNone(october['source'])

    def test_sorting_precedes_pagination_and_totals_cover_all_pages(self):
        params = report.parse_report_params(dict(date_from='2026-11-01', date_to='2026-11-30',
                                                sort='registered_at', direction='asc', page='2'), per_page=2)
        rows, totals, effective, pages = self.load(params)
        self.assertEqual([r['user_id'] for r in rows], [6, 3])
        self.assertEqual((totals['users_count'], effective.page, pages), (4, 2, 2))
        all_rows, _, _, _ = self.load(params, paginate=False)
        self.assertEqual([r['user_id'] for r in all_rows], [1, 5, 6, 3])

    def test_empty_report_and_page_clamping(self):
        params = report.parse_report_params(dict(date_from='2027-01-01', date_to='2027-01-31', page='999'))
        rows, totals, effective, pages = self.load(params)
        self.assertEqual((rows, totals['users_count'], totals['orders_count'], effective.page, pages), ([], 0, 0, 1, 1))

    def test_localized_datetime_range_includes_the_final_minute(self):
        params = report.parse_report_params(dict(date_from='30.11.2026 23:59', date_to='30.11.2026 23:59'))
        rows, totals, _, _ = self.load(params)
        self.assertEqual([row['user_id'] for row in rows], [3])
        self.assertEqual(totals['orders_count'], 1)
        self.assertEqual(params.sql_params('ordinary_user')['date_to'], datetime(2026, 12, 1))
        self.assertEqual(params.query_args()['date_from'], '30.11.2026 23:59')
        earlier = report.parse_report_params(dict(date_from='30.11.2026 00:00', date_to='30.11.2026 23:58'))
        self.assertEqual(self.load(earlier)[1]['users_count'], 0)

    def test_defaults_are_full_days_and_invalid_times_are_rejected(self):
        params = report.parse_report_params({}, today=date(2026, 11, 4))
        self.assertEqual(params.date_from, datetime(2026, 11, 1))
        self.assertEqual(params.date_to, datetime(2026, 11, 4, 23, 59))
        for value in ['31.11.2026 10:00', '04.11.2026 24:00', '04.11.2026 10:60']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                report.parse_report_params(dict(date_to=value))

    def test_month_shortcuts_disable_future_months_and_cap_current_month(self):
        months = report.month_shortcuts(date(2026, 11, 4))
        self.assertEqual(len(months), 12)
        self.assertEqual(months[9]['date_from'], '01.10.2026 00:00')
        self.assertEqual(months[9]['date_to'], '31.10.2026 23:59')
        self.assertEqual(months[10]['date_to'], '04.11.2026 23:59')
        self.assertFalse(months[10]['disabled'])
        self.assertTrue(months[11]['disabled'])

    def test_month_shortcuts_handle_leap_year_and_new_year(self):
        self.assertEqual(report.month_shortcuts(date(2024, 3, 1))[1]['date_to'], '29.02.2024 23:59')
        january = report.month_shortcuts(date(2027, 1, 1))
        self.assertEqual(january[0]['date_from'], '01.01.2027 00:00')
        self.assertEqual(january[0]['date_to'], '01.01.2027 23:59')
        self.assertEqual(sum(not month['disabled'] for month in january), 1)

    def test_invalid_filters_and_sort_injection_are_rejected(self):
        for args in [dict(date_from='bad'), dict(date_from='2026-11-30', date_to='2026-11-01'),
                     dict(sort='u.id; DROP TABLE users'), dict(direction='desc; SELECT 1'),
                     dict(page='0'), dict(page='abc'), dict(date_to='9999-12-31')]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                report.parse_report_params(args, today=date(2026, 11, 4))

    def test_excel_has_real_dates_agent_and_safe_text(self):
        row = dict(balance=-1500, user_id=9876, login_name='=1+1', registered_at=datetime(2026, 10, 3),
                   first_order_at=datetime(2026, 11, 1), source='telegram', email='a@example.com',
                   phone='+79991234567', agent_name='Agent Alpha', orders_count=2)
        workbook = load_workbook(report.report_excel([row, dict(row, user_id=1234)], self.params, {'telegram': 'Telegram'}))
        self.addCleanup(workbook.close)
        sheet = workbook.active
        self.assertEqual(sheet.title, 'Отчёт первичного заказа')
        self.assertEqual(sheet['A4'].value, '№')
        self.assertEqual(sheet['A5'].value, 1)
        self.assertEqual(sheet['A6'].value, 2)
        self.assertEqual(sheet['B5'].data_type, 's')
        self.assertEqual(sheet['C5'].value, -1500)
        self.assertEqual(sheet['C5'].data_type, 'n')
        self.assertEqual(sheet['D5'].value, datetime(2026, 10, 3))
        self.assertEqual(sheet['E5'].value, datetime(2026, 11, 1))
        self.assertEqual(sheet['F5'].value, 'Telegram')
        self.assertEqual(sheet['I5'].value, 'Agent Alpha')
        self.assertEqual(sheet['J5'].value, 2)

    def test_table_renders_sort_links_and_escapes_user_data(self):
        env = Environment(loader=FileSystemLoader(ROOT / 'app/templates'), autoescape=select_autoescape())
        env.globals['url_for'] = lambda endpoint, **args: '/' + endpoint + '?' + str(args)
        row = dict(balance=-1500, user_id=1, login_name='<script>bad</script>', registered_at=datetime(2026, 10, 3),
                   first_order_at=datetime(2026, 11, 1), source=None, email='a@example.com',
                   phone='+79991234567', agent_name=None, orders_count=2)
        html = env.get_template('admin/first_order_report/table.html').render(
            rows=[row], totals=dict(users_count=1, orders_count=2), params=self.params, pages=1, source_labels={})
        self.assertIn('aria-sort="descending"', html)
        self.assertIn('data-first-order-nav', html)
        self.assertIn('Без агента', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<script>', html)

    def test_ajax_errors_are_400_without_running_query(self):
        app = Flask(__name__)
        settings = SimpleNamespace(PAGINATION_PER_PAGE=50)
        with patch.dict(sys.modules, {'config': SimpleNamespace(settings=settings),
                                     'models': SimpleNamespace(RegistrationSourceEnum=object, db=None)}):
            with app.test_request_context('/?bck=1&date_from=invalid'):
                response, status = report.first_order_report()
                self.assertEqual(status, 400)
                self.assertEqual(response.get_json()['status'], 'error')

    def test_pagination_has_ends_gaps_and_continuous_row_numbers(self):
        env = Environment(loader=FileSystemLoader(ROOT / 'app/templates'), autoescape=select_autoescape())
        env.globals['url_for'] = lambda endpoint, **args: '/' + endpoint + '?' + str(args)
        row = dict(balance=-1500, user_id=9876, login_name='Test', registered_at=datetime(2026, 10, 3),
                   first_order_at=datetime(2026, 11, 1), source=None, email='', phone='', agent_name=None, orders_count=2)
        params = replace(self.params, per_page=2, page=6)
        template = env.get_template('admin/first_order_report/table.html')
        html = template.render(rows=[row, dict(row, user_id=1234)], totals=dict(users_count=40, orders_count=80),
                               params=params, pages=20, source_labels={})
        self.assertEqual(re.findall(r'data-first-order-page="(\d+)"', html), ['1', '4', '5', '6', '7', '8', '20'])
        self.assertEqual(html.count('<li><span>…</span></li>'), 2)
        self.assertIn('<td>11</td>', html)
        self.assertIn('<td>12</td>', html)
        self.assertIn('<b>11 - 12</b>', html)
        self.assertIn('first-order-pagination', html)
        self.assertNotIn('9876', html)
        empty = template.render(rows=[], totals=dict(users_count=0, orders_count=0), params=self.params, pages=1, source_labels={})
        self.assertNotIn('data-first-order-page=', empty)
        self.assertIn('<b>0 - 0</b>', empty)


if __name__ == '__main__':
    unittest.main()
