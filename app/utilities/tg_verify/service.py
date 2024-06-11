from datetime import datetime

from flask import request, jsonify, Response
from flask_login import current_user
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from config import settings
from logger import logger
from models import TgUser, db, Promo, User, UserTransaction, users_promos
from redis_queue.connection import tg_redis_database_connection
from utilities.telegram import NotificationTgUser
from validators.api import TransactionInData


def h_tg_markineris_verify() -> Response:
    user = current_user
    status = 'danger'
    verification_code = request.form.get("tg_verification_code", '')

    tg_user_from_db: TgUser = TgUser.query.filter_by(verification_code=verification_code).first()

    if not tg_user_from_db or not len(verification_code) == settings.TG_VERIFICATION_LENGTH:
        message = f"{settings.Messages.TG_VERIFICATION_ERROR} {settings.Messages.TG_VERIFICATION_ASK_BOT}"
        return jsonify(status=status, message=message.format(tg_link=settings.TELEGRAMM_USER_NOTIFY_LINK))

    if tg_user_from_db.flask_user_id is None:
        try:
            tg_user_from_db.flask_user_id = user.id
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            message = f"{settings.Messages.TG_VERIFICATION_ERROR} {settings.Messages.TG_VERIFICATION_EXISTS}"
            tg_message = {"chat_id": tg_user_from_db.tg_chat_id, "message": message}
            logger.error(message)
        else:
            status = "success"
            message = settings.Messages.TG_VERIFICATION_SUCCESS
            tg_message = {"chat_id": tg_user_from_db.tg_chat_id, "message": message}
    else:
        status = "success"
        message = settings.Messages.TG_VERIFICATION_NO_NEED
        tg_message = {"chat_id": tg_user_from_db.tg_chat_id, "message": message}

    NotificationTgUser.send_notification.delay(**tg_message)

    return jsonify(status=status, message=message)


def h_tg_markineris_stop_verify():
    status = 'danger'
    tg_user = TgUser.query.filter(TgUser.flask_user_id == current_user.id).first()
    if tg_user:
        tg_user_id = tg_user.tg_user_id
        tg_chat_id = tg_user.tg_chat_id
        try:
            db.session.delete(tg_user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            message = f"{settings.Messages.TG_VERIF_DELETE_ERROR}"
            logger.error(f"{message} {e}")
        else:
            try:
                keys = tg_redis_database_connection.keys(f"fsm:{tg_user_id}:{tg_chat_id}*")
                tg_redis_database_connection.unlink(*keys)
            except Exception:
                logger.exception("Ошибка при удалении состояния пользователя телеграм из кеша.")
            status = 'success'
            message = f"{settings.Messages.TG_VERIF_DELETE_SUCCESS}"
    else:
        message = settings.Messages.STRANGE_REQUESTS
    return jsonify(dict(status=status, message=message))


def check_promo_exists(promo_code: str) -> Promo | None:
    promo_code_obj: Promo = Promo.query.filter(Promo.code == promo_code).first()

    return promo_code_obj


def check_promo_used(user_id: int, promo_code: str) -> bool:
    query = db.session.query(
        User.id, Promo.code,
    ).join(
        users_promos, users_promos.c.user_id == User.id,
    ).join(
        Promo,
        users_promos.c.promo_id == Promo.id,
    ).filter(
        User.id == user_id,
        Promo.code == promo_code,
    )
    return query.first()


def create_transaction_from_tg(data: TransactionInData) -> bool:
    try:
        created_at = datetime.now()
        query = (
            f"""INSERT into public.user_transactions (type, status, amount, promo_info, user_id, sa_id, bill_path, created_at)
                    VALUES(True, {data.status}, {data.amount}, '{data.promo_info}', {data.user_id}, {data.sa_id}, '{data.bill_path}', '{created_at}');
                UPDATE public.users SET pending_balance_rf=pending_balance_rf + {data.amount} WHERE public.users.id = {data.user_id};
                UPDATE public.server_params SET pending_balance_rf=pending_balance_rf + {data.amount};
            """
        )

        if data.promo_id is not None:
            query += f"INSERT into public.users_promos VALUES({data.user_id}, {data.promo_id});"
        db.session.execute(text(query))
        db.session.commit()

    except Exception:
        db.session.rollback()
        logger.exception("Ошибка в процессе создания транзакции.")
        return False

    return True


def send_tg_message_with_transaction_updated_status(user_id, transaction_id):
    messages = {
        0: "Транзакция отклонена оператором",
        1: "Транзакция в обработке",
        2: "Транзакция успешно проведена оператором",
    }
    try:
        tg_user = TgUser.query.filter(TgUser.flask_user_id == user_id).first()
        transaction = UserTransaction.query.filter(
            UserTransaction.id == transaction_id,
        ).first()
        if tg_user is not None and transaction is not None:
            tg_message = {"chat_id": tg_user.tg_chat_id, "message": messages[transaction.status]}
            NotificationTgUser.send_notification.delay(**tg_message)
    except Exception:
        logger.exception("Ошибка отправки при формировании и отправки сообщения в телеграм по статусу транзакции")