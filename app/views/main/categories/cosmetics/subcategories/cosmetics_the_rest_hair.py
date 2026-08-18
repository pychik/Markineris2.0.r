from views.main.categories.cosmetics.subcategories.data import CosmeticsSubcategories
from views.main.categories.cosmetics.subcategories.decor_ukhod import (
    CONTENT_TYPE_CHOICES,
    DEFAULT_COUNTRIES,
    FOR_CHILDREN_CHOICES,
    NOMINAL_QUANTITY_TYPES_BY_PRODUCT_TYPE,
)


SUBCATEGORY_SLUG = CosmeticsSubcategories.cosmetics_the_rest_hair.value
SUBCATEGORY_TITLE = "Прочие косметические средства для волос"
SUBCATEGORY_CATEGORY_CODE = "234573"
ALLOWED_TNVED_CODES = (
    "3305900009",
)
ALLOWED_TNVED_CHOICES = (
    (
        "3305900009",
        "Прочие косметические средства для волос",
    ),
)
NOMINAL_QUANTITY_TYPES = ("мл", "л", "г", "кг")
PRODUCT_TYPES = (
    "АКТИВАТОР",
    "БАЗА",
    "БАЛЬЗАМ",
    "БАЛЬЗАМ ОТТЕНОЧНЫЙ",
    "БАСМА",
    "БЛЕСК",
    "БРИЛЛИАНТИН",
    "ВОСК",
    "ГЕЛЬ",
    "КОМПЛЕКС ВОССТАНАВЛИВАЮЩИЙ",
    "КОНДИЦИОНЕР",
    "КОНДИЦИОНЕР СУХОЙ",
    "КОНЦЕНТРАТ",
    "КРАСКА",
    "КРАСКА ДЛЯ БРОВЕЙ",
    "КРАСКА ДЛЯ БРОВЕЙ И РЕСНИЦ",
    "КРАСКА-БАЛЬЗАМ",
    "КРАСКА-МУСС",
    "КРАСЯЩЕЕ ЖЕЛЕ",
    "КРЕМ",
    "КРЕМ-КОНДИЦИОНЕР",
    "КРЕМ-КРАСКА",
    "КРЕМ-МАСЛО",
    "КРЕМ-ОПОЛАСКИВАТЕЛЬ",
    "КРЕМ-ПЕНА",
    "КРЕМ-СПРЕЙ",
    "ЛОСЬОН",
    "МАСКА",
    "МАСКА ОТТЕНОЧНАЯ",
    "МАСЛО",
    "МОЛОЧКО",
    "МУСС",
    "ОПОЛАСКИВАТЕЛЬ",
    "ОПОЛАСКИВАТЕЛЬ ОТТЕНОЧНЫЙ",
    "ПАСТА",
    "ПЕНА",
    "ПЕНКА",
    "ПИЛИНГ",
    "ПОМАДА ДЛЯ ВОЛОС",
    "ПРАЙМЕР",
    "ПРОДУКЦИЯ ДЛЯ ОСВЕТЛЕНИЯ ВОЛОС",
    "ПУДРА",
    "СКРАБ",
    "СПРЕЙ",
    "СПРЕЙ ДЛЯ ВОЛОС",
    "СПРЕЙ-БАЛЬЗАМ",
    "СПРЕЙ-ВОСК",
    "СПРЕЙ-КОНДИЦИОНЕР",
    "СПРЕЙ-МУСС",
    "СПРЕЙ-ОСНОВА",
    "СПРЕЙ ТОНИРУЮЩИЙ",
    "СРЕДСТВО ДЛЯ ВОЛОС",
    "СРЕДСТВО ДЛЯ ОСВЕТЛЕНИЯ ВОЛОС",
    "СЫВОРОТКА",
    "ТОН",
    "ТОНИК",
    "ТУШЬ",
    "УКСУС",
    "ФИЛЛЕР",
    "ФЛЮИД",
    "ХНА",
    "ЭЛИКСИР",
    "ЭССЕНЦИЯ",
)
USAGE_TERM_TYPES = (
    "СРОК ГОДНОСТИ",
    "СРОК СЛУЖБЫ",
    "СРОК ИСПОЛЬЗОВАНИЯ НЕ УСТАНАВЛИВАЕТСЯ",
)
CONTENT_TYPE_CHOICES = CONTENT_TYPE_CHOICES
FOR_CHILDREN_CHOICES = FOR_CHILDREN_CHOICES
DEFAULT_COUNTRIES = DEFAULT_COUNTRIES
MASK_PRODUCT_TYPES = (
    "МАСКА",
    "МАСКА ОТТЕНОЧНАЯ",
)
NOMINAL_QUANTITY_TYPES_BY_PRODUCT_TYPE = {
    **{
        product_type: ("г", "мл")
        for product_type in MASK_PRODUCT_TYPES
    },
    **NOMINAL_QUANTITY_TYPES_BY_PRODUCT_TYPE,
}
