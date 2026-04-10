import time
import functools
import hashlib
from typing import Iterable, Tuple, Optional
from datetime import datetime
from flask import flash, jsonify, redirect, request, url_for, Response
from flask_login import current_user
from typing import Union, Any

from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
from werkzeug.datastructures import ImmutableMultiDict

from config import settings
from logger import logger
from models import db, Clothes, LinenSizesUnits, ProductCard, ClothesQuantitySize, Shoe, ShoeQuantitySize, Socks, \
    SocksQuantitySize, Linen, LinenQuantitySize, Parfum, UserProcessingCompany, ProcessingCompany, ModerationStatus
from utilities.categories_data.subcategories_data import ClothesSubcategories
from utilities.exceptions import SizeTypeException, CompanyPoolError
from utilities.saving_uts import process_input_str, get_clothes_size_type
from utilities.support import check_forbidden_words
from utilities.validators import ValidatorProcessor
from views.crm.schema import CompanyLite, is_forbidden_pair_by_inn
from views.main.categories.clothes.subcategories import ClothesSubcategoryProcessor


CATEGORIES_COMMON = {
    "shoes": {
        "title": "обувь",
        "model": Shoe,
        "rel_name": "shoes",
        "has_subcategory": False,
        "subcategories": None,
    },

    "linen": {
        "title": "белье",
        "model": Linen,
        "rel_name": "linen",
        "has_subcategory": False,
        "subcategories": None,
    },

    "parfum": {
        "title": "парфюм",
        "model": Parfum,
        "rel_name": "parfum",
        "has_subcategory": False,
        "subcategories": None,
    },

    "clothes": {
        "title": "одежда",
        "model": Clothes,
        "rel_name": "clothes",
        "has_subcategory": True,
        "subcategories": {
            "common": "одежда",
            "underwear": "нижнее белье",
            "swimming_accessories": "плавательные аксессуары",
            "hats": "шляпы",
            "gloves": "перчатки",
            "shawls": "шали",
        }
    },

    "socks": {
        "title": "носки и прочее",
        "model": Socks,
        "rel_name": "socks",
        "has_subcategory": False,
        "subcategories": None,
    },
}

CATEGORY_TITLES = {
        key: cfg["title"]
        for key, cfg in CATEGORIES_COMMON.items()
    }

CARD_FIELDS = {
    "clothes": {
        "article": "Артикул",
        "trademark": "Товарный знак",
        "type": "Тип",
        "color": "Цвет",
        "gender": "Пол",
        "content": "Состав",
        "country": "Страна",
        "tnved_code": "ТН ВЭД",
        "subcategory": "Подкатегория",
    },

    "socks": {
        "article": "Артикул",
        "trademark": "Товарный знак",
        "type": "Тип",
        "color": "Цвет",
        "gender": "Пол",
        "content": "Состав",
        "country": "Страна",
        "tnved_code": "ТН ВЭД",
    },

    "linen": {
        "article": "Артикул",
        "trademark": "Товарный знак",
        "color": "Цвет",
        "customer_age": "Возраст",
        "textile_type": "Тип текстиля",
        "content": "Состав",
        "country": "Страна",
        "tnved_code": "ТН ВЭД",
    },

    "shoes": {
        "article": "Артикул",
        "trademark": "Товарный знак",
        "color": "Цвет",
        "material_top": "Материал верха",
        "material_lining": "Материал подкладки",
        "material_bottom": "Материал подошвы",
        "gender": "Пол",
        "country": "Страна",
        "tnved_code": "ТН ВЭД",
    },

    "parfum": {
        "trademark": "Товарный знак",
        "type": "Тип",
        "volume": "Объем",
        "volume_type": "Ед. объема",
        "package_type": "Тип упаковки",
        "material_package": "Материал упаковки",
        "country": "Страна",
        "tnved_code": "ТН ВЭД",
    }
}


MODERATION_STATUS_COLORS = {
    "created": "info",        # голубой
    "sent": "secondary",        # серый
    "in_progress": "primary",   # синий
    "in_moderation": "warning",   # желтый
    "clarification": "warning", # жёлтый
    "approved": "success",      # зелёный
    "partially_approved": "success",      # зелёный
    "rejected": "danger",       # красный
}

MODERATION_STATUS_TITLES = {
    "created": "Создана",
    "sent": "Отправлена на модерацию",
    "sent_no_rd": "Отправлена на модерацию без РД",
    "in_progress": "В обработке",
    "in_moderation": "На модерации",
    "clarification": "На уточнении",
    "approved": "Одобрена",
    "partially_approved": "Частично одобрена",
    "rejected": "Отклонена",
}

CARD_STATUS_DATETIME_ATTR = {
    ModerationStatus.CREATED.value: "created_at",
    ModerationStatus.SENT_NO_RD.value: "sent_at",
    ModerationStatus.SENT.value: "sent_at",
    ModerationStatus.IN_PROGRESS.value: "taken_at",
    ModerationStatus.IN_MODERATION.value: "moderation_at",
    ModerationStatus.CLARIFICATION.value: "clarification_requested_at",
    ModerationStatus.APPROVED.value: "approved_at",
    ModerationStatus.PARTIALLY_APPROVED.value: "approved_at",
    ModerationStatus.REJECTED.value: "rejected_at",
}

ALLOWED_CARDS_DELETE_STATUSES = {
    ModerationStatus.CREATED,
    ModerationStatus.APPROVED,
    ModerationStatus.REJECTED,
    ModerationStatus.PARTIALLY_APPROVED,
}


def helper_clothes_info(subcategory: str | None) -> Union[Response,  dict[str, Any]]:

    # Формируем набор глобальных переменных для категории одежда и ее подкатегорий

    price_description = settings.PRICE_DESCRIPTION
    tnved_description = settings.TNVED_DESCRIPTION

    rd_description = settings.RD_DESCRIPTION
    rd_types_list = settings.RD_TYPES

    price_text = settings.PRICES_TEXT
    company_types = settings.COMPANY_TYPES
    edo_types = settings.EDO_TYPES
    tax_list = settings.TAX_LIST
    countries = settings.COUNTRIES_LIST
    rd_countries = settings.CLOTHES_COUNTRIES_RD

    clothes_content = settings.Clothes.CLOTHES_CONTENT
    clothes_nat_content = settings.Clothes.CLOTHES_NAT_CONTENT
    # colors = settings.Clothes.COLORS
    colors = settings.ALL_COLORS
    genders = settings.Clothes.GENDERS

    clothes_size_description = settings.Clothes.CLOTHES_SIZE_DESC
    category = settings.Clothes.CATEGORY
    category_process_name = settings.Clothes.CATEGORY_PROCESS
    (clothes_all_tnved, clothes_sizes,
     clothes_types_sizes_dict, types, subcategory_name) = ClothesSubcategoryProcessor(
        subcategory=subcategory, is_cards=True).get_creds()

    return locals()


def helper_shoes_info(subcategory: str | None) -> Union[Response, dict[str, Any]]:
    price_description = settings.PRICE_DESCRIPTION
    rd_description = settings.RD_DESCRIPTION
    rd_types_list = settings.RD_TYPES

    category = settings.Shoes.CATEGORY
    category_process_name = settings.Shoes.CATEGORY_PROCESS
    types = settings.Shoes.TYPES
    company_types = settings.COMPANY_TYPES
    edo_types = settings.EDO_TYPES
    tax_list = settings.TAX_LIST
    countries = settings.COUNTRIES_LIST
    rd_countries = settings.CLOTHES_COUNTRIES_RD
    shoe_tnved = settings.Shoes.TNVED_CODE
    shoe_al = settings.Shoes.SHOE_AL
    shoe_ot = settings.Shoes.SHOE_OT
    shoe_nl = settings.Shoes.SHOE_NL
    shoe_sizes = settings.Shoes.SIZES_ALL
    shoe_size_description = settings.Shoes.SHOE_SIZE_DESC

    # colors = settings.Shoes.COLORS
    colors = settings.ALL_COLORS
    genders = settings.Shoes.GENDERS
    materials_up_linen = settings.Shoes.MATERIALS_UP_LINEN
    materials_bottom = settings.Shoes.MATERIALS_BOTTOM

    subcategory = request.args.get('subcategory', '')
    if subcategory:
        flash(message=settings.Messages.STRANGE_REQUESTS + f'подкатегория неизвестна сервису', category='error')
        return redirect(url_for(f'main.enter'))
    return locals()


def helper_socks_info(subcategory: str | None) -> Union[Response,  dict[str, Any]]:

    price_description = settings.PRICE_DESCRIPTION
    tnved_description = settings.TNVED_DESCRIPTION
    socks_all_tnved = settings.Socks.TNVED_ALL

    rd_description = settings.RD_DESCRIPTION
    rd_types_list = settings.RD_TYPES

    price_text = settings.PRICES_TEXT
    company_types = settings.COMPANY_TYPES
    edo_types = settings.EDO_TYPES
    tax_list = settings.TAX_LIST
    countries = settings.COUNTRIES_LIST
    rd_countries = settings.CLOTHES_COUNTRIES_RD
    socks_content = settings.Socks.CLOTHES_CONTENT
    socks_types_sizes_dict = settings.Socks.SIZE_ALL_DICT

    category = settings.Socks.CATEGORY
    category_process_name = settings.Socks.CATEGORY_PROCESS

    types = settings.Socks.TYPES
    # colors = settings.Clothes.COLORS
    colors = settings.ALL_COLORS
    genders = settings.Socks.GENDERS
    subcategory = request.args.get('subcategory', '')
    if subcategory:
        flash(message=settings.Messages.STRANGE_REQUESTS + f'подкатегория неизвестна сервису', category='error')
        return redirect(url_for(f'main.enter'))
    return locals()


def helper_linen_info(subcategory: str | None) -> Union[Response, dict[str, Any]]:

    category = settings.Linen.CATEGORY
    category_process_name = settings.Linen.CATEGORY_PROCESS

    price_description = settings.PRICE_DESCRIPTION
    tnved_description = settings.TNVED_DESCRIPTION
    linen_tnved = settings.Linen.TNVED_CODE
    rd_description = settings.RD_DESCRIPTION
    rd_types_list = settings.RD_TYPES

    price_text = settings.PRICES_TEXT
    company_types = settings.COMPANY_TYPES
    edo_types = settings.EDO_TYPES
    tax_list = settings.TAX_LIST
    countries = settings.COUNTRIES_LIST
    rd_countries = settings.CLOTHES_COUNTRIES_RD

    types = settings.Linen.TYPES_CARDS
    # colors = settings.Linen.COLORS
    colors = settings.ALL_COLORS
    textile_types = settings.Linen.TEXTILE_TYPES
    customer_ages = settings.Linen.CUSTOMER_AGES
    box_quantity_description = settings.Linen.BOX_QUANTITY_DESCRIPTION
    size_units = LinenSizesUnits.choices()
    subcategory = request.args.get('subcategory', '')
    if subcategory:
        flash(message=settings.Messages.STRANGE_REQUESTS + f'подкатегория неизвестна сервису', category='error')
        return redirect(url_for(f'main.enter'))
    return locals()


def helper_parfum_info(subcategory: str | None) -> Union[Response, dict[str, Any]]:
    price_description = settings.PRICE_DESCRIPTION
    tnved_description = settings.TNVED_DESCRIPTION
    parfum_tnved = settings.Parfum.TNVED_CODE
    rd_description = settings.RD_DESCRIPTION
    rd_types_list = settings.RD_TYPES

    price_text = settings.PRICES_TEXT
    company_types = settings.COMPANY_TYPES
    edo_types = settings.EDO_TYPES
    tax_list = settings.TAX_LIST
    countries = settings.COUNTRIES_LIST
    rd_countries = settings.CLOTHES_COUNTRIES_RD

    category = settings.Parfum.CATEGORY
    category_process_name = settings.Parfum.CATEGORY_PROCESS
    types = settings.Parfum.TYPES
    volume_types = settings.Parfum.VOLUMES
    package_types = settings.Parfum.PACKAGE_TYPES
    material_packages = settings.Parfum.MATERIAL_PACKAGES
    price_text = settings.PRICES_TEXT

    subcategory = request.args.get('subcategory', '')
    if subcategory:
        flash(message=settings.Messages.STRANGE_REQUESTS + f'подкатегория неизвестна сервису', category='error')
        return redirect(url_for(f'main.enter'))

    return locals()


def validate_card_form(category_process: str, subcategory: str, form_data: ImmutableMultiDict):
    """
    Валидирует данные карточки.
    Генерирует Exception если ошибка.
    """
    cfg = CATEGORIES_COMMON.get(category_process)
    if not cfg:
        raise ValueError("Неизвестная категория")

    has_subcat = cfg.get("has_subcategory", False)

    # -------------------------
    # 0. Проверка подкатегории
    # -------------------------

    if has_subcat:
        # категория (например clothes) ОБЯЗАТЕЛЬНО должна иметь подкатегорию
        valid_subcats = [s.value for s in ClothesSubcategories]

        if not subcategory:
            # по умолчанию "common"
            subcategory = ClothesSubcategories.common.value

        if subcategory not in valid_subcats:
            raise ValueError(f"Подкатегория '{subcategory}' не существует для категории '{cfg.get('title')}'.")
    # else:
    #     # Если категория НЕ поддерживает подкатегории, но subcategory передана → ошибка
    #     if subcategory:
    #         raise ValueError(f"Категория '{category}' не имеет подкатегорий.")

    # 1. Запрещённые слова
    check_forbidden_words(form_data.get("article", "").strip(), "article")
    check_forbidden_words(form_data.get("trademark", "").strip(), "trademark")
    category_title = CATEGORIES_COMMON.get(category_process).get('title').lower()

    # 2. Цвета (кроме парфюма)
    if category_process != settings.Parfum.CATEGORY_PROCESS:
        color = form_data.get("color")
        if ValidatorProcessor.check_colors(color=color):
            raise ValueError(settings.Messages.COLOR_INPUT_ERROR.format(color=color))

    # 3. TНВЭД
    if ValidatorProcessor.check_tnveds(
        category=category_title,
        subcategory=subcategory,
        tnved_str=form_data.get("tnved_code")
    ):
        raise ValueError(settings.Messages.TNVED_ABSENCE_ERROR)

    # # 4. RD документация
    # rd_name = form_data.get("rd_name")
    # rd_type = form_data.get("rd_type")
    # if (rd_name and not rd_type) or (rd_type and not rd_name):
    #     raise ValueError("Поля разрешительной документации должны быть заполнены полностью или пусты.")

    return True


def parse_sizes_for_category(category: str, form_data_raw, subcategory: str | None = None) -> list[tuple]:
    """
    Возвращает список sizes_quantities в зависимости от категории.

    Для:
      - clothes, socks: (size, quantity, size_type)
      - shoes:          (size, quantity)
      - linen:          (size_str "X*Y", size_unit, quantity)

    form_data_raw — обычно request.form (ImmutableMultiDict).
    subcategory сейчас не используется, но оставлен на будущее.
    """
    category_process = CATEGORIES_COMMON.get(category).get('title').lower()
    if category_process == settings.Clothes.CATEGORY:
        sizes = form_data_raw.getlist("size")
        quantities = form_data_raw.getlist("quantity")
        size_types = form_data_raw.getlist("size_type")

        sizes_quantities = sorted(
            list(zip(sizes, quantities, size_types)),
            key=lambda x: x[0]
        )

    elif category_process == settings.Socks.CATEGORY:
        sizes = form_data_raw.getlist("size")
        quantities = form_data_raw.getlist("quantity")
        size_types = form_data_raw.getlist("size_type")

        sizes_quantities = sorted(
            list(zip(sizes, quantities, size_types)),
            key=lambda x: x[0]
        )

    elif category_process == settings.Shoes.CATEGORY:
        sizes = form_data_raw.getlist("size")
        quantities = form_data_raw.getlist("quantity")

        sizes_quantities = sorted(
            list(zip(sizes, quantities)),
            key=lambda x: x[0]
        )

    elif category_process == settings.Linen.CATEGORY:
        sizesX = form_data_raw.getlist("sizeX")
        sizesY = form_data_raw.getlist("sizeY")
        sizes = [f"{x}*{y}" for x, y in zip(sizesX, sizesY)]
        sizes_units = form_data_raw.getlist("sizeUnit")
        quantities = form_data_raw.getlist("quantity")

        sizes_quantities = sorted(
            list(zip(sizes, sizes_units, quantities)),
            key=lambda x: x[0]
        )

    else:
        raise Exception("Выбрана некорректная категория")

    return sizes_quantities


def normalize_article_for_category(category: str, form_dict: dict) -> str:
    """Приводим артикул к тому виду, в котором он лежит в БД."""
    raw = (form_dict.get("article") or "").strip()
    article = process_input_str(raw)
    # Во всех вещевых категориях такая же логика, как в save_*
    if article.upper() == "БЕЗ АРТИКУЛА":
        article = "ОТСУТСТВУЕТ"
    return article


def normalize_color_for_category(form_dict: dict) -> str:
    """Цвет хранится как значение из формы; для сравнения убираем лишние пробелы."""
    return (form_dict.get("color") or "").strip()


def collect_existing_size_keys(user_id: int, category: str, subcategory: str | None,
                               article: str, color: str | None = None, crm_: bool = False) -> tuple[set, set]:
    """
    Возвращает:
      - set ключей размеров
      - set id карточек, где они найдены
    """
    cfg = CATEGORIES_COMMON[category]
    model = cfg["model"]
    rel_name = cfg["rel_name"]
    has_subcategory = cfg.get("has_subcategory", False)

    rel = getattr(ProductCard, rel_name)

    q = (ProductCard.query
         .filter_by(user_id=user_id, category=category)
         .filter(ProductCard.status != ModerationStatus.REJECTED)
         .join(rel)
         .filter(model.article == article))

    if hasattr(model, "color"):
        q = q.filter(model.color == (color or ""))

    if has_subcategory and subcategory:
        # только для одежды
        q = q.filter(Clothes.subcategory == subcategory)

    cards = q.all()

    size_keys: set = set()
    card_ids: set[int] = set()

    if not cards:
        return size_keys, card_ids

    if category == settings.Clothes.CATEGORY_PROCESS:
        for card in cards:
            for c in card.clothes:
                if has_subcategory and subcategory and c.subcategory != subcategory:
                    continue
                for sq in c.sizes_quantities:
                    size_keys.add((sq.size, sq.size_type))
                    card_ids.add(card.id)

    elif category == settings.Socks.CATEGORY_PROCESS:
        for card in cards:
            for s in card.socks:
                for sq in s.sizes_quantities:
                    size_keys.add((sq.size, sq.size_type))
                    card_ids.add(card.id)

    elif category == settings.Shoes.CATEGORY_PROCESS:
        for card in cards:
            for sh in card.shoes:
                for sq in sh.sizes_quantities:
                    size_keys.add(sq.size)
                    card_ids.add(card.id)

    elif category == settings.Linen.CATEGORY_PROCESS:
        for card in cards:
            for l in card.linen:
                for sq in l.sizes_quantities:
                    size_keys.add((sq.size, sq.unit))
                    card_ids.add(card.id)

    # для парфюма пока не считаем "размеры"
    return size_keys, card_ids


def filter_new_sizes(category: str,
                     sizes_quantities: list,
                     existing_keys: set) -> tuple[list, list]:
    """
    На вход:
      sizes_quantities — то, что вернул parse_sizes_for_category.

    Возвращает:
      (новые_размеры, список_строк_пропущенных_размеров_для_сообщения)
    """
    new_sq: list = []
    skipped_labels: list = []

    if category == settings.Clothes.CATEGORY_PROCESS:
        # [(size, qty, size_type_raw)]
        for size, qty, size_type_raw in sizes_quantities:
            key = (size, get_clothes_size_type(size, size_type_raw))
            if key in existing_keys:
                skipped_labels.append(f"{size} ({size_type_raw})")
            else:
                new_sq.append((size, qty, size_type_raw))

    elif category == settings.Socks.CATEGORY_PROCESS:
        # [(size, qty, size_type_raw)]
        for size, qty, size_type_raw in sizes_quantities:
            # логика как в save_socks
            if size in settings.Socks.UNITE_SIZE_VALUES:
                eff_type = settings.Socks.DEFAULT_SIZE_TYPE
            else:
                eff_type = size_type_raw
            key = (size, eff_type)
            if key in existing_keys:
                skipped_labels.append(f"{size} ({size_type_raw})")
            else:
                new_sq.append((size, qty, size_type_raw))

    elif category == settings.Shoes.CATEGORY_PROCESS:
        # [(size, qty)]
        for size, qty in sizes_quantities:
            key = size
            if key in existing_keys:
                skipped_labels.append(str(size))
            else:
                new_sq.append((size, qty))

    elif category == settings.Linen.CATEGORY_PROCESS:
        # [(size, unit, qty)]
        for size, unit, qty in sizes_quantities:
            key = (size, unit)
            if key in existing_keys:
                skipped_labels.append(f"{size} {unit}")
            else:
                new_sq.append((size, unit, qty))
    else:
        # parfum и пр. — возвращаем как есть
        new_sq = sizes_quantities

    return new_sq, skipped_labels


# ---------- SHOES ----------
def save_shoes_card(
    card: ProductCard,
    form_dict: dict,
    sizes_quantities: list,
    subcategory: str | None = None,
) -> ProductCard:
    """
    Создаёт объект Shoe, привязанный к карточке (card_id), + размеры.
    sizes_quantities: [(size, quantity), ...]
    """
    rd_date = form_dict.get("_rd_date_obj")
    rd_date_to = form_dict.get("_rd_date_to_obj")

    article = process_input_str(form_dict.get("article") or "")
    article = article if article.upper() != 'БЕЗ АРТИКУЛА' else 'ОТСУТСТВУЕТ'

    shoe = Shoe(
        trademark=process_input_str(form_dict.get("trademark") or ""),
        article=article,
        type=form_dict.get("type"),
        color=form_dict.get("color"),
        box_quantity=form_dict.get("box_quantity"),
        material_top=form_dict.get("material_top"),
        material_lining=form_dict.get("material_lining"),
        material_bottom=form_dict.get("material_bottom"),
        gender=form_dict.get("gender"),
        country=form_dict.get("country"),
        with_packages=True if form_dict.get("with_packages") == "True" else False,
        tnved_code=form_dict.get("tnved_code"),
        article_price=form_dict.get("article_price"),
        tax=form_dict.get("tax"),
        rd_type=form_dict.get("rd_type"),
        rd_name=form_dict.get("rd_name"),
        rd_date=rd_date,
        rd_date_to=rd_date_to,
        card_id=card.id,
        # order_id оставляем None
    )

    extend_sq = (
        ShoeQuantitySize(size=el[0], quantity=1)
        for el in sizes_quantities
    )
    shoe.sizes_quantities.extend(extend_sq)

    db.session.add(shoe)
    return card


# # ---------- CLOTHES ----------
# def get_clothes_size_type(size: str, provided_type: str) -> str:
#     if not provided_type:
#         raise SizeTypeException("Тип размера не указан.")
#
#     provided_type = provided_type.strip()
#
#     valid_keys = settings.Clothes.SIZE_ALL_DICT.keys()
#     if provided_type not in valid_keys:
#         raise SizeTypeException(f"Неизвестный тип размера: '{provided_type}'.")
#
#     if provided_type == 'РОССИЯ':
#         valid_sizes = settings.Clothes.CLOTHES_ST_RUSSIA
#         if size not in valid_sizes:
#             raise SizeTypeException(
#                 f"Размер '{size}' не соответствует типу 'РОССИЯ'."
#             )
#         return settings.Clothes.DEFAULT_SIZE_TYPE
#
#     if provided_type == 'МЕЖДУНАРОДНЫЙ':
#         return settings.Clothes.INTERNATIONAL_SIZE_TYPE
#
#     if provided_type == 'ОСОБЫЕ_РАЗМЕРЫ':
#         return settings.Clothes.INTERNATIONAL_SIZE_TYPE
#
#     if provided_type == 'РОСТ':
#         return settings.Clothes.ROST_SIZE_TYPE
#
#     raise SizeTypeException(f"Не удалось определить size_type для '{provided_type}'.")


def save_clothes_card(
    card: ProductCard,
    form_dict: dict,
    sizes_quantities: list,
    subcategory: str | None = None,
) -> ProductCard:
    """
    sizes_quantities: [(size, quantity, size_type), ...]
    """
    rd_date = form_dict.get("_rd_date_obj")
    rd_date_to = form_dict.get("_rd_date_to_obj")

    article = process_input_str(form_dict.get("article") or "")
    article = article if article.upper() != 'БЕЗ АРТИКУЛА' else 'ОТСУТСТВУЕТ'

    clothes = Clothes(
        trademark=process_input_str(form_dict.get("trademark") or ""),
        article=article,
        type=form_dict.get("type"),
        color=form_dict.get("color"),
        content=(form_dict.get("content") or "")[:101],
        box_quantity=form_dict.get("box_quantity"),
        gender=form_dict.get("gender"),
        country=form_dict.get("country"),
        tnved_code=form_dict.get("tnved_code"),
        article_price=form_dict.get("article_price"),
        tax=form_dict.get("tax"),
        rd_type=form_dict.get("rd_type"),
        rd_name=form_dict.get("rd_name"),
        rd_date=rd_date,
        rd_date_to=rd_date_to,
        subcategory=subcategory or ClothesSubcategories.common.value,
        card_id=card.id,
        # order_id оставим None
    )

    extend_sq = (
        ClothesQuantitySize(
            size=el[0],
            quantity=1,
            size_type=get_clothes_size_type(el[0], el[2]),
        )
        for el in sizes_quantities
    )
    clothes.sizes_quantities.extend(extend_sq)

    db.session.add(clothes)
    return card


# ---------- SOCKS ----------

def save_socks_card(
    card: ProductCard,
    form_dict: dict,
    sizes_quantities: list,
    subcategory: str | None = None,
) -> ProductCard:
    """
    sizes_quantities: [(size, quantity, size_type), ...]
    """
    rd_date = form_dict.get("_rd_date_obj")
    rd_date_to = form_dict.get("_rd_date_to_obj")

    article = process_input_str(form_dict.get("article") or "")
    article = article if article.upper() != 'БЕЗ АРТИКУЛА' else 'ОТСУТСТВУЕТ'

    socks = Socks(
        trademark=process_input_str(form_dict.get("trademark") or ""),
        article=article,
        type=form_dict.get("type"),
        color=form_dict.get("color"),
        content=(form_dict.get("content") or "")[:101],
        box_quantity=form_dict.get("box_quantity"),
        gender=form_dict.get("gender"),
        country=form_dict.get("country"),
        tnved_code=form_dict.get("tnved_code"),
        article_price=form_dict.get("article_price"),
        tax=form_dict.get("tax"),
        rd_type=form_dict.get("rd_type"),
        rd_name=form_dict.get("rd_name"),
        rd_date=rd_date,
        rd_date_to=rd_date_to,
        card_id=card.id,
    )

    extend_sq = (
        SocksQuantitySize(
            size=el[0],
            quantity=1,
            size_type=(
                el[2]
                if el[0] not in settings.Socks.UNITE_SIZE_VALUES
                else settings.Socks.DEFAULT_SIZE_TYPE
            ),
        )
        for el in sizes_quantities
    )
    socks.sizes_quantities.extend(extend_sq)

    db.session.add(socks)
    return card


# ---------- LINEN ----------

def save_linen_card(
    card: ProductCard,
    form_dict: dict,
    sizes_quantities: list,
    subcategory: str | None = None,
) -> ProductCard:
    """
    sizes_quantities: [(size, unit, quantity), ...]
    size = "X*Y"
    """
    # with_p = form_dict.get("with_packages")
    with_p = "False"  # как у тебя в старом коде
    rd_date = form_dict.get("_rd_date_obj")
    rd_date_to = form_dict.get("_rd_date_to_obj")

    article = process_input_str(form_dict.get("article") or "")
    article = article if article.upper() != 'БЕЗ АРТИКУЛА' else 'ОТСУТСТВУЕТ'

    linen = Linen(
        trademark=process_input_str(form_dict.get("trademark") or ""),
        article=article,
        type=form_dict.get("type"),
        color=form_dict.get("color"),
        with_packages='да' if form_dict.get("with_packages") == "True" else 'нет',
        box_quantity=form_dict.get("box_quantity"),
        customer_age=form_dict.get("customer_age"),
        textile_type=form_dict.get("textile_type"),
        content=form_dict.get("content"),
        country=form_dict.get("country"),
        tnved_code=form_dict.get("tnved_code"),
        article_price=form_dict.get("article_price"),
        tax=form_dict.get("tax"),
        rd_type=form_dict.get("rd_type"),
        rd_name=form_dict.get("rd_name"),
        rd_date=rd_date,
        rd_date_to=rd_date_to,
        card_id=card.id,
    )

    if with_p == "True":
        # максимум по площади X*Y
        def area(tuple_sq):
            size_str = tuple_sq[0]  # "X*Y"
            try:
                x_str, y_str = size_str.split('*')
                return int(x_str) * int(y_str)
            except Exception:
                return 0

        max_sq = max(sizes_quantities, key=area)
        append_sq = LinenQuantitySize(size=max_sq[0], unit=max_sq[1], quantity=1)
        linen.sizes_quantities.append(append_sq)
    else:
        extend_sq = (
            LinenQuantitySize(size=el[0], unit=el[1], quantity=el[2])
            for el in sizes_quantities
        )
        linen.sizes_quantities.extend(extend_sq)

    db.session.add(linen)
    return card


# ---------- PARFUM ----------

def save_parfum_card(
    card: ProductCard,
    form_dict: dict,
    sizes_quantities: list | None = None,
    subcategory: str | None = None,
) -> ProductCard:
    """
    Для парфюма размеров нет, sizes_quantities не используется.
    """
    rd_date = form_dict.get("_rd_date_obj")
    rd_date_to = form_dict.get("_rd_date_to_obj")

    parfum = Parfum(
        trademark=process_input_str(form_dict.get("trademark") or ""),
        volume_type=form_dict.get("volume_type"),
        volume=form_dict.get("volume"),
        package_type=form_dict.get("package_type"),
        material_package=form_dict.get("material_package"),
        type=form_dict.get("type"),
        with_packages='да' if form_dict.get("with_packages") == "True" else 'нет',
        box_quantity=1,
        quantity=1,
        country=form_dict.get("country"),
        tnved_code=form_dict.get("tnved_code"),
        # article_price=form_dict.get("article_price"),
        # tax=form_dict.get("tax"),
        rd_type=form_dict.get("rd_type"),
        rd_name=form_dict.get("rd_name"),
        rd_date=rd_date,
        rd_date_to=rd_date_to,
        card_id=card.id,
        # is_approved оставляем по default=False
    )

    db.session.add(parfum)
    return card


def extract_card_main_and_sizes(card: ProductCard):
    """
    Возвращает main-объект (Clothes/Shoes/...) и список размеров для формы.
    quantity нигде не нужен — не возвращаем.
    """
    cfg = CATEGORIES_COMMON.get(card.category)
    if not cfg:
        raise ValueError("Неизвестная категория карточки")

    rel_name = cfg["rel_name"]  # shoes / clothes / ...
    items = getattr(card, rel_name)
    main = items[0] if items else None

    sizes = []

    if card.category == settings.Clothes.CATEGORY_PROCESS:
        for c in card.clothes:
            for sq in c.sizes_quantities:
                sizes.append({
                    "size": sq.size,
                    "size_type": sq.size_type,
                })

    elif card.category == settings.Socks.CATEGORY_PROCESS:
        for s in card.socks:
            for sq in s.sizes_quantities:
                sizes.append({
                    "size": sq.size,
                    "size_type": sq.size_type,
                })

    elif card.category == settings.Shoes.CATEGORY_PROCESS:
        for sh in card.shoes:
            for sq in sh.sizes_quantities:
                sizes.append({
                    "size": sq.size,
                })

    elif card.category == settings.Linen.CATEGORY_PROCESS:
        for l in card.linen:
            for sq in l.sizes_quantities:
                sizes.append({
                    "size": sq.size,
                    "unit": sq.unit,
                })

    elif card.category == settings.Parfum.CATEGORY_PROCESS:
        sizes = []

    return main, sizes


def get_card_ctx(category: str, subcategory: str | None = None) -> dict:

    category_ctx_builder = {
        "clothes": helper_clothes_info,
        "socks": helper_socks_info,
        "linen": helper_linen_info,
        "parfum": helper_parfum_info,
        "shoes": helper_shoes_info,
    }

    builder = category_ctx_builder[category]

    # все helper-ы принимают subcategory (кому не нужно — просто не используют)
    ctx = builder(subcategory=subcategory)

    return ctx


def check_same_fields_if_exists(*, category: str, subcategory: str | None, form_dict: dict):
    """
    Проверяет, существует ли у текущего пользователя товар с тем же ключом
    (артикул / товарный знак) в рамках категории, и валидирует допустимость
    создания новой карточки товара.

    Логика проверки зависит от категории:

    1. Категория "parfum"
       ------------------
       Для парфюма товарный знак (trademark) считается уникальным ключом
       товара у пользователя.

       Если у текущего пользователя уже существует карточка парфюма
       с таким же trademark, создание новой карточки запрещено.

       В этом случае выбрасывается исключение с сообщением:
       - что карточка с таким товарным знаком уже существует;
       - что пользователь должен либо удалить существующую карточку,
         либо изменить товарный знак в создаваемой.

       Остальные поля карточки при этом не сравниваются.

    2. Остальные категории (clothes, shoes, linen, socks)
       ---------------------------------------------------
       Для остальных категорий ключом товара считается комбинация
       артикул (article) + цвет (color)
       в рамках категории (и подкатегории, если она участвует в уникальности).

       Если у пользователя уже существует товар с тем же article + color:
       - все поля, перечисленные в CARD_FIELDS[category], должны полностью
         совпадать со значениями в базе данных;
       - изменение любых из этих полей запрещено.

       В случае расхождений выбрасывается исключение с перечислением полей,
       значения которых менять нельзя, и указанием старых и новых значений.

       Если все поля совпадают, проверка считается пройденной, а дальнейшая
       логика (например, проверка и добавление новых размеров) выполняется
       в других частях кода.

    Параметры:
        category (str):
            Категория товара (ключ из CATEGORIES_COMMON).

        subcategory (str | None):
            Подкатегория товара. Используется только для категорий,
            у которых подкатегория участвует в уникальности товара
            (например, clothes).

        form_dict (dict):
            Данные формы создания карточки товара.

    Исключения:
        Exception:
            Выбрасывается, если:
            - категория не существует;
            - для парфюма уже существует карточка с таким trademark;
            - для остальных категорий найден товар с тем же article + color,
              но значения защищённых полей не совпадают.

    Возвращаемое значение:
        None — если проверка пройдена и создание карточки разрешено.
    """

    def _norm(v):
        return ("" if v is None else str(v)).strip()

    if category not in CARD_FIELDS:
        raise Exception(f"Введена не существующая категория {category}")

    cfg = CATEGORIES_COMMON[category]
    model = cfg["model"]
    fields_to_lock = list(CARD_FIELDS[category].keys())

    # =========================
    # PARFUM: trademark уникален
    # =========================
    if category == settings.Parfum.CATEGORY_PROCESS:
        trademark = _norm(form_dict.get("trademark"))
        if not trademark:
            return  # или raise

        existing = (
            db.session.query(model)
            .join(ProductCard, ProductCard.id == model.card_id)
            .filter(
                ProductCard.user_id == current_user.id,
                ProductCard.category == category,
                ProductCard.status != ModerationStatus.REJECTED,
                model.trademark == trademark,
            )
            .first()
        )

        if existing:
            raise Exception(
                f"У вас уже есть карточка парфюма с товарным знаком '{trademark}' (ID {existing.card_id}). "
                f"Удалите существующую карточку или измените товарный знак в текущей."
            )
        return

    # =========================
    # ОСТАЛЬНЫЕ: article + совпадение полей
    # =========================
    article_norm = normalize_article_for_category(category, form_dict)
    color_norm = normalize_color_for_category(form_dict)
    key_value = _norm(article_norm)
    if not key_value:
        return

    q = (
        db.session.query(model)
        .join(ProductCard, ProductCard.id == model.card_id)
        .filter(
            ProductCard.user_id == current_user.id,
            ProductCard.category == category,
            ProductCard.status != ModerationStatus.REJECTED,
            model.article == article_norm,
        )
    )

    if hasattr(model, "color"):
        q = q.filter(model.color == color_norm)

    if cfg.get("has_subcategory") and hasattr(model, "subcategory"):
        q = q.filter(model.subcategory == subcategory)

    existing = q.first()
    if not existing:
        return

    diffs = []
    for field in fields_to_lock:
        label = CARD_FIELDS[category][field]

        if field == "article":
            form_val = _norm(normalize_article_for_category(category, form_dict))
        else:
            form_val = _norm(form_dict.get(field))

        db_val = _norm(getattr(existing, field, None))

        if db_val != form_val:
            diffs.append((label, db_val, form_val))

    if diffs:
        changed_labels = ", ".join(label for label, _, _ in diffs)
        details = "; ".join(f"{label}: было '{dbv}', стало '{fv}'" for label, dbv, fv in diffs)

        raise Exception(
            f"У вас уже есть карточка с артикулом '{key_value}' и цветом '{color_norm}' в категории '{category}'. "
            f"Менять значения нельзя для полей: {changed_labels}. "
            f"Несовпадения: {details}"
        )


def handle_company_removed(company_id: int):
    try:
        bindings = UserProcessingCompany.query.filter_by(company_id=company_id).all()
        affected_user_ids = sorted({b.user_id for b in bindings})

        for b in bindings:
            db.session.delete(b)

        # если пул теперь <2, require_user_two_companies кинет CompanyPoolError -> rollback всего удаления
        for uid in affected_user_ids:
            require_user_two_companies(uid)

            (ProductCard.query
             .filter(ProductCard.user_id == uid,
                     ProductCard.status != ModerationStatus.REJECTED)
             .update({ProductCard.status: ModerationStatus.PARTIALLY_APPROVED},
                     synchronize_session=False))

        db.session.commit()

    except CompanyPoolError:
        db.session.rollback()
        raise  # пусть админ-интерфейс покажет ошибку “в пуле меньше 2”
    except SQLAlchemyError:
        db.session.rollback()
        raise


def user_has_any_approved_company(user_id: int) -> bool:
    return (UserProcessingCompany.query
            .filter(UserProcessingCompany.user_id == user_id,
                    UserProcessingCompany.is_approved.is_(True))
            .first()) is not None


def set_user_cards_partially_approved(user_id: int):
    (ProductCard.query
     .filter(ProductCard.user_id == user_id,
             ProductCard.status.in_([
                 ModerationStatus.SENT,
                 ModerationStatus.SENT_NO_RD,
                 ModerationStatus.IN_PROGRESS,
                 ModerationStatus.IN_MODERATION,
                 ModerationStatus.CLARIFICATION,
                 ModerationStatus.APPROVED,
                 ModerationStatus.PARTIALLY_APPROVED,
             ]))
     .update({ProductCard.status: ModerationStatus.PARTIALLY_APPROVED}, synchronize_session=False))


def _hrw_score(user_id: int, company_id: int, salt: str) -> int:
    payload = f"{salt}|u:{user_id}|c:{company_id}".encode("utf-8")
    return int.from_bytes(
        hashlib.blake2b(payload, digest_size=8).digest(),
        "big"
    )


# def pick_two_companies_for_user(
#     user_id: int,
#     company_ids: Iterable[int],
#     salt: str,
# ) -> Optional[Tuple[int, int]]:
#     ids = list(company_ids)
#     if len(ids) < 2:
#         return None
#
#     scored = [(cid, _hrw_score(user_id, cid, salt)) for cid in ids]
#     scored.sort(key=lambda x: x[1], reverse=True)
#     return scored[0][0], scored[1][0]


def pick_two_companies_for_user_checked(
    user_id: int,
    companies: Iterable[CompanyLite],
    salt: str,
) -> Optional[Tuple[int, int]]:
    items = list(companies)
    if len(items) < 2:
        return None

    scored = [(c, _hrw_score(user_id, c.id, salt)) for c in items]
    scored.sort(key=lambda x: x[1], reverse=True)
    ordered = [c for c, _ in scored]

    # первая допустимая пара в порядке HRW
    for i in range(len(ordered) - 1):
        c1 = ordered[i]
        for j in range(i + 1, len(ordered)):
            c2 = ordered[j]
            if not is_forbidden_pair_by_inn(c1.inn, c2.inn):
                return c1.id, c2.id
    return None


def require_user_two_companies(user_id: int) -> tuple[int, int]:
    salt = "pc_companies_v1"


    pool_rows = (
        db.session.query(ProcessingCompany.id, ProcessingCompany.inn, ProcessingCompany.title)
        .filter(ProcessingCompany.is_active.is_(True))
        .order_by(ProcessingCompany.id.asc())
        .all()
    )
    pool = [CompanyLite(id=cid, title=(title or ""), inn=(inn or "")) for cid, title, inn in pool_rows]

    if len(pool) < 2:
        raise CompanyPoolError("В пуле меньше двух активных компаний. Обратитесь к администратору.")

    pool_by_id = {c.id: c for c in pool}

    # 1) текущие привязки 1/2
    rows = (
        UserProcessingCompany.query
        .options(joinedload(UserProcessingCompany.company))
        .filter(UserProcessingCompany.user_id == user_id)
        .filter(UserProcessingCompany.slot.in_([1, 2]))
        .order_by(UserProcessingCompany.slot.asc())
        .all()
    )

    by_slot = {r.slot: r for r in rows}

    # удалить (или считать отсутствующими) только неактивные
    active_bindings = []  # list[UserProcessingCompany] только с активной company
    for slot, r in list(by_slot.items()):
        if r.company and r.company.is_active:
            active_bindings.append(r)
        else:
            db.session.delete(r)
            by_slot.pop(slot, None)

    # helper: upsert слота
    def upsert(slot: int, company_id: int):
        r = by_slot.get(slot)
        if r:
            if r.company_id != company_id:
                r.company_id = company_id
                r.is_approved = True
            return
        db.session.add(UserProcessingCompany(
            user_id=user_id,
            slot=slot,
            company_id=company_id,
            is_approved=True,
        ))

    # helper: проверка пары по ids
    def ids_forbidden(cid1: int, cid2: int) -> bool:
        c1 = pool_by_id.get(cid1)
        c2 = pool_by_id.get(cid2)
        if not c1 or not c2:
            return False
        return is_forbidden_pair_by_inn(c1.inn, c2.inn)

    # если уже две активные и разные — и НЕ запрещённая пара — ничего не меняем
    if len(active_bindings) >= 2 and by_slot.get(1) and by_slot.get(2):
        cid1 = by_slot[1].company_id
        cid2 = by_slot[2].company_id
        if cid1 != cid2 and not ids_forbidden(cid1, cid2):
            return cid1, cid2
        # иначе (дубль или запрещённая пара) — пересобираем ниже

    # если есть ровно одна активная — сохраняем её (но всё равно учитываем запрет пары)
    keep_company_id = None
    keep_slot = None
    if len(active_bindings) == 1:
        keep_company_id = active_bindings[0].company_id
        keep_slot = active_bindings[0].slot

        # на всякий случай: если keep уже не в пуле активных (не должно быть) — сбрасываем
        if keep_company_id not in pool_by_id:
            keep_company_id = None
            keep_slot = None

    # Выбор 2х компаний с учётом запрещённых пар
    if keep_company_id is None:
        picked = pick_two_companies_for_user_checked(user_id, pool, salt)
        if not picked:
            raise CompanyPoolError("Невозможно подобрать 2 компании без запрещённых сочетаний.")
        c1_id, c2_id = picked
    else:
        keep = pool_by_id[keep_company_id]

        # кандидаты для второй: все кроме keep, и чтобы пара была разрешена
        candidates = [
            c for c in pool
            if c.id != keep_company_id and not is_forbidden_pair_by_inn(keep.inn, c.inn)
        ]
        if not candidates:
            raise CompanyPoolError("Недостаточно компаний для назначения без запрещённых сочетаний.")

        # детерминированно выбираем лучшую вторую по HRW
        scored = [(c, _hrw_score(user_id, c.id, salt)) for c in candidates]
        scored.sort(key=lambda x: x[1], reverse=True)
        second = scored[0][0]

        # раскладываем по слотам: сохраняем слот keep
        if keep_slot == 1:
            c1_id, c2_id = keep_company_id, second.id
        else:
            c1_id, c2_id = second.id, keep_company_id

    # финальная страховка
    if c1_id == c2_id:
        # не должно случиться, но перестрахуемся
        for c in pool:
            if c.id != c1_id:
                c2_id = c.id
                break

    if ids_forbidden(c1_id, c2_id):
        # теоретически не должно случиться, но лучше явно упасть
        raise CompanyPoolError("Подобралась запрещённая пара компаний. Обратитесь к администратору.")

    # upsert слотов 1/2
    upsert(1, c1_id)
    upsert(2, c2_id)

    db.session.flush()
    return c1_id, c2_id


def get_card_entity_for_prefill(card: ProductCard):
    if card.category == "clothes":
        return card.clothes[0] if card.clothes else None
    if card.category == "socks":
        return card.socks[0] if card.socks else None
    if card.category == "shoes":
        return card.shoes[0] if card.shoes else None
    if card.category == "linen":
        return card.linen[0] if card.linen else None
    if card.category == "parfum":
        return card.parfum[0] if card.parfum else None
    return None


def build_size_keys_for_incoming(category: str, sizes_quantities: list) -> set:
    keys = set()

    if category == settings.Clothes.CATEGORY_PROCESS:
        for size, qty, size_type_raw in sizes_quantities:
            keys.add((size, get_clothes_size_type(size, size_type_raw)))

    elif category == settings.Socks.CATEGORY_PROCESS:
        for size, qty, size_type_raw in sizes_quantities:
            if size in settings.Socks.UNITE_SIZE_VALUES:
                eff_type = settings.Socks.DEFAULT_SIZE_TYPE
            else:
                eff_type = size_type_raw
            keys.add((size, eff_type))

    elif category == settings.Shoes.CATEGORY_PROCESS:
        for size, qty in sizes_quantities:
            keys.add(size)

    elif category == settings.Linen.CATEGORY_PROCESS:
        for size, unit, qty in sizes_quantities:
            keys.add((size, unit))

    return keys


def assert_frozen_fields_unchanged(card: ProductCard, form_data):
    category = card.category

    if category == settings.Parfum.CATEGORY_PROCESS:
        parfum = card.parfum[0]
        # замораживаем trademark
        incoming_trademark = (form_data.get("trademark") or "").strip()
        if (parfum.trademark or "").strip() != incoming_trademark:
            raise ValueError("Нельзя менять товарный знак (карточка на уточнении).")

        # цвета у парфюма нет — пропускаем
        # sizes у парфюма нет — пропускаем
        return

    # не парфюм:
    entity = get_card_entity_for_prefill(card)
    if not entity:
        raise ValueError("Не удалось прочитать данные карточки для сравнения.")

    incoming_article = (form_data.get("article") or "").strip()
    db_article = (entity.article or "").strip()
    # если у тебя нормализация артикула (БЕЗ АРТИКУЛА → ОТСУТСТВУЕТ) — сравнивай нормализованно:
    incoming_article_norm = normalize_article_for_category(category, {"article": incoming_article})
    db_article_norm = normalize_article_for_category(category, {"article": db_article})
    if incoming_article_norm != db_article_norm:
        raise ValueError("Нельзя менять артикул (карточка на уточнении).")

    incoming_color = (form_data.get("color") or "").strip()
    db_color = (entity.color or "").strip()
    if incoming_color != db_color:
        raise ValueError("Нельзя менять цвет (карточка на уточнении).")

    # sizes: сравниваем набор ключей (как ты уже делаешь через collect_existing_size_keys)
    incoming_sq = parse_sizes_for_category(category=category, form_data_raw=form_data, subcategory=getattr(entity, "subcategory", None))
    db_keys, _ = collect_existing_size_keys(user_id=card.user_id,
        category=category,
        subcategory=getattr(entity, "subcategory", None),
        article=db_article_norm,
        color=db_color,
    )

    incoming_keys = build_size_keys_for_incoming(category, incoming_sq)

    if not (incoming_keys <= db_keys):
        raise ValueError("Нельзя добавлять новые размеры")


FROZEN_FIELDS = {
    "default": {"article", "color", "size", "size_type", "quantity", "sizeX", "sizeY", "sizeUnit"},
    "parfum": {"trademark"},
}


def update_card_allowed_fields(card: ProductCard, form_dict: dict, form_data):
    category = card.category

    # берём объект категории (первая запись)
    entity = get_card_entity_for_prefill(card)
    if not entity:
        raise ValueError("Нет данных категории в карточке")

    frozen = FROZEN_FIELDS["parfum"] if category == "parfum" else FROZEN_FIELDS["default"]

    # разрешённые поля = CARD_FIELDS[category] - frozen(по смыслу)
    for field in CARD_FIELDS[category].keys():
        if field in frozen:
            continue
        if hasattr(entity, field) and field in form_dict:
            setattr(entity, field, form_dict[field])

    if hasattr(entity, "rd_type"):
        entity.rd_type = (form_dict.get("rd_type") or "").strip() or None
    if hasattr(entity, "rd_name"):
        entity.rd_name = (form_dict.get("rd_name") or "").replace("№", "").strip() or None

        # даты берём распарсенные (которые положила validate_rd_block)
    if hasattr(entity, "rd_date"):
        entity.rd_date = form_dict.get("_rd_date_obj")
    if hasattr(entity, "rd_date_to"):
        entity.rd_date_to = form_dict.get("_rd_date_to_obj")


def json_response(message: str, status: str = "success", code: int = 200, **extra):
    payload = {"status": status, "message": message, **extra}
    resp = jsonify(payload)
    resp.status_code = code
    return resp


def card_has_rd(card: ProductCard) -> bool:
    cat = card.category

    def _has_rd_on_item(it) -> bool:
        # return any(
        #     getattr(it, "rd_date", None) and
        #     getattr(it, "rd_type", None) and
        #     getattr(it, "rd_name", None)
        #     for it in (card.clothes or [])
        # )
        return bool(getattr(it, "rd_date", None))

    if cat == "shoes":
        return any(_has_rd_on_item(it) for it in (card.shoes or []))
    if cat == "clothes":
        return any(_has_rd_on_item(it) for it in (card.clothes or []))
    if cat == "socks":
        return any(_has_rd_on_item(it) for it in (card.socks or []))
    if cat == "linen":
        return any(_has_rd_on_item(it) for it in (card.linen or []))
    if cat == "parfum":
        return any(_has_rd_on_item(it) for it in (card.parfum or []))

    return False


def profile_db_verbose(name=None, max_sql=100):
    def dec(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            q = []
            sql_time = 0.0

            def before(conn, cursor, statement, parameters, context, executemany):
                context._t0 = time.perf_counter()

            def after(conn, cursor, statement, parameters, context, executemany):
                nonlocal sql_time
                sql_time += (time.perf_counter() - context._t0)
                if len(q) < max_sql:
                    q.append(statement.strip().replace("\n", " ")[:220])

            event.listen(db.engine, "before_cursor_execute", before)
            event.listen(db.engine, "after_cursor_execute", after)

            t0 = time.perf_counter()
            try:
                return fn(*args, **kwargs)
            finally:
                total = time.perf_counter() - t0
                event.remove(db.engine, "before_cursor_execute", before)
                event.remove(db.engine, "after_cursor_execute", after)

                msg = (f"[PROFILE] {name or fn.__name__} total={total*1000:.1f}ms "
                       f"sql={sql_time*1000:.1f}ms ({len(q)}+ queries) "
                       f"python={(total - sql_time)*1000:.1f}ms")

                logger.info(msg)
                for i, s in enumerate(q, 1):
                    logger.info(f"  [SQL {i}] {s}")
        return wrapper
    return dec

