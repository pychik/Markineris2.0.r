from views.main.categories.cosmetics.subcategories.data import CosmeticsSubcategories
from views.main.categories.cosmetics.subcategories.decor_ukhod import (
    CONTENT_TYPE_CHOICES,
    DEFAULT_COUNTRIES,
    FOR_CHILDREN_CHOICES,
    USAGE_TERM_TYPES,
)


SUBCATEGORY_SLUG = CosmeticsSubcategories.cosmetics_mochalki.value
SUBCATEGORY_TITLE = "Мочалки и губки"
SUBCATEGORY_CATEGORY_CODE = "30644"
ALLOWED_TNVED_CODES = (
    "7323100000",
    "7418109000",
    "7615108001",
    "3924900001",
)
ALLOWED_TNVED_CHOICES = (
    (
        "7323100000",
        '"Шерсть" из черных металлов; мочалки для чистки кухонной посуды, подушечки для чистки или полировки, перчатки и аналогичные изделия',
    ),
    (
        "7418109000",
        "Прочие изделия столовые, кухонные или прочие изделия для бытовых нужд и их части; мочалки для чистки кухонной посуды, подушечки для чистки или полировки, перчатки и аналогичные изделия",
    ),
    (
        "7615108001",
        "Мочалки для чистки кухонной посуды, подушечки для чистки или полировки, перчатки и аналогичные изделия из алюминия",
    ),
    (
        "3924900001",
        "Прочие: посуда столовая и кухонная, приборы столовые и кухонные принадлежности, предметы домашнего обихода и предметы гигиены или туалета, из целлюлозы регенерированной",
    ),
)
NOMINAL_QUANTITY_TYPES = ("шт",)
PRODUCT_TYPES = (
    "ГУБКА",
    "КЕСЕ",
    "МОЧАЛКА",
    "МОЧАЛКА-ВАРЕЖКА",
    "МОЧАЛКА-ГУБКА",
    "МОЧАЛКА-ЛЕНТА",
    "МОЧАЛКА-ПОЛОТЕНЦЕ",
    "МОЧАЛКА-ПОЯС",
    "МОЧАЛКА-РОЗОЧКА",
    "МОЧАЛКА-ЩЁТКА",
    "ПОДУШЕЧКА",
    "ЩЁТКА",
)
USAGE_TERM_TYPES = USAGE_TERM_TYPES
CONTENT_TYPE_CHOICES = CONTENT_TYPE_CHOICES
FOR_CHILDREN_CHOICES = FOR_CHILDREN_CHOICES
DEFAULT_COUNTRIES = DEFAULT_COUNTRIES
NOMINAL_QUANTITY_TYPES_BY_PRODUCT_TYPE = {}
CONTENT_TYPE_ENABLED = False
DEFAULT_CONTENT_LABEL = "Состав товара / материал изделия"
