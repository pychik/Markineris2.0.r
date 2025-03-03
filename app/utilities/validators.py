from flask import request
from re import fullmatch
from typing import Optional

from config import settings
from utilities.categories_data.subcategories_data import ClothesSubcategories
from utilities.categories_data.underwear_data import UNDERWEAR_TNVEDS


class ValidatorProcessor:
    @staticmethod
    def sign_up(form_dict: dict) -> Optional[tuple]:
        def check_email(email_str: str) -> Optional[str]:
            regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
            if fullmatch(regex, email_str):
                return email_str

        sp_link = form_dict.get("p_link")
        login_name = form_dict.get('login_name')
        email = form_dict.get('email')

        full_phone = form_dict.get('full_phone')
        password = form_dict.get('password')
        partner_code_id = form_dict.get('partner_code_id')
        admin_id = form_dict.get('admin_id')

        res_tuple = sp_link, login_name, check_email(email_str=email), full_phone, password, partner_code_id, admin_id
        if not all(res_tuple) or email.lower().startswith('agent_'):
            return None
        else:
            res_tuple = tuple(map(lambda x: x.replace('--', ''), res_tuple))
            return res_tuple

    @staticmethod
    def common_pre_validate_tnved(tnved_str: str, category: str) -> bool:
        tnved_all = []
        match category:
            case ClothesSubcategories.underwear.value:
                tnved_all += UNDERWEAR_TNVEDS
            case settings.Socks.CATEGORY:
                tnved_all += settings.Socks.TNVED_ALL
            case settings.Linen.CATEGORY:
                tnved_all += settings.Linen.TNVED_ALL
            case settings.Shoes.CATEGORY:
                tnved_all += settings.Shoes.TNVEDS_ALL
            case settings.Parfum.CATEGORY:
                tnved_all += settings.Parfum.TNVED_CODE
            case settings.Clothes.CATEGORY:
                tnved_all += settings.Clothes.TNVED_ALL
        if not tnved_str or tnved_str not in tnved_all:
            return True
        else:
            return False

    @staticmethod
    def clothes_pre_validate_tnved(tnved_str: str) -> bool:
        if not tnved_str or tnved_str not in settings.Clothes.TNVED_ALL:
            return True
        else:
            return False

    @staticmethod
    def linen_pre_validate_tnved(tnved_str: str) -> bool:
        if not tnved_str or tnved_str not in settings.Linen.TNVED_ALL:
            return True
        else:
            return False

    @staticmethod
    def parfum_pre_validate_tnved(tnved_str: str) -> bool:
        if not tnved_str or tnved_str not in settings.Parfum.TNVED_CODE:
            return True
        else:
            return False

    @staticmethod
    def shoes_pre_validate_tnved(tnved_str: str) -> bool:
        if not tnved_str or tnved_str not in settings.Shoes.TNVEDS_ALL:
            return True
        else:
            return False

    @staticmethod
    def socks_pre_validate_tnved(tnved_str: str) -> bool:
        if not tnved_str or tnved_str not in settings.Socks.TNVED_ALL:
            return True
        else:
            return False

    @staticmethod
    def underwear_pre_validate_tnved(tnved_str: str) -> bool:
        if not tnved_str or tnved_str not in UNDERWEAR_TNVEDS:
            return True
        else:
            return False

    @staticmethod
    def check_tnveds(category: str, subcategory: str, tnved_str: str) -> bool:
        if category == settings.Socks.CATEGORY:
            return ValidatorProcessor.socks_pre_validate_tnved(tnved_str=tnved_str)
        elif category == settings.Linen.CATEGORY:
            return ValidatorProcessor.linen_pre_validate_tnved(tnved_str=tnved_str)
        elif category == settings.Parfum.CATEGORY:
            return ValidatorProcessor.parfum_pre_validate_tnved(tnved_str=tnved_str)
        elif category == settings.Shoes.CATEGORY:
            return ValidatorProcessor.shoes_pre_validate_tnved(tnved_str=tnved_str)
        else:
            match subcategory:
                case ClothesSubcategories.underwear.value:
                    return ValidatorProcessor.underwear_pre_validate_tnved(tnved_str=tnved_str)
                case _:
                    return ValidatorProcessor.clothes_pre_validate_tnved(tnved_str=tnved_str)
