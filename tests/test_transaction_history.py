"""Audit append preserves prior events and participates in the caller's rollback."""
import importlib.util
from pathlib import Path
import unittest

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

spec = importlib.util.spec_from_file_location('transaction_history', Path(__file__).resolve().parents[1] / 'app/utilities/transaction_history.py')
history = importlib.util.module_from_spec(spec)
spec.loader.exec_module(history)


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        with self.engine.begin() as connection:
            connection.connection.create_function('chr', 1, chr)
            connection.execute(text('CREATE TABLE user_transactions (id INTEGER PRIMARY KEY, transaction_comment TEXT, status INTEGER)'))
            connection.execute(text("INSERT INTO user_transactions VALUES (1, 'Предыдущее разделение', 1)"))
        self.session = Session(self.engine)

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_primary_cancel_then_callback_preserve_order(self):
        history.append_event(self.session, 1, 'Отмена вручную', actor='SuperMarkineris', before=1, after=0)
        self.session.execute(text('UPDATE user_transactions SET status=0 WHERE id=1'))
        self.session.commit()
        history.append_event(self.session, 1, 'Получен колбэк Platega: canceled', before=0, after=0)
        self.session.commit()
        comment, status = self.session.execute(text('SELECT transaction_comment,status FROM user_transactions')).one()
        self.assertEqual(status, 0)
        self.assertTrue(comment.startswith('Предыдущее разделение\n'))
        self.assertLess(comment.index('Отмена вручную'), comment.index('Получен колбэк'))
        self.assertIn('ожидание → отменена', comment)
        self.assertIn('изменений нет', comment)
        self.assertIn('SuperMarkineris', comment)

    def test_rollback_discards_both_status_and_history(self):
        history.append_event(self.session, 1, 'Одобрение вручную', before=1, after=2)
        self.session.execute(text('UPDATE user_transactions SET status=2 WHERE id=1'))
        self.session.rollback()
        self.assertEqual(tuple(self.session.execute(text('SELECT transaction_comment,status FROM user_transactions')).one()), ('Предыдущее разделение', 1))

    def test_multiline_reason_cannot_inject_public_history_line(self):
        line = history.event_line('Отмена\nчужая строка', actor='admin\nещё строка', before=1, after=0)
        self.assertNotIn('\n', line)
        self.assertTrue(line.startswith('[Служебное событие]'))


@unittest.skipUnless((Path(__file__).resolve().parents[1] / 'app/payments').is_dir(), 'В этом сервисе нет внешних провайдеров')
class CallbackHistoryTests(unittest.TestCase):
    def callback(self, provider, status, initial_status=1, update_ok=True):
        import ast
        from decimal import Decimal
        from types import SimpleNamespace as NS
        from unittest.mock import Mock
        path = Path(__file__).resolve().parents[1] / f'app/payments/{provider}/provider.py'
        tree = ast.parse(path.read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and any(isinstance(child, ast.FunctionDef) and child.name == 'process_callback' for child in node.body))
        method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == 'process_callback')
        transaction = NS(id=1, user_id=2, status=initial_status, invoice_id='invoice-1')
        session = Mock()
        append = Mock()
        change = Mock(return_value=(update_ok, 'update failed'))
        enum = NS(pending=NS(value=1), success=NS(value=2), cancelled=NS(value=0))
        namespace = dict(Any=object, UserTransaction=object, db=NS(session=session),
                         lock_transaction=Mock(return_value=transaction), append_event=append,
                         TransactionStatuses=enum, TransactionOperations=NS(refill=NS(value=True)),
                         helper_update_pending_rf_transaction_status=change,
                         CallbackProcessingError=ValueError, Decimal=Decimal,
                         InvoiceCallback=lambda **kwargs: NS(**kwargs), logger=Mock(),
                         PLATEGA_CALLBACK_STATUS_MAP={'confirmed':2, 'canceled':0},
                         MULEN_CALLBACK_STATUS_MAP={'success':2, 'cancel':0})
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), namespace)
        result = namespace['process_callback'](NS(_normalize_amount=lambda value: str(value)),
                     {'transaction':transaction, 'status':status, 'payment_status':status,
                      'amount':75000, 'id':'invoice-1'})
        return result, change, append, session

    def test_primary_callback_records_source_with_status_update(self):
        for provider, status in [('platega','canceled'), ('mulen_pay','cancel')]:
            with self.subTest(provider=provider):
                result, change, append, session = self.callback(provider, status)
                self.assertTrue(result)
                self.assertIn(status, change.call_args.kwargs['history_source'])
                self.assertEqual(change.call_args.kwargs['tr_status'], 0)
                append.assert_not_called()

    def test_late_callback_records_no_change_without_updating_money(self):
        for provider, status in [('platega','confirmed'), ('mulen_pay','success')]:
            with self.subTest(provider=provider):
                result, change, append, session = self.callback(provider, status, initial_status=0)
                change.assert_not_called()
                self.assertEqual(append.call_args.kwargs, {'before':0, 'after':0})
                session.commit.assert_called_once()

    def test_failed_update_cannot_acknowledge_successful_processing(self):
        for provider, status in [('platega','confirmed'), ('mulen_pay','success')]:
            with self.subTest(provider=provider), self.assertRaises(ValueError):
                self.callback(provider, status, update_ok=False)
