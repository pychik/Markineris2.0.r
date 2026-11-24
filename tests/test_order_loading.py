"""Count SQL queries for ordinary-order loading on an isolated SQLite database."""
import ast
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, create_engine, event
from sqlalchemy.orm import declarative_base, lazyload, relationship, selectinload, sessionmaker

ROOT = Path(__file__).resolve().parents[1]


def load_function(name, namespace):
    tree = ast.parse((ROOT / 'app/utilities/support.py').read_text())
    node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), 'support.py', 'exec'), namespace)
    return namespace[name]


Base = declarative_base()


class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)
    category = Column(String, default='одежда')
    user_id = Column(Integer, default=1)
    stage = Column(Integer, default=0)
    is_moderation = Column(Boolean, default=True)
    processed = Column(Boolean, default=False)
    to_delete = Column(Boolean, default=False)
    clothes = relationship('Clothes', back_populates='order', lazy='joined')
    cosmetics = relationship('Cosmetics', lazy='joined')


class Clothes(Base):
    __tablename__ = 'clothes'
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'))
    order = relationship(Order, back_populates='clothes')
    sizes_quantities = relationship('Size', back_populates='clothes', lazy='joined')


class Cosmetics(Base):
    __tablename__ = 'cosmetics'
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'))


class Size(Base):
    __tablename__ = 'sizes'
    id = Column(Integer, primary_key=True)
    cl_id = Column(Integer, ForeignKey('clothes.id'))
    clothes = relationship(Clothes, back_populates='sizes_quantities')
    quantity = Column(Integer)


class OrderLoadingTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()
        self.namespace = dict(Order=Order, settings=NS(CATEGORIES_DICT={'одежда': 'clothes'}),
                              lazyload=lazyload, selectinload=selectinload)
        self.options = load_function('category_order_load_options', self.namespace)

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def fixture(self, count):
        order = Order(clothes=[Clothes(sizes_quantities=[Size(quantity=2)]) for _ in range(count)])
        self.session.add(order)
        self.session.commit()
        self.session.expunge_all()

    def read(self, optimized):
        statements = []
        def record(_conn, _cursor, statement, *_args):
            if statement.lstrip().upper().startswith('SELECT'):
                statements.append(statement)
        event.listen(self.engine, 'before_cursor_execute', record)
        try:
            query = self.session.query(Order)
            if optimized:
                query = query.options(*self.options('одежда'))
            order = query.first()
            sizes = [size for position in order.clothes for size in position.sizes_quantities]
            linked_sizes = []
            result = sum(size.quantity for size in sizes), len(linked_sizes)
        finally:
            event.remove(self.engine, 'before_cursor_execute', record)
            self.session.expunge_all()
        return result, statements

    def test_loading_category_has_bounded_query_count_and_same_values(self):
        self.fixture(30)
        baseline, old_queries = self.read(False)
        optimized, queries = self.read(True)
        self.assertEqual(optimized, baseline)
        self.assertEqual(optimized, (60, 0))
        self.assertEqual(len(old_queries), 1)
        self.assertEqual(len(queries), 3)
        self.assertTrue(all('cosmetics' not in statement for statement in queries))

    def test_small_order_uses_the_same_three_queries(self):
        self.fixture(2)
        result, queries = self.read(True)
        self.assertEqual(result, (4, 0))
        self.assertEqual(len(queries), 3)

    def test_pc_checkout_loads_only_its_category_and_reuses_positions(self):
        self.fixture(30)
        Order.query = self.session.query(Order)
        ns = dict(self.namespace, current_user=NS(id=1),
                  category_order_load_options=self.options,
                  _get_pc_order_header=lambda *args, **kwargs: NS(category='одежда'))
        ns['settings'] = NS(CATEGORIES_DICT={'одежда': 'clothes'}, OrderStage=NS(CREATING=0))
        tree = ast.parse((ROOT / 'app/views/main/product_cards/handlers.py').read_text())
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_get_pc_order_for_process')
        exec(compile(ast.Module(body=[node], type_ignores=[]), 'handlers.py', 'exec'), ns)
        statements = []
        def record(_conn, _cursor, statement, *_args):
            statements.append(statement)
        event.listen(self.engine, 'before_cursor_execute', record)
        try:
            order = ns['_get_pc_order_for_process'](1)
            self.assertEqual(sum(s.quantity for p in order.clothes for s in p.sizes_quantities), 60)
            self.assertTrue(all('cosmetics' not in sql for sql in statements))
            count = len(statements)
            # Both validators and stage assignment can read these collections without another SELECT.
            self.assertEqual(len(list(order.clothes)), 30)
            self.assertEqual(len(statements), count)
            order.stage = 1
            self.session.flush()
            self.session.expire_all()
            self.assertIsNone(ns['_get_pc_order_for_process'](1))
        finally:
            event.remove(self.engine, 'before_cursor_execute', record)

    def test_rd_check_only_reads_the_current_category(self):
        def unexpected():
            raise AssertionError('An unrelated category was loaded')
        class Draft:
            category = 'одежда'
            clothes = [NS(rd_date=None), NS(rd_date='2026-01-01')]
            cosmetics = property(lambda self: unexpected())
            shoes = property(lambda self: unexpected())
        check = load_function('order_has_user_rd', self.namespace)
        self.assertTrue(check(Draft()))
        Draft.clothes = [NS(rd_date=None)]
        self.assertFalse(check(Draft()))

    def test_stage_and_stats_reuse_one_count_without_reloading_order(self):
        counts = []
        saved = []
        order = NS(id=1, mark_type='Этикетка', category='обувь', company_idn='123', company_type='ИП',
                   company_name='Клиент', created_at=datetime.now(), manager_id=None, user_id=4, order_log='')
        settings = NS(Clothes=NS(CATEGORY='одежда'), OrderStage=NS(POOL=2, NEW=1))
        ns = dict(User=object, Order=object, Optional=__import__('typing').Optional, settings=settings,
                  get_rows_marks=lambda **kwargs: counts.append(kwargs['o_id']) or (4, 10),
                  helper_get_limits=lambda: NS(ap_rows=5, ap_marks=100),
                  current_user=NS(is_authenticated=True, login_name='user'),
                  db=NS(session=NS(add=saved.append)), OrderStat=lambda **kwargs: NS(**kwargs),
                  datetime=datetime, h_append_order_log=lambda *args: '', order_log_line=lambda *args, **kwargs: '',
                  CRM_STAGE_LABELS={2: 'Пул'}, IntegrityError=RuntimeError)
        for name in ('get_process_stage', 'create_order_stats', 'process_order_start'):
            load_function(name, ns)
        self.assertEqual(ns['process_order_start'](NS(is_at2=False), 'обувь', 1, '4_20', order=order), 2)
        self.assertEqual(counts, [1])
        self.assertEqual((saved[0].rows_count, saved[0].marks_count), (4, 10))
        self.assertEqual(order.order_idn, '4_20')


if __name__ == '__main__':
    unittest.main()
