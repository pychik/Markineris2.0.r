import re
from datetime import date, datetime

from dateutil.relativedelta import relativedelta
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import selectinload

from config import settings
from models import db
from rd_registry.models import RdRegistryEntry
from rd_registry.normalize import rd_key
from tezaurus.runtime_catalogs import get_all_countries, get_valid_rd
from views.main.product_cards.constants import PC_DISABLED_CARD_CATEGORIES
from views.main.product_cards.support import CATEGORIES_COMMON

MIN_QUERY_LEN = 5
SEARCH_LIMIT = 20
RECOMMEND_LIMIT = 20
NO_COUNTRY = "-"  # фильтр страницы реестра: записи без страны (внесены до появления поля)
PAGE_SIZE = 50
RD_MIN_DATE = date(2022, 1, 1)
TNVED_RE = re.compile(r"^\d{10}$")
# сортировка страницы реестра: ?sort=created|updated&dir=asc|desc
SORT_COLUMNS = {"created": RdRegistryEntry.created_at, "updated": RdRegistryEntry.updated_at}


def min_suggest_date() -> date:
    """Как в validate_rd_block: РД с «До» раньше этой даты карточка не примет, в подсказки он не попадает."""
    return date.today() + relativedelta(months=+1)


def category_choices() -> dict[str, dict]:
    """Категории карточек для формы и фильтра: {slug: {"title", "subcategories": {slug: title}}}."""
    return {
        slug: {"title": cfg["title"], "subcategories": cfg["subcategories"] or {}}
        for slug, cfg in CATEGORIES_COMMON.items()
        if slug not in PC_DISABLED_CARD_CATEGORIES
    }


def _clean_subcategory(category: str, subcategory: str | None) -> str:
    """Подкатегорию храним, только если она есть у категории (у носков модель отдаёт 'common' - не храним)."""
    subcategories = (CATEGORIES_COMMON.get(category) or {}).get("subcategories") or {}
    return subcategory if subcategory in subcategories else ""


def _clean_country(country: str | None) -> str:
    """Страна как в карточке (CommonMixin.country): верхний регистр, без пробелов по краям."""
    return (country or "").strip().upper()


def category_label(category: str, subcategory: str) -> str:
    """«одежда / шали» или просто «парфюм», если подкатегории нет."""
    cfg = CATEGORIES_COMMON.get(category)
    if not cfg:
        return category or "—"
    sub_title = (cfg["subcategories"] or {}).get(subcategory)
    return f"{cfg['title']} / {sub_title}" if sub_title else cfg["title"]


def remember_rd(*, rd_type: str, rd_name: str, rd_date: date, rd_date_to: date,
                category: str, subcategory: str | None, tnved_code: str | None, country: str | None,
                user_id: int | None) -> None:
    """Добавляет РД в реестр или отмечает повторное использование.

    Пишет в текущую сессию без commit - коммитит вызывающий код вместе с карточкой.
    Архивную запись не возвращает из архива: это решение администратора.
    """
    key = rd_key(rd_name)
    if not (rd_type and key and rd_date and rd_date_to):
        return

    stmt = insert(RdRegistryEntry).values(
        rd_type=rd_type,
        rd_name=rd_name,
        rd_date=rd_date,
        rd_date_to=rd_date_to,
        search_key=key,
        category=category or "",
        subcategory=_clean_subcategory(category, subcategory),
        tnved_code=(tnved_code or "").strip(),
        country=_clean_country(country),
        created_by_id=user_id,
    )
    db.session.execute(stmt.on_conflict_do_update(
        constraint="uq_rd_registry_key_dates_category_tnved_country",
        set_={"usage_count": RdRegistryEntry.usage_count + 1, "last_used_at": func.now()},
    ))


def search_rd(query: str | None, tnved: str | None = None, country: str | None = None) -> tuple[list[dict], bool]:
    """Подсказки для модалки карточки. Возвращает (записи, есть_ли_ещё).

    Запрос от 5 символов - поиск номера по всему реестру, РД с ТНВЭД карточки первыми.
    Без запроса - предзагрузка: РД с ТНВЭД карточки.
    Страна карточки сужает и то, и другое; если в карточке её ещё нет, ищем по всем странам.
    """
    key = rd_key(query)
    tnved = (tnved or "").strip()
    country = _clean_country(country)
    stmt = select(RdRegistryEntry).where(
        RdRegistryEntry.rd_date_to >= min_suggest_date(),
        RdRegistryEntry.is_archived.is_(False),
    )
    if country:
        stmt = stmt.where(RdRegistryEntry.country == country)
    if len(key) >= MIN_QUERY_LEN:
        stmt = stmt.where(RdRegistryEntry.search_key.contains(key))
        if tnved:
            stmt = stmt.order_by((RdRegistryEntry.tnved_code == tnved).desc())
    elif tnved:
        stmt = stmt.where(RdRegistryEntry.tnved_code == tnved)
    else:
        return [], False

    today = date.today()

    rows = db.session.execute(
        stmt.order_by(
            RdRegistryEntry.usage_count.desc(),
            RdRegistryEntry.last_used_at.desc(),
            RdRegistryEntry.id.desc(),
        )
        .limit(SEARCH_LIMIT + 1)
    ).scalars().all()

    items = [
        {
            "id": row.id,
            "rd_type": row.rd_type,
            "rd_name": row.rd_name,
            "rd_date": row.rd_date.strftime("%d.%m.%Y"),
            "rd_date_to": row.rd_date_to.strftime("%d.%m.%Y"),
            "days_left": (row.rd_date_to - today).days,
            "category": category_label(row.category, row.subcategory),
            "tnved_code": row.tnved_code,
            "country": row.country,
            "search_key": row.search_key,
        }
        for row in rows[:SEARCH_LIMIT]
    ]
    return items, len(rows) > SEARCH_LIMIT


def _type_stem(product_type: str | None) -> str:
    """Основа первого слова вида товара: «ПЛАТЬЕ» -> «плат», «ТУФЛИ» -> «туфл». Только для ранжирования."""
    words = re.findall(r"[а-яё]+", (product_type or "").lower())
    stem = re.sub(r"[аеёиоуыэюяьй]+$", "", words[0]) if words else ""
    return stem if len(stem) >= 3 else ""


def recommend_rd(tnved: str | None, country: str | None, product_type: str | None = None) -> list[dict]:
    """Проверенные РД из Tezaurus под карточку - блок над таблицей реестра в модалке.

    РД подходит, если ТНВЭД карточки начинается с одного из его кодов (у РД бывают и группы «6204»,
    и полные коды) и страна совпадает. Вид товара только поднимает РД выше: описания в Tezaurus
    свободным текстом. «До» не раньше чем через месяц - уже в get_valid_rd().
    """
    tnved = re.sub(r"\D", "", tnved or "")
    country = _clean_country(country)
    if not (tnved and country):
        return []
    stem = _type_stem(product_type)
    today = date.today()
    items = []
    for rd in get_valid_rd():
        codes = [code for code in map(str, rd.get("tnved_codes") or []) if code and tnved.startswith(code)]
        if not codes or _clean_country(rd.get("country")) != country:
            continue
        try:
            rd_date, rd_date_to = date.fromisoformat(rd["rd_date"]), date.fromisoformat(rd["rd_date_to"])
        except (KeyError, TypeError, ValueError):
            continue
        description = rd.get("description") or ""
        items.append({
            "rd_type": rd.get("rd_type") or "",
            "rd_name": rd.get("rd_name") or "",
            "rd_date": rd_date.strftime("%d.%m.%Y"),
            "rd_date_to": rd_date_to.strftime("%d.%m.%Y"),
            "days_left": (rd_date_to - today).days,
            "country": country,
            "tnved_code": max(codes, key=len),  # самый точный из совпавших кодов
            "description": description,
            "type_match": bool(stem) and stem in description.lower(),
        })
    items.sort(key=lambda item: (not item["type_match"], -item["days_left"]))
    return items[:RECOMMEND_LIMIT]


def list_rd(*, query: str | None = None, archived: bool = False, hide_expired: bool = False,
            category: str = "", rd_type: str = "", country: str = "", sort: str = "created", direction: str = "desc",
            page: int = 1):
    """Страница реестра для администрирования (Flask-SQLAlchemy Pagination)."""
    column = SORT_COLUMNS.get(sort, RdRegistryEntry.created_at)
    is_asc = direction == "asc"
    stmt = (
        select(RdRegistryEntry)
        .options(selectinload(RdRegistryEntry.created_by), selectinload(RdRegistryEntry.updated_by))
        .where(RdRegistryEntry.is_archived.is_(archived))
        # updated_at пустой у неправленых записей - они в конце в обе стороны
        .order_by(
            (column.asc() if is_asc else column.desc()).nulls_last(),
            RdRegistryEntry.id.asc() if is_asc else RdRegistryEntry.id.desc(),
        )
    )
    key = rd_key(query)
    if key:
        condition = RdRegistryEntry.search_key.contains(key)
        if key.isdigit():  # одни цифры - это может быть и начало ТНВЭД (6214 - шали)
            condition = condition | RdRegistryEntry.tnved_code.startswith(key)
        stmt = stmt.where(condition)
    if hide_expired:
        stmt = stmt.where(RdRegistryEntry.rd_date_to >= date.today())
    if category:
        stmt = stmt.where(RdRegistryEntry.category == category)
    if rd_type:
        stmt = stmt.where(RdRegistryEntry.rd_type == rd_type)
    if country:
        stmt = stmt.where(RdRegistryEntry.country == ("" if country == NO_COUNTRY else _clean_country(country)))
    return db.paginate(stmt, page=page, per_page=PAGE_SIZE, error_out=False)


def _get_entry(entry_id: int) -> RdRegistryEntry:
    entry = db.session.get(RdRegistryEntry, entry_id)
    if entry is None:
        raise ValueError("Запись реестра не найдена.")
    return entry


def save_rd(form, *, user_id: int, entry_id: int | None = None) -> RdRegistryEntry:
    """Ручное добавление (entry_id=None) или правка записи. Без commit.

    Правила как у блока РД карточки, кроме «До >= сегодня + 1 месяц»: достаточно «До >= От»,
    чтобы можно было поправить старую запись. Ошибки ввода - ValueError с текстом для пользователя.
    """
    rd_type = (form.get("rd_type") or "").strip()
    rd_name = (form.get("rd_name") or "").replace("№", "").strip()
    category = (form.get("category") or "").strip()
    subcategory = (form.get("subcategory") or "").strip()
    tnved_code = (form.get("tnved_code") or "").strip()
    country = _clean_country(form.get("country"))
    try:
        rd_date = date.fromisoformat(form.get("rd_date") or "")
        rd_date_to = date.fromisoformat(form.get("rd_date_to") or "")
    except ValueError:
        raise ValueError("Укажите даты «От» и «До».") from None

    if rd_type not in settings.RD_TYPES:
        raise ValueError("Выберите тип документа.")
    categories = category_choices()
    if category not in categories:
        raise ValueError("Выберите категорию.")
    if subcategory and subcategory not in categories[category]["subcategories"]:
        raise ValueError("Выберите подкатегорию из списка.")
    if not TNVED_RE.match(tnved_code):
        raise ValueError("ТНВЭД: 10 цифр.")
    if country not in get_all_countries():
        raise ValueError("Выберите страну.")
    key = rd_key(rd_name)
    if len(rd_name) > 100 or len(key) < 3:
        raise ValueError("Номер РД: от 3 до 100 символов.")
    if not RD_MIN_DATE <= rd_date <= date.today():
        raise ValueError(f"Дата «От» должна быть с {RD_MIN_DATE:%d.%m.%Y} по сегодня.")
    if rd_date_to < rd_date:
        raise ValueError("Дата «До» не может быть раньше даты «От».")

    duplicate = db.session.execute(
        select(RdRegistryEntry.is_archived).where(
            RdRegistryEntry.search_key == key,
            RdRegistryEntry.rd_date == rd_date,
            RdRegistryEntry.rd_date_to == rd_date_to,
            RdRegistryEntry.category == category,
            RdRegistryEntry.subcategory == subcategory,
            RdRegistryEntry.tnved_code == tnved_code,
            RdRegistryEntry.country == country,
            RdRegistryEntry.id != entry_id,
        )
    ).first()
    if duplicate:
        where = " в архиве" if duplicate.is_archived else ""
        raise ValueError(f"Такой РД с этими датами, категорией, ТНВЭД и страной уже есть{where}.")

    if entry_id is None:
        entry = RdRegistryEntry(usage_count=0, created_by_id=user_id)
        db.session.add(entry)
    else:
        entry = _get_entry(entry_id)
        entry.updated_by_id = user_id
        entry.updated_at = datetime.now()

    entry.rd_type = rd_type
    entry.rd_name = rd_name
    entry.rd_date = rd_date
    entry.rd_date_to = rd_date_to
    entry.search_key = key
    entry.category = category
    entry.subcategory = subcategory
    entry.tnved_code = tnved_code
    entry.country = country
    return entry


def set_archived(entry_id: int, archived: bool, *, user_id: int) -> RdRegistryEntry:
    """Архивирует или возвращает из архива. Без commit."""
    entry = _get_entry(entry_id)
    entry.is_archived = archived
    entry.updated_by_id = user_id
    entry.updated_at = datetime.now()
    return entry
