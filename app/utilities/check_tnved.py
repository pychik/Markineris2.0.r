from typing import Optional

from config import settings


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
    def tnved_clothes_parse(cloth_type: str, tnved_code) -> tuple[int, Optional[str]]:
        result_status = 1
        # simple checks
        if len(tnved_code) != 10:
            answer = f"{tnved_code}{settings.Messages.TNVED_INPUT_ERROR_10}"
            return result_status, answer
        elif not tnved_code.isdigit():
            answer = f"{tnved_code}{settings.Messages.TNVED_INPUT_ERROR_DIGITS}"
            return result_status, answer
        # good checks
        big_tnved_tuple = settings.Clothes.CLOTHES_TNVED_DICT.get(cloth_type)[0]
        if tnved_code in big_tnved_tuple or tnved_code in settings.Tnved.BIG_TNVED_LIST:
            result_status = 5
            answer = f"{settings.Messages.TNVED_INPUT_SUCCESS}"
        else:
            answer = f"Введенный код {tnved_code}:{settings.Messages.TNVED_CLOTHES_INPUT_ERROR_NF}"

        return result_status, answer
