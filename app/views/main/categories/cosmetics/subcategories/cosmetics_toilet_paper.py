from views.main.categories.cosmetics.subcategories.data import CosmeticsSubcategories
from views.main.categories.cosmetics.subcategories.decor_ukhod import (
    DEFAULT_COUNTRIES,
    FOR_CHILDREN_CHOICES,
    USAGE_TERM_TYPES,
)


SUBCATEGORY_SLUG = CosmeticsSubcategories.cosmetics_toilet_paper.value
SUBCATEGORY_TITLE = "Бумага туалетная"
SUBCATEGORY_CATEGORY_CODE = "30647"
ALLOWED_TNVED_CODES = (
    "4818101000",
    "4818109000",
)
ALLOWED_TNVED_CHOICES = (
    (
        "4818101000",
        "Бумага туалетная массой 1 м2 каждого слоя 25 г или менее",
    ),
    (
        "4818109000",
        "Бумага туалетная массой 1 м2 каждого слоя более 25 г",
    ),
)
NOMINAL_QUANTITY_TYPES = ("шт",)
PRODUCT_TYPES = (
    "БУМАГА ТУАЛЕТНАЯ",
    "БУМАГА ТУАЛЕТНАЯ ВЛАЖНАЯ",
    "БУМАГА ТУАЛЕТНАЯ ЛИСТОВАЯ",
    "БУМАГА ТУАЛЕТНАЯ РУЛОННАЯ БЕЗ ГИЛЬЗЫ",
    "БУМАГА ТУАЛЕТНАЯ РУЛОННАЯ НА ГИЛЬЗЕ",
)
LAYERS_CHARACTERISTIC_CHOICES = (
    "ОДНОСЛОЙНОЕ",
    "ДВУХСЛОЙНОЕ",
    "ТРЁХСЛОЙНОЕ",
    "ЧЕТЫРЁХСЛОЙНОЕ",
    "ПЯТИСЛОЙНОЕ",
    "МНОГОСЛОЙНОЕ",
)
USAGE_TERM_TYPES = USAGE_TERM_TYPES
CONTENT_TYPE_CHOICES = ()
FOR_CHILDREN_CHOICES = FOR_CHILDREN_CHOICES
DEFAULT_COUNTRIES = DEFAULT_COUNTRIES
NOMINAL_QUANTITY_TYPES_BY_PRODUCT_TYPE = {}
CONTENT_TYPE_ENABLED = False
CONTENT_VALUE_ENABLED = True
FOR_CHILDREN_ENABLED = True
DEFAULT_CONTENT_LABEL = "Состав товара / материал изделия"
