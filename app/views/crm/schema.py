from collections import namedtuple
from enum import Enum

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

    def __init__(self, name, inn):
        self.display_name = name
        self.inn = inn

    def as_option(self):
        return (self.name, f"{self.display_name} ({self.inn})")
