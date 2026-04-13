from datetime import datetime

from flask import Blueprint, jsonify
from flask_login import login_required, current_user

from utilities.support import (
    user_activated,
    sumausmumu_required,
    suausmumu_required,
    susmumu_required,
    bck_sumausmumu_required, sumsuu_required, bck_susmu_required, bck_suausmumu_t2_required,
)


from .handlers import h_crm_cards, h_download_product_card, h_pc_take_card_to_processing, h_companies_delete, \
    h_companies_create, h_companies_update, h_companies_modal, h_pc_move_card, h_pc_cards, h_pc_lazy_column, \
    h_search_crm_card, h_crm_set_company_slot, h_crm_approve_from_partially, h_download_cards_companies_in_progress, \
    h_transfer_sent_to_in_progress, h_download_cards_companies_by_status,  h_crm_reject_cards_by_rd_today
from .helpers import get_crm_card_for_user


from ..handlers import h_card_view, h_edit_product_card, h_update_product_card

crm_product_cards = Blueprint('crm_product_cards', __name__)


@crm_product_cards.route("/cards", methods=["GET"])
@login_required
@user_activated
@bck_suausmumu_t2_required
def cards():
    return h_crm_cards()


@crm_product_cards.route("/crm/cards/lazy_column", methods=["GET"])
@login_required
@user_activated
@bck_suausmumu_t2_required
def pc_lazy_column():
    return h_pc_lazy_column()


@crm_product_cards.route("/crm_card_view/<int:card_id>", methods=["GET"])
@login_required
@user_activated
@bck_suausmumu_t2_required
def crm_card_view(card_id: int):
    if not get_crm_card_for_user(card_id, current_user):
        return jsonify(status="error", message="Карточка не найдена"), 404
    return h_card_view(card_id=card_id, crm_=True)


@crm_product_cards.route("/crm_card_edit/<int:card_id>", methods=["GET"])
@login_required
@user_activated
@bck_sumausmumu_required
def crm_card_edit(card_id: int):
    return h_edit_product_card(card_id=card_id, crm_=True)


@crm_product_cards.route("/crm/update_product_card", methods=["POST"])
@login_required
@user_activated
@bck_sumausmumu_required
def crm_update_product_card():
    return h_update_product_card(crm_=True)


@crm_product_cards.route('/crm/download_card/<int:pc_id>', methods=["POST"])
@login_required
@user_activated
@suausmumu_required
def download_product_card(pc_id: int):
    return h_download_product_card(pc_id=pc_id)


@crm_product_cards.route("/crm/transfer_sent_to_in_progress", methods=["POST"])
@login_required
@user_activated
@sumausmumu_required
def transfer_sent_to_in_progress():
    return h_transfer_sent_to_in_progress()


@crm_product_cards.route("/crm/download_cards_companies_in_progress", methods=["POST"])
@login_required
@user_activated
@suausmumu_required
def download_cards_companies_in_progress():
    """
        POST:
          - manager_id (optional) — фильтр по закреплённому менеджеру (только для админ-ролей)
        """
    return h_download_cards_companies_in_progress()


@crm_product_cards.route("/crm/download_cards_companies", methods=["POST"])
@login_required
@user_activated
@suausmumu_required
def download_cards_companies():
    return h_download_cards_companies_by_status()


@crm_product_cards.route('/crm/pc_take_card_to_processing/<int:pc_id>', methods=["POST"])
@login_required
@user_activated
@bck_sumausmumu_required
def pc_take_card_to_processing(pc_id: int):
    return h_pc_take_card_to_processing(pc_id=pc_id)


@crm_product_cards.route("/crm/companies/modal", methods=["GET"])
@login_required
@user_activated
@bck_sumausmumu_required
def companies_modal():
    return h_companies_modal()


@crm_product_cards.route("/crm/companies/create", methods=["POST"])
@login_required
@user_activated
@sumsuu_required
def companies_create():
    return h_companies_create()


@crm_product_cards.route("/crm/companies/<int:company_id>/delete", methods=["POST"])
@login_required
@user_activated
@sumsuu_required
def companies_delete(company_id: int):
    return h_companies_delete(company_id=company_id)


@crm_product_cards.route("/crm/move_card/<int:pc_id>", methods=["POST"])
@login_required
@user_activated
@bck_sumausmumu_required
def pc_move_card(pc_id: int):
    return h_pc_move_card(pc_id)


@crm_product_cards.route("/pc/<int:pc_id>/logs")
@login_required
@user_activated
@bck_suausmumu_t2_required
def pc_card_logs(pc_id):
    return h_pc_cards(pc_id=pc_id)


@crm_product_cards.route('/crm/search_card', methods=['POST'])
@login_required
@user_activated
@bck_suausmumu_t2_required
def search_card():

    return h_search_crm_card()


@crm_product_cards.route("/crm/card/<int:card_id>/set_company_slot", methods=["POST"])
@login_required
@user_activated
@susmumu_required
def crm_set_company_slot(card_id: int):
    return h_crm_set_company_slot(card_id)


@crm_product_cards.route("/crm/card/<int:card_id>/approve_from_partially", methods=["POST"])
@login_required
@user_activated
@susmumu_required
def crm_approve_from_partially(card_id: int):
    return h_crm_approve_from_partially(card_id)


@crm_product_cards.route("/crm/cards/reject_by_rd_today", methods=["POST"])
@login_required
@user_activated
@susmumu_required
def crm_reject_cards_by_rd_today():
    return h_crm_reject_cards_by_rd_today()
