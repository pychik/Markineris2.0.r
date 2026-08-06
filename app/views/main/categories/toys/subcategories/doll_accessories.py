from views.main.categories.toys.subcategories.data import ToysSubcategories


SUBCATEGORY_SLUG = ToysSubcategories.doll_accessories.value
SUBCATEGORY_TITLE = "Аксессуары и принадлежности для кукол"
SUBCATEGORY_CATEGORY_CODE = "237033 / 551734"

ACCESSORIES_TNVED_CODE = "9503002900"
STROLLERS_TNVED_CODE = "9503001001"

ALLOWED_TNVED_CODES = (ACCESSORIES_TNVED_CODE, STROLLERS_TNVED_CODE)
ALLOWED_TNVED_CHOICES = (
    (ACCESSORIES_TNVED_CODE, "Части и принадлежности кукол, изображающих только людей"),
    (STROLLERS_TNVED_CODE, "Коляски для кукол"),
)

CATEGORY_CODE_BY_TNVED = {
    ACCESSORIES_TNVED_CODE: "237033",
    STROLLERS_TNVED_CODE: "551734",
}

OKPD2_CHOICES_BY_TNVED = {
    ACCESSORIES_TNVED_CODE: (
        ("32.40.13.111", "Одежда и ее принадлежности, обувь и головные уборы для кукол, изображающих людей"),
        ("32.40.13.119", "Аксессуары для кукол, изображающих людей, прочие"),
    ),
    STROLLERS_TNVED_CODE: (
        ("32.40.31.110", "Коляски для кукол"),
    ),
}

MODEL_ARTICLE_TYPES = ("Модель", "Артикул", "Модель / Артикул")

PRODUCT_TYPES = (
    "ЧАСТИ ДЛЯ КУКОЛ",
    "ПРИНАДЛЕЖНОСТИ ДЛЯ КУКОЛ",
    "ОДЕЖДА ДЛЯ КУКОЛ",
    "ПРИНАДЛЕЖНОСТИ ОДЕЖДЫ ДЛЯ КУКОЛ",
    "ОБУВЬ ДЛЯ КУКОЛ",
    "ГОЛОВНЫЕ УБОРЫ ДЛЯ КУКОЛ",
    "КОЛЯСКА ДЛЯ КУКОЛ",
    "КОЛЯСКА-ТРОСТЬ ДЛЯ КУКОЛ",
    "НЕТ В СПРАВОЧНИКЕ",
)

ALLOWED_TNVED_CODES_BY_PRODUCT_TYPE = {
    "ЧАСТИ ДЛЯ КУКОЛ": (ACCESSORIES_TNVED_CODE,),
    "ПРИНАДЛЕЖНОСТИ ДЛЯ КУКОЛ": (ACCESSORIES_TNVED_CODE,),
    "ОДЕЖДА ДЛЯ КУКОЛ": (ACCESSORIES_TNVED_CODE,),
    "ПРИНАДЛЕЖНОСТИ ОДЕЖДЫ ДЛЯ КУКОЛ": (ACCESSORIES_TNVED_CODE,),
    "ОБУВЬ ДЛЯ КУКОЛ": (ACCESSORIES_TNVED_CODE,),
    "ГОЛОВНЫЕ УБОРЫ ДЛЯ КУКОЛ": (ACCESSORIES_TNVED_CODE,),
    "КОЛЯСКА ДЛЯ КУКОЛ": (STROLLERS_TNVED_CODE,),
    "КОЛЯСКА-ТРОСТЬ ДЛЯ КУКОЛ": (STROLLERS_TNVED_CODE,),
    "НЕТ В СПРАВОЧНИКЕ": ALLOWED_TNVED_CODES,
}

MATERIAL_CHOICES = (
    "БАРХАТ",
    "БУМАГА",
    "ВАТА",
    "ДЕРЕВО",
    "ДРЕВЕСНО-ОПИЛОЧНАЯ МАССА",
    "ЗАМЕНИТЕЛЬ КОЖИ",
    "ИСКУССТВЕННЫЙ МЕХ",
    "КАРТОН",
    "КЕРАМИКА",
    "КОЖА",
    "МЕТАЛЛ",
    "МЕХ",
    "МЯГКОНАБИВНОЙ МАТЕРИАЛ",
    "НАБИВНОЙ МАТЕРИАЛ",
    "НЕТКАНЫЙ МАТЕРИАЛ",
    "ПАПЬЕ-МАШЕ",
    "ПЛАСТМАССА",
    "ПЛЮШ",
    "ПОЛИМЕРНЫЕ МАТЕРИАЛЫ",
    "РЕЗИНА",
    "СТЕКЛО",
    "ТКАНЬ",
    "ФАРФОР",
    "ФАЯНС",
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
