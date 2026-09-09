from views.main.categories.toys.subcategories.data import ToysSubcategories


SUBCATEGORY_SLUG = ToysSubcategories.puzzles.value
SUBCATEGORY_TITLE = "Головоломки"
SUBCATEGORY_CATEGORY_CODE = "237038"

WOODEN_PUZZLES_TNVED_CODE = "9503006100"
OTHER_PUZZLES_TNVED_CODE = "9503006900"

ALLOWED_TNVED_CODES = (WOODEN_PUZZLES_TNVED_CODE, OTHER_PUZZLES_TNVED_CODE)
ALLOWED_TNVED_CHOICES = (
    (WOODEN_PUZZLES_TNVED_CODE, "Головоломки деревянные"),
    (OTHER_PUZZLES_TNVED_CODE, "Головоломки прочие (кроме деревянных)"),
)

CATEGORY_CODE_BY_TNVED = {
    WOODEN_PUZZLES_TNVED_CODE: SUBCATEGORY_CATEGORY_CODE,
    OTHER_PUZZLES_TNVED_CODE: SUBCATEGORY_CATEGORY_CODE,
}

OKPD2_CHOICES_BY_TNVED = {
    WOODEN_PUZZLES_TNVED_CODE: (
        ("32.40.32.110", "Головоломки деревянные"),
    ),
    OTHER_PUZZLES_TNVED_CODE: (
        ("32.40.32.190", "Головоломки прочие"),
    ),
}

MODEL_ARTICLE_TYPES = ("Модель", "Артикул", "Модель / Артикул")

PRODUCT_TYPES = (
    "ГОЛОВОЛОМКА",
    "ИГРА ДОРОЖНАЯ",
    "ЛОГИЧЕСКАЯ ИГРА",
    "ЛОГИЧЕСКАЯ ИГРА-ГОЛОВОЛОМКА",
    "ПАЗЛ-ГОЛОВОЛОМКА",
    "НЕТ В СПРАВОЧНИКЕ",
)

ALLOWED_TNVED_CODES_BY_PRODUCT_TYPE = {
    "ГОЛОВОЛОМКА": ALLOWED_TNVED_CODES,
    "ИГРА ДОРОЖНАЯ": ALLOWED_TNVED_CODES,
    "ЛОГИЧЕСКАЯ ИГРА": ALLOWED_TNVED_CODES,
    "ЛОГИЧЕСКАЯ ИГРА-ГОЛОВОЛОМКА": ALLOWED_TNVED_CODES,
    "ПАЗЛ-ГОЛОВОЛОМКА": ALLOWED_TNVED_CODES,
    "НЕТ В СПРАВОЧНИКЕ": ALLOWED_TNVED_CODES,
}

MATERIAL_CHOICES = (
    "БУМАГА",
    "ДЕРЕВО",
    "КАРТОН",
    "МАГНИТ",
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
