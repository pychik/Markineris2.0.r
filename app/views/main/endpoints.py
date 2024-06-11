from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from config import settings
from logger import logger
from utilities.support import helper_get_current_sa
from utilities.tg_verify.service import (
    check_promo_exists,
    check_promo_used,
    create_transaction_from_tg,
)
from validators.api import TransactionInData, PromoCheckInData

api = Blueprint('api', __name__)


# done
@api.get("/check_promo_code")
def check_promo_code():
    if request.headers.get("MARKINERS_V2_TOKEN") != settings.MARKINERS_V2_TOKEN:
        return jsonify({"detail": "Нет доступа."}), 403

    try:
        data = PromoCheckInData(**request.args)
    except ValidationError:
        logger.exception("Ошибка валидации при проверке промо кода.")
        return jsonify(
            {"detail": settings.Messages.STRANGE_REQUESTS}
        ), 500

    try:
        promo_code_obj = check_promo_exists(promo_code=data.promo_code)
    except Exception:
        logger.exception("Ошибка проверки промо кода")
        return jsonify(
            {"detail": settings.Messages.STRANGE_REQUESTS}
        ), 500

    if promo_code_obj is None:
        return jsonify(
            {"detail": settings.Messages.PROMO_NE_ERROR}
        ), 404

    is_used = check_promo_used(user_id=data.user_id, promo_code=promo_code_obj.code)

    if is_used:
        return jsonify(
            {"detail": settings.Messages.PROMO_USED_ERROR}
        ), 409

    return jsonify({
        "promo_id": promo_code_obj.id,
        "amount": promo_code_obj.value,
    })


# done
@api.get("/get_current_service_account")
def get_current_service_account():
    if request.headers.get("MARKINERS_V2_TOKEN") != settings.MARKINERS_V2_TOKEN:
        return jsonify({"detail": "Нет доступа."}), 403

    try:
        current_service_account = helper_get_current_sa()
    except Exception as e:
        logger.exception(e)
        return jsonify(
            {"detail": settings.Messages.STRANGE_REQUESTS}
        ), 500
    else:
        return jsonify(
            {
                "requisite_id": current_service_account.id,
                "requisite": (
                    current_service_account.sa_reqs if
                    current_service_account.sa_type == "requisites" else
                    current_service_account.sa_qr_path
                ),
                "requisite_type": current_service_account.sa_type,
            },
        )


@api.post("/create_transaction")
def create_transaction():
    if request.headers.get("MARKINERS_V2_TOKEN") != settings.MARKINERS_V2_TOKEN:
        return jsonify({"detail": "Нет доступа."}), 403

    try:
        data = TransactionInData(**request.form)
    except ValidationError as e:
        logger.exception(e)
        return jsonify(
            # TODO: подумать над сообщением ответа в бот при ошибке получения create_transaction
            {"detail": "Ошибка валидации данных."}
        ), 422

    is_created = create_transaction_from_tg(data)

    if not is_created:
        return jsonify({"detail": settings.Messages.STRANGE_REQUESTS}), 400

    return jsonify({"detail": "Транзакция успешно создана, оператор скоро ее проверит."}), 201
