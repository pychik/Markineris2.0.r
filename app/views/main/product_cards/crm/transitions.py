from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Iterable

from sqlalchemy.exc import SQLAlchemyError

from logger import logger
from models import db, ProductCard, ModerationStatus
from views.main.product_cards.crm.helpers import h_append_card_log

# какие роли “админские” (могут двигать чужие карточки и возвращать назад и т.п.)
CRM_ADMIN_ROLES = {"superuser", "supermanager"}
CRM_MANAGER_ROLE = "manager"

# матрица переходов: ОТКУДА -> КУДА можно
TRANSITIONS: dict[str, set[str]] = {
    ModerationStatus.SENT.value: set(),  # "взять в работу" отдельным методом (как у тебя)
    ModerationStatus.SENT_NO_RD.value: {ModerationStatus.IN_PROGRESS.value,},  # "взять в работу" отдельным методом (как у тебя)
    ModerationStatus.IN_PROGRESS.value: {
        ModerationStatus.SENT.value,
        ModerationStatus.IN_MODERATION.value,
        # ModerationStatus.CLARIFICATION.value,
        # ModerationStatus.APPROVED.value,
        # ModerationStatus.REJECTED.value,
    },
    ModerationStatus.IN_MODERATION.value: {
            ModerationStatus.IN_PROGRESS.value,
            ModerationStatus.CLARIFICATION.value,
            ModerationStatus.APPROVED.value,
            ModerationStatus.REJECTED.value,
        },
    ModerationStatus.CLARIFICATION.value: {
        ModerationStatus.IN_PROGRESS.value,
        ModerationStatus.IN_MODERATION.value,
        ModerationStatus.APPROVED.value,
        ModerationStatus.REJECTED.value,
    },
    ModerationStatus.APPROVED.value: {
        ModerationStatus.IN_PROGRESS.value,
    },
    ModerationStatus.REJECTED.value: {
        ModerationStatus.IN_PROGRESS.value,
    },
}

ALLOWED_BACK_TO_SENT_ROLES = {"superuser", "supermanager"}


@dataclass
class MoveResult:
    ok: bool
    status_code: int = 200
    message: str = ""
    card: Optional[ProductCard] = None
    from_status: Optional[str] = None
    to_status: Optional[str] = None


def can_see_all(user) -> bool:
    return getattr(user, "role", None) in CRM_ADMIN_ROLES


def is_manager(user) -> bool:
    return getattr(user, "role", None) == CRM_MANAGER_ROLE


def validate_transition(from_status: str, to_status: str) -> bool:
    return to_status in TRANSITIONS.get(from_status, set())


def check_owner_or_admin(user, card: ProductCard) -> Optional[MoveResult]:
    """Обычный manager может двигать только свои карточки (кроме SENT, но SENT двигается отдельным методом)."""
    if can_see_all(user):
        return None
    # manager / прочие — только если закреплена за ним
    if card.manager_id != user.id:
        return MoveResult(False, 403, "Карточка закреплена за другим оператором")
    return None


def check_special_rules(user, card: ProductCard, to_status: str) -> Optional[MoveResult]:
    # пример: назад в SENT только для ролей
    if to_status == ModerationStatus.SENT.value and getattr(user, "role", None) not in ALLOWED_BACK_TO_SENT_ROLES:
        return MoveResult(False, 403, "Недостаточно прав для возврата в 'Отправленные'")
    return None


def apply_transition(user, card: ProductCard, to_status: str, reject_reason: str = "") -> Optional[MoveResult]:
    """Меняем статус и связанные поля/тайминги/логи."""
    dt = datetime.now()
    manager_login = getattr(user, "login_name", "") or str(user.id)
    dt_str = dt.strftime("%d-%m-%Y %H:%M:%S")
    # Набор обновлений (без commit)
    if to_status == ModerationStatus.SENT.value:
        card.status = ModerationStatus.SENT
        card.manager_id = None
        card.taken_at = None
        card.card_log = h_append_card_log((card.card_log or ""), f"\n{dt_str} вернул в отправленные {manager_login};")

    elif to_status == ModerationStatus.IN_PROGRESS.value:
        card.status = ModerationStatus.IN_PROGRESS
        # тут важно: если карточка уже закреплена — оставляем manager_id как есть.
        # если админ двигает “чужую” из approved/rejected/clarification → in_progress, обычно manager_id сохраняется.
        card.card_log = h_append_card_log((card.card_log or ""), f"\n{dt_str} перевёл в обработку {manager_login};")
    elif to_status == ModerationStatus.IN_MODERATION.value:
        card.status = ModerationStatus.IN_MODERATION
        # тут важно: если карточка уже закреплена — оставляем manager_id как есть.
        # если админ двигает “чужую” из approved/rejected/clarification → in_progress, обычно manager_id сохраняется.
        card.card_log = h_append_card_log((card.card_log or ""), f"\n{dt_str} перевёл на модерацию {manager_login};")
    elif to_status == ModerationStatus.CLARIFICATION.value:
        card.status = ModerationStatus.CLARIFICATION
        card.clarification_requested_at = dt
        card.card_log = h_append_card_log((card.card_log or ""), f"\n{dt_str} отправил на уточнение {manager_login};")

    elif to_status == ModerationStatus.APPROVED.value:
        card.status = ModerationStatus.APPROVED
        card.approved_at = dt
        card.card_log = h_append_card_log((card.card_log or ""), f"\n{dt_str} одобрил {manager_login};")

    elif to_status == ModerationStatus.REJECTED.value:
        if not reject_reason:
            return MoveResult(False, 400, "Укажите причину отмены")
        card.status = ModerationStatus.REJECTED
        card.reject_reason = reject_reason
        card.rejected_at = dt
        card.card_log = h_append_card_log((card.card_log or ""), f"\n{dt_str} отменил {manager_login}; причина: {reject_reason};")

    else:
        return MoveResult(False, 400, "Некорректный target")

    return None
