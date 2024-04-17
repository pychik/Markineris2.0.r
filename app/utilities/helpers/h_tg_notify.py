from utilities.telegram import NotificationTgUser
from models import TgUser, Order
from config import settings


def helper_send_user_order_tg_notify(user_id: int, order_idn: str, order_stage: int = settings.OrderStage.NEW):

    chat_id = TgUser.query.with_entities(TgUser.tg_chat_id).filter(TgUser.flask_user_id == user_id).first()
    if chat_id:
        tg_message = {
            "chat_id": chat_id.tg_chat_id,
            "message": settings.OrderStage.M_ORDER_MSG_DICT[order_stage].format(order_idn=order_idn)
        }
        NotificationTgUser.send_notification.delay(**tg_message)


def helper_suotls(users_orders: list[Order], order_stage: int = settings.OrderStage.SENT):
    # send_user_order_tg_notify_list scheduled task
    for data in users_orders:
        chat_id = TgUser.query.with_entities(TgUser.tg_chat_id).filter(TgUser.flask_user_id == data.user_id).first()
        if chat_id:
            tg_message = {
                "chat_id": chat_id.tg_chat_id,
                "message": settings.OrderStage.M_ORDER_MSG_DICT[order_stage].format(order_idn=data.order_idn)
            }
            NotificationTgUser.send_notification(**tg_message)
