"""Personal-account rendering must retain role-based financial visibility."""
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parents[1]
# These are capabilities of the actual transaction model, independent of the new UI.
model_source = (ROOT / 'app/models.py').read_text().split('class UserTransaction(', 1)[1].split('def change_user_balance', 1)[0]
HAS_EXTERNAL = 'is_external = ' in model_source
HAS_BILL_TIME = 'bill_time = ' in model_source
HAS_MC_CONVERSION = 'mc_conversion_request_id = ' in model_source


class TextContent(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.parts = []
        self.feed(markup)

    def handle_data(self, data):
        self.parts.append(data)

    @property
    def text(self):
        return ' '.join(self.parts)


class PersonalTransactionDetailTests(unittest.TestCase):
    def setUp(self):
        self.env = Environment(loader=FileSystemLoader(ROOT / 'app/templates'), autoescape=select_autoescape())
        self.env.globals.update(url_for=lambda *args, **kwargs: '/test', csrf_token=lambda: 'test-csrf')
        self.template = self.env.get_template('user_control/transactions/transaction_report.html')
        names = ['refill_balance', 'promo', 'refund_funds', 'agent_withdrawal', 'order_payment', 'marka_coin_service', 'at2_client_mc_refill']
        self.enums = NS(**{name: NS(value=name) for name in names})
        self.tx = NS(id=741, user_id=11, type=False, status=2, amount=73157, op_cost=179,
                     transaction_type='order_payment', is_bonus=False, is_external=False,
                     created_at=datetime(2026, 11, 23, 10, 11, 12), bill_time=datetime(2026, 11, 23, 12, 30),
                     promo_info='', cancel_comment='', transaction_comment='', wo_account_info='',
                     balance_before=98243, balance_after=25086, invoice_id='invoice-demo-741')
        self.context = dict(transaction=self.tx, transaction_type_enum=self.enums,
                            transaction_types={name:name for name in names},
                            transaction_statuses={0:'Отменена', 1:'Ожидается подтверждение', 2:'Успешно проведена'},
                            current_user=NS(role='ordinary_user'), is_at2=False,
                            mc_conversion_data=None, service_account=NS(sa_name='Счёт для пополнения'),
                            order_prices_marks=[NS(order_idn='ORDER-741', category='Одежда', subcategory='common', marks_count=14)],
                            total_marks=14, subcategories_dict={'common':'Основная одежда'},
                            transaction_image='', invoice_callbacks=[],
                            config={'CALLBACKS_STATUS_DICT':{'payment':'Оплата', 'confirmed':'Подтверждено', 'partial':'Частичная оплата'},
                                    'CALLBACK_STATUS_MAP':{'partial':'partial'}, 'PAYMENT_STATUSES':NS(PARTIAL=NS(value='partial'))})

    def render(self, **context):
        return self.template.render(**{**self.context, **context})

    @staticmethod
    def text(markup):
        return TextContent(markup).text

    def test_regular_user_sees_existing_amount_order_price_and_balances(self):
        markup = self.render()
        text = self.text(markup)
        compact = ''.join(text.split())
        for value in ('73157', '179', '2506', '98243', '25086', '14'):
            self.assertIn(value, compact)
        self.assertIn('ORDER-741', text)
        self.assertIn('Основная одежда', text)
        self.assertIn('Успешно проведена', text)
        self.assertIn('23.11.2026 10:11:12', text)
        self.assertIn('class="transaction-detail"', markup)

    def test_at2_cannot_see_amount_price_order_cost_or_balances(self):
        markup = self.render(is_at2=True)
        text = ''.join(self.text(markup).split())
        for value in ('73157', '179', '2506', '98243', '25086'):
            self.assertNotIn(value, text)
        self.assertNotIn('td-amount', markup)
        self.assertNotIn('Цена за марку', markup)
        self.assertNotIn('Баланс до', markup)
        self.assertNotIn('Сумма, ₽', markup)
        self.assertIn('ORDER-741', markup)
        self.assertIn('14', text)

    def test_no_staff_approval_controls_in_personal_account(self):
        self.tx.status = 1
        self.tx.transaction_type = 'agent_withdrawal'
        markup = self.render()
        for identifier in ('partial_withdrawal_form', 'confirm_transaction_btn', 'cancel_transaction_btn', 'editAccountBtn'):
            self.assertNotIn(identifier, markup)

    def test_withdrawal_history_is_escaped_and_requisites_keep_formatting(self):
        self.tx.transaction_comment = 'Первое разделение\nВторое <script>alert(1)</script>'
        self.tx.wo_account_info = '<i>Иван Иванов</i>\n<b>Банк 123</b>'
        markup = self.render()
        self.assertIn('История вывода', markup)
        self.assertIn('Первое разделение\nВторое &lt;script&gt;', markup)
        self.assertNotIn('<script>alert(1)</script>', markup)
        self.assertIn('<i>Иван Иванов</i>', markup)
        self.assertIn('<b>Банк 123</b>', markup)

    def test_missing_optional_sections_and_balance_snapshots_stay_hidden(self):
        self.tx.balance_before = self.tx.balance_after = None
        markup = self.render(order_prices_marks=[])
        for label in ('История вывода', 'Реквизиты счёта', 'Заказы ·', 'Чек / подтверждение', 'Баланс до'):
            self.assertNotIn(label, markup)
        self.tx.status = 1
        self.tx.balance_before, self.tx.balance_after = 98243, 25086
        self.assertNotIn('Баланс до', self.render())

    def test_refill_promo_and_bonus_conditions_remain(self):
        self.tx.type = True
        self.tx.transaction_type = 'refill_balance'
        self.tx.promo_info = '<b>PROMO-741</b>'
        markup = self.render()
        self.assertIn('Счёт для пополнения', markup)
        self.assertIn('<b>PROMO-741</b>', markup)
        self.assertNotIn('ORDER-741', markup)
        self.tx.transaction_type = 'promo'
        markup = self.render()
        self.assertEqual('Счёт для пополнения' in markup, not HAS_EXTERNAL)
        self.tx.is_bonus = True
        self.assertIn('БОНУС КОД', self.render())

    def test_refund_description_is_retained_and_escaped(self):
        self.tx.type = True
        self.tx.transaction_type = 'refund_funds'
        self.tx.wo_account_info = 'ORDER-741 <tag>'
        markup = self.render()
        self.assertIn('Возврат средств отмененного заказа', markup)
        self.assertIn('ORDER-741 &lt;tag&gt;', markup)
        self.assertNotIn('Реквизиты счёта', markup)

    def test_receipt_zoom_and_modal_callbacks_are_retained(self):
        markup = self.render(transaction_image='<img id="bill-modal-image" onclick="zoom_image()" src="/test.png">')
        self.assertIn('id="bill-modal-image"', markup)
        self.assertIn('onclick="zoom_image()"', markup)
        modal = self.env.get_template('user_control/transactions/transaction_modal.html').render()
        self.assertIn('id="transactionDetaildiv"', modal)
        self.assertIn('id="transactionDetailModal"', modal)
        self.assertIn('onclick="clear_td_modal()"', modal)
        self.assertIn('transaction-detail-modal', modal)
        if HAS_EXTERNAL:
            self.assertIn('id="cancelTransactionModal"', modal)
            self.assertIn('id="confirmCancelBtn"', modal)

    @unittest.skipUnless(HAS_BILL_TIME, 'M2R does not have bill_time')
    def test_receipt_date_editing_keeps_superuser_only_controls(self):
        self.tx.type = True
        self.tx.transaction_type = 'refill_balance'
        markup = self.render()
        self.assertIn('23.11.2026 12:30:00', markup)
        self.assertNotIn('id="editBillTimeBtn"', markup)
        markup = self.render(current_user=NS(role='superuser'))
        for value in ('id="editBillTimeBtn"', 'id="bill-time-input"', 'openUserBillTimeEditor()', 'handleUserBillTimeChange()', 'handleUserBillTimeBlur()', 'data-csrf-token="test-csrf"'):
            self.assertIn(value, markup)

    @unittest.skipUnless(HAS_EXTERNAL, 'M2R does not have external payments')
    def test_cancellation_comment_and_late_payment_warning_stay_visible(self):
        self.tx.type = True
        self.tx.status = 0
        self.tx.is_external = True
        self.tx.cancel_comment = 'Истёк срок\nКомментарий <пользователя>'
        callback = NS(callback_type='payment', callback_status='confirmed', callback_amount=73157,
                      callback_created_at=datetime(2026,11,23,12,40))
        markup = self.render(invoice_callbacks=[callback])
        self.assertIn('Комментарий к отмене', markup)
        self.assertIn('Истёк срок\nКомментарий &lt;пользователя&gt;', markup)
        self.assertIn('Требуется ручная проверка', markup)
        self.assertIn('invoice-demo-741', markup)
        self.assertIn('copy_to_buffer(\'invoice-demo-741\')', markup)
        self.assertIn('23-11-2026 12:40', markup)

    @unittest.skipUnless(HAS_MC_CONVERSION, 'M2R does not have MC conversions')
    def test_mc_conversion_amount_visibility_matches_existing_at2_exception(self):
        conversion = dict(amount=54321.9, mc_amount=4321.9)
        markup = self.render(is_at2=True, mc_conversion_data=conversion)
        text = ''.join(self.text(markup).split())
        self.assertIn('54321', text)
        self.assertIn('4321MC', text)
        self.assertNotIn('73157', text)
        self.assertNotIn('Цена за марку', markup)
        markup = self.render(mc_conversion_data=conversion)
        text = ''.join(self.text(markup).split())
        self.assertIn('73157', text)
        self.assertNotIn('54321', text)
        self.assertIn('4321MC', text)

    @unittest.skipUnless(HAS_MC_CONVERSION, 'M2R does not have MC transactions')
    def test_coin_transaction_unit_remains_mc(self):
        self.tx.transaction_type = 'marka_coin_service'
        markup = self.render()
        self.assertIn('<small>MC</small>', markup)


if __name__ == '__main__':
    unittest.main()
