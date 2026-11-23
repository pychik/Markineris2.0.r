"""Daily weighted mark prices, using the finance dashboard's write-off rules."""
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO

from dateutil.relativedelta import relativedelta
from flask import abort, jsonify, render_template, request, send_file
from openpyxl import Workbook
from sqlalchemy import text


DAILY_SQL = """
WITH filtered_transactions AS (
    SELECT id, created_at, amount FROM public.user_transactions
    WHERE op_cost IS NOT NULL AND type = FALSE
      AND created_at >= :date_from AND created_at < :date_until
), mark_count AS (
    SELECT os.transaction_id, SUM(os.marks_count) AS total_marks
    FROM public.orders_stats os
    JOIN filtered_transactions ut ON ut.id = os.transaction_id
    GROUP BY os.transaction_id
)
SELECT DATE(ut.created_at) AS day,
       COALESCE(SUM(ut.amount), 0) AS amount,
       COALESCE(SUM(mc.total_marks), 0) AS marks
FROM filtered_transactions ut
JOIN mark_count mc ON mc.transaction_id = ut.id
GROUP BY DATE(ut.created_at)
ORDER BY day
"""


def parse_filters(args):
    today = datetime.now().date()

    def parse(value, default):
        if not value:
            return default
        for fmt in ('%d.%m.%Y', '%Y-%m-%d'):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                pass
        raise ValueError('Неверный формат даты. Используйте ДД.ММ.ГГГГ.')

    start = parse(args.get('date_from'), today.replace(day=1))
    end = parse(args.get('date_to'), today)
    if start > end:
        raise ValueError('Начальная дата позже конечной.')
    if end.year == 9999:
        raise ValueError('Конечная дата вне допустимого диапазона.')
    if end > start + relativedelta(months=12):
        raise ValueError('Выберите период не более 12 месяцев. Выгрузка в Excel также ограничена одним годом.')
    return dict(date_from=start, date_to=end,
                sort='asc' if args.get('sort') == 'asc' else 'desc')


def load_daily_prices(session, filters):
    records = session.execute(text(DAILY_SQL), dict(
        date_from=datetime.combine(filters['date_from'], datetime.min.time()),
        date_until=datetime.combine(filters['date_to'] + timedelta(days=1), datetime.min.time()),
    )).mappings()
    prices = {}
    for record in records:
        day = record['day']
        if isinstance(day, str):
            day = datetime.strptime(day, '%Y-%m-%d').date()
        amount, marks = Decimal(str(record['amount'])), int(record['marks'])
        price = (amount / marks if marks else Decimal(0)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        prices[day] = dict(average_price=price, marks=marks, amount=amount)
    return [dict(day=filters['date_from'] + timedelta(days=index),
                 **prices.get(filters['date_from'] + timedelta(days=index),
                              dict(average_price=None, marks=0, amount=Decimal(0))))
            for index in range((filters['date_to'] - filters['date_from']).days + 1)]


def export_prices(rows):
    book = Workbook()
    sheet = book.active
    sheet.title = 'Средняя цена'
    sheet.append(['Дата / день', 'Средняя цена, руб.', 'Количество марок', 'Всего списано, руб.'])
    sheet.freeze_panes = 'A2'
    sheet.auto_filter.ref = f'A1:D{len(rows) + 1}'
    sheet.column_dimensions['A'].width = 20
    sheet.column_dimensions['B'].width = 26
    sheet.column_dimensions['C'].width = 23
    sheet.column_dimensions['D'].width = 26
    for row in rows:
        sheet.append([row['day'], row['average_price'], row['marks'], row['amount']])
        sheet.cell(sheet.max_row, 1).number_format = 'DD.MM.YYYY'
        sheet.cell(sheet.max_row, 2).number_format = '0.00'
        sheet.cell(sheet.max_row, 3).number_format = '#,##0'
        sheet.cell(sheet.max_row, 4).number_format = '#,##0.00'
    output = BytesIO()
    book.save(output)
    output.seek(0)
    return output


def average_price_report():
    from models import db

    try:
        filters = parse_filters(request.args)
    except ValueError as error:
        if request.args.get('format') in ('json', 'xlsx'):
            return jsonify(message=str(error)), 400
        abort(400, str(error))
    report_format = request.args.get('format')
    if report_format not in ('json', 'xlsx'):
        return render_template('admin/finance/average_price/main.html', filters=filters)

    rows = load_daily_prices(db.session, filters)
    ordered = rows if filters['sort'] == 'asc' else list(reversed(rows))
    if report_format == 'xlsx':
        return send_file(export_prices(ordered), as_attachment=True,
                         download_name=f"average_price_{filters['date_from']}_{filters['date_to']}.xlsx",
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    per_page = 31
    pages = max(1, (len(rows) + per_page - 1) // per_page)
    page = min(pages, max(1, request.args.get('page', 1, type=int)))
    offset = (page - 1) * per_page
    total_marks = sum(row['marks'] for row in rows)
    total_amount = sum((row['amount'] for row in rows), Decimal(0))
    return jsonify(htmlresponse=render_template(
        'admin/finance/average_price/table.html', rows=ordered[offset:offset + per_page],
        filters=filters, page=page, pages=pages, total=len(rows), offset=offset,
        total_marks=total_marks, total_amount=total_amount),
        chart=[dict(date=row['day'].strftime('%d.%m.%Y'), price=float(row['average_price']) if row['average_price'] is not None else None,
                    marks=row['marks'])
               for row in rows] if request.args.get('chart') != '0' else None)
