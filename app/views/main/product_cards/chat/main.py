from datetime import datetime

from flask import flash, render_template, redirect, url_for, request, jsonify, Blueprint
from flask_login import current_user, login_required

from config import settings
from logger import logger
from utilities.download import orders_download_common
from utilities.support import (
    user_activated,
    sumausmumu_required,
    susmumu_required,
    susmu_required,
    su_mod_required, bck_sumausmumu_required, sumsuu_required,
)
from views.main.product_cards.chat.handlers import h_pc_chat_get_messages, h_pc_chat_send, h_pc_chat_mark_read

chat_product_cards = Blueprint('chat_product_cards', __name__)


@chat_product_cards.route("/crm/cards/<int:pc_id>/chat/messages", methods=["GET"])
@login_required
@user_activated
def pc_chat_get_messages(pc_id: int):
    return h_pc_chat_get_messages(pc_id)


@chat_product_cards.route("/crm/cards/<int:pc_id>/chat/send", methods=["POST"])
@login_required
@user_activated
def pc_chat_send(pc_id: int):
    return h_pc_chat_send(pc_id)


@chat_product_cards.route("/crm/cards/<int:pc_id>/chat/read", methods=["POST"])
@login_required
@user_activated
def pc_chat_mark_read(pc_id: int):
    return h_pc_chat_mark_read(pc_id)
