"""Manual XLSX report for agent type 2 transactions.

Usage in ``flask shell``:

    from utilities.reports_manual.at2_transactions_report import export_at2_transactions_report

    export_at2_transactions_report("ruznak@agentsm2r.com")

What the report does:
- finds an agent by email;
- checks that the agent is type 2;
- collects successful transactions for the agent and all direct users;
- attaches order ids for order write-offs and order cancellations;
- writes two sheets:
  1. ``Успешные транзакции``
  2. ``Отмененные заказы``
- fixes the current agent balance in report metadata at generation time.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from xlsxwriter import Workbook
from xlsxwriter.utility import xl_rowcol_to_cell

from config import settings
from models import TransactionStatuses, TransactionTypes, User, db


REPORT_DIR = Path(__file__).resolve().parent
SUCCESS_SHEET_NAME = "Успешные транзакции"
CANCELLED_SHEET_NAME = "Отмененные заказы"


@dataclass(frozen=True)
class AgentContext:
    id: int
    email: str
    login_name: str
    balance: int


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _sanitize_file_chunk(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value)
    return cleaned.strip("_") or "agent"


def _load_agent(email: str) -> AgentContext:
    agent = (
        User.query.with_entities(User.id, User.email, User.login_name, User.balance, User.is_at2)
        .filter(User.email == _normalize_email(email))
        .first()
    )
    if not agent:
        raise ValueError(f"Agent with email {email!r} was not found")
    if not agent.is_at2:
        raise ValueError(f"User {email!r} is not an agent type 2")
    return AgentContext(
        id=agent.id,
        email=agent.email,
        login_name=agent.login_name or "",
        balance=agent.balance or 0,
    )


def _transaction_rows(agent_id: int) -> list[dict[str, Any]]:
    sql = text(
        """
        WITH scoped_users AS (
            SELECT
                u.id,
                u.email,
                u.login_name,
                u.role,
                u.admin_parent_id
            FROM public.users u
            WHERE u.id = :agent_id OR u.admin_parent_id = :agent_id
        ),
        payment_orders AS (
            SELECT
                os.transaction_id,
                STRING_AGG(DISTINCT os.order_idn, ', ' ORDER BY os.order_idn) AS order_idns,
                STRING_AGG(DISTINCT ou.email, ', ' ORDER BY ou.email) FILTER (
                    WHERE ou.email IS NOT NULL AND BTRIM(ou.email) <> ''
                ) AS order_user_emails,
                STRING_AGG(DISTINCT ou.login_name, ', ' ORDER BY ou.login_name) FILTER (
                    WHERE ou.login_name IS NOT NULL AND BTRIM(ou.login_name) <> ''
                ) AS order_user_logins
            FROM public.orders_stats os
            JOIN scoped_users su ON su.id = os.user_id
            LEFT JOIN public.users ou ON ou.id = os.user_id
            WHERE os.transaction_id IS NOT NULL
            GROUP BY os.transaction_id
        ),
        cancel_orders AS (
            SELECT
                ut.id AS transaction_id,
                STRING_AGG(DISTINCT o.order_idn, ', ' ORDER BY o.order_idn) AS order_idns,
                STRING_AGG(DISTINCT ou.email, ', ' ORDER BY ou.email) FILTER (
                    WHERE ou.email IS NOT NULL AND BTRIM(ou.email) <> ''
                ) AS order_user_emails,
                STRING_AGG(DISTINCT ou.login_name, ', ' ORDER BY ou.login_name) FILTER (
                    WHERE ou.login_name IS NOT NULL AND BTRIM(ou.login_name) <> ''
                ) AS order_user_logins
            FROM public.user_transactions ut
            LEFT JOIN public.orders o ON o.order_idn = ut.wo_account_info
            LEFT JOIN public.users ou ON ou.id = o.user_id
            WHERE ut.transaction_type = :refund_funds_type
            GROUP BY ut.id
        )
        SELECT
            ut.id AS transaction_id,
            ut.created_at AS created_at,
            ut.type AS operation_type,
            ut.transaction_type AS transaction_type,
            ut.status AS status,
            ut.amount AS amount,
            ut.op_cost AS op_cost,
            ut.agent_fee AS agent_fee,
            ut.promo_info AS promo_info,
            ut.wo_account_info AS wo_account_info,
            ut.cancel_comment AS cancel_comment,
            su.id AS user_id,
            su.email AS user_email,
            su.login_name AS user_login,
            su.role AS user_role,
            CASE
                WHEN su.id = :agent_id THEN 'Агент'
                ELSE 'Пользователь агента'
            END AS scope_label,
            COALESCE(po.order_idns, co.order_idns, NULLIF(BTRIM(ut.wo_account_info), ''), '') AS order_idns,
            COALESCE(po.order_user_emails, co.order_user_emails, '') AS order_user_emails,
            COALESCE(po.order_user_logins, co.order_user_logins, '') AS order_user_logins
        FROM public.user_transactions ut
        JOIN scoped_users su ON su.id = ut.user_id
        LEFT JOIN payment_orders po ON po.transaction_id = ut.id
        LEFT JOIN cancel_orders co ON co.transaction_id = ut.id
        WHERE ut.status = :success_status
        ORDER BY ut.created_at ASC, ut.id ASC
        """
    )
    return [dict(row) for row in db.session.execute(
        sql,
        {
            "agent_id": agent_id,
            "success_status": TransactionStatuses.success.value,
            "refund_funds_type": TransactionTypes.refund_funds.value,
        },
    ).mappings().all()]


def _status_label(status: int) -> str:
    return settings.Transactions.TRANSACTIONS.get(status, str(status))


def _transaction_type_label(transaction_type: str) -> str:
    return settings.Transactions.TRANSACTION_TYPES.get(transaction_type, transaction_type)


def _operation_label(operation_type: bool) -> str:
    return settings.Transactions.TRANSACTION_OPERATION_TYPES.get(int(bool(operation_type)), str(operation_type))


def _signed_amount(amount: int | None, operation_type: bool) -> int:
    raw_amount = int(amount or 0)
    return raw_amount if operation_type else -raw_amount


def _comment(row: dict[str, Any]) -> str:
    parts = [
        row.get("promo_info") or "",
        row.get("wo_account_info") or "",
        row.get("cancel_comment") or "",
    ]
    return " | ".join(part for part in parts if part)


def _report_row(row: dict[str, Any]) -> list[Any]:
    signed_amount = _signed_amount(row.get("amount"), row.get("operation_type"))
    return [
        row.get("created_at"),
        row.get("user_email") or "",
        row.get("scope_label") or "",
        _operation_label(row.get("operation_type")),
        _transaction_type_label(row.get("transaction_type")),
        _status_label(row.get("status")),
        signed_amount,
        row.get("order_idns") or "",
    ]


def _metadata(agent: AgentContext, generated_at: datetime, rows: list[dict[str, Any]]) -> dict[str, Any]:
    client_count = User.query.filter(User.admin_parent_id == agent.id).count()
    return {
        "Дата формирования": generated_at.strftime("%d.%m.%Y %H:%M:%S"),
        "ID агента": agent.id,
        "Email агента": agent.email,
        "Login агента": agent.login_name,
        "Тип агента": "type2",
        "Текущий баланс агента": agent.balance,
        "Кол-во пользователей агента": client_count,
        "Кол-во успешных транзакций": len(rows),
    }


def _set_column_widths(sheet, rows: list[list[Any]], headers: list[str], metadata: dict[str, Any]) -> None:
    col_widths: dict[int, int] = {}
    all_rows = list(zip(metadata.keys(), metadata.values())) + [headers] + rows
    for row in all_rows:
        for idx, value in enumerate(row):
            if value is None:
                continue
            col_widths[idx] = max(col_widths.get(idx, 0), len(str(value)))
    for idx, width in col_widths.items():
        sheet.set_column(idx, idx, min(width + 2, 60))


def _write_sheet(workbook: Workbook, sheet_name: str, rows: list[list[Any]], metadata: dict[str, Any]) -> None:
    sheet = workbook.add_worksheet(sheet_name)
    header_format = workbook.add_format({"bold": True, "bg_color": "#D9EAD3", "border": 1})
    meta_key_format = workbook.add_format({"bold": True})
    cell_format = workbook.add_format({"border": 1, "text_wrap": True, "valign": "top"})
    datetime_format = workbook.add_format(
        {
            "border": 1,
            "text_wrap": True,
            "valign": "top",
            "num_format": "dd.mm.yyyy hh:mm:ss",
        }
    )
    amount_format = workbook.add_format({"border": 1, "valign": "top", "num_format": "+0;-0;0"})
    total_label_format = workbook.add_format({"bold": True, "border": 1, "bg_color": "#FFF2CC"})
    total_amount_format = workbook.add_format({"bold": True, "border": 1, "bg_color": "#FFF2CC", "num_format": "+0;-0;0"})

    headers = [
        "Дата транзакции",
        "Email транзакции",
        "Контур",
        "Тип операции",
        "Тип транзакции",
        "Статус",
        "Сумма транзакции",
        "Заказы",
    ]
    amount_col_idx = headers.index("Сумма транзакции")

    row_idx = 0
    for key, value in metadata.items():
        sheet.write(row_idx, 0, key, meta_key_format)
        sheet.write(row_idx, 1, value)
        row_idx += 1

    row_idx += 1
    for col_idx, header in enumerate(headers):
        sheet.write(row_idx, col_idx, header, header_format)

    data_start_row = row_idx + 1
    for data_row in rows:
        for col_idx, value in enumerate(data_row):
            if isinstance(value, datetime):
                sheet.write_datetime(row_idx + 1, col_idx, value, datetime_format)
            elif col_idx == amount_col_idx:
                sheet.write_number(row_idx + 1, col_idx, int(value or 0), amount_format)
            else:
                sheet.write(row_idx + 1, col_idx, value, cell_format)
        row_idx += 1

    total_row_idx = row_idx + 1
    sheet.write(total_row_idx, amount_col_idx - 1, "Итого", total_label_format)
    if rows:
        start_cell = xl_rowcol_to_cell(data_start_row, amount_col_idx)
        end_cell = xl_rowcol_to_cell(row_idx, amount_col_idx)
        total_amount = sum(int(data_row[amount_col_idx] or 0) for data_row in rows)
        sheet.write_formula(
            total_row_idx,
            amount_col_idx,
            f"=SUM({start_cell}:{end_cell})",
            total_amount_format,
            total_amount,
        )
    else:
        sheet.write_number(total_row_idx, amount_col_idx, 0, total_amount_format)

    sheet.freeze_panes(data_start_row, 0)
    sheet.autofilter(data_start_row - 1, 0, max(data_start_row - 1, row_idx), len(headers) - 1)
    _set_column_widths(sheet, rows, headers, metadata)


def export_at2_transactions_report(agent_email: str, output_path: str | Path | None = None) -> dict[str, Any]:
    """Build an XLSX report for a type2 agent and save it to disk."""
    agent = _load_agent(agent_email)
    generated_at = datetime.now()
    raw_rows = _transaction_rows(agent.id)

    success_rows = [_report_row(row) for row in raw_rows]
    cancelled_order_rows = [
        _report_row(row)
        for row in raw_rows
        if row.get("transaction_type") == TransactionTypes.refund_funds.value and (row.get("order_idns") or "").strip()
    ]
    metadata = _metadata(agent=agent, generated_at=generated_at, rows=raw_rows)

    if output_path is None:
        email_chunk = _sanitize_file_chunk(agent.email.split("@", 1)[0])
        output_path = REPORT_DIR / f"at2_transactions_{email_chunk}_{generated_at:%Y%m%d_%H%M%S}.xlsx"
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    workbook = Workbook(str(output_path))
    try:
        _write_sheet(
            workbook=workbook,
            sheet_name=SUCCESS_SHEET_NAME,
            rows=success_rows,
            metadata=metadata,
        )
        _write_sheet(
            workbook=workbook,
            sheet_name=CANCELLED_SHEET_NAME,
            rows=cancelled_order_rows,
            metadata=metadata,
        )
    finally:
        workbook.close()

    return {
        "agent_id": agent.id,
        "agent_email": agent.email,
        "agent_balance": agent.balance,
        "successful_transactions_count": len(success_rows),
        "cancelled_orders_count": len(cancelled_order_rows),
        "output_path": str(output_path),
    }


def help_at2_transactions_report() -> None:
    print("Usage in flask shell:")
    print("from utilities.reports_manual.at2_transactions_report import export_at2_transactions_report")
    print('export_at2_transactions_report("ruznak@agentsm2r.com")')

from utilities.reports_manual.at2_transactions_report import export_at2_transactions_report
export_at2_transactions_report("ruznak@agentsmarkineris.com")
