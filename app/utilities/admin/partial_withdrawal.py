"""Atomic partial approval of pending agent withdrawals."""
import re
from datetime import datetime
from uuid import uuid4

from sqlalchemy import null, select
from sqlalchemy.orm import lazyload


class PartialWithdrawalError(ValueError):
    pass


def parse_approval_amount(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]+', value.strip()):
        raise PartialWithdrawalError('Введите сумму целым числом рублей.')
    value = value.strip()
    if len(value) > 10 or not 0 < int(value) <= 2147483647:
        raise PartialWithdrawalError('Сумма должна быть положительным целым числом рублей.')
    return int(value)


def approve_partial_withdrawal(session, transaction_model, user_model, *, user_id,
                               transaction_id, amount, actor):
    """Caller commits or rolls back; use the same user-first lock order as full approval."""
    amount = parse_approval_amount(amount)
    user = session.execute(select(user_model).options(lazyload('*')).where(
        user_model.id == user_id).with_for_update(of=user_model).execution_options(populate_existing=True)
    ).scalar_one_or_none()
    transaction = session.execute(select(transaction_model).options(lazyload('*')).where(
        transaction_model.id == transaction_id, transaction_model.user_id == user_id
    ).with_for_update(of=transaction_model).execution_options(populate_existing=True)).scalar_one_or_none()
    if user is None or transaction is None:
        raise PartialWithdrawalError('Пользователь или транзакция не найдены.')
    if (transaction.type is not False or transaction.transaction_type != 'agent_withdrawal'
            or transaction.status != 1):
        raise PartialWithdrawalError('Частичное одобрение доступно только для ожидающего вывода агента.')
    original = transaction.amount
    if original is None or not 0 < amount < original:
        raise PartialWithdrawalError('Одобренная сумма должна быть больше нуля и меньше суммы заявки.')
    if user.balance is None or user.balance < amount:
        raise PartialWithdrawalError('Недостаточно средств на балансе агента.')
    remainder = transaction_model(
        user_id=user_id, type=False, transaction_type='agent_withdrawal', status=1,
        amount=original - amount, parent_transaction_id=transaction.id,
        original_amount=original - amount, wo_account_info=transaction.wo_account_info,
        # Keep the original request date so the remainder stays in the same report period.
        created_at=transaction.created_at,
        bill_path=f'partial_withdrawal_{uuid4().hex}', op_cost=null(),
    )
    session.add(remainder)
    session.flush()
    stamp = f"{datetime.now():%d.%m.%Y %H:%M:%S} · {actor}"
    previous = transaction.transaction_comment or ''
    transaction.original_amount = transaction.original_amount or original
    transaction.transaction_comment = '\n'.join(filter(None, [previous,
        f'{stamp}: Частичное одобрение вывода №{transaction.id}: из {original} руб. '
        f'одобрено {amount} руб.; остаток {remainder.amount} руб. — заявка №{remainder.id}.']))
    remainder.transaction_comment = '\n'.join(filter(None, [previous,
        f'{stamp}: Остаток {remainder.amount} руб. от частично одобренной транзакции '
        f'№{transaction.id} на {original} руб. Одобрено {amount} руб.']))
    transaction.amount = amount
    transaction.status = 2
    transaction.change_user_balance(user, -amount)
    session.flush()
    return transaction, remainder
