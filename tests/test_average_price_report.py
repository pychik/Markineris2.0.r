"""Check the finance formula, date boundaries and all-period AJAX/Excel data."""
import importlib.util
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from flask import Flask
from jinja2 import ChoiceLoader, DictLoader, FileSystemLoader
from openpyxl import load_workbook
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('average_price_report', ROOT / 'app/utilities/admin/average_price_report.py')
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


class AveragePriceReportTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine('sqlite://')
        self.addCleanup(engine.dispose)
        connection = engine.connect()
        self.addCleanup(connection.close)
        connection.execute(text("ATTACH DATABASE ':memory:' AS public"))
        connection.execute(text('CREATE TABLE public.user_transactions (id INTEGER, created_at TIMESTAMP, amount INTEGER, op_cost NUMERIC, type BOOLEAN)'))
        connection.execute(text('CREATE TABLE public.orders_stats (id INTEGER PRIMARY KEY, transaction_id INTEGER, marks_count INTEGER)'))
        self.session = Session(bind=connection)
        self.addCleanup(self.session.close)
        self.filters = report.parse_filters(dict(date_from='01.11.2026', date_to='30.11.2026'))
        self.app = Flask(__name__)
        self.app.jinja_loader = ChoiceLoader([
            DictLoader({'main/base_v2.html': '{% block admin_panel %}{% endblock %}'}),
            FileSystemLoader(ROOT / 'app/templates'),
        ])
        self.app.add_url_rule('/report', view_func=report.average_price_report)
        self.app.add_url_rule('/admin', endpoint='admin_control.index', view_func=lambda: '')
        self.app.add_url_rule('/finance', endpoint='admin_control.su_control_finance', view_func=lambda: '')
        models_patch = patch.dict(sys.modules, models=SimpleNamespace(db=SimpleNamespace(session=self.session)))
        models_patch.start()
        self.addCleanup(models_patch.stop)

    def transaction(self, identifier, day, amount, marks, op_cost=1, refill=False):
        self.session.execute(text('INSERT INTO public.user_transactions VALUES (:id, :day, :amount, :cost, :type)'),
                             dict(id=identifier, day=day, amount=amount, cost=op_cost, type=refill))
        for count in marks:
            self.session.execute(text('INSERT INTO public.orders_stats (transaction_id, marks_count) VALUES (:id, :count)'), dict(id=identifier, count=count))

    def test_weighted_price_does_not_duplicate_amount_for_multi_order_payment(self):
        self.transaction(1, '2026-11-01 00:00:00', 300, [100, 50])
        self.transaction(2, '2026-11-01 13:00:00', 100, [10])
        self.transaction(3, '2026-11-30 23:59:59', 70, [10])
        self.transaction(4, '2026-10-31 23:59:59', 999, [1])
        self.transaction(5, '2026-12-01 00:00:00', 999, [1])
        self.transaction(6, '2026-11-01 01:00:00', 999, [1], refill=True)
        self.transaction(7, '2026-11-01 01:00:00', 999, [1], op_cost=None)
        self.transaction(8, '2026-11-01 01:00:00', 999, [])
        rows = report.load_daily_prices(self.session, self.filters)
        self.assertEqual([(r['day'], r['average_price']) for r in rows if r['average_price'] is not None],
                         [(date(2026, 11, 1), Decimal('2.50')), (date(2026, 11, 30), Decimal('7.00'))])

        self.assertEqual((rows[0]['marks'], rows[0]['amount']), (160, Decimal('400')))
        self.assertEqual((rows[-1]['marks'], rows[-1]['amount']), (10, Decimal('70')))
        self.assertEqual((rows[1]['marks'], rows[1]['amount']), (0, Decimal('0')))

    def test_zero_marks_and_rounding(self):
        self.transaction(1, '2026-11-01 00:00:00', 10, [0])
        self.transaction(2, '2026-11-02 00:00:00', 1, [8])
        rows = report.load_daily_prices(self.session, self.filters)
        self.assertEqual([r['average_price'] for r in rows[:2]], [Decimal('0.00'), Decimal('0.13')])

    def test_sort_pagination_chart_and_export_cover_full_period(self):
        start = date(2026, 10, 1)
        for index in range(40):
            self.transaction(index, f'{start + timedelta(days=index)} 12:00:00', index + 1, [1])
        client = self.app.test_client()
        params = dict(date_from='01.10.2026', date_to='09.11.2026', format='json')
        response = client.get('/report', query_string=params)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data['chart']), 40)
        self.assertEqual(data['chart'][0]['date'], '01.10.2026')
        self.assertIn('09.11.2026', data['htmlresponse'])
        self.assertNotIn('<td>01.10.2026</td>', data['htmlresponse'])
        response = client.get('/report', query_string={**params, 'page': 2, 'chart': '0'})
        self.assertIsNone(response.json['chart'])
        self.assertIn('<td>01.10.2026</td>', response.json['htmlresponse'])
        response = client.get('/report', query_string={**params, 'sort': 'asc'})
        self.assertLess(response.json['htmlresponse'].index('<td>01.10.2026</td>'), response.json['htmlresponse'].index('<td>02.10.2026</td>'))
        response = client.get('/report', query_string={**params, 'format': 'xlsx', 'page': 2})
        from io import BytesIO
        book = load_workbook(BytesIO(response.data))
        self.assertEqual(book.active.max_row, 41)
        self.assertEqual(book.active['A2'].value.date(), date(2026, 11, 9))
        self.assertEqual(book.active['B2'].value, 40)
        self.assertEqual(book.active['C2'].value, 1)
        self.assertEqual(book.active['D2'].value, 40)
        self.assertEqual(book.active.auto_filter.ref, 'A1:D41')
        self.assertEqual(book.active['A41'].value.date(), start)

    def test_missing_days_are_retained_in_table_chart_and_excel(self):
        self.transaction(1, '2026-11-02 12:00:00', 20, [10])
        params = dict(date_from='01.11.2026', date_to='03.11.2026', format='json', sort='asc')
        response = self.app.test_client().get('/report', query_string=params)
        self.assertEqual([point['price'] for point in response.json['chart']], [None, 2, None])
        self.assertEqual([point['marks'] for point in response.json['chart']], [0, 10, 0])
        self.assertIn('Количество марок', response.json['htmlresponse'])
        self.assertIn('Всего списано, руб.', response.json['htmlresponse'])
        self.assertIn('Итого за выбранный период</th><td>10</td><td>20.00</td>', response.json['htmlresponse'])
        for day in ('01.11.2026', '02.11.2026', '03.11.2026'):
            self.assertIn(f'<td>{day}</td>', response.json['htmlresponse'])
        from io import BytesIO
        response = self.app.test_client().get('/report', query_string={**params, 'format': 'xlsx'})
        sheet = load_workbook(BytesIO(response.data)).active
        self.assertEqual(sheet.max_row, 4)
        self.assertIsNone(sheet['B2'].value)
        self.assertEqual(sheet['B3'].value, 2)
        self.assertIsNone(sheet['B4'].value)
        self.assertEqual(sheet['C2'].value, 0)
        self.assertEqual(sheet['D2'].value, 0)
        self.assertEqual(sheet['C3'].value, 10)
        self.assertEqual(sheet['D3'].value, 20)

    def test_twelve_month_limit_including_leap_day(self):
        for start, end in [('01.11.2025', '01.11.2026'), ('29.02.2024', '28.02.2025')]:
            report.parse_filters(dict(date_from=start, date_to=end))
        client = self.app.test_client()
        for fmt in ('json', 'xlsx'):
            response = client.get('/report', query_string=dict(date_from='01.11.2025', date_to='02.11.2026', format=fmt))
            self.assertEqual(response.status_code, 400)
            self.assertIn('12 месяцев', response.json['message'])

    def test_initial_page_renders_filters_chart_and_export(self):
        response = self.app.test_client().get('/report?date_from=01.11.2026&date_to=30.11.2026')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        for value in ('01.11.2026', '30.11.2026', 'price_chart', 'price_export', 'average_price_report.js'):
            self.assertIn(value, html)

    def test_empty_data_and_invalid_dates(self):
        client = self.app.test_client()
        response = client.get('/report?format=json')
        self.assertTrue(all(point['price'] is None for point in response.json['chart']))
        self.assertIn('—', response.json['htmlresponse'])
        for params in (dict(date_from='31.02.2026'), dict(date_from='30.11.2026', date_to='01.11.2026')):
            for fmt in ('json', 'xlsx'):
                response = client.get('/report', query_string={**params, 'format': fmt})
                self.assertEqual(response.status_code, 400)
                self.assertTrue(response.json['message'])


if __name__ == '__main__':
    unittest.main()
