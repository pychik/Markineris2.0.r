from views.main.categories.cosmetics.subcategories.data import CosmeticsSubcategories
from views.main.categories.cosmetics.subcategories.decor_ukhod import (
    CONTENT_TYPE_CHOICES,
    DEFAULT_COUNTRIES,
    FOR_CHILDREN_CHOICES,
    NOMINAL_QUANTITY_TYPES,
    USAGE_TERM_TYPES,
)


SUBCATEGORY_SLUG = CosmeticsSubcategories.cosmetics_deodorants.value
SUBCATEGORY_TITLE = "Дезодоранты, антиперспиранты"
SUBCATEGORY_CATEGORY_CODE = "30611"
ALLOWED_TNVED_CODES = (
    "3307200000",
)
ALLOWED_TNVED_CHOICES = (
    (
        "3307200000",
        "Дезодоранты и антиперспиранты индивидуального назначения",
    ),
)
NOMINAL_QUANTITY_TYPES = NOMINAL_QUANTITY_TYPES
PRODUCT_TYPES = (
    "АНТИПЕРСПИРАНТ",
    "ДЕЗОДОРАНТ",
    "ДЕЗОДОРАНТ-АНТИПЕРСПИРАНТ",
)
USAGE_TERM_TYPES = USAGE_TERM_TYPES
CONTENT_TYPE_CHOICES = CONTENT_TYPE_CHOICES
FOR_CHILDREN_CHOICES = FOR_CHILDREN_CHOICES
DEFAULT_COUNTRIES = DEFAULT_COUNTRIES
NOMINAL_QUANTITY_TYPES_BY_PRODUCT_TYPE = {}
