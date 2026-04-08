from sqlalchemy import func
from config import settings
from models import db, ProductCard, ModerationStatus, User, CardChatRead, CardMessage

USER_CHAT_WRITE_STATUSES = {
    ModerationStatus.CLARIFICATION.value,
}


def h_pc_chat_can_read(card: ProductCard, user: User) -> bool:
    st = card.status.value if hasattr(card.status, "value") else str(card.status)

    if user.role not in settings.PRODUCT_CARD_CHAT_ALLOWED_ROLES:
        return False

    if user.role == settings.ORD_USER:
        if card.user_id != user.id:
            return False
        if st in USER_CHAT_WRITE_STATUSES:
            return True
        return h_pc_chat_has_visible_messages(card.id, user)

    if user.role == settings.MANAGER_USER:
        return card.manager_id == user.id

    if h_pc_chat_is_at2_admin(user):
        return card.creator is not None and card.creator.admin_parent_id == user.id

    if user.role == settings.ADMIN_USER:
        return False

    return user.role in settings.PRODUCT_CARD_CHAT_FULL_ACCESS_ROLES


def h_pc_chat_can_send(card: ProductCard, user: User) -> bool:
    if not h_pc_chat_can_read(card, user):
        return False

    st = card.status.value if hasattr(card.status, "value") else str(card.status)

    if user.role == settings.ORD_USER:
        return st in USER_CHAT_WRITE_STATUSES

    return True


def h_pc_chat_is_at2_admin(user: User | None) -> bool:
    return bool(
        user
        and getattr(user, "role", None) == settings.ADMIN_USER
        and getattr(user, "is_at2", False) is True
    )


def h_pc_chat_get_card_for_access(pc_id: int, user: User | None):
    q = ProductCard.query.filter(ProductCard.id == pc_id)

    if h_pc_chat_is_at2_admin(user):
        q = q.join(User, User.id == ProductCard.user_id).filter(User.admin_parent_id == user.id)

    return q.first()


def h_pc_chat_can_access(card: ProductCard, user: User) -> bool:
    return h_pc_chat_can_read(card, user)


def h_pc_chat_visible_filter(q, user):
    if user.role == settings.ORD_USER:
        return q.filter(CardMessage.is_internal.is_(False))
    return q


def h_pc_chat_has_visible_messages(card_id: int, user) -> bool:
    q = CardMessage.query.filter(CardMessage.card_id == card_id)
    q = h_pc_chat_visible_filter(q, user)
    return db.session.query(q.exists()).scalar()


def h_visible_chat_card_ids(card_ids: list[int], user) -> set[int]:
    if not card_ids:
        return set()

    q = db.session.query(CardMessage.card_id).filter(CardMessage.card_id.in_(card_ids))
    q = h_pc_chat_visible_filter(q, user)
    rows = q.distinct().all()
    return {int(card_id) for (card_id,) in rows}


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
