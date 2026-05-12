"""
Отчет по реализованным и оплаченным заказам для запуска из Flask shell.

Что делает:
- строит отчет по годам и за весь период;
- берет только оплаченные заказы в статусах SENT / CRM_PROCESSED;
- дату реализации определяет по sent_at или closed_at;
- количество заказов, общее количество марок и общую сумму берет из orders / orders_stats;
- количество марок по РФ и по остальным странам считает по товарным позициям заказа;
- если в одном заказе есть и РФ, и другие страны, марки делятся по странам фактически,
  а сумма распределяется пропорционально количеству марок по странам.

Формат строки отчета:
- category_group: категория заказа;
- marks_rf: количество марок по РФ;
- marks_other: количество марок по остальным странам;
- orders_count: количество заказов по категории;
- marks_count: общее количество марок по категории;
- amount: общая сумма по категории.
"""

from decimal import Decimal
from datetime import datetime
from pprint import pprint

from sqlalchemy import text

from config import settings
from models import db


def pp(data):
    pprint(data, width=180)


def _to_float(value):
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def print_table(rows, title=None):
    if not rows:
        print("\n<empty>\n")
        return
    if title:
        print("\n" + "=" * len(title))
        print(title)
        print("=" * len(title))
    headers = list(rows[0].keys())
    col_widths = {h: max(len(str(h)), max(len(str(row.get(h, ""))) for row in rows)) for h in headers}
    print(" | ".join(str(h).ljust(col_widths[h]) for h in headers))
    print("-+-".join("-" * col_widths[h] for h in headers))
    for row in rows:
        print(" | ".join(str(row.get(h, "")).ljust(col_widths[h]) for h in headers))
    print()


def _realized_deals_sql(date_from=None, date_to=None):
    date_filter = ""
    if date_from and date_to:
        date_filter = """
              AND COALESCE(
                    CASE WHEN o.stage = :sent_stage THEN o.sent_at END,
                    CASE WHEN o.stage = :crm_processed_stage THEN o.closed_at END
              ) >= :date_from
              AND COALESCE(
                    CASE WHEN o.stage = :sent_stage THEN o.sent_at END,
                    CASE WHEN o.stage = :crm_processed_stage THEN o.closed_at END
              ) < :date_to
        """
    sql = text(
        f"""
        WITH paid_orders AS (
            SELECT
                o.id AS order_id,
                o.order_idn,
                o.category,
                o.has_aggr,
                COALESCE(os.marks_count, 0) AS order_marks_count,
                COALESCE(os.op_cost, ut.op_cost, 0) AS op_cost,
                COALESCE(
                    CASE WHEN o.stage = :sent_stage THEN o.sent_at END,
                    CASE WHEN o.stage = :crm_processed_stage THEN o.closed_at END
                ) AS realized_at
            FROM public.orders o
            LEFT JOIN public.orders_stats os
                ON os.order_idn = o.order_idn
            LEFT JOIN public.user_transactions ut
                ON ut.id = COALESCE(o.transaction_id, os.transaction_id)
            WHERE o.payment = TRUE
              AND o.to_delete IS NOT TRUE
              AND o.stage IN ({settings.OrderStage.SENT}, {settings.OrderStage.CRM_PROCESSED})
              AND COALESCE(
                    CASE WHEN o.stage = :sent_stage THEN o.sent_at END,
                    CASE WHEN o.stage = :crm_processed_stage THEN o.closed_at END
              ) IS NOT NULL
              {date_filter}
        ),
        country_marks AS (
            SELECT
                sh.order_id,
                COALESCE(NULLIF(BTRIM(sh.country), ''), 'НЕ УКАЗАНО') AS country,
                SUM(COALESCE(sh.box_quantity, 0) * COALESCE(sh_qs.quantity, 0))::bigint AS marks_count
            FROM paid_orders po
            JOIN public.shoes sh ON sh.order_id = po.order_id
            JOIN public.shoes_quantity_sizes sh_qs ON sh_qs.shoe_id = sh.id
            GROUP BY sh.order_id, COALESCE(NULLIF(BTRIM(sh.country), ''), 'НЕ УКАЗАНО')
            UNION ALL
            SELECT
                cl.order_id,
                COALESCE(NULLIF(BTRIM(cl.country), ''), 'НЕ УКАЗАНО') AS country,
                SUM(COALESCE(cl.box_quantity, 0) * COALESCE(cl_qs.quantity, 0))::bigint AS marks_count
            FROM paid_orders po
            JOIN public.clothes cl ON cl.order_id = po.order_id
            JOIN public.cl_quantity_sizes cl_qs ON cl_qs.cl_id = cl.id
            WHERE COALESCE(po.has_aggr, FALSE) IS NOT TRUE
            GROUP BY cl.order_id, COALESCE(NULLIF(BTRIM(cl.country), ''), 'НЕ УКАЗАНО')
            UNION ALL
            SELECT
                sk.order_id,
                COALESCE(NULLIF(BTRIM(sk.country), ''), 'НЕ УКАЗАНО') AS country,
                SUM(COALESCE(sk.box_quantity, 0) * COALESCE(sk_qs.quantity, 0))::bigint AS marks_count
            FROM paid_orders po
            JOIN public.socks sk ON sk.order_id = po.order_id
            JOIN public.socks_quantity_sizes sk_qs ON sk_qs.socks_id = sk.id
            WHERE COALESCE(po.has_aggr, FALSE) IS NOT TRUE
            GROUP BY sk.order_id, COALESCE(NULLIF(BTRIM(sk.country), ''), 'НЕ УКАЗАНО')
            UNION ALL
            SELECT
                l.order_id,
                COALESCE(NULLIF(BTRIM(l.country), ''), 'НЕ УКАЗАНО') AS country,
                SUM(COALESCE(l.box_quantity, 0) * COALESCE(l_qs.quantity, 0))::bigint AS marks_count
            FROM paid_orders po
            JOIN public.linen l ON l.order_id = po.order_id
            JOIN public.linen_quantity_sizes l_qs ON l_qs.lin_id = l.id
            GROUP BY l.order_id, COALESCE(NULLIF(BTRIM(l.country), ''), 'НЕ УКАЗАНО')
            UNION ALL
            SELECT
                p.order_id,
                COALESCE(NULLIF(BTRIM(p.country), ''), 'НЕ УКАЗАНО') AS country,
                SUM(COALESCE(p.quantity, 0))::bigint AS marks_count
            FROM paid_orders po
            JOIN public.parfum p ON p.order_id = po.order_id
            GROUP BY p.order_id, COALESCE(NULLIF(BTRIM(p.country), ''), 'НЕ УКАЗАНО')
            UNION ALL
            SELECT
                ao.order_id,
                COALESCE(NULLIF(BTRIM(cl.country), ''), 'НЕ УКАЗАНО') AS country,
                SUM(COALESCE(acs.total_quantity, 0))::bigint AS marks_count
            FROM paid_orders po
            JOIN public.aggr_orders ao ON ao.order_id = po.order_id
            JOIN public.aggr_clothes_sizes acs ON acs.aggr_order_id = ao.id
            JOIN public.cl_quantity_sizes cqs ON cqs.id = acs.cqs_id
            JOIN public.clothes cl ON cl.id = cqs.cl_id
            WHERE COALESCE(po.has_aggr, FALSE) IS TRUE
            GROUP BY ao.order_id, COALESCE(NULLIF(BTRIM(cl.country), ''), 'НЕ УКАЗАНО')
            UNION ALL
            SELECT
                ao.order_id,
                COALESCE(NULLIF(BTRIM(sk.country), ''), 'НЕ УКАЗАНО') AS country,
                SUM(COALESCE(ass.total_quantity, 0))::bigint AS marks_count
            FROM paid_orders po
            JOIN public.aggr_orders ao ON ao.order_id = po.order_id
            JOIN public.aggr_socks_sizes ass ON ass.aggr_order_id = ao.id
            JOIN public.socks_quantity_sizes sqs ON sqs.id = ass.sqs_id
            JOIN public.socks sk ON sk.id = sqs.socks_id
            WHERE COALESCE(po.has_aggr, FALSE) IS TRUE
            GROUP BY ao.order_id, COALESCE(NULLIF(BTRIM(sk.country), ''), 'НЕ УКАЗАНО')
        ),
        country_marks_agg AS (
            SELECT
                cm.order_id,
                cm.country,
                SUM(cm.marks_count)::bigint AS marks_count
            FROM country_marks cm
            GROUP BY cm.order_id, cm.country
        ),
        order_country_totals AS (
            SELECT
                cma.order_id,
                SUM(cma.marks_count)::bigint AS country_marks_count
            FROM country_marks_agg cma
            GROUP BY cma.order_id
        ),
        category_order_totals AS (
            SELECT
                {_category_group_expr("po")} AS category_group,
                COUNT(DISTINCT po.order_id)::bigint AS orders_count
            FROM paid_orders po
            GROUP BY 1
        )
        SELECT
            CASE
                WHEN LOWER(TRIM(po.category)) IN ('одежда', 'clothes') THEN 'Одежда'
                WHEN LOWER(TRIM(po.category)) IN ('обувь', 'shoes') THEN 'Обувь'
                WHEN LOWER(TRIM(po.category)) IN ('белье', 'linen') THEN 'Белье'
                WHEN LOWER(TRIM(po.category)) IN ('парфюм', 'parfum') THEN 'Парфюм'
                WHEN LOWER(TRIM(po.category)) IN ('носки', 'socks') THEN 'Носки'
                ELSE 'Прочее'
            END AS category_group,
            CASE
                WHEN UPPER(TRIM(cma.country)) IN ('РОССИЯ', 'РФ', 'RUSSIA', 'RU') THEN 'РФ'
                ELSE 'Остальные страны'
            END AS country_group,
            MAX(cot.orders_count)::bigint AS orders_count,
            COALESCE(SUM(cma.marks_count), 0)::bigint AS marks_count,
            ROUND(
                COALESCE(
                    SUM(
                        CASE
                            WHEN oct.country_marks_count > 0
                                THEN po.op_cost * po.order_marks_count * cma.marks_count / oct.country_marks_count
                            ELSE 0
                        END
                    ),
                    0
                ),
                2
            ) AS amount
        FROM paid_orders po
        JOIN country_marks_agg cma ON cma.order_id = po.order_id
        JOIN order_country_totals oct ON oct.order_id = po.order_id
        JOIN category_order_totals cot
            ON cot.category_group = CASE
                WHEN LOWER(TRIM(po.category)) IN ('одежда', 'clothes') THEN 'Одежда'
                WHEN LOWER(TRIM(po.category)) IN ('обувь', 'shoes') THEN 'Обувь'
                WHEN LOWER(TRIM(po.category)) IN ('белье', 'linen') THEN 'Белье'
                WHEN LOWER(TRIM(po.category)) IN ('парфюм', 'parfum') THEN 'Парфюм'
                WHEN LOWER(TRIM(po.category)) IN ('носки', 'socks') THEN 'Носки'
                ELSE 'Прочее'
            END
        GROUP BY 1, 2
        ORDER BY
            CASE
                WHEN CASE
                    WHEN LOWER(TRIM(po.category)) IN ('одежда', 'clothes') THEN 'Одежда'
                    WHEN LOWER(TRIM(po.category)) IN ('обувь', 'shoes') THEN 'Обувь'
                    WHEN LOWER(TRIM(po.category)) IN ('белье', 'linen') THEN 'Белье'
                    WHEN LOWER(TRIM(po.category)) IN ('парфюм', 'parfum') THEN 'Парфюм'
                    WHEN LOWER(TRIM(po.category)) IN ('носки', 'socks') THEN 'Носки'
                    ELSE 'Прочее'
                END = 'Носки' THEN 1
                WHEN CASE
                    WHEN LOWER(TRIM(po.category)) IN ('одежда', 'clothes') THEN 'Одежда'
                    WHEN LOWER(TRIM(po.category)) IN ('обувь', 'shoes') THEN 'Обувь'
                    WHEN LOWER(TRIM(po.category)) IN ('белье', 'linen') THEN 'Белье'
                    WHEN LOWER(TRIM(po.category)) IN ('парфюм', 'parfum') THEN 'Парфюм'
                    WHEN LOWER(TRIM(po.category)) IN ('носки', 'socks') THEN 'Носки'
                    ELSE 'Прочее'
                END = 'Белье' THEN 2
                WHEN CASE
                    WHEN LOWER(TRIM(po.category)) IN ('одежда', 'clothes') THEN 'Одежда'
                    WHEN LOWER(TRIM(po.category)) IN ('обувь', 'shoes') THEN 'Обувь'
                    WHEN LOWER(TRIM(po.category)) IN ('белье', 'linen') THEN 'Белье'
                    WHEN LOWER(TRIM(po.category)) IN ('парфюм', 'parfum') THEN 'Парфюм'
                    WHEN LOWER(TRIM(po.category)) IN ('носки', 'socks') THEN 'Носки'
                    ELSE 'Прочее'
                END = 'Обувь' THEN 3
                WHEN CASE
                    WHEN LOWER(TRIM(po.category)) IN ('одежда', 'clothes') THEN 'Одежда'
                    WHEN LOWER(TRIM(po.category)) IN ('обувь', 'shoes') THEN 'Обувь'
                    WHEN LOWER(TRIM(po.category)) IN ('белье', 'linen') THEN 'Белье'
                    WHEN LOWER(TRIM(po.category)) IN ('парфюм', 'parfum') THEN 'Парфюм'
                    WHEN LOWER(TRIM(po.category)) IN ('носки', 'socks') THEN 'Носки'
                    ELSE 'Прочее'
                END = 'Парфюм' THEN 4
                WHEN CASE
                    WHEN LOWER(TRIM(po.category)) IN ('одежда', 'clothes') THEN 'Одежда'
                    WHEN LOWER(TRIM(po.category)) IN ('обувь', 'shoes') THEN 'Обувь'
                    WHEN LOWER(TRIM(po.category)) IN ('белье', 'linen') THEN 'Белье'
                    WHEN LOWER(TRIM(po.category)) IN ('парфюм', 'parfum') THEN 'Парфюм'
                    WHEN LOWER(TRIM(po.category)) IN ('носки', 'socks') THEN 'Носки'
                    ELSE 'Прочее'
                END = 'Одежда' THEN 5
                ELSE 6
            END,
            2
        """
    )
    params = {
        "sent_stage": settings.OrderStage.SENT,
        "crm_processed_stage": settings.OrderStage.CRM_PROCESSED,
    }
    if date_from and date_to:
        params.update(
            {
                "date_from": date_from,
                "date_to": date_to,
            }
        )
    return sql, params


def _category_group_expr(alias):
    return f"""
        CASE
            WHEN LOWER(TRIM({alias}.category)) IN ('одежда', 'clothes') THEN 'Одежда'
            WHEN LOWER(TRIM({alias}.category)) IN ('обувь', 'shoes') THEN 'Обувь'
            WHEN LOWER(TRIM({alias}.category)) IN ('белье', 'linen') THEN 'Белье'
            WHEN LOWER(TRIM({alias}.category)) IN ('парфюм', 'parfum') THEN 'Парфюм'
            WHEN LOWER(TRIM({alias}.category)) IN ('носки', 'socks', 'носки и прочее') THEN 'Носки'
            ELSE 'Прочее'
        END
    """


def _realized_deals_totals_sql(date_from=None, date_to=None):
    date_filter = ""
    if date_from and date_to:
        date_filter = """
              AND COALESCE(
                    CASE WHEN o.stage = :sent_stage THEN o.sent_at END,
                    CASE WHEN o.stage = :crm_processed_stage THEN o.closed_at END
              ) >= :date_from
              AND COALESCE(
                    CASE WHEN o.stage = :sent_stage THEN o.sent_at END,
                    CASE WHEN o.stage = :crm_processed_stage THEN o.closed_at END
              ) < :date_to
        """
    sql = text(
        f"""
        WITH paid_orders AS (
            SELECT
                o.id AS order_id,
                o.category,
                COALESCE(os.marks_count, 0) AS marks_count,
                COALESCE(os.op_cost, ut.op_cost, 0) AS op_cost
            FROM public.orders o
            LEFT JOIN public.orders_stats os
                ON os.order_idn = o.order_idn
            LEFT JOIN public.user_transactions ut
                ON ut.id = COALESCE(o.transaction_id, os.transaction_id)
            WHERE o.payment = TRUE
              AND o.to_delete IS NOT TRUE
              AND o.stage IN ({settings.OrderStage.SENT}, {settings.OrderStage.CRM_PROCESSED})
              AND COALESCE(
                    CASE WHEN o.stage = :sent_stage THEN o.sent_at END,
                    CASE WHEN o.stage = :crm_processed_stage THEN o.closed_at END
              ) IS NOT NULL
              {date_filter}
        )
        SELECT
            {_category_group_expr("po")} AS category_group,
            COUNT(DISTINCT po.order_id)::bigint AS orders_count,
            COALESCE(SUM(po.marks_count), 0)::bigint AS marks_count,
            ROUND(COALESCE(SUM(po.op_cost * po.marks_count), 0), 2) AS amount
        FROM paid_orders po
        GROUP BY 1
        """
    )
    params = {
        "sent_stage": settings.OrderStage.SENT,
        "crm_processed_stage": settings.OrderStage.CRM_PROCESSED,
    }
    if date_from and date_to:
        params.update(
            {
                "date_from": date_from,
                "date_to": date_to,
            }
        )
    return sql, params


def _realized_deals_summary(date_from=None, date_to=None):
    sql, params = _realized_deals_totals_sql(date_from=date_from, date_to=date_to)
    rows = db.session.execute(sql, params).mappings().all()
    summary = {
        row["category_group"]: {
            "orders_count": int(row["orders_count"] or 0),
            "marks_count": int(row["marks_count"] or 0),
            "amount": round(_to_float(row["amount"]), 2),
        }
        for row in rows
    }
    summary["ВСЕГО"] = {
        "orders_count": sum(item["orders_count"] for item in summary.values()),
        "marks_count": sum(item["marks_count"] for item in summary.values()),
        "amount": round(sum(item["amount"] for item in summary.values()), 2),
    }
    return summary


def realized_deals_report(date_from=None, date_to=None):
    """
    Отчет по всем реализованным и оплаченным сделкам за все время.

    Логика:
    - берем только оплаченные заказы;
    - считаем реализованными только заказы в статусах SENT / CRM_PROCESSED;
    - для периода используем только sent_at / closed_at по факту реализации;
    - сумму считаем как op_cost * количество марок;
    - разбиваем по категориям: Одежда / Обувь / Белье / Парфюм / Носки / Прочее;
    - внутри разбиваем по странам: РФ / Остальные страны;
    - если в одном заказе несколько стран, сумма делится по странам
      пропорционально количеству марок.
    """
    sql, params = _realized_deals_sql(date_from=date_from, date_to=date_to)
    raw_rows = [dict(row) for row in db.session.execute(sql, params).mappings().all()]
    summary = _realized_deals_summary(date_from=date_from, date_to=date_to)
    rows_by_category = {}
    for row in raw_rows:
        category_group = row["category_group"]
        category_row = rows_by_category.setdefault(
            category_group,
            {
                "category_group": category_group,
                "marks_rf": 0,
                "marks_other": 0,
                "orders_count": 0,
                "marks_count": 0,
                "amount": 0.0,
            },
        )
        if row["country_group"] == "РФ":
            category_row["marks_rf"] += int(row["marks_count"] or 0)
        else:
            category_row["marks_other"] += int(row["marks_count"] or 0)
    for category_group, category_row in rows_by_category.items():
        category_summary = summary.get(category_group, {})
        category_row["orders_count"] = int(category_summary.get("orders_count", 0))
        category_row["marks_count"] = int(category_summary.get("marks_count", 0))
        category_row["amount"] = round(_to_float(category_summary.get("amount", 0)), 2)
    ordered_rows = sorted(rows_by_category.values(), key=_category_sort_key)
    return ordered_rows


def realized_deals_totals(date_from=None, date_to=None):
    rows = realized_deals_report(date_from=date_from, date_to=date_to)
    return _realized_deals_totals_from_rows(rows)


def _category_sort_key(row):
    order_map = {
        "Носки": 1,
        "Белье": 2,
        "Обувь": 3,
        "Парфюм": 4,
        "Одежда": 5,
        "Прочее": 6,
        "ВСЕГО": 7,
    }
    return order_map.get(row["category_group"], 99)


def _realized_deals_totals_from_rows(rows):
    grand_total = {
        "category_group": "ВСЕГО",
        "marks_rf": sum(int(row["marks_rf"] or 0) for row in rows),
        "marks_other": sum(int(row["marks_other"] or 0) for row in rows),
        "orders_count": sum(int(row["orders_count"] or 0) for row in rows),
        "marks_count": sum(int(row["marks_count"] or 0) for row in rows),
        "amount": round(sum(_to_float(row["amount"]) for row in rows), 2),
    }
    return rows + [grand_total]


def _merge_category_rows(rows):
    merged = {}
    for row in rows:
        category_group = row["category_group"]
        target = merged.setdefault(
            category_group,
            {
                "category_group": category_group,
                "marks_rf": 0,
                "marks_other": 0,
                "orders_count": 0,
                "marks_count": 0,
                "amount": 0.0,
            },
        )
        target["marks_rf"] += int(row["marks_rf"] or 0)
        target["marks_other"] += int(row["marks_other"] or 0)
        target["orders_count"] += int(row["orders_count"] or 0)
        target["marks_count"] += int(row["marks_count"] or 0)
        target["amount"] = round(target["amount"] + _to_float(row["amount"]), 2)
    return sorted(merged.values(), key=_category_sort_key)


def print_realized_deals_report():
    rows = realized_deals_report()
    print_table(rows, "РЕАЛИЗОВАННЫЕ И ОПЛАЧЕННЫЕ СДЕЛКИ ЗА ВСЕ ВРЕМЯ")
    print_table(realized_deals_totals(), "ИТОГИ")
    return rows


def realized_deals_years():
    sql = text(
        f"""
        SELECT
            EXTRACT(
                YEAR FROM COALESCE(
                    CASE WHEN o.stage = :sent_stage THEN o.sent_at END,
                    CASE WHEN o.stage = :crm_processed_stage THEN o.closed_at END
                )
            )::int AS year
        FROM public.orders o
        WHERE o.payment = TRUE
          AND o.to_delete IS NOT TRUE
          AND o.stage IN (:sent_stage, :crm_processed_stage)
          AND COALESCE(
                CASE WHEN o.stage = :sent_stage THEN o.sent_at END,
                CASE WHEN o.stage = :crm_processed_stage THEN o.closed_at END
          ) IS NOT NULL
        GROUP BY 1
        ORDER BY 1
        """
    ).bindparams(sent_stage=settings.OrderStage.SENT, crm_processed_stage=settings.OrderStage.CRM_PROCESSED)
    return [row.year for row in db.session.execute(sql).all()]


def print_realized_deals_report_by_years(year_from=None, year_to=None):
    years = realized_deals_years()
    if year_from is not None:
        years = [year for year in years if year >= year_from]
    if year_to is not None:
        years = [year for year in years if year <= year_to]
    all_rows = []
    for year in years:
        date_from = datetime(year, 1, 1)
        date_to = datetime(year + 1, 1, 1)
        rows = realized_deals_report(date_from=date_from, date_to=date_to)
        print_table(rows, "РЕАЛИЗОВАННЫЕ СДЕЛКИ ЗА %s ГОД" % year)
        all_rows.extend(rows)
    merged_rows = _merge_category_rows(all_rows)
    print_table(_realized_deals_totals_from_rows(merged_rows), "ИТОГИ ЗА ВЕСЬ ПЕРИОД")
    return all_rows


def print_realized_deals_report_2023_2026():
    return print_realized_deals_report_by_years(2023, 2026)


def help_realized_deals_report():
    print("Usage in flask shell:")
    print("from utilities.reports_manual.realized_deals_report import print_realized_deals_report, realized_deals_report, realized_deals_totals, pp")
    print("print_realized_deals_report()")
    print("pp(realized_deals_report())")
    print("print_realized_deals_report_by_years()")
    print("print_realized_deals_report_2023_2026()")
