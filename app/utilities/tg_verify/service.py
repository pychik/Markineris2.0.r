from datetime import datetime

from flask import request, jsonify, Response
from flask_login import current_user
from sqlalchemy import text, Table, not_
from sqlalchemy.exc import IntegrityError

from config import settings
from logger import logger
from models import TgUser, db, Promo, Bonus, User, UserTransaction
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


def check_promo_exists(promo_code: str, model: Promo | Bonus) -> Promo | Bonus | None:
    promo_code_obj: Bonus | Bonus = model.query.filter(
        model.code == promo_code,
        not_(model.is_archived.is_(True)),
    ).first()

    return promo_code_obj


def check_promo_used(user_id: int, code: str, model: Promo | Bonus, relation_model: Table) -> bool:
    query = db.session.query(
        User.id, model.code,
    ).join(
        relation_model, relation_model.c.user_id == User.id,
    ).join(
        model,
        relation_model.c.promo_id == model.id,
    ).filter(
        User.id == user_id,
        model.code == code,
        not_(model.is_archived.is_(True)),
    )
    return query.first()


def create_transaction_from_tg(data: TransactionInData) -> bool:
    try:
        created_at = datetime.now()
        query = (
            f"""INSERT into public.user_transactions (type, status, transaction_type, amount, promo_info, user_id, sa_id, bill_path, created_at, is_bonus)
                    VALUES(True, {data.status}, '{data.transaction_type}', {data.amount}, '{data.promo_info}', {data.user_id}, {data.sa_id}, '{data.bill_path}', '{created_at}', '{data.is_bonus}');
                UPDATE public.users SET pending_balance_rf=pending_balance_rf + {data.amount} WHERE public.users.id = {data.user_id};
                UPDATE public.server_params SET pending_balance_rf=pending_balance_rf + {data.amount};
            """
        )

        if data.promo_id is not None:
            if data.is_bonus:
                query += f"INSERT into public.users_bonus_codes VALUES({data.user_id}, {data.promo_id}, '{created_at}');"
            else:
                query += f"INSERT into public.users_promos VALUES({data.user_id}, {data.promo_id}, '{created_at}');"

        db.session.execute(text(query))
        db.session.commit()

    except Exception:
        db.session.rollback()
        logger.exception("Ошибка при попытке создать транзакцию.")
        return False

    return True


def send_tg_message_with_transaction_updated_status(user_id, transaction_id):
    messages = {
        0: "Транзакция на сумму {amount} отклонена оператором",
        1: "Транзакция на сумму {amount} в обработке",
        2: "Транзакция на сумму {amount} успешно проведена оператором",
    }
    try:
        tg_user = TgUser.query.filter(TgUser.flask_user_id == user_id).first()
        transaction = UserTransaction.query.filter(
            UserTransaction.id == transaction_id,
        ).first()
        if tg_user is not None and transaction is not None:
            tg_message = {
                "chat_id": tg_user.tg_chat_id,
                "message": messages[transaction.status].format(amount=transaction.amount)
            }
            NotificationTgUser.send_notification.delay(**tg_message)
    except Exception:
        logger.exception("Ошибка отправки при формировании и отправки сообщения в телеграм по статусу транзакции")
