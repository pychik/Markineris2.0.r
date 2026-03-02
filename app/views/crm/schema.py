from collections import namedtuple
from dataclasses import dataclass
from enum import Enum
from typing import Optional

CrmDefaults = namedtuple('CrmDefaults', 'ps_limit, mo_limit, po_limit, ap_rows, ap_marks, as_minutes')


class CompaniesOperators(Enum):
    GRENADA = ("Гренада", "4400023137")
    ANRI = ("ООО Анри", "7743473955")
    BEROT = ("Берот", "9713027393")
    RAMIT = ("ООО Рамит", "9713028069")
    TANIG = ("Таниг", "7751356148")
    TURKIN = ("ИП Туркин Дмитрий Сергеевич", "111604076740")
    AVRORA = ("Аврора", "4400023120")
    MIRAT = ("ООО Мират", "7730338476")
    MITAV = ("ООО Митав", "9726102048")
    ISHMITOV = ("ИП Ишмитов Илья Алексеевич", "023103006891")
    ALASTOR = ("ООО \"Аластор\"", "7751357550")

    def __init__(self, name, inn):
        self.display_name = name
        self.inn = inn

    def as_option(self):
        return (self.name, f"{self.display_name} ({self.inn})")


# если у тебя ProcessingCompany имеет поля id/title/inn/is_active
@dataclass(frozen=True)
class CompanyLite:
    id: int
    title: str
    inn: str


def _norm_inn(inn: Optional[str]) -> str:
    return (inn or "").strip()


# Запрещённые пары по ИНН (симметрично)
FORBIDDEN_INN_PAIRS = {
    frozenset({"4400023137", "4400023120"}),      # Гренада + Аврора
    frozenset({"9713028069", "111604076740"}),    # ООО Рамит + ИП Туркин
}


def is_forbidden_pair_by_inn(inn1: Optional[str], inn2: Optional[str]) -> bool:
    a = _norm_inn(inn1)
    b = _norm_inn(inn2)
    if not a or not b:
        return False
    return frozenset({a, b}) in FORBIDDEN_INN_PAIRS