from typing import Optional

from config import settings
from utilities.categories_data.accessories_data import HATS_TNVED_DICT, SHAWLS_TNVED_DICT, GLOVES_TNVED_DICT
from utilities.categories_data.clothes_common.tnved_processor import get_tnved_codes_for_gender
from utilities.categories_data.subcategories_data import ClothesSubcategories
from utilities.categories_data.swimming_accessories_data import SWIMMING_ACCESSORIES_TNVED_DICT
from utilities.categories_data.underwear_data import UNDERWEAR_TNVED_DICT


class TnvedChecker:
    def __init__(self, category: str, tnved_code: str):
        self.category = category
        self.tnved_code = tnved_code

    def tnved_parse(self) -> tuple[int, Optional[str]]:
        result_status = 1

        # simple checks
        if len(self.tnved_code) != 10:
            answer = f"{self.tnved_code}{settings.Messages.TNVED_INPUT_ERROR_10}"
            return result_status, answer
        elif not self.tnved_code.isdigit():
            answer = f"{self.tnved_code}{settings.Messages.TNVED_INPUT_ERROR_DIGITS}"
            return result_status, answer
        # good checks
        big_tnved_tuple = settings.Tnved.BIG_TNVED_DICT.get(self.category)

        if self.tnved_code in big_tnved_tuple[1]:
            result_status = 5
            answer = f"{settings.Messages.TNVED_INPUT_SUCCESS}"
        else:
            answer = f"Введенный код {self.tnved_code}:{settings.Messages.TNVED_INPUT_ERROR_NF}"

        return result_status, answer

    @staticmethod
    def tnved_clothes_parse(cloth_type: str, tnved_code, subcategory: str = None, gender: str = None) -> tuple[
        int, Optional[str]]:
        result_status = 1
        # simple checks
        if len(tnved_code) != 10:
            answer = f"{tnved_code}{settings.Messages.TNVED_INPUT_ERROR_10}"
            return result_status, answer
        elif not tnved_code.isdigit():
            answer = f"{tnved_code}{settings.Messages.TNVED_INPUT_ERROR_DIGITS}"
            return result_status, answer
        # good checks
        match subcategory:
            case ClothesSubcategories.underwear.value:
                tnved_dict = UNDERWEAR_TNVED_DICT
                big_tnved_tuple = tnved_dict.get(cloth_type)[0]
            case ClothesSubcategories.swimming_accessories.value:
                tnved_dict = SWIMMING_ACCESSORIES_TNVED_DICT
                big_tnved_tuple = tnved_dict.get(cloth_type)[0]
            case ClothesSubcategories.hats.value:
                tnved_dict = HATS_TNVED_DICT
                big_tnved_tuple = tnved_dict.get(cloth_type)[0]
            case ClothesSubcategories.gloves.value:
                tnved_dict = GLOVES_TNVED_DICT
                big_tnved_tuple = tnved_dict.get(cloth_type)[0]
            case ClothesSubcategories.shawls.value:
                tnved_dict = SHAWLS_TNVED_DICT
                big_tnved_tuple = tnved_dict.get(cloth_type)[0]
            case _:
                tnved_dict = settings.Clothes.CLOTHES_TNVED_DICT
                if gender not in settings.Clothes.GENDERS:
                    answer = f"{settings.Messages.TNVED_INPUT_ERROR_GT.format(gender=gender)}"
                    return result_status, answer
                big_tnved_tuple = get_tnved_codes_for_gender(type_name=cloth_type, gender=gender)

        if cloth_type.upper() not in tnved_dict.keys():
            answer = f"{tnved_code}{settings.Messages.TNVED_INPUT_ERROR_CT.format(category='одежды')}"
            return result_status, answer

        # big_tnved_tuple = tnved_dict.get(cloth_type)[0]
        if tnved_code in big_tnved_tuple or (
                subcategory not in ['common', '', None] and tnved_code in settings.Tnved.BIG_TNVED_LIST):
            result_status = 5
            answer = f"{settings.Messages.TNVED_INPUT_SUCCESS}"
        else:
            answer = f"Введенный код {tnved_code}:{settings.Messages.TNVED_CLOTHES_INPUT_ERROR_NF.format(category='одежды')}"

        return result_status, answer

    @staticmethod
    def tnved_socks_parse(socks_type: str, tnved_code) -> tuple[int, Optional[str]]:
        result_status = 1
        # simple checks
        if len(tnved_code) != 10:
            answer = f"{tnved_code}{settings.Messages.TNVED_INPUT_ERROR_10}"
            return result_status, answer
        elif not tnved_code.isdigit():
            answer = f"{tnved_code}{settings.Messages.TNVED_INPUT_ERROR_DIGITS}"
            return result_status, answer
        # good checks
        if socks_type.upper() not in settings.Socks.SOCKS_TNVED_DICT.keys():
            answer = f"{tnved_code}{settings.Messages.TNVED_INPUT_ERROR_CT.format(category='чулочно-носочных изделий')}"
            return result_status, answer
        big_tnved_tuple = settings.Socks.SOCKS_TNVED_DICT.get(socks_type)[0]
        if tnved_code in big_tnved_tuple or tnved_code in settings.Tnved.BIG_TNVED_LIST:
            result_status = 5
            answer = f"{settings.Messages.TNVED_INPUT_SUCCESS}"
        else:
            answer = f"Введенный код {tnved_code}:{settings.Messages.TNVED_CLOTHES_INPUT_ERROR_NF.format(category='чулочно-носочных изделий')}"

        return result_status, answer
