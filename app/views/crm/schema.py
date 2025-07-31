from collections import namedtuple
from enum import Enum

CrmDefaults = namedtuple('CrmDefaults', 'ps_limit, mo_limit, po_limit, ap_rows, ap_marks, as_minutes')


class CompaniesOperators(Enum):
    GRENADA = ("Гренада", "4400023137")
    AVRORA = ("Аврора", "4400023120")
    BEROT = ("Берот", "9713027393")
    NOVASTOR = ("Новастор", "4400024187")
    STARMARKET = ("Стармаркет", "4400024211")
    EVRIKA = ("Эврика", "4400024243")
    GRACIYA = ("Грация", "4400024275")
    TANIG = ("Таниг", "7751356148")
    ZIMA = ("Зима", "4400024412")

    def __init__(self, name, inn):
        self.display_name = name
        self.inn = inn

    def as_option(self):
        return (self.name, f"{self.display_name} ({self.inn})")
