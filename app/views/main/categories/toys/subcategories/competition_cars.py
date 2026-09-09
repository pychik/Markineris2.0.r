from views.main.categories.toys.subcategories.data import ToysSubcategories


SUBCATEGORY_SLUG = ToysSubcategories.competition_cars.value
SUBCATEGORY_TITLE = "Гоночные автомобили для соревновательных игр"
SUBCATEGORY_CATEGORY_CODE = "237079"

COMPETITION_CARS_TNVED_CODE = "9504901000"

ALLOWED_TNVED_CODES = (COMPETITION_CARS_TNVED_CODE,)
ALLOWED_TNVED_CHOICES = (
    (COMPETITION_CARS_TNVED_CODE, "Наборы электрических гоночных автомобилей для соревновательных игр"),
)

CATEGORY_CODE_BY_TNVED = {
    COMPETITION_CARS_TNVED_CODE: SUBCATEGORY_CATEGORY_CODE,
}

OKPD2_CHOICES_BY_TNVED = {
    COMPETITION_CARS_TNVED_CODE: (
        ("32.40.42.199", "Игры и изделия для игр прочие, не включенные в другие группировки"),
    ),
}

MODEL_ARTICLE_TYPES = ("Модель", "Артикул", "Модель / Артикул")

PRODUCT_TYPES = (
    "НАБОР ЭЛЕКТРИЧЕСКИХ ГОНОЧНЫХ АВТОМОБИЛЕЙ ДЛЯ СОРЕВНОВАТЕЛЬНЫХ ИГР",
    "НЕТ В СПРАВОЧНИКЕ",
)

ALLOWED_TNVED_CODES_BY_PRODUCT_TYPE = {
    "НАБОР ЭЛЕКТРИЧЕСКИХ ГОНОЧНЫХ АВТОМОБИЛЕЙ ДЛЯ СОРЕВНОВАТЕЛЬНЫХ ИГР": ALLOWED_TNVED_CODES,
    "НЕТ В СПРАВОЧНИКЕ": ALLOWED_TNVED_CODES,
}

MATERIAL_CHOICES = (
    "ДЕРЕВО",
    "МЕТАЛЛ",
    "ПЛАСТМАССА",
    "ПОЛИМЕРНЫЕ МАТЕРИАЛЫ",
    "ТКАНЬ",
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
