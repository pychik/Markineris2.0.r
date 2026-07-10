from views.main.categories.cosmetics.subcategories.data import CosmeticsSubcategories
from views.main.categories.cosmetics.subcategories.decor_ukhod import (
    CONTENT_TYPE_CHOICES,
    DEFAULT_COUNTRIES,
    FOR_CHILDREN_CHOICES,
    USAGE_TERM_TYPES,
)


SUBCATEGORY_SLUG = CosmeticsSubcategories.cosmetics_rascheski.value
SUBCATEGORY_TITLE = "Расчёски, щётки и гребни для волос"
SUBCATEGORY_CATEGORY_CODE = "30596"
ALLOWED_TNVED_CODES = (
    "9603293000",
    "9615110000",
    "9615190000",
)
ALLOWED_TNVED_CHOICES = (
    (
        "9603293000",
        "Щётки для волос",
    ),
    (
        "9615110000",
        "Расчески, гребни для волос и аналогичные предметы эбонитовые или пластмассовые",
    ),
    (
        "9615190000",
        "Расчески, гребни для волос и аналогичные предметы; шпильки для волос, зажимы для завивки, бигуди и аналогичные предметы",
    ),
)
NOMINAL_QUANTITY_TYPES = ("шт",)
PRODUCT_TYPES = (
    "ГРЕБЕНЬ",
    "ГРЕБЕНЬ ДЛЯ ВОЛОС",
    "РАСЧЁСКА",
    "РАСЧЁСКА ДЛЯ ВОЛОС",
    "РАСЧЁСКА ДЛЯ НАЧЕСА",
    "РАСЧЁСКА СКЕЛЕТНАЯ",
    "РАСЧЁСКА СКЛАДНАЯ",
    "РАСЧЁСКА-БРАШИНГ",
    "РАСЧЁСКА-ХВОСТИК",
    "ЩЁТКА",
    "ЩЁТКА ДЛЯ ВОЛОС",
    "ЩЁТКА ДЛЯ ВЫПРЯМЛЕНИЯ",
    "ЩЁТКА ДЛЯ УКЛАДКИ",
    "ЩЁТКА МАССАЖНАЯ",
)
USAGE_TERM_TYPES = USAGE_TERM_TYPES
CONTENT_TYPE_CHOICES = CONTENT_TYPE_CHOICES
FOR_CHILDREN_CHOICES = FOR_CHILDREN_CHOICES
DEFAULT_COUNTRIES = DEFAULT_COUNTRIES
NOMINAL_QUANTITY_TYPES_BY_PRODUCT_TYPE = {}
CONTENT_TYPE_ENABLED = False
DEFAULT_CONTENT_LABEL = "Состав товара / материал изделия"
