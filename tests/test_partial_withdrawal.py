"""Verify money conservation, repeated splits, validation and rollback."""
import ast
import importlib.util
from functools import wraps
from types import SimpleNamespace
from datetime import datetime
from io import StringIO
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from flask import Blueprint, Flask, jsonify, request, flash, redirect, url_for
from flask_login import LoginManager, UserMixin, current_user, login_required
from jinja2 import Environment, FileSystemLoader, select_autoescape
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, create_engine, select, event
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import declarative_base, Session

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


service = load('partial_withdrawal', 'app/utilities/admin/partial_withdrawal.py')
Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    balance = Column(Integer)


class Transaction(Base):
    __tablename__ = 'user_transactions'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    type = Column(Boolean)
    status = Column(Integer)
    transaction_type = Column(String)
    amount = Column(Integer)
    parent_transaction_id = Column(Integer, ForeignKey('user_transactions.id'))
    original_amount = Column(Integer)
    transaction_comment = Column(Text)
    promo_info = Column(String, default='')
    wo_account_info = Column(Text)
    created_at = Column(DateTime)
    bill_path = Column(String, unique=True)
    op_cost = Column(Integer, default=0)
    balance_before = Column(Integer)
    balance_after = Column(Integer)

    def change_user_balance(self, user, delta):
        self.balance_before = user.balance
        user.balance += delta
        self.balance_after = user.balance


class PartialWithdrawalTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.addCleanup(self.session.close)
        self.session.add(User(id=1, balance=100000))
        self.session.add(Transaction(id=1, user_id=1, type=False, status=1,
                                     transaction_type='agent_withdrawal', amount=50000,
                                     wo_account_info='Agent bank details', bill_path='original',
                                     created_at=datetime(2026, 11, 4, 17, 16, 14)))
        self.session.commit()

    def approve(self, amount='20000', transaction_id=1, user_id=1):
        return service.approve_partial_withdrawal(self.session, Transaction, User,
                                                 transaction_id=transaction_id, user_id=user_id,
                                                 amount=amount, actor='Moderator (ID 99)')

    def test_split_and_balance_snapshots(self):
        approved, pending = self.approve()
        self.session.commit()
        self.assertEqual((approved.amount, approved.status), (20000, 2))
        self.assertEqual((pending.amount, pending.status, pending.parent_transaction_id), (30000, 1, 1))
        self.assertEqual((approved.balance_before, approved.balance_after), (100000, 80000))
        self.assertEqual(approved.original_amount, 50000)
        self.assertEqual(pending.wo_account_info, approved.wo_account_info)
        self.assertEqual(pending.created_at, approved.created_at)
        self.assertNotEqual(pending.bill_path, approved.bill_path)
        self.assertIsNone(pending.balance_before)
        self.assertIsNone(pending.op_cost)
        self.assertIn(str(pending.id), approved.transaction_comment)
        self.assertIn('Moderator (ID 99)', approved.transaction_comment)
        self.assertIn('частично одобренной', pending.transaction_comment)

    def test_repeat_split_preserves_money_and_history(self):
        first, pending = self.approve()
        self.session.commit()
        comment = pending.transaction_comment
        second, remainder = self.approve('10000', pending.id)
        self.session.commit()
        rows = self.session.execute(select(Transaction).order_by(Transaction.id)).scalars().all()
        self.assertEqual([row.amount for row in rows], [20000, 10000, 20000])
        self.assertEqual(sum(row.amount for row in rows), 50000)
        self.assertEqual(self.session.get(User, 1).balance, 70000)
        self.assertEqual(remainder.parent_transaction_id, second.id)
        self.assertEqual(second.original_amount, 30000)
        self.assertTrue(second.transaction_comment.startswith(comment))
        self.assertTrue(remainder.transaction_comment.startswith(comment))

    def test_duplicate_or_completed_request_cannot_charge_twice(self):
        self.approve()
        self.session.commit()
        with self.assertRaises(service.PartialWithdrawalError):
            self.approve('1000')
        self.session.rollback()
        self.assertEqual(self.session.get(User, 1).balance, 80000)
        self.assertEqual(len(self.session.execute(select(Transaction)).scalars().all()), 2)

    def test_invalid_amounts_and_wrong_user(self):
        for amount in ('', '0', '-1', '50000', '50001', '1.5', '1e3', 'nan', '100000000000000000000'):
            with self.subTest(amount=amount):
                with self.assertRaises(service.PartialWithdrawalError):
                    self.approve(amount)
                self.session.rollback()
        with self.assertRaises(service.PartialWithdrawalError):
            self.approve(user_id=2)
        self.session.rollback()
        self.assertEqual(self.session.get(User, 1).balance, 100000)

    def test_only_pending_agent_withdrawals(self):
        tx = self.session.get(Transaction, 1)
        for field, value in [('transaction_type', 'withdraw_from_referral_balance'), ('transaction_type', 'order_payment'),
                             ('type', True), ('status', 0), ('status', 2), ('status', 3)]:
            with self.subTest(field=field, value=value):
                setattr(tx, field, value)
                self.session.flush()
                with self.assertRaises(service.PartialWithdrawalError):
                    self.approve()
                self.session.rollback()

    def test_insufficient_balance_and_transaction_rollback(self):
        user = self.session.get(User, 1)
        user.balance = 100
        self.session.flush()
        with self.assertRaises(service.PartialWithdrawalError):
            self.approve()
        self.session.rollback()
        self.approve()
        self.session.rollback()
        self.assertEqual(self.session.get(User, 1).balance, 100000)
        self.assertEqual((self.session.get(Transaction, 1).amount, self.session.get(Transaction, 1).status), (50000, 1))
        self.assertEqual(len(self.session.execute(select(Transaction)).scalars().all()), 1)

    def test_postgres_row_locks_are_user_first(self):
        calls = []
        real_session = self.session

        class RecordingSession:
            def execute(self, stmt):
                calls.append(str(stmt.compile(dialect=postgresql.dialect())))
                return real_session.execute(stmt)

            def add(self, obj):
                real_session.add(obj)

            def flush(self):
                real_session.flush()

        service.approve_partial_withdrawal(RecordingSession(), Transaction, User,
                                           user_id=1, transaction_id=1, amount='20000', actor='Moderator')
        self.assertIn('FOR UPDATE OF users', calls[0])
        self.assertIn('FOR UPDATE OF user_transactions', calls[1])

    def handler_app(self, notify=None):
        app = Flask(__name__)
        namespace = dict(db=SimpleNamespace(session=self.session), UserTransaction=Transaction, User=User,
                         approve_partial_withdrawal=service.approve_partial_withdrawal,
                         PartialWithdrawalError=service.PartialWithdrawalError,
                         current_user=SimpleNamespace(id=99, login_name='Moderator'),
                         request=request, jsonify=jsonify, logger=Mock(),
                         send_tg_message_with_transaction_updated_status=notify or Mock(),
                         settings=SimpleNamespace(SUCCESS='success', ERROR='error'))
        tree = ast.parse((ROOT / 'app/utilities/admin/h_finance_control.py').read_text())
        handler = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'h_su_partial_withdrawal')
        exec(compile(ast.Module(body=[handler], type_ignores=[]), '<actual partial handler>', 'exec'), namespace)
        app.add_url_rule('/partial/<int:u_id>/<int:t_id>', view_func=namespace[handler.name], methods=['POST'])
        return app

    def test_actual_handler_commits_and_does_not_report_notification_failure_as_failed_payment(self):
        app = self.handler_app(notify=Mock(side_effect=RuntimeError('Notification unavailable')))
        client = app.test_client()
        response = client.post('/partial/1/1', data={'amount':'20000'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['status'], 'success')
        self.assertIn('30000', response.json['message'])
        self.assertEqual(self.session.get(User, 1).balance, 80000)
        duplicate = client.post('/partial/1/1', data={'amount':'1000'})
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(self.session.get(User, 1).balance, 80000)

    def test_actual_handler_rolls_back_inserted_remainder_on_payment_error(self):
        client = self.handler_app().test_client()
        with patch.object(Transaction, 'change_user_balance', side_effect=RuntimeError('Payment failed')):
            response = client.post('/partial/1/1', data={'amount':'20000'})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json['status'], 'error')
        self.assertEqual(self.session.get(User, 1).balance, 100000)
        self.assertEqual(self.session.get(Transaction, 1).amount, 50000)
        self.assertEqual(self.session.get(Transaction, 1).status, 1)
        self.assertEqual(len(self.session.execute(select(Transaction)).scalars().all()), 1)

    def full_handler_app(self):
        app = Flask(__name__)
        processor = Mock(return_value=(True, ''))
        Transaction.query = self.session.query(Transaction)
        User.query = self.session.query(User)
        namespace = dict(db=SimpleNamespace(session=self.session), UserTransaction=Transaction, User=User,
                         request=request, jsonify=jsonify, select=select,
                         TransactionTypes=SimpleNamespace(agent_withdrawal=SimpleNamespace(value='agent_withdrawal')),
                         TransactionStatuses=SimpleNamespace(**{key:SimpleNamespace(value=value) for key,value in
                                                                 [('cancelled',0),('pending',1),('success',2)]}),
                         helper_update_pending_rf_transaction_status=processor,
                         helper_get_promo_on_cancel_transaction=Mock(),
                         send_tg_message_with_transaction_updated_status=Mock(),
                         settings=SimpleNamespace(SUCCESS='success', ERROR='error',
                                                  Messages=SimpleNamespace(SU_TRANSACTION_CHANGE_ERROR='Failed', SU_TRANSACTION_CHANGE='Done'),
                                                  Transactions=SimpleNamespace(TRANSACTIONS={0:'Cancelled',1:'Pending',2:'Success',3:'Expired'})))
        tree = ast.parse((ROOT / 'app/utilities/admin/h_finance_control.py').read_text())
        handler = next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='h_su_pending_transaction_update')
        exec(compile(ast.Module(body=[handler], type_ignores=[]), '<actual full handler>', 'exec'), namespace)
        app.add_url_rule('/full/<int:u_id>/<int:t_id>', view_func=namespace[handler.name], methods=['POST'])
        return app, processor

    def test_full_agent_approval_locks_and_rejects_wrong_operation(self):
        app, processor = self.full_handler_app()
        client = app.test_client()
        statements = []
        def record(connection, statement, multiparams, params, execution_options):
            statements.append(str(statement.compile(dialect=postgresql.dialect())))
        event.listen(self.engine, 'before_execute', record)
        response = client.post('/full/1/1', data={'operation_type':0, 'tr_status':2})
        self.assertEqual(response.json['status'], 'success')
        self.assertEqual(processor.call_args.kwargs['amount'], 50000)
        self.assertTrue(any('FOR UPDATE OF users' in stmt for stmt in statements))
        self.assertTrue(any('FOR UPDATE OF user_transactions' in stmt for stmt in statements))
        processor.reset_mock()
        response = client.post('/full/1/1', data={'operation_type':1, 'tr_status':2})
        self.assertNotEqual(response.json['status'], 'success')
        processor.assert_not_called()
        self.approve()
        self.session.commit()
        response = client.post('/full/1/1', data={'operation_type':0, 'tr_status':2})
        self.assertNotEqual(response.json['status'], 'success')
        processor.assert_not_called()

    def test_other_full_transaction_types_keep_existing_processor_without_new_locks(self):
        app, processor = self.full_handler_app()
        client = app.test_client()
        for kind, operation in [('refill_balance',1),('order_payment',0),('withdraw_from_referral_balance',0)]:
            tx = self.session.get(Transaction,1)
            tx.transaction_type = kind
            tx.type = bool(operation)
            self.session.commit()
            statements = []
            def record(connection, statement, multiparams, params, execution_options):
                statements.append(str(statement.compile(dialect=postgresql.dialect())))
            event.listen(self.engine, 'before_execute', record)
            try:
                response = client.post('/full/1/1', data={'operation_type':operation,'tr_status':2})
                self.assertEqual(response.json['status'], 'success')
                self.assertEqual(processor.call_args.kwargs, dict(u_id=1,t_id=1,amount=50000,operation_type=operation,tr_status=2))
                self.assertFalse(any('FOR UPDATE' in stmt for stmt in statements))
                self.assertEqual(tx.amount,50000)
                self.assertEqual(self.session.get(User,1).balance,100000)
            finally:
                event.remove(self.engine, 'before_execute', record)

    def test_endpoint_keeps_existing_roles_and_login_requirement(self):
        app = Flask(__name__)
        app.secret_key = 'test-only'
        login = LoginManager(app)
        users = {}

        class LoginUser(UserMixin):
            def __init__(self, role, active=True):
                self.id = role
                self.role = role
                self.status = active

        @login.user_loader
        def load_user(identifier):
            return users.get(identifier)

        calls = []
        namespace = dict(wraps=wraps, current_user=current_user, request=request,
                         jsonify=jsonify, flash=flash, redirect=redirect, url_for=url_for,
                         login_required=login_required,
                         settings=SimpleNamespace(SUPER_USER='superuser', MARKINERIS_ADMIN_USER='m2r_admin',
                                                  Messages=SimpleNamespace(SUPERADMINUSER_REQUIRED='Denied')),
                         h_su_partial_withdrawal=lambda **kwargs: calls.append(kwargs) or jsonify(status='success'))
        support = ast.parse((ROOT / 'app/utilities/support.py').read_text())
        decorator = next(node for node in support.body if isinstance(node, ast.FunctionDef) and node.name == 'bck_su_mod_required')
        exec(compile(ast.Module(body=[decorator], type_ignores=[]), '<existing role decorator>', 'exec'), namespace)
        blueprint = Blueprint('admin_control', __name__)
        namespace['admin_control'] = blueprint
        routes = ast.parse((ROOT / 'app/views/main/admin_control.py').read_text())
        route = next(node for node in routes.body if isinstance(node, ast.FunctionDef) and node.name == 'partial_withdrawal')
        exec(compile(ast.Module(body=[route], type_ignores=[]), '<actual partial route>', 'exec'), namespace)
        app.register_blueprint(blueprint, url_prefix='/admin_control')
        client = app.test_client()
        path = '/admin_control/partial_withdrawal/1/1?bck=1'
        self.assertEqual(client.post(path).status_code, 401)
        for role in ('superuser', 'm2r_admin', 'manager', 'supermanager', 'admin', 'ordinary_user', 'markineris_admin'):
            users[role] = LoginUser(role)
            with client.session_transaction() as session:
                session['_user_id'] = role
                session['_fresh'] = True
            before = len(calls)
            response = client.post(path)
            if role in ('superuser', 'm2r_admin'):
                self.assertEqual(response.json['status'], 'success')
                self.assertEqual(len(calls), before + 1)
            else:
                self.assertEqual(response.json['status'], 'danger')
                self.assertEqual(len(calls), before)
        users['superuser'].status = False
        with client.session_transaction() as session:
            session['_user_id'] = 'superuser'
        self.assertEqual(client.post(path).json['status'], 'danger')

    def test_modal_only_offers_partial_approval_for_allowed_withdrawals(self):
        env = Environment(loader=FileSystemLoader(ROOT / 'app/templates'), autoescape=select_autoescape())
        env.globals.update(url_for=lambda *args, **kwargs: '/test', csrf_token=lambda: 'test')
        tx = SimpleNamespace(id=1, user_id=1, type=False, status=1, amount=50000,
                             created_at=datetime(2026, 11, 4), transaction_type='agent_withdrawal',
                             is_external=False, promo_info='', cancel_comment='', wo_account_info='',
                             login_name='agent', email='agent@example.test', phone='',
                             balance_before=None, balance_after=None)
        enums = SimpleNamespace(**{name: SimpleNamespace(value=name) for name in
                                  ('agent_withdrawal', 'refill_balance', 'refund_funds')})
        template = env.get_template('admin/transactions/su_transaction_report.html')
        def render(role, enabled=True):
            return template.render(transaction=tx, current_user=SimpleNamespace(role=role), partial_withdrawal_enabled=enabled,
                                   transaction_type_enum=enums, transaction_statuses={0:'cancelled',1:'pending',2:'success'},
                                   transaction_types={'agent_withdrawal':'withdrawal'})
        self.assertIn('id="partial_withdrawal_form"', render('m2r_admin'))
        self.assertIn('max="49999"', render('superuser'))
        self.assertNotIn('id="partial_withdrawal_form"', render('superuser', enabled=False))
        self.assertNotIn('id="partial_withdrawal_form"', render('supermanager'))
        tx.status = 2
        self.assertNotIn('id="partial_withdrawal_form"', render('superuser'))
        tx.status = 1
        tx.transaction_type = 'withdraw_from_referral_balance'
        self.assertNotIn('id="partial_withdrawal_form"', render('superuser'))

    @unittest.skipUnless((ROOT / 'app/migrations/versions/a17e92bf40c6_partial_agent_withdrawals.py').exists(),
                         'Локальная миграция не входит в репозиторий')
    def test_migration_changes_only_new_fields_and_related_constraints(self):
        migration = load('partial_migration', 'app/migrations/versions/a17e92bf40c6_partial_agent_withdrawals.py')
        output = StringIO()
        context = MigrationContext.configure(dialect_name='postgresql', opts={'as_sql': True, 'output_buffer': output})
        with Operations.context(context):
            migration.upgrade()
        sql = output.getvalue()
        self.assertEqual(sql.count('ADD COLUMN'), 3)
        for field in ('parent_transaction_id', 'original_amount', 'transaction_comment'):
            self.assertIn('ADD COLUMN ' + field, sql)
        self.assertIn('REFERENCES user_transactions (id)', sql)
        self.assertNotIn('UPDATE ', sql)
        self.assertNotIn('CREATE TABLE', sql)
        self.assertNotIn('ALTER COLUMN', sql)
        self.assertNotIn('DROP ', sql)
        self.assertTrue(all('user_transactions' in statement for statement in sql.split(';') if statement.strip()))


if __name__ == '__main__':
    unittest.main()
