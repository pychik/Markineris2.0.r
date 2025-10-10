from flask import request
from re import fullmatch
from typing import Optional

from config import settings
from utilities.categories_data.accessories_data import HATS_TNVEDS, GLOVES_TNVEDS, SHAWLS_TNVEDS
from utilities.categories_data.subcategories_data import ClothesSubcategories
from utilities.categories_data.swimming_accessories_data import SWIMMING_ACCESSORIES_TNVEDS
from utilities.categories_data.underwear_data import UNDERWEAR_TNVEDS


class ValidationError(Exception):
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


class ValidatorProcessor:
    @staticmethod
    def sign_up(form_dict: dict) -> tuple:
        def check_email(email_str: str) -> Optional[str]:
            regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
            if not email_str:
                return None
            return email_str if fullmatch(regex, email_str) else None

        sp_link = form_dict.get("p_link")
        login_name = form_dict.get('login_name')
        email = form_dict.get('email')
        full_phone = form_dict.get('full_phone')
        password = form_dict.get('password')
        partner_code_id = form_dict.get('partner_code_id')
        admin_id = form_dict.get('admin_id')

        if not sp_link:
            return None, 'p_link', 'Ссылка не указана'

        if not login_name:
            return None, 'login_name', 'Логин не указан'

        if not email:
            return None, 'email', 'E-mail не указан'
        if email.lower().startswith('agent_'):
            return None, 'email', 'E-mail не должен начинаться с "agent_"'
        if not check_email(email):
            return None, 'email', 'Некорректный формат e-mail'

        if not full_phone:
            return None, 'full_phone', 'Телефон не указан'
        if full_phone in settings.ExceptionOrders.PHONE_NUMBERS:
            raise ValidationError('full_phone', 'Этот номер телефона запрещён для регистрации')

        if not password:
            return None, 'password', 'Пароль не указан'

        if not admin_id:
            return None, 'admin_id', 'ID администратора не указан'

        res_tuple = (
            sp_link, login_name, email, full_phone, password, partner_code_id, admin_id
        )

        # sanitize
        res_tuple = tuple(map(lambda x: x.replace('--', '') if isinstance(x, str) else x, res_tuple))
        return res_tuple, None, None

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
    def swimming_accessories_pre_validate_tnved(tnved_str: str) -> bool:
        if not tnved_str or tnved_str not in SWIMMING_ACCESSORIES_TNVEDS:
            return True
        else:
            return False

    @staticmethod
    def hats_pre_validate_tnved(tnved_str: str) -> bool:
        if not tnved_str or tnved_str not in HATS_TNVEDS:
            return True
        else:
            return False

    @staticmethod
    def gloves_pre_validate_tnved(tnved_str: str) -> bool:
        if not tnved_str or tnved_str not in GLOVES_TNVEDS:
            return True
        else:
            return False

    @staticmethod
    def shawls_pre_validate_tnved(tnved_str: str) -> bool:
        if not tnved_str or tnved_str not in SHAWLS_TNVEDS:
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
                case ClothesSubcategories.swimming_accessories.value:
                    return ValidatorProcessor.swimming_accessories_pre_validate_tnved(tnved_str=tnved_str)
                case ClothesSubcategories.hats.value:
                    return ValidatorProcessor.hats_pre_validate_tnved(tnved_str=tnved_str)
                case ClothesSubcategories.gloves.value:
                    return ValidatorProcessor.gloves_pre_validate_tnved(tnved_str=tnved_str)
                case ClothesSubcategories.shawls.value:
                    return ValidatorProcessor.shawls_pre_validate_tnved(tnved_str=tnved_str)
                case _:
                    return ValidatorProcessor.clothes_pre_validate_tnved(tnved_str=tnved_str)

    @staticmethod
    def check_colors(color: str) -> bool:
        return color not in settings.ALL_COLORS
