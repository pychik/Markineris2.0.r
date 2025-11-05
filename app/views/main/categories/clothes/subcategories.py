from config import settings
from models import ClothesSubcategories
from utilities.categories_data.accessories_data import HATS_TNVED_DICT, HATS_TYPES, HATS_NAME, GLOVES_TNVED_DICT, \
    GLOVES_TYPES, GLOVES_NAME, SHAWLS_TNVED_DICT, SHAWLS_TYPES, SHAWLS_NAME, HATS_TNVEDS, GLOVES_TNVEDS, SHAWLS_TNVEDS
from utilities.categories_data.clothes_common.tnved_processor import get_tnved_gender_clothes_common
from utilities.categories_data.swimming_accessories_data import SWIMMING_ACCESSORIES_TNVED_DICT, \
    SWIMMING_ACCESSORIES_TYPES, SWIMMING_ACCESSORIES_NAME, SWIMMING_ACCESSORIES_TNVEDS
from views.main.categories.clothes.schemas import SubCategoriesCreds
from utilities.categories_data.underwear_data import (UNDERWEAR_TYPES, UNDERWEAR_TYPES_056, UNDERWEAR_TNVED_DICT,
                                                      UNDERWEAR_NAME, UNDERWEAR_TNVEDS)


# todo understand real need of double request for globals
class Underwear:
    clothes_all_tnved = UNDERWEAR_TNVED_DICT,
    clothes_sizes = settings.Clothes.SIZES_ALL,
    clothes_types_sizes_dict = settings.Clothes.SIZE_ALL_DICT,
    types = UNDERWEAR_TYPES


class ClothesSubcategoryProcessor:
    def __init__(self, subcategory: str = ClothesSubcategories.common.value):
        self._subcategory = subcategory

    @property
    def subcategory(self) -> str:
        return self._subcategory

    def get_creds(self) -> SubCategoriesCreds:
        match self.subcategory:
            case ClothesSubcategories.underwear.value:
                scc = SubCategoriesCreds(clothes_all_tnved=UNDERWEAR_TNVEDS,
                                         clothes_sizes=settings.Clothes.SIZES_ALL,
                                         clothes_types_sizes_dict=settings.Clothes.SIZE_ALL_DICT,
                                         types=UNDERWEAR_TYPES,
                                         subcategory_name=UNDERWEAR_NAME)
            case ClothesSubcategories.swimming_accessories.value:
                scc = SubCategoriesCreds(clothes_all_tnved=SWIMMING_ACCESSORIES_TNVEDS,
                                         clothes_sizes=settings.Clothes.SIZES_ALL,
                                         clothes_types_sizes_dict=settings.Clothes.SIZE_ALL_DICT,
                                         types=SWIMMING_ACCESSORIES_TYPES,
                                         subcategory_name=SWIMMING_ACCESSORIES_NAME)
            case ClothesSubcategories.hats.value:
                scc = SubCategoriesCreds(clothes_all_tnved=HATS_TNVEDS,
                                         clothes_sizes=settings.Clothes.SIZES_ALL,
                                         clothes_types_sizes_dict=settings.Clothes.SIZE_ALL_DICT,
                                         types=HATS_TYPES,
                                         subcategory_name=HATS_NAME)
            case ClothesSubcategories.gloves.value:
                scc = SubCategoriesCreds(clothes_all_tnved=GLOVES_TNVEDS,
                                         clothes_sizes=settings.Clothes.SIZES_ALL,
                                         clothes_types_sizes_dict=settings.Clothes.SIZE_ALL_DICT,
                                         types=GLOVES_TYPES,
                                         subcategory_name=GLOVES_NAME)
            case ClothesSubcategories.shawls.value:
                scc = SubCategoriesCreds(clothes_all_tnved=SHAWLS_TNVEDS,
                                         clothes_sizes=settings.Clothes.SIZES_ALL,
                                         clothes_types_sizes_dict=settings.Clothes.SIZE_ALL_DICT,
                                         types=SHAWLS_TYPES,
                                         subcategory_name=SHAWLS_NAME)
            case _:  # case ClothesSubcategories.common.value:
                scc = SubCategoriesCreds(clothes_all_tnved=settings.Clothes.TNVED_ALL,
                                         clothes_sizes=settings.Clothes.SIZES_ALL,
                                         clothes_types_sizes_dict=settings.Clothes.SIZE_ALL_DICT,
                                         types=settings.Clothes.TYPES,
                                         subcategory_name='')
        return scc

    @staticmethod
    def get_tnveds(subcategory: str = ClothesSubcategories.common.value, cl_type: str = '', cl_gender: str = '') -> tuple | None:
        # print(f"{subcategory=}, {cl_type=}")
        match subcategory:
            case ClothesSubcategories.underwear.value:
                tnved_dict = UNDERWEAR_TNVED_DICT
            case ClothesSubcategories.swimming_accessories.value:
                tnved_dict = SWIMMING_ACCESSORIES_TNVED_DICT
            case ClothesSubcategories.hats.value:
                tnved_dict = HATS_TNVED_DICT
            case ClothesSubcategories.gloves.value:
                tnved_dict = GLOVES_TNVED_DICT
            case ClothesSubcategories.shawls.value:
                tnved_dict = SHAWLS_TNVED_DICT
            case _:  # case ClothesSubcategories.common.value:
                if cl_type in settings.Clothes.TYPES:
                    # tnved_dict = settings.Clothes.CLOTHES_TNVED_DICT
                    # print(get_tnved_gender_clothes_common(type_name=cl_type, gender=cl_gender))
                    return get_tnved_gender_clothes_common(type_name=cl_type, gender=cl_gender)
                else:
                    return
        return tnved_dict.get(cl_type)[1]
