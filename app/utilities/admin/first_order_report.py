"""Users whose first submitted order falls in the selected period."""
from dataclasses import dataclass, replace
from calendar import monthrange
from datetime import date, datetime, time, timedelta
from io import BytesIO

from flask import jsonify, render_template, request, send_file
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from sqlalchemy import text


SORT_COLUMNS = {"registered_at": "u.created_at", "first_order_at": "history.first_order_at"}
DATETIME_FORMAT = "%d.%m.%Y %H:%M"
MONTH_LABELS = ("Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь")
REPORT_CTE = """
WITH history AS (
    SELECT os.user_id,
           MIN(COALESCE(os.crm_created_at, os.created_at)) AS first_order_at,
           SUM(CASE WHEN COALESCE(os.crm_created_at, os.created_at) >= :date_from
                     AND COALESCE(os.crm_created_at, os.created_at) < :date_to
                    THEN 1 ELSE 0 END) AS orders_count
    FROM public.orders_stats os
    GROUP BY os.user_id
    HAVING MIN(COALESCE(os.crm_created_at, os.created_at)) >= :date_from
       AND MIN(COALESCE(os.crm_created_at, os.created_at)) < :date_to
)
"""
REPORT_JOINS = """
FROM history
JOIN public.users u ON u.id = history.user_id
LEFT JOIN public.users agent ON agent.id = u.admin_parent_id
WHERE u.role = :user_role
"""


@dataclass(frozen=True)
class ReportParams:
    date_from: datetime
    date_to: datetime
    sort: str = "first_order_at"
    direction: str = "desc"
    page: int = 1
    per_page: int = 50

    def query_args(self, **overrides):
        values = dict(date_from=self.date_from.strftime(DATETIME_FORMAT), date_to=self.date_to.strftime(DATETIME_FORMAT),
                      sort=self.sort, direction=self.direction, page=self.page)
        values.update(overrides)
        return values

    def sql_params(self, user_role):
        return dict(date_from=self.date_from,
                    date_to=self.date_to + timedelta(minutes=1),
                    user_role=user_role, limit=self.per_page, offset=(self.page - 1) * self.per_page)


def month_shortcuts(today=None):
    today = today or date.today()
    months = []
    for number, label in enumerate(MONTH_LABELS, 1):
        start = datetime(today.year, number, 1)
        last_day = date(today.year, number, monthrange(today.year, number)[1])
        end = datetime.combine(min(last_day, today) if number == today.month else last_day, time(23, 59))
        months.append(dict(label=label, year=today.year, disabled=number > today.month,
                           date_from=start.strftime(DATETIME_FORMAT), date_to=end.strftime(DATETIME_FORMAT)))
    return months


def parse_report_params(args, *, today=None, per_page=50):
    today = today or date.today()

    def parse_datetime(value, default, end=False):
        if not value:
            return default
        try:
            return datetime.strptime(value, DATETIME_FORMAT)
        except ValueError:
            # Keep links to the original report with ISO date-only filters working.
            day = date.fromisoformat(value)
            return datetime.combine(day, time(23, 59) if end else time.min)

    try:
        date_from = parse_datetime(args.get("date_from"), datetime.combine(today.replace(day=1), time.min))
        date_to = parse_datetime(args.get("date_to"), datetime.combine(today, time(23, 59)), end=True)
    except (TypeError, ValueError):
        raise ValueError("Укажите корректные даты отчёта") from None
    if date_from > date_to:
        raise ValueError("Дата начала не может быть позже даты окончания")
    if date_to >= datetime(9999, 12, 31, 23, 59):
        raise ValueError("Укажите корректную дату окончания")
    sort = args.get("sort", "first_order_at")
    direction = args.get("direction", "desc")
    if sort not in SORT_COLUMNS or direction not in {"asc", "desc"}:
        raise ValueError("Некорректная сортировка отчёта")
    try:
        page = int(args.get("page", 1))
    except (TypeError, ValueError):
        raise ValueError("Некорректный номер страницы") from None
    if page < 1:
        raise ValueError("Некорректный номер страницы")
    return ReportParams(date_from, date_to, sort, direction, page, per_page)


def report_statement(params, *, paginate=True):
    # Both SQL fragments come exclusively from the allowlists above.
    order_by = SORT_COLUMNS[params.sort]
    direction = params.direction.upper()
    sql = REPORT_CTE + """
SELECT u.id AS user_id, u.login_name, u.balance, u.created_at AS registered_at,
       history.first_order_at, NULL AS source, u.email, u.phone,
       COALESCE(NULLIF(agent.login_name, ''), agent.email) AS agent_name,
       history.orders_count
""" + REPORT_JOINS + f" ORDER BY {order_by} {direction} NULLS LAST, u.id ASC"
    if paginate:
        sql += " LIMIT :limit OFFSET :offset"
    return text(sql)


def load_report(session, params, user_role, *, paginate=True):
    sql_params = params.sql_params(user_role)
    totals = session.execute(text(REPORT_CTE + """
SELECT COUNT(*) AS users_count, COALESCE(SUM(history.orders_count), 0) AS orders_count
""" + REPORT_JOINS), sql_params).mappings().one()
    pages = max(1, (totals["users_count"] + params.per_page - 1) // params.per_page)
    params = replace(params, page=min(params.page, pages))
    rows = session.execute(report_statement(params, paginate=paginate), params.sql_params(user_role)).mappings().all()
    return rows, totals, params, pages


def report_excel(rows, params, source_labels):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Отчёт первичного заказа"
    sheet.append(["Отчёт первичного заказа"])
    sheet.append(["Период", f"{params.date_from:%d.%m.%Y %H:%M} — {params.date_to:%d.%m.%Y %H:%M}"])
    sheet.append([])
    sheet.append(["№", "Пользователь", "Текущий баланс, ₽", "Дата регистрации", "Дата первого заказа",
                  "Откуда пришёл", "Почта", "Телефон", "Агент пользователя", "Заказов за период"])
    for number, row in enumerate(rows, 1):
        sheet.append([number, row["login_name"] or "", row["balance"] or 0, row["registered_at"], row["first_order_at"],
                      source_labels.get(row["source"], row["source"] or "Не указан"),
                      row["email"] or "", row["phone"] or "", row["agent_name"] or "Без агента",
                      row["orders_count"]])
        for cell in sheet[sheet.max_row]:
            if isinstance(cell.value, str):
                cell.data_type = "s"
        sheet.cell(sheet.max_row, 3).number_format = '#,##0.00" ₽"'
        for col in (4, 5):
            sheet.cell(sheet.max_row, col).number_format = "dd.mm.yyyy hh:mm"
    for cell in sheet[4]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="FFF2CC")
    for col, width in zip("ABCDEFGHIJ", (8, 28, 24, 24, 24, 32, 36, 24, 28, 22)):
        sheet.column_dimensions[col].width = width
    sheet.freeze_panes = "A5"
    sheet.auto_filter.ref = f"A4:J{max(4, sheet.max_row)}"
    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return output


def first_order_report(*, excel=False):
    from config import settings
    from models import db

    try:
        params = parse_report_params(request.args, per_page=settings.PAGINATION_PER_PAGE)
    except ValueError as exc:
        if request.args.get("bck") == "1" or excel:
            return jsonify(status="error", message=str(exc)), 400
        params = parse_report_params({}, per_page=settings.PAGINATION_PER_PAGE)
        return render_template("admin/first_order_report/main.html", params=params, error=str(exc),
                               months=month_shortcuts()), 400

    rows, totals, params, pages = load_report(db.session, params, settings.ORD_USER, paginate=not excel)
    source_labels = {}  # This service does not collect registration sources.
    if excel:
        filename = f"Отчёт первичного заказа {params.date_from:%d.%m.%Y %H-%M} — {params.date_to:%d.%m.%Y %H-%M}.xlsx"
        return send_file(report_excel(rows, params, source_labels), as_attachment=True, download_name=filename,
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    context = dict(params=params, rows=rows, totals=totals, pages=pages, source_labels=source_labels,
                   months=month_shortcuts())
    if request.args.get("bck") == "1":
        return jsonify(status="success", htmlresponse=render_template("admin/first_order_report/table.html", **context))
    return render_template("admin/first_order_report/main.html", **context)
