from flask import request, jsonify, Response
from flask_login import current_user
from sqlalchemy.exc import IntegrityError

from logger import logger
from models import TgUser, db
from utilities.telegram import NotificationTgUser
from config import settings


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
        try:
            # tg_user.flask_user_id = None
            db.session.delete(tg_user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            message = f"{settings.Messages.TG_VERIF_DELETE_ERROR}"
            logger.error(f"{message} {e}")
        else:
            status = 'success'
            message = f"{settings.Messages.TG_VERIF_DELETE_SUCCESS}"
    else:
        message = settings.Messages.STRANGE_REQUESTS
    return jsonify(dict(status=status, message=message))
