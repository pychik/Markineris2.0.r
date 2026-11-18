"""Regression checks for draft deletion, copy IDs and checkout account locks."""
import ast
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace as NS
from typing import Optional
import unittest

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, create_engine, event, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import declarative_base, relationship, scoped_session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]


def load_function(path, name, namespace):
    node = next(node for node in ast.parse((ROOT / path).read_text()).body
                if isinstance(node, ast.FunctionDef) and node.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), path, 'exec'), namespace)
    return namespace[name]


Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    __table_args__ = {'schema': 'public'}
    id = Column(Integer, primary_key=True)
    role = Column(String, default='admin')
    login_name = Column(String, default='Agent')
    admin_parent_id = Column(Integer)
    admin_order_num = Column(Integer, default=0)
    balance = Column(Integer, default=100)
    trust_limit = Column(Integer, default=0)
    price_id = Column(Integer, default=1)
    is_at2 = Column(Boolean, default=False)
    is_crm = Column(Boolean, default=True)
    orders = relationship('Order', lazy='dynamic')


class Order(Base):
    __tablename__ = 'orders'
    __table_args__ = {'schema': 'public'}
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('public.users.id'))
    category = Column(String, default='одежда')
    company_type = Column(String, default='ИП')
    company_name = Column(String, default='Клиент')
    company_idn = Column(String, default='123456789012')
    edo_type = Column(String, default='ЭДО-ЛАЙТ')
    edo_id = Column(String, default='')
    mark_type = Column(String, default='Этикетка')
    has_aggr = Column(Boolean, default=False)
    processed = Column(Boolean, default=False)
    to_delete = Column(Boolean, default=False)
    is_moderation = Column(Boolean, default=False)
    stage = Column(Integer, default=0)
    order_idn = Column(String, unique=True)
    created_at = Column(DateTime, default=datetime.now)
    cost = Column(Integer, default=60)


class Item(Base):
    __tablename__ = 'items'
    __table_args__ = {'schema': 'public'}
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('public.orders.id', ondelete='CASCADE'))
    quantity = Column(Integer, default=2)


def settings():
    return NS(ORD_USER='ordinary_user', ADMIN_USER='admin',
              OrderStage=NS(CREATING=0, NEW=1, CANCELLED=9, TELEGRAM_PROCESSED=10, CRM_PROCESSED=11),
              Messages=NS(CLEAN_EMPTY='Нет черновика', NO_SUCH_ORDER='Нет заказа',
                          ORDER_DELETE_ERROR='Ошибка удаления', ORDER_DELETE_POS_SUCCESS='Удалено',
                          answer_refill_balance=lambda **kwargs: str(kwargs['balance'])),
              CATEGORIES_DICT={'одежда': 'clothes'},
              **{name: NS(CATEGORY='одежда' if name=='Clothes' else name.lower())
                 for name in ('Shoes', 'Clothes', 'Socks', 'Linen', 'Parfum', 'Cosmetics', 'Toys')})


class OrderRaceFixTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        with self.engine.connect() as connection:
            connection.exec_driver_sql("ATTACH DATABASE ':memory:' AS public")
        Base.metadata.create_all(self.engine)
        self.session = scoped_session(sessionmaker(bind=self.engine))
        Base.query = self.session.query_property()
        self.session.add_all([User(id=1), User(id=2, role='ordinary_user', admin_parent_id=1)])
        self.session.commit()
        self.ns = dict(User=User, Order=Order, Optional=Optional, settings=settings(), text=text,
                       db=NS(session=self.session), flash=lambda *args, **kwargs: None,
                       logger=NS(error=lambda *args: None))

    def tearDown(self):
        self.session.remove()
        self.engine.dispose()

    def balance_helper(self, cost=80):
        self.price_ids = []
        def cost_data(**kwargs):
            self.price_ids.append(kwargs['price_id'])
            return {'report_data': {'ao_price': cost, 'smc': 10},
                    'current_order': {'new_idn': False, 'op_cost': 1, 'marks_count': 10}}
        self.ns['get_cocmd'] = cost_data
        return load_function('app/utilities/support.py', 'helper_check_uoabm', self.ns)

    def test_final_check_uses_locked_live_balance_and_price_while_preview_keeps_old_behavior(self):
        self.session.execute(text('UPDATE public.users SET balance=50, price_id=7 WHERE id=1'))
        self.session.commit()
        stale = NS(id=1, role='admin', balance=100, price_id=1, is_at2=False)
        check = self.balance_helper()
        self.assertEqual(check(stale, 1)[0], 1)
        self.assertEqual(check(stale, 1, lock=True)[0], 0)
        self.assertEqual(self.price_ids, [1, 7])

    def test_locked_check_preserves_at2_balance_trust_limit_and_client_price(self):
        parent = self.session.get(User, 1)
        parent.is_at2, parent.balance, parent.trust_limit = True, 50, 50
        client = self.session.get(User, 2)
        client.balance, client.price_id = 0, 9
        self.session.commit()
        check = self.balance_helper()
        self.assertEqual(check(client, 1), check(client, 1, lock=True))
        self.assertEqual(check(client, 1, lock=True)[:3], (1, 80, True))
        self.assertEqual(self.price_ids, [9, 9, 9])

    def test_checkout_locks_accounts_in_id_order_without_committing_and_preview_does_not_lock(self):
        statements, commits = [], []
        def record(state):
            if state.is_select:
                statements.append(str(state.statement.compile(dialect=postgresql.dialect(),
                                                               compile_kwargs={'literal_binds': True})))
        event.listen(self.session(), 'do_orm_execute', record)
        event.listen(self.session(), 'after_commit', lambda session: commits.append(True))
        check = self.balance_helper()
        client = NS(id=2, role='ordinary_user', admin_parent_id=1, balance=100, price_id=1)
        check(client, 1)
        self.assertTrue(all('FOR NO KEY UPDATE' not in sql for sql in statements))
        statements.clear()
        check(client, 1, lock=True)
        self.assertEqual(len(statements), 1)
        self.assertIn('ORDER BY public.users.id', statements[0])
        self.assertIn('FOR NO KEY UPDATE', statements[0])
        self.assertEqual(commits, [])

    def test_number_reservation_can_share_checkout_transaction_and_legacy_default_is_preserved(self):
        reserve = load_function('app/utilities/support.py', 'process_admin_order_num', self.ns)
        user = NS(id=1, role='admin')
        self.assertEqual(reserve(user), (1, '1_1', True, False))
        self.assertEqual(reserve(user, commit=False), (2, '1_2', True, False))
        self.session.rollback()
        self.assertEqual(self.session.execute(text('SELECT admin_order_num FROM public.users WHERE id=1')).scalar(), 1)

    def test_copy_returns_its_own_id_when_another_copy_commits_before_return(self):
        user = self.session.get(User, 1)
        source = NS(company_type='ИП', company_name='Исходная', company_idn='123456789012',
                    edo_type='ЭДО-ЛАЙТ', edo_id='', mark_type='Этикетка', category='одежда', has_aggr=False,
                    aggr_orders=[], clothes=[NS(weight_grams=100, trademark='Бренд', type='Куртка')])
        other_ids = []
        def commit_then_other_copy():
            self.session.commit()
            other = Order(user_id=1, company_name='Другая копия')
            self.session.add(other)
            self.session.commit()
            other_ids.append(other.id)
        context = dict(self.ns, normalize_mark_type_full=lambda value, **kwargs: value,
                       trademark_matches_product_type=lambda *args: False,
                       save_copy_order_clothes=lambda **kwargs: kwargs['new_order'],
                       db=NS(session=NS(flush=self.session.flush, commit=commit_then_other_copy,
                                        rollback=self.session.rollback)))
        copy_order = load_function('app/utilities/saving_uts.py', 'common_save_copy_order', context)
        copied_id = copy_order(1, user, 'одежда', source)
        self.assertIsNotNone(copied_id)
        self.assertNotEqual(copied_id, other_ids[0])
        self.assertEqual(self.session.get(Order, copied_id).company_name, 'Исходная')

    def test_position_and_whole_draft_deletion_recheck_stage_under_parent_lock(self):
        user = self.session.get(User, 1)
        order = Order(user_id=1, stage=1)
        self.session.add(order)
        self.session.flush()
        self.session.add(Item(order_id=order.id))
        self.session.commit()
        self.ns.update(current_user=user,
                       get_delete_pos_stmts=lambda **kwargs: f"DELETE FROM public.items WHERE order_id={kwargs['o_id']}")
        queries = []
        def record(state):
            if state.is_select:
                queries.append(str(state.statement.compile(dialect=postgresql.dialect())))
        event.listen(self.session(), 'do_orm_execute', record)
        delete_position = load_function('app/utilities/support.py', 'process_delete_order_pos', self.ns)
        delete_order = load_function('app/utilities/support.py', 'common_process_delete_order', self.ns)
        self.assertEqual(delete_position('одежда', order.id, 1), 'Нет черновика')
        self.assertEqual(delete_order(order.id, 0), 'Нет черновика')
        self.assertGreaterEqual(sum('FOR UPDATE OF orders' in query for query in queries), 2)
        self.assertEqual(self.session.query(Item).filter(Item.order_id == order.id).count(), 1)
        self.assertIsNotNone(self.session.get(Order, order.id))


if __name__ == '__main__':
    unittest.main()
