from re import fullmatch
from typing import Optional

from config import settings


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
        if not all(res_tuple):
            return None
        else:
            res_tuple = tuple(map(lambda x: x.replace('--', ''), res_tuple))
            return res_tuple

    @staticmethod
    def clothes_pre_validate_tnved(tnved_str: str) -> bool:
        if not tnved_str or tnved_str not in settings.Clothes.TNVED_ALL:
            return True
        else:
            return False
