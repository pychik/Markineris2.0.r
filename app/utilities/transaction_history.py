"""Append-only transaction audit. Never commits or changes balances.

Callers hold the transaction row lock; history and status share their commit.
SQL concatenation preserves earlier entries even when the ORM field is deferred.
"""
from datetime import datetime

from sqlalchemy import text

STATUS_LABELS = {0: 'отменена', 1: 'ожидание', 2: 'успешно проведена'}


def event_line(message, *, actor=None, before=None, after=None):
    message = " ".join(str(message).splitlines())
    actor = " ".join(str(actor).splitlines()) if actor else None
    parts = [f"[Служебное событие] {datetime.now():%d.%m.%Y %H:%M:%S.%f} — {message}"]
    if actor:
        parts.append(f"Исполнитель: {actor}.")
    if before is not None and after is not None:
        if before == after:
            parts.append(f"Статус: {STATUS_LABELS.get(before, before)}; изменений нет.")
        else:
            parts.append(f"Статус: {STATUS_LABELS.get(before, before)} → {STATUS_LABELS.get(after, after)}.")
    return ' '.join(parts)


def append_event(session, transaction_id, message, *, actor=None, before=None, after=None):
    line = event_line(message, actor=actor, before=before, after=after)
    session.execute(text("""
        UPDATE user_transactions
        SET transaction_comment = CASE
            WHEN coalesce(transaction_comment, '') = '' THEN :line
            ELSE transaction_comment || chr(10) || :line END
        WHERE id = :transaction_id
    """), {'line': line, 'transaction_id': transaction_id})


def lock_transaction(session, model, transaction_id):
    # Avoid FOR UPDATE over the nullable joined invoice_callbacks relationship.
    from sqlalchemy import select
    from sqlalchemy.orm import lazyload
    return session.execute(select(model).options(lazyload('*')).where(
        model.id == transaction_id
    ).with_for_update(of=model).execution_options(populate_existing=True)).scalar_one_or_none()
