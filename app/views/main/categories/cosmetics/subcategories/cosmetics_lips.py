from views.main.categories.cosmetics.subcategories.data import CosmeticsSubcategories
from views.main.categories.cosmetics.subcategories.decor_ukhod import (
    CONTENT_TYPE_CHOICES,
    DEFAULT_COUNTRIES,
    FOR_CHILDREN_CHOICES,
    NOMINAL_QUANTITY_TYPES,
    NOMINAL_QUANTITY_TYPES_BY_PRODUCT_TYPE,
    PRODUCT_TYPES,
    USAGE_TERM_TYPES,
)


SUBCATEGORY_SLUG = CosmeticsSubcategories.cosmetics_lips.value
SUBCATEGORY_TITLE = "Косметика для губ"
SUBCATEGORY_CATEGORY_CODE = "31051"
ALLOWED_TNVED_CODES = (
    "3304990000",
    "3304100000",
)
ALLOWED_TNVED_CHOICES = (
    (
        "3304990000",
        "Косметические средства или средства для макияжа и средства для ухода за кожей (кроме лекарственных), включая средства против загара или для загара; средства для маникюра или педикюра: прочие: прочие",
    ),
    (
        "3304100000",
        "Средства для макияжа губ",
    ),
)
NOMINAL_QUANTITY_TYPES = NOMINAL_QUANTITY_TYPES
PRODUCT_TYPES = PRODUCT_TYPES
USAGE_TERM_TYPES = USAGE_TERM_TYPES
CONTENT_TYPE_CHOICES = CONTENT_TYPE_CHOICES
FOR_CHILDREN_CHOICES = FOR_CHILDREN_CHOICES
DEFAULT_COUNTRIES = DEFAULT_COUNTRIES
NOMINAL_QUANTITY_TYPES_BY_PRODUCT_TYPE = NOMINAL_QUANTITY_TYPES_BY_PRODUCT_TYPE
