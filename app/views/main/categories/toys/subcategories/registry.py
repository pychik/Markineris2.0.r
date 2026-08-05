import views.main.categories.toys.subcategories.doll_accessories as doll_accessories


SUBCATEGORY_CONFIG = {
    doll_accessories.SUBCATEGORY_SLUG: {
        "slug": doll_accessories.SUBCATEGORY_SLUG,
        "title": doll_accessories.SUBCATEGORY_TITLE,
        "icon": "main_v2/img/icons/toys/doll_accessories.png",
        "category_code": doll_accessories.SUBCATEGORY_CATEGORY_CODE,
        "allowed_tnved_codes": doll_accessories.ALLOWED_TNVED_CODES,
        "allowed_tnved_choices": doll_accessories.ALLOWED_TNVED_CHOICES,
        "okpd2_choices_by_tnved": doll_accessories.OKPD2_CHOICES_BY_TNVED,
        "model_article_types": doll_accessories.MODEL_ARTICLE_TYPES,
        "product_types": doll_accessories.PRODUCT_TYPES,
        "material_choices": doll_accessories.MATERIAL_CHOICES,
        "min_child_age_choices": doll_accessories.MIN_CHILD_AGE_CHOICES,
        "usage_term_types": doll_accessories.USAGE_TERM_TYPES,
        "service_life_types": doll_accessories.SERVICE_LIFE_TYPES,
        "default_countries": doll_accessories.DEFAULT_COUNTRIES,
        "step_2_template": "helpers/toys/doll_accessories/2nd_step.html",
        "step_3_template": "helpers/toys/doll_accessories/3rd_step.html",
    },
}


def get_subcategory_config(subcategory: str | None) -> dict | None:
    if not subcategory:
        return None
    return SUBCATEGORY_CONFIG.get(subcategory)
