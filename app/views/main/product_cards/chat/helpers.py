from sqlalchemy import func
from models import db, ProductCard, ModerationStatus, User, CardChatRead, CardMessage

CHAT_ALLOWED_ROLES = {"superuser", "supermanager", "markineris_admin", "manager", "ordinary_user"}


def h_pc_chat_can_access(card: ProductCard, user: User) -> bool:
    st = card.status.value if hasattr(card.status, "value") else str(card.status)
    if st not in {ModerationStatus.IN_PROGRESS.value, ModerationStatus.IN_MODERATION.value, ModerationStatus.CLARIFICATION.value}:
        return False

    if user.role not in CHAT_ALLOWED_ROLES:
        return False

    if user.role == "ordinary_user":
        return card.user_id == user.id

    if user.role == "manager":
        return card.manager_id == user.id

    return True  # super roles


def h_pc_chat_visible_filter(q, user):
    if user.role == "ordinary_user":
        return q.filter(CardMessage.is_internal.is_(False))
    return q


def h_pc_chat_unread_count(card_id: int, user) -> int:
    read_row = CardChatRead.query.filter_by(card_id=card_id, user_id=user.id).first()
    last_read = read_row.last_read_message_id if read_row else 0

    q = CardMessage.query.filter(CardMessage.card_id == card_id, CardMessage.id > last_read)
    q = h_pc_chat_visible_filter(q, user)
    return q.count()


def h_unread_map_for_cards(card_ids: list[int], user):
    if not card_ids:
        return {}

    # 1) last_read по всем карточкам
    reads = (
        db.session.query(CardChatRead.card_id, CardChatRead.last_read_message_id)
        .filter(CardChatRead.user_id == user.id, CardChatRead.card_id.in_(card_ids))
        .all()
    )
    last_read_by_card = {cid: (last_id or 0) for cid, last_id in reads}

    # 2) unread counts по всем карточкам
    # ВАЖНО: тут мы не можем одной строкой сравнить id > last_read_by_card[cid] без join-а,
    # поэтому делаем join на CardChatRead (outer), и сравниваем с coalesce.
    q = (
        db.session.query(CardMessage.card_id, func.count(CardMessage.id))
        .outerjoin(
            CardChatRead,
            (CardChatRead.card_id == CardMessage.card_id) & (CardChatRead.user_id == user.id)
        )
        .filter(CardMessage.card_id.in_(card_ids))
        .filter(CardMessage.id > func.coalesce(CardChatRead.last_read_message_id, 0))
    )

    # применяем видимость (должна уметь работать на Query с join-ами)
    q = h_pc_chat_visible_filter(q, user)

    rows = q.group_by(CardMessage.card_id).all()

    result = {cid: 0 for cid in card_ids}
    for cid, cnt in rows:
        result[cid] = int(cnt)
    return result
