from views.main.categories.toys.subcategories.data import ToysSubcategories


SUBCATEGORY_SLUG = ToysSubcategories.electric_train_sets.value
SUBCATEGORY_TITLE = "Поезда электрические и наборы элементов для сборки моделей"
SUBCATEGORY_CATEGORY_CODE = ""

ELECTRIC_TRAIN_SETS_TNVED_CODE = "9503003000"

ALLOWED_TNVED_CODES = (ELECTRIC_TRAIN_SETS_TNVED_CODE,)
ALLOWED_TNVED_CHOICES = (
    (
        ELECTRIC_TRAIN_SETS_TNVED_CODE,
        'Поезда электрические, включая рельсы, светофоры и их прочие принадлежности; наборы элементов для сборки моделей в уменьшенном размере ("в масштабе")',
    ),
)

CATEGORY_CODE_BY_TNVED = {
    ELECTRIC_TRAIN_SETS_TNVED_CODE: SUBCATEGORY_CATEGORY_CODE,
}

OKPD2_CHOICES_BY_TNVED = {
    ELECTRIC_TRAIN_SETS_TNVED_CODE: (
        ("32.40.20.111", "Модели электрических поездов и их принадлежности в уменьшенном размере (в масштабе)"),
        ("32.40.20.112", "Модели электрических поездов в уменьшенном размере и их принадлежности прочие"),
        ("32.40.20.121", "Наборы пластмассовые"),
        ("32.40.20.122", "Наборы из прочих материалов"),
        ("32.40.20.123", "Модели в масштабе и прочие модели в уменьшенном размере, кроме моделей электропоездов"),
    ),
}

MODEL_ARTICLE_TYPES = ("Модель", "Артикул", "Модель / Артикул")

PRODUCT_TYPES = (
    "ВЕРТОЛЁТ",
    "ЖЕЛЕЗНАЯ ДОРОГА",
    "ЖЕЛЕЗНАЯ ДОРОГА С ПОЕЗДАМИ",
    "КОРАБЛЬ",
    "ЛОДКА",
    "МАШИНА",
    "НАБОР ИГРОВОЙ",
    "ПОЕЗД",
    "ПРИЦЕП",
    "САМОЛЁТ",
    "НЕТ В СПРАВОЧНИКЕ",
)

ALLOWED_TNVED_CODES_BY_PRODUCT_TYPE = {
    product_type: ALLOWED_TNVED_CODES
    for product_type in PRODUCT_TYPES
}

MATERIAL_CHOICES = (
    "БУМАГА",
    "ДЕРЕВО",
    "ДРЕВЕСНО-ОПИЛОЧНАЯ МАССА",
    "КАРТОН",
    "МЕТАЛЛ",
    "ПЛАСТМАССА",
    "ПОЛИМЕРНЫЕ МАТЕРИАЛЫ",
    "РЕЗИНА",
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
