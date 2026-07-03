from views.main.categories.cosmetics.subcategories.data import CosmeticsSubcategories
from views.main.categories.cosmetics.subcategories.decor_ukhod import (
    DEFAULT_COUNTRIES,
    USAGE_TERM_TYPES,
)


SUBCATEGORY_SLUG = CosmeticsSubcategories.cosmetics_tweezers.value
SUBCATEGORY_TITLE = "Пинцеты"
SUBCATEGORY_CATEGORY_CODE = "30956"
ALLOWED_TNVED_CODES = (
    "8203200001",
)
ALLOWED_TNVED_CHOICES = (
    (
        "8203200001",
        "Пинцеты",
    ),
)
NOMINAL_QUANTITY_TYPES = ("шт",)
PRODUCT_TYPES = (
    "ИНСТРУМЕНТ ДЛЯ УДАЛЕНИЯ ВОЛОС",
    "ПИНЦЕТ",
    "ПИНЦЕТ ДЛЯ БРОВЕЙ",
    "ПИНЦЕТ УНИВЕРСАЛЬНЫЙ",
    "СИСТЕМА ДЛЯ УДАЛЕНИЯ ВОЛОС",
)
USAGE_TERM_TYPES = USAGE_TERM_TYPES
CONTENT_TYPE_CHOICES = ()
FOR_CHILDREN_CHOICES = ()
DEFAULT_COUNTRIES = DEFAULT_COUNTRIES
NOMINAL_QUANTITY_TYPES_BY_PRODUCT_TYPE = {}
CONTENT_TYPE_ENABLED = False
CONTENT_VALUE_ENABLED = True
FOR_CHILDREN_ENABLED = False
DEFAULT_CONTENT_LABEL = "Состав товара / материал изделия"
