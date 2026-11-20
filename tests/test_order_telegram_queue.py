"""Excel sends use RQ; product-card orders queue them only after commit."""
import ast
from io import BytesIO
from pathlib import Path
import pickle
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


def load_function(path, name, namespace):
    node = next(node for node in ast.parse((ROOT / path).read_text()).body
                if isinstance(node, ast.FunctionDef) and node.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), path, 'exec'), namespace)
    return namespace[name]


class OrderTelegramQueueTests(unittest.TestCase):
    def test_excel_send_enqueues_serializable_file_instead_of_calling_telegram_directly(self):
        send = Mock(side_effect=AssertionError('Telegram must not be called synchronously'))
        files = (BytesIO(b'xlsx content'), 'order_GTIN.xlsx')
        context = dict(User=object, settings=NS(ORD_USER='ordinary_user'),
                       TelegramProcessor=NS(send_message_tg=send, make_message_tg=lambda **kwargs: 'Заказ'),
                       get_download_info=lambda **kwargs: (False, '123', 'ИП', 'Клиент', '', '', '',
                                                           1, 2, 'одежда', '', files))
        enqueue = load_function('app/utilities/download.py', 'orders_process_send_order', context)
        user = NS(role='admin', admin_parent_id=None, is_at2=True, telegram=[NS(channel_id='-1001')])
        self.assertTrue(enqueue(1, user, '', '1_1'))
        send.assert_not_called()
        send.delay.assert_called_once()
        payload = pickle.loads(pickle.dumps(send.delay.call_args.kwargs))
        self.assertEqual(set(payload), {'message', 'group_id', 'files_list'})
        self.assertEqual(payload['group_id'], '-1001')
        self.assertEqual(payload['files_list'][0].read(), b'xlsx content')
        self.assertEqual(payload['files_list'][1], 'order_GTIN.xlsx')
        # Preserve the local agent-2 rule: notify without attaching files, also through RQ.
        text_send = Mock()
        context['TelegramProcessor'].send_message_text = text_send
        send.delay.reset_mock()
        user.admin_parent_id = 2
        self.assertTrue(enqueue(1, user, '', '1_2'))
        send.delay.assert_not_called()
        text_send.assert_not_called()
        text_send.delay.assert_called_once_with(message='Заказ', chat_id='-1001')


    def test_product_card_order_queues_only_after_successful_commit(self):
        for commit_fails, queue_fails, at2 in ((False, False, True), (True, False, True),
                                              (False, True, True), (False, False, False)):
            with self.subTest(commit_fails=commit_fails, queue_fails=queue_fails, at2=at2):
                events = []
                order = NS(id=1, category='одежда', company_idn='123', clothes=[])
                column = NS(is_=lambda value: True)
                model = NS(id=1, user_id=2, stage=0, is_moderation=column, processed=column, to_delete=column,
                           query=NS(filter=lambda *args: NS(first=lambda: order)))
                class Form(dict):
                    def to_dict(self):
                        return dict(self)
                def commit():
                    events.append('commit')
                    if commit_fails:
                        raise RuntimeError('commit failed')
                def queue_send(**kwargs):
                    events.append('queue')
                    if queue_fails:
                        raise RuntimeError('queue unavailable')
                    return True
                reserve = Mock(return_value=(1, '2_1', True, at2))
                start = Mock(return_value=2)
                context = dict(Order=model, current_user=NS(id=2), request=NS(form=Form(order_comment='Тест')),
                               db=NS(session=NS(commit=commit, rollback=lambda: events.append('rollback'))),
                               settings=NS(OrderStage=NS(CREATING=0), CATEGORIES_DICT={'одежда': 'clothes'},
                                           Messages=NS(PROCESS_SUCCESS='Оформлен ', ORDER_ADD_ERROR='Ошибка')),
                               _validate_pc_order_company_fields=lambda order: (True, dict(company_type='ИП', company_name='Клиент', company_idn='123'), ''),
                               _get_pc_order_for_process=lambda o_id: order,
                               validate_pc_order_items_ready_for_process=lambda *args: [],
                               validate_order_comment_length=lambda **kwargs: True,
                               validate_and_build_contact_info=lambda *args: (True, 'contact', ''),
                               ExceptionDataUsers=NS(get_company_idns=lambda: []),
                               check_order_pos=lambda **kwargs: True,
                               ValidatorProcessor=NS(validate_aggr_order_completeness=lambda **kwargs: True),
                               helper_check_uoabm=lambda **kwargs: (1, 0, at2, ''),
                               process_admin_order_num=reserve, process_order_start=start,
                               flash=lambda *args, **kwargs: None, Markup=str,
                               redirect=lambda value: value, url_for=lambda endpoint, **kwargs: endpoint,
                               logger=NS(error=Mock(), exception=Mock()),
                               helper_send_user_order_tg_notify=lambda **kwargs: events.append('notify'),
                               MarkinerisInform=NS(send_message_tg=NS(delay=lambda **kwargs: None)))
                process = load_function('app/views/main/product_cards/handlers.py', 'h_pc_order_process', context)
                modules = {'utilities.download': NS(orders_process_send_order=queue_send),
                           'unused_port_placeholder': NS()}
                with patch.dict('sys.modules', modules):
                    result = process(1)
                reserve.assert_called_once_with(user=context['current_user'], commit=False)
                self.assertIs(start.call_args.kwargs['order'], order)
                if commit_fails:
                    self.assertEqual(events, ['commit', 'rollback'])
                    self.assertEqual(result, 'user_product_cards.pc_order_view')
                else:
                    self.assertEqual(events, ['commit', 'queue', 'notify'] if at2 else ['commit', 'notify'])
                    self.assertEqual(result, 'user_product_cards.pc_orders_drafts')
                    if queue_fails:
                        context['logger'].exception.assert_called_once()


if __name__ == '__main__':
    unittest.main()
