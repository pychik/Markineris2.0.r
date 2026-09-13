from views.main.categories.toys.subcategories.data import ToysSubcategories


SUBCATEGORY_SLUG = ToysSubcategories.card_games.value
SUBCATEGORY_TITLE = "Карточные игры"
SUBCATEGORY_CATEGORY_CODE = "551746"

CARD_GAMES_TNVED_CODE = "9504400000"

ALLOWED_TNVED_CODES = (CARD_GAMES_TNVED_CODE,)
ALLOWED_TNVED_CHOICES = (
    (CARD_GAMES_TNVED_CODE, "Карточные игры"),
)

CATEGORY_CODE_BY_TNVED = {
    CARD_GAMES_TNVED_CODE: SUBCATEGORY_CATEGORY_CODE,
}

OKPD2_CHOICES_BY_TNVED = {
    CARD_GAMES_TNVED_CODE: (
        ("32.40.41.000", "Карты игральные"),
    ),
}

MODEL_ARTICLE_TYPES = ("Модель", "Артикул", "Модель / Артикул")

PRODUCT_TYPES = (
    "ИГРА КАРТОЧНАЯ",
    "НЕТ В СПРАВОЧНИКЕ",
)

ALLOWED_TNVED_CODES_BY_PRODUCT_TYPE = {
    product_type: ALLOWED_TNVED_CODES
    for product_type in PRODUCT_TYPES
}

MATERIAL_CHOICES = (
    "ДЕРЕВО",
    "КАРТОН",
    "МЕТАЛЛ",
    "ПЛАСТМАССА",
    "ПОЛИМЕРНЫЕ МАТЕРИАЛЫ",
    "КОМБИНИРОВАННЫЙ",
)

MIN_CHILD_AGE_CHOICES = (
    "ОТ 0 МЕС",
    "ОТ 1 МЕС",
    "ОТ 2 МЕС",
    "ОТ 3 МЕС",
    "ОТ 4 МЕС",
    "ОТ 5 МЕС",
    "ОТ 6 МЕС",
    "ОТ 7 МЕС",
    "ОТ 8 МЕС",
    "ОТ 9 МЕС",
    "ОТ 10 МЕС",
    "ОТ 11 МЕС",
    "ОТ 1 ГОДА",
    "ОТ 1,5 ЛЕТ",
    "ОТ 2 ЛЕТ",
    "ОТ 3 ЛЕТ",
    "ОТ 4 ЛЕТ",
    "ОТ 5 ЛЕТ",
    "ОТ 6 ЛЕТ",
    "ОТ 7 ЛЕТ",
    "ОТ 8 ЛЕТ",
    "ОТ 9 ЛЕТ",
    "ОТ 10 ЛЕТ",
    "ОТ 11 ЛЕТ",
    "ОТ 12 ЛЕТ",
    "ОТ 13 ЛЕТ",
    "ОТ 14 ЛЕТ",
)

USAGE_TERM_TYPES = (
    "СРОК ГОДНОСТИ",
    "СРОК СЛУЖБЫ",
    "СРОК ИСПОЛЬЗОВАНИЯ НЕ УСТАНАВЛИВАЕТСЯ",
)

SERVICE_LIFE_TYPES = ("сут; дн", "мес", "г; лет")
DEFAULT_COUNTRIES = ("ГОНКОНГ", "РОССИЯ", "КИТАЙ")
