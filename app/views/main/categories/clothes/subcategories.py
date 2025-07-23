from config import settings
from models import ClothesSubcategories
from utilities.categories_data.swimming_accessories_data import SWIMMING_ACCESSORIES_TNVED_DICT, \
    SWIMMING_ACCESSORIES_TYPES, SWIMMING_ACCESSORIES_NAME
from views.main.categories.clothes.schemas import SubCategoriesCreds
from utilities.categories_data.underwear_data import (UNDERWEAR_TYPES, UNDERWEAR_TYPES_056, UNDERWEAR_TNVED_DICT,
                                                      UNDERWEAR_NAME)


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
                scc = SubCategoriesCreds(clothes_all_tnved=UNDERWEAR_TNVED_DICT,
                                         clothes_sizes=settings.Clothes.SIZES_ALL,
                                         clothes_types_sizes_dict=settings.Clothes.SIZE_ALL_DICT,
                                         types=UNDERWEAR_TYPES,
                                         subcategory_name=UNDERWEAR_NAME)
            case ClothesSubcategories.swimming_accessories.value:
                scc = SubCategoriesCreds(clothes_all_tnved=SWIMMING_ACCESSORIES_TNVED_DICT,
                                         clothes_sizes=settings.Clothes.SIZES_ALL,
                                         clothes_types_sizes_dict=settings.Clothes.SIZE_ALL_DICT,
                                         types=SWIMMING_ACCESSORIES_TYPES,
                                         subcategory_name=SWIMMING_ACCESSORIES_NAME)
            case _:  # case ClothesSubcategories.common.value:
                scc = SubCategoriesCreds(clothes_all_tnved=settings.Clothes.TNVED_ALL,
                                         clothes_sizes=settings.Clothes.SIZES_ALL,
                                         clothes_types_sizes_dict=settings.Clothes.SIZE_ALL_DICT,
                                         types=settings.Clothes.TYPES,
                                         subcategory_name='')
        return scc

    @staticmethod
    def get_tnveds(subcategory: str = ClothesSubcategories.common.value, cl_type: str = '') -> tuple | None:
        # print(f"{subcategory=}, {cl_type=}")
        match subcategory:
            case ClothesSubcategories.underwear.value:
                tnved_dict = UNDERWEAR_TNVED_DICT
            case ClothesSubcategories.swimming_accessories.value:
                tnved_dict = SWIMMING_ACCESSORIES_TNVED_DICT
            case _:  # case ClothesSubcategories.common.value:
                if cl_type in settings.Clothes.TYPES:
                    tnved_dict = settings.Clothes.CLOTHES_TNVED_DICT
                else:
                    return
        return tnved_dict.get(cl_type)[1]
