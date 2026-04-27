from io import BytesIO
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from flask import jsonify

RD_MIN_DATE = date(2022, 1, 1)
RD_MIN_DATE_STR = RD_MIN_DATE.strftime('%d.%m.%Y')


def _safe_part(s: str) -> str:
    s = (s or "").strip()
    for ch in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
        s = s.replace(ch, "_")
    return s[:180]


def _spec_json_error(message: str, code: int = 400):
    return jsonify(status="error", message=message), code


def parse_rd_dates_from_form(form_dict: dict) -> tuple[date | None, date | None]:
    rd_date_str = (form_dict.get("rd_date") or "").strip()
    rd_date_to_str = (form_dict.get("rd_date_to") or "").strip()

    rd_date = datetime.strptime(rd_date_str, "%d.%m.%Y").date() if rd_date_str else None
    rd_date_to = datetime.strptime(rd_date_to_str, "%d.%m.%Y").date() if rd_date_to_str else None
    return rd_date, rd_date_to


def validate_rd_block(form_dict: dict) -> None:
    """
    Правила (как на фронте):
    - min дата = 01.01.2022
    - rd_date_to >= today + 1 month
    - rd_date <= rd_date_to
    - если тумблер включён — должны быть заполнены ВСЕ поля
    """
    has_rd = (str(form_dict.get("has_rd") or "").lower() in ("1", "true", "on", "yes"))

    rd_type = (form_dict.get("rd_type") or "").strip()
    rd_name = (form_dict.get("rd_name") or "").replace("№", "").strip()
    rd_date, rd_date_to = parse_rd_dates_from_form(form_dict)

    if not has_rd:
        # тумблер выключен -> РД игнорируем полностью
        form_dict["rd_type"] = ""
        form_dict["rd_name"] = ""
        form_dict["_rd_date_obj"] = None
        form_dict["_rd_date_to_obj"] = None
        return

    # тумблер включен -> обязаны быть все поля
    all_filled = bool(rd_type and rd_name and rd_date and rd_date_to)
    if not all_filled:
        raise ValueError("Заполните все поля РД: тип, название, даты 'От' и 'До'.")

    if rd_date < RD_MIN_DATE:
        raise ValueError(f"Дата 'От' не может быть раньше {RD_MIN_DATE_STR}.")
    if rd_date > date.today():
        raise ValueError("Дата 'От' не может быть позже сегодняшней даты.")
    if rd_date_to < RD_MIN_DATE:
        raise ValueError(f"Дата 'До' не может быть раньше {RD_MIN_DATE_STR}.")

    min_to = date.today() + relativedelta(months=+1)
    if rd_date_to < min_to:
        raise ValueError(
            f"Дата 'До' не может быть раньше {min_to.strftime('%d.%m.%Y')} (сегодня + 1 месяц)."
        )

    if rd_date > rd_date_to:
        raise ValueError("Дата 'От' не может быть позже даты 'До'.")

    # нормализуем обратно
    form_dict["rd_type"] = rd_type
    form_dict["rd_name"] = rd_name
    form_dict["_rd_date_obj"] = rd_date
    form_dict["_rd_date_to_obj"] = rd_date_to
