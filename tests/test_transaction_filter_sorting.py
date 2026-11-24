"""Keep the displayed sort order in pagination links and partial-approval refreshes."""
import ast
import dataclasses
from datetime import datetime, timedelta
from enum import Enum
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from urllib.parse import parse_qs, urlencode, urlsplit

from flask import Flask, request
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import Boolean, Column, DateTime, Integer, String, asc, desc, or_
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql.elements import UnaryExpression

ROOT = Path(__file__).resolve().parents[1]
Base = declarative_base()


class UserTransaction(Base):
    __tablename__ = 'user_transactions'
    id = Column(Integer, primary_key=True)
    sa_id = Column(Integer)
    status = Column(Integer)
    type = Column(Boolean)
    transaction_type = Column(String)
    amount = Column(Integer)
    created_at = Column(DateTime)
    bill_time = Column(DateTime)


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    admin_parent_id = Column(Integer)


class TransactionTypes(Enum):
    agent_withdrawal = 'agent_withdrawal'
    refill_balance = 'refill_balance'
    order_payment = 'order_payment'


class RefreshURL(HTMLParser):
    url = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id') == 'transactions_table_info':
            self.url = attrs.get('data-refresh-url')


def load_actual_filters():
    tree = ast.parse((ROOT / 'app/utilities/support.py').read_text())
    nodes = [node for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef))
             and node.name in ('TransactionFilters', 'helper_get_filters_transactions')]
    namespace = dict(__name__=__name__, dataclasses=dataclasses, datetime=datetime, timedelta=timedelta,
                     UnaryExpression=UnaryExpression, UserTransaction=UserTransaction, User=User,
                     TransactionTypes=TransactionTypes, request=request, asc=asc, desc=desc, or_=or_,
                     settings=NS(Transactions=NS(DEFAULT_DAYS_RANGE=10, TRANSACTIONS={0:'cancelled',1:'pending',2:'success'})))
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<actual transaction filters>', 'exec'), namespace)
    return namespace['helper_get_filters_transactions'], namespace['TransactionFilters']


class TransactionFilterSortingTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.load, filters_class = load_actual_filters()
        self.date_modes = ['created_at', 'bill_time'] if 'date_mode' in filters_class.__dataclass_fields__ else [None]
        env = Environment(loader=FileSystemLoader(ROOT / 'app/templates'), autoescape=select_autoescape())
        env.globals.update(url_for=lambda *args, **kwargs:'/admin_control/su_bck_control_ut')
        self.table = env.get_template('admin/transactions/su_transactions_table.html')
        self.params = dict(tr_status='1', transaction_type='agent_withdrawal', operation_type='0',
                           amount='50000', service_account='9', date_from='01.11.2026', date_to='23.11.2026',
                           agent_id='42', page='3')

    def assert_order(self, filters, direction, date_mode=None):
        expected_column = 'bill_time' if date_mode == 'bill_time' else 'created_at'
        self.assertEqual(str(filters.model_order_type), f'user_transactions.{expected_column} {direction}')

    def test_partial_approval_refresh_keeps_direction_page_and_all_filters(self):
        for sort_type, direction in [('0','DESC'), ('1','ASC')]:
            for date_mode in self.date_modes:
                params = {**self.params, 'sort_type':sort_type}
                if date_mode:
                    params['date_mode'] = date_mode
                with self.subTest(sort=sort_type, date_mode=date_mode):
                    with self.app.test_request_context('/?' + urlencode(params)):
                        filters = self.load()
                        self.assert_order(filters, direction, date_mode)
                        markup = self.table.render(transaction_filters=filters, transactions_list=[], transaction_summ=0,
                                                   pagination=NS(links='', total=95), page=3, offset=60,
                                                   operation_types={0:'Списание'}, transaction_types={'agent_withdrawal':'Вывод'},
                                                   transaction_statuses={1:'Ожидает'})
                        parser = RefreshURL()
                        parser.feed(markup)
                        self.assertIsNotNone(parser.url)
                        query = parse_qs(urlsplit(parser.url).query)
                        for key, value in params.items():
                            self.assertEqual(query[key], [value], key)
                    with self.app.test_request_context(parser.url):
                        refreshed = self.load()
                        self.assert_order(refreshed, direction, date_mode)
                        self.assertEqual([str(clause.compile(compile_kwargs={'literal_binds':True})) for clause in refreshed.model_conditions],
                                         [str(clause.compile(compile_kwargs={'literal_binds':True})) for clause in filters.model_conditions])
                        self.assertEqual(refreshed.date_from, filters.date_from)
                        self.assertEqual(refreshed.date_to, filters.date_to)

    def test_pagination_urls_keep_direction(self):
        for sort_type, direction in [('0','DESC'), ('1','ASC')]:
            with self.subTest(sort=sort_type):
                with self.app.test_request_context('/?' + urlencode({**self.params,'sort_type':sort_type})):
                    filters = self.load()
                    page_url = '/admin_control/su_bck_control_ut?bck=1' + filters.link_filters + 'page=4'
                with self.app.test_request_context(page_url):
                    self.assert_order(self.load(), direction)
                    self.assertEqual(request.args['page'], '4')

    def test_excel_post_and_default_order_remain_unchanged(self):
        for sort_type, direction in [('0','DESC'), ('1','ASC')]:
            with self.app.test_request_context('/', method='POST', data={**self.params,'sort_type':sort_type}):
                filters = self.load(report=True)
                self.assert_order(filters, direction)
                self.assertEqual(parse_qs(filters.link_filters.lstrip('&'))['sort_type'], [sort_type])
        with self.app.test_request_context('/?' + urlencode(self.params)):
            self.assert_order(self.load(), 'DESC')


if __name__ == '__main__':
    unittest.main()
