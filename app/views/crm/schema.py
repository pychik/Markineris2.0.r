from collections import namedtuple
from dataclasses import dataclass
from enum import Enum
from typing import Optional

CrmDefaults = namedtuple('CrmDefaults', 'ps_limit, mo_limit, po_limit, ap_rows, ap_marks, as_minutes')


class CompaniesOperators(Enum):
    GRENADA = ("Гренада", "4400023137")
    # ANRI = ("ООО Анри", "7743473955")
    # BEROT = ("Берот", "9713027393")
    # RAMIT = ("ООО Рамит", "9713028069")
    # TANIG = ("Таниг", "7751356148")
    TURKIN = ("ИП Туркин Дмитрий Сергеевич", "111604076740")
    AVRORA = ("Аврора", "4400023120")
    MIRAT = ("ООО Мират", "7730338476")
    # MITAV = ("ООО Митав", "9726102048")
    ISHMITOV = ("ИП Ишмитов Илья Алексеевич", "023103006891")
    # ALASTOR = ("ООО \"Аластор\"", "7751357550")
    PEREMENI = ("ООО \"Перемены\"", "4400027438")
    MOSKIN = ("ИП \"Моськин\"", "771988302928")
    IGNATUK = ("ИП \"Игнатюк Анастасия Дмитриевна\"", "026491035246")
    BETASTROY = ("ООО \"Бетастрой\"", "7720963833")
    MINDIYAROV = ("ИП \"Миндияров Савелий Валерьевич\"", "022703451765")
    KHUZIN = ("ИП \"Хузин Булат Денисович\"", "023104386702")

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


# Компания, от имени которой проводится заказ и от которой придёт УПД.
#
# Правила распределения по категориям ещё не согласованы. Когда придут - заполняем словарь
# ниже (ключ - нормализованное название категории заказа, значение - элемент CompaniesOperators),
# и больше ничего менять не нужно: вызывающий код обращается только к pick_upd_company().
CATEGORY_UPD_COMPANY: dict = {}


def pick_upd_company(category: Optional[str] = None, order_id: Optional[int] = None) -> CompaniesOperators:
    """Выбрать компанию для УПД по заказу.

    результат детерминированный, поэтому повторная выдача
    заказа после таймаута даёт ту же компанию.
    """
    company = CATEGORY_UPD_COMPANY.get((category or "").strip().lower())
    if company is not None:
        return company

    # ponytail: правил по категориям пока нет - раскладываем по id заказа, чтобы нагрузка
    # не легла на одну фирму. Заменяется заполнением CATEGORY_UPD_COMPANY.
    pool = list(CompaniesOperators)
    return pool[(order_id or 0) % len(pool)]


def format_upd_company(company_name: Optional[str], company_inn: Optional[str]) -> str:
    """Строка компании в том же виде, в каком её выбирает оператор в модалке УПД."""
    name = (company_name or "").strip()
    inn = _norm_inn(company_inn)
    if not name:
        return ""
    return f"{name} ({inn})" if inn else name


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