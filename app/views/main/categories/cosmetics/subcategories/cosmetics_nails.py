from views.main.categories.cosmetics.subcategories.data import CosmeticsSubcategories
from views.main.categories.cosmetics.subcategories.decor_ukhod import (
    CONTENT_TYPE_CHOICES,
    DEFAULT_COUNTRIES,
    FOR_CHILDREN_CHOICES,
    USAGE_TERM_TYPES,
)


SUBCATEGORY_SLUG = CosmeticsSubcategories.cosmetics_nails.value
SUBCATEGORY_TITLE = "Средства и инструменты для маникюра и педикюра"
SUBCATEGORY_CATEGORY_CODE = "30122 / 30648"
CATEGORY_CODE_BY_TNVED = {
    "3304300000": "30122",
    "8214200000": "30648",
}
ALLOWED_TNVED_CODES = (
    "3304300000",
    "8214200000",
)
ALLOWED_TNVED_CHOICES = (
    ("3304300000", "Средства для маникюра и педикюра"),
    (
        "8214200000",
        "Наборы и инструменты маникюрные или педикюрные (включая пилки для ногтей)",
    ),
)
NOMINAL_QUANTITY_TYPES = ("мл", "л", "г", "кг", "шт")
PRODUCT_TYPES = (
    "АКРИЛ-ГЕЛЬ",
    "АКРИЛОВАЯ ПУДРА",
    "БАЗА",
    "БАЗА И ВЕРХНЕЕ ПОКРЫТИЕ",
    "БЛЕСК ДЛЯ НОГТЕЙ",
    "БЛЕСТКИ",
    "ВЕРХНЕЕ ПОКРЫТИЕ",
    "ГЕЛЬ",
    "ГЕЛЬ-КРАСКА",
    "ГЕЛЬ-ЛАК",
    "ГЕЛЬ-СКРАБ",
    "ЖИДКОЕ МЫЛО",
    "ЖИДКОСТЬ ДЛЯ СНЯТИЯ ЛАКА",
    "ЗАКРЕПЛЯЮЩЕЕ ПОКРЫТИЕ",
    "ЗАЩИТНОЕ ПОКРЫТИЕ",
    "ИНСТРУМЕНТЫ МАНИКЮРНЫЕ",
    "ИНСТРУМЕНТЫ МАНИКЮРНЫЕ И ПЕДИКЮРНЫЕ",
    "ИНСТРУМЕНТЫ ПЕДИКЮРНЫЕ",
    "КЛЕЙ",
    "КРАСКА",
    "КРЕМ",
    "КРЕМ ДЛЯ НОГТЕЙ",
    "КРЕМ-ГЕЛЬ",
    "ЛАК",
    "МАСЛО",
    "МУСС",
    "МЫЛО",
    "НАБОР ДЛЯ МАНИКЮРА",
    "НАБОР ДЛЯ МАНИКЮРА И ПЕДИКЮРА",
    "НАБОР ДЛЯ ПЕДИКЮРА",
    "НАСТОЙ",
    "ОБЕЗЖИРИВАТЕЛЬ",
    "ОСНОВА",
    "ПЕМЗА",
    "ПЕНА",
    "ПЕНКА",
    "ПИЛКИ ДЛЯ НОГТЕЙ",
    "РАЗБАВИТЕЛЬ ДЛЯ ЛАКА",
    "СКРАБ",
    "СМЕСЬ АРОМАТИЧЕСКАЯ",
    "СОЛЬ",
    "СРЕДСТВО ДЛЯ БЫСТРОГО ВЫСЫХАНИЯ ЛАКА",
    "СРЕДСТВО ДЛЯ НОГТЕЙ",
    "СРЕДСТВО ДЛЯ ОТБЕЛИВАНИЯ НОГТЕЙ",
    "СРЕДСТВО ДЛЯ УДАЛЕНИЯ КУТИКУЛЫ",
    "СРЕДСТВО ДЛЯ УКРЕПЛЕНИЯ НОГТЕЙ",
    "СУШКА ЛАКА",
    "СЫВОРОТКА",
    "ФИКСАТОР ЛАКА",
    "ФЛЮИД",
    "ЭМАЛЬ",
)
MEANS_PRODUCT_TYPES = (
    "АКРИЛ-ГЕЛЬ",
    "АКРИЛОВАЯ ПУДРА",
    "БАЗА",
    "БАЗА И ВЕРХНЕЕ ПОКРЫТИЕ",
    "БЛЕСК ДЛЯ НОГТЕЙ",
    "БЛЕСТКИ",
    "ВЕРХНЕЕ ПОКРЫТИЕ",
    "ГЕЛЬ",
    "ГЕЛЬ-КРАСКА",
    "ГЕЛЬ-ЛАК",
    "ГЕЛЬ-СКРАБ",
    "ЖИДКОЕ МЫЛО",
    "ЖИДКОСТЬ ДЛЯ СНЯТИЯ ЛАКА",
    "ЗАКРЕПЛЯЮЩЕЕ ПОКРЫТИЕ",
    "ЗАЩИТНОЕ ПОКРЫТИЕ",
    "КЛЕЙ",
    "КРАСКА",
    "КРЕМ",
    "КРЕМ ДЛЯ НОГТЕЙ",
    "КРЕМ-ГЕЛЬ",
    "ЛАК",
    "МАСЛО",
    "МУСС",
    "МЫЛО",
    "НАСТОЙ",
    "ОБЕЗЖИРИВАТЕЛЬ",
    "ОСНОВА",
    "ПЕМЗА",
    "ПЕНА",
    "ПЕНКА",
    "РАЗБАВИТЕЛЬ ДЛЯ ЛАКА",
    "СКРАБ",
    "СМЕСЬ АРОМАТИЧЕСКАЯ",
    "СОЛЬ",
    "СРЕДСТВО ДЛЯ БЫСТРОГО ВЫСЫХАНИЯ ЛАКА",
    "СРЕДСТВО ДЛЯ НОГТЕЙ",
    "СРЕДСТВО ДЛЯ ОТБЕЛИВАНИЯ НОГТЕЙ",
    "СРЕДСТВО ДЛЯ УДАЛЕНИЯ КУТИКУЛЫ",
    "СРЕДСТВО ДЛЯ УКРЕПЛЕНИЯ НОГТЕЙ",
    "СУШКА ЛАКА",
    "СЫВОРОТКА",
    "ФИКСАТОР ЛАКА",
    "ФЛЮИД",
    "ЭМАЛЬ",
)
TOOLS_PRODUCT_TYPES = (
    "ИНСТРУМЕНТЫ МАНИКЮРНЫЕ",
    "ИНСТРУМЕНТЫ МАНИКЮРНЫЕ И ПЕДИКЮРНЫЕ",
    "ИНСТРУМЕНТЫ ПЕДИКЮРНЫЕ",
    "НАБОР ДЛЯ МАНИКЮРА",
    "НАБОР ДЛЯ МАНИКЮРА И ПЕДИКЮРА",
    "НАБОР ДЛЯ ПЕДИКЮРА",
    "ПИЛКИ ДЛЯ НОГТЕЙ",
)
USAGE_TERM_TYPES = USAGE_TERM_TYPES
CONTENT_TYPE_CHOICES = CONTENT_TYPE_CHOICES
FOR_CHILDREN_CHOICES = FOR_CHILDREN_CHOICES
DEFAULT_COUNTRIES = DEFAULT_COUNTRIES
TNVED_CODES_BY_PRODUCT_TYPE = {
    **{product_type: ("3304300000",) for product_type in MEANS_PRODUCT_TYPES},
    **{product_type: ("8214200000",) for product_type in TOOLS_PRODUCT_TYPES},
}
NOMINAL_QUANTITY_TYPES_BY_PRODUCT_TYPE = {
    product_type: ("шт",)
    for product_type in TOOLS_PRODUCT_TYPES
}
CONTENT_TYPE_TRIGGER_TNVED_CODES = (
    "3304300000",
)
CONTENT_TYPE_TRIGGER_PRODUCT_TYPES = MEANS_PRODUCT_TYPES
CONTENT_LABEL_BY_TNVED = {
    "3304300000": "Состав товара",
    "8214200000": "Состав товара / материал изделия",
}
CONTENT_LABEL_BY_PRODUCT_TYPE = {
    **{product_type: "Состав товара" for product_type in MEANS_PRODUCT_TYPES},
    **{product_type: "Состав товара / материал изделия" for product_type in TOOLS_PRODUCT_TYPES},
}
DEFAULT_CONTENT_LABEL = "Состав товара"
COMPLECTATION_TRIGGER_PRODUCT_TYPES = ()
COMPLECTATION_TRIGGER_TNVED_CODES = (
    "8214200000",
)
SERVICE_LIFE_TRIGGER_PRODUCT_TYPES = MEANS_PRODUCT_TYPES
SERVICE_LIFE_TRIGGER_TNVED_CODES = (
    "3304300000",
)
