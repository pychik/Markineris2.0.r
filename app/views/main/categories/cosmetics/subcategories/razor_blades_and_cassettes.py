from views.main.categories.cosmetics.subcategories.data import CosmeticsSubcategories
from views.main.categories.cosmetics.subcategories.decor_ukhod import (
    DEFAULT_COUNTRIES,
    USAGE_TERM_TYPES,
)


SUBCATEGORY_SLUG = CosmeticsSubcategories.razor_blades_and_cassettes.value
SUBCATEGORY_TITLE = "Бритвы и лезвия"
SUBCATEGORY_CATEGORY_CODE = "30957 / 30958 / 231207"
CATEGORY_CODE_BY_TNVED = {
    "8212101000": "30958",
    "8212109000": "30957",
    "8212200000": "231207",
}
ALLOWED_TNVED_CODES = (
    "8212101000",
    "8212109000",
    "8212200000",
)
ALLOWED_TNVED_CHOICES = (
    ("8212101000", "Бритвы одноразовые"),
    ("8212109000", "Бритвы со сменными лезвиями / кассетами"),
    ("8212200000", "Лезвия / кассеты"),
)
NOMINAL_QUANTITY_TYPES = ("шт.", "пакетик", "пакетиков", "саше", "пара", "пары")
PRODUCT_TYPES = (
    "БРИТВА",
    "БРИТВА ОДНОРАЗОВАЯ",
    "БРИТВА Т-ОБРАЗНАЯ",
    "СТАНОК БРИТВЕННЫЙ",
    "СИСТЕМА БРИТВЕННАЯ",
    "ЛЕЗВИЕ ДЛЯ БРИТВЫ",
    "КАССЕТА ДЛЯ БРИТВЫ",
)
DEFAULT_COUNTRIES = DEFAULT_COUNTRIES
USAGE_TERM_TYPES = USAGE_TERM_TYPES
NOMINAL_QUANTITY_TYPES_BY_PRODUCT_TYPE = {}
CONTENT_TYPE_CHOICES = ()
FOR_CHILDREN_CHOICES = ()
COMPLECTATION_TRIGGER_PRODUCT_TYPES = ()
COMPLECTATION_TRIGGER_TNVED_CODES = (
    "8212109000",
)
TNVED_CODES_BY_PRODUCT_TYPE = {
    "БРИТВА ОДНОРАЗОВАЯ": ("8212101000",),
    "БРИТВА": ("8212101000", "8212109000"),
    "БРИТВА Т-ОБРАЗНАЯ": ("8212101000", "8212109000"),
    "СТАНОК БРИТВЕННЫЙ": ("8212101000", "8212109000"),
    "СИСТЕМА БРИТВЕННАЯ": ("8212109000",),
    "ЛЕЗВИЕ ДЛЯ БРИТВЫ": ("8212200000",),
    "КАССЕТА ДЛЯ БРИТВЫ": ("8212200000",),
}
