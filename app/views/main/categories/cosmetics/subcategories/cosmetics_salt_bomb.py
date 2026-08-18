from views.main.categories.cosmetics.subcategories.data import CosmeticsSubcategories
from views.main.categories.cosmetics.subcategories.decor_ukhod import (
    CONTENT_TYPE_CHOICES,
    DEFAULT_COUNTRIES,
    FOR_CHILDREN_CHOICES,
    USAGE_TERM_TYPES,
)


SUBCATEGORY_SLUG = CosmeticsSubcategories.cosmetics_salt_bomb.value
SUBCATEGORY_TITLE = "Соли и бомбочки"
SUBCATEGORY_CATEGORY_CODE = "30606"
ALLOWED_TNVED_CODES = (
    "3307300000",
)
ALLOWED_TNVED_CHOICES = (
    (
        "3307300000",
        "Ароматизированные соли и прочие составы для принятия ванн",
    ),
)
NOMINAL_QUANTITY_TYPES = ("мл", "л", "г", "кг")
PRODUCT_TYPES = (
    "БОМБА",
    "БОМБОЧКА",
    "КОНФЕТТИ ДЛЯ ВАННЫ",
    "КОНЦЕНТРАТ ДЛЯ ВАННЫ",
    "МАСЛО",
    "ПЕНА ДЛЯ ВАННЫ",
    "СБОР ДЛЯ КУПАНИЯ",
    "СКРАБ",
    "СМЕСЬ АРОМАТИЧЕСКАЯ",
    "СОЛЬ",
    "СОЛЬ АРОМАТИЗИРОВАННАЯ",
    "СОЛЬ МОРСКАЯ",
    "ФИТОЭМУЛЬСИЯ",
    "ЭМУЛЬСИЯ",
)
USAGE_TERM_TYPES = USAGE_TERM_TYPES
CONTENT_TYPE_CHOICES = CONTENT_TYPE_CHOICES
FOR_CHILDREN_CHOICES = FOR_CHILDREN_CHOICES
DEFAULT_COUNTRIES = DEFAULT_COUNTRIES
NOMINAL_QUANTITY_TYPES_BY_PRODUCT_TYPE = {}
