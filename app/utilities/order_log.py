"""Bounded CRM order history. Callers own the transaction; chat is excluded."""

from datetime import datetime


MAX_ORDER_LOG = 1000

# CRM column names; public OrderStage.STAGES hides several distinct stages
# behind the same customer-facing label «Заказ в работе».
CRM_STAGE_LABELS = {
    0: "Создаётся пользователем", 1: "Новые заказы", 2: "ПУЛ компаний",
    3: "В работе у оператора", 4: "Одобрение ЭДО", 5: "Обработан оператором",
    6: "Проблема в заказе", 7: "Проблема решена", 8: "Заказ отправлен",
    9: "Заказ отменён", 10: "Обработка завершена (телеграм)", 11: "Обработка завершена",
}


def h_append_order_log(old: str | None, line: str) -> str:
    return ((old or "") + line)[-MAX_ORDER_LOG:]


def order_log_line(action: str, actor: str, *, at: datetime | None = None) -> str:
    # Keep one action per line even when names/comments contain newlines.
    actor = " ".join(actor.split())
    action = " ".join(action.split())
    timestamp = (at or datetime.now()).strftime("%d.%m.%Y %H:%M:%S")
    return f"\n{timestamp} {actor}: {action};"


def append_order_log(order_id: int, action: str, *, actor: str | None = None) -> None:
    """Append atomically, preserving concurrent entries and the caller's rollback."""
    from flask import has_request_context
    from flask_login import current_user
    from sqlalchemy import text
    from models import db

    if actor is None:
        actor = current_user.login_name if has_request_context() and current_user.is_authenticated else "Система"
    db.session.execute(
        text("""UPDATE orders
                SET order_log = right(coalesce(order_log, '') || :line, :max_length)
                WHERE id = :order_id"""),
        {"order_id": order_id, "line": order_log_line(action, actor), "max_length": MAX_ORDER_LOG},
    )


def log_order_stage(order_id: int, stage: int, *, actor: str | None = None) -> None:
    label = CRM_STAGE_LABELS.get(stage, str(stage))
    append_order_log(order_id, f"перевёл заказ в «{label}»", actor=actor)
