from flask import Blueprint
from flask_login import login_required


from utilities.support import user_activated
from views.main.product_cards.handlers import h_cards, h_cards_table, h_new_product_card, \
    h_save_product_card, h_card_delete, h_card_edit, h_card_view, h_get_created_cards, \
    h_send_cards_moderate, h_make_pc_basket_order, h_pc_order_view, h_pc_orders_drafts, h_pc_order_table, \
    h_pc_order_pos_view, h_pc_order_delete_pos, h_pc_order_delete, h_pc_order_preview, h_pc_order_check_before_process, \
    h_pc_order_process, h_update_product_card, h_edit_product_card, h_pc_order_copy, h_pc_order_draft_delete

user_product_cards = Blueprint('user_product_cards', __name__)


@user_product_cards.route('/cards', methods=['GET'])
@login_required
@user_activated
def cards():
    return h_cards()


@user_product_cards.route('/cards/table', methods=['POST'])
@login_required
@user_activated
def cards_table():
    return h_cards_table()


@user_product_cards.route('/new_product_card', methods=['GET', ])
@login_required
@user_activated
def new_product_card():
    return h_new_product_card()


@user_product_cards.route("/save_product_card", methods=["POST"])
@login_required
@user_activated
def save_product_card():
    return h_save_product_card()


@user_product_cards.route("/cards/<int:card_id>/edit", methods=["GET"])
@login_required
@user_activated
def edit_product_card(card_id):
    return h_edit_product_card(card_id=card_id)


@user_product_cards.route("/update_product_card", methods=["POST"])
@login_required
@user_activated
def update_product_card():
    return h_update_product_card()


@user_product_cards.route("/cards/created", methods=["GET"])
@login_required
@user_activated
def get_created_cards():
    return h_get_created_cards()


@user_product_cards.route("/cards/send_moderate", methods=["POST"])
@login_required
@user_activated
def send_cards_moderate():
    return h_send_cards_moderate()


@user_product_cards.route("/card_view/<int:card_id>", methods=["GET"])
@login_required
@user_activated
def card_view(card_id: int):
    return h_card_view(card_id=card_id)


@user_product_cards.route("/card_edit/<int:card_id>", methods=["GET"])
@login_required
@user_activated
def card_edit(card_id: int):
    return h_card_edit(card_id=card_id)


@user_product_cards.route("/card_delete/<int:card_id>", methods=["POST"])
@login_required
@user_activated
def card_delete(card_id: int):
    return h_card_delete(card_id=card_id)


@user_product_cards.route("/make_pc_basket_order", methods=["POST"])
@login_required
@user_activated
def make_pc_basket_order():
    return h_make_pc_basket_order()


@user_product_cards.route("/pc_orders_drafts", methods=["GET"])
@login_required
@user_activated
def pc_orders_drafts():
    return h_pc_orders_drafts()


@user_product_cards.route("/pc_order_copy/<int:o_id>", methods=["POST"])
@login_required
@user_activated
def pc_order_copy(o_id: int):
    return h_pc_order_copy(o_id=o_id)


@user_product_cards.route("/pc_order_draft_delete/<int:o_id>", methods=["POST"])
@login_required
@user_activated
def pc_order_draft_delete(o_id: int):
    return h_pc_order_draft_delete(o_id=o_id)


@user_product_cards.route("/pc_order/<int:o_id>", methods=["GET"])
@login_required
@user_activated
def pc_order_view(o_id: int):
    return h_pc_order_view(o_id=o_id)


@user_product_cards.route("/order/<int:o_id>/preview", methods=["GET"])
@login_required
@user_activated
def pc_order_preview(o_id: int):
    return h_pc_order_preview(o_id=o_id)


@user_product_cards.route("/pc_order/<int:o_id>/table", methods=["GET"])
@login_required
@user_activated
def pc_order_table(o_id: int):
    return h_pc_order_table(o_id=o_id)


@user_product_cards.route("/pc_order/<int:o_id>/pos/<int:pos_id>", methods=["GET"])
@login_required
@user_activated
def pc_order_pos_view(o_id: int, pos_id: int):
    return h_pc_order_pos_view(o_id=o_id, pos_id=pos_id)


@user_product_cards.route("/pc_order/<int:o_id>/pos/<int:pos_id>/delete", methods=["POST"])
@login_required
@user_activated
def pc_order_delete_pos(o_id: int, pos_id: int):
    return h_pc_order_delete_pos(o_id=o_id, pos_id=pos_id)


@user_product_cards.route("/pc_order/<int:o_id>/delete", methods=["POST"])
@login_required
@user_activated
def pc_order_delete(o_id: int):
    return h_pc_order_delete(o_id=o_id)


@user_product_cards.route("/pc_order/<int:o_id>/check_before_process", methods=["POST"])
@login_required
@user_activated
def pc_order_check_before_process(o_id: int):
    return h_pc_order_check_before_process(o_id=o_id)


@user_product_cards.route("/pc_order/<int:o_id>/process", methods=["POST"])
@login_required
@user_activated
def pc_order_process(o_id: int):
    return h_pc_order_process(o_id=o_id)


@user_product_cards.route('/create_card', methods=['POST', ])
@login_required
@user_activated
def create_card():
    return ...
# @product_cards.route('/process_order/<int:o_id>', methods=['POST', ])
# @login_required
# @user_activated
# def process_order(o_id: int):
#     user = current_user
#     order_comment = request.form.to_dict().get("order_comment", "")
#
#     order = user.orders.filter_by(category=settings.Linen.CATEGORY, processed=False, id=o_id).filter(~Order.to_delete).first()
#
#     return helper_process_category_order(user=user, order=order, category=settings.Linen.CATEGORY,
#                                          order_comment=order_comment)


