from views.main.categories.cosmetics.subcategories.data import CosmeticsSubcategories
from views.main.categories.cosmetics.subcategories.decor_ukhod import (
    CONTENT_TYPE_CHOICES,
    DEFAULT_COUNTRIES,
    FOR_CHILDREN_CHOICES,
    NOMINAL_QUANTITY_TYPES,
    USAGE_TERM_TYPES,
)


SUBCATEGORY_SLUG = CosmeticsSubcategories.cosmetics_aroma.value
SUBCATEGORY_TITLE = "Товары для ароматизации"
SUBCATEGORY_CATEGORY_CODE = "30624"
ALLOWED_TNVED_CODES = (
    "3307490000",
)
ALLOWED_TNVED_CHOICES = (
    (
        "3307490000",
        "Средства для ароматизации или дезодорирования воздуха помещений, включая благовония для религиозных обрядов",
    ),
)
NOMINAL_QUANTITY_TYPES = NOMINAL_QUANTITY_TYPES
PRODUCT_TYPES = (
    "ДИФФУЗОР АРОМАТИЧЕСКИЙ",
    "МАСЛО АРОМАТИЧЕСКОЕ",
    "АРОМАТИЗАТОР",
    "АРОМАТИЗАТОР ГЕЛЕВЫЙ",
    "БЛАГОВОНИЯ",
    "ДУХИ ИНТЕРЬЕРНЫЕ",
    "КОНЦЕНТРАТ ДЛЯ ОСВЕЖЕНИЯ И ДЕЗОДОРИРОВАНИЯ ВОЗДУХА",
    "ОСВЕЖИТЕЛЬ ВОЗДУХА",
    "ОСВЕЖИТЕЛЬ ВОЗДУХА АЭРОЗОЛЬНЫЙ",
    "ОСВЕЖИТЕЛЬ ВОЗДУХА ГЕЛЕВЫЙ",
    "САШЕ АРОМАТИЧЕСКОЕ",
    "СВЕЧА",
    "ТАБЛЕТКА АРОМАТИЧЕСКАЯ",
    "ШАРИКИ ГЕЛЕВЫЕ",
)
USAGE_TERM_TYPES = USAGE_TERM_TYPES
CONTENT_TYPE_CHOICES = CONTENT_TYPE_CHOICES
FOR_CHILDREN_CHOICES = FOR_CHILDREN_CHOICES
DEFAULT_COUNTRIES = DEFAULT_COUNTRIES
NOMINAL_QUANTITY_TYPES_BY_PRODUCT_TYPE = {}
