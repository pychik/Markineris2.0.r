from flask import Blueprint, flash, redirect, request, url_for
from flask_login import current_user, login_required

from config import settings
from models import Order, Toys
from utilities.support import (
    common_process_delete_order,
    helper_delete_order_pos,
    helper_process_category_order,
    helper_preload_common,
    preprocess_order_category,
    user_activated,
)
from views.main.categories.toys.support import helper_toys_index


toys = Blueprint("toys", __name__)


@toys.route("/", defaults={"subcategory": None, "o_id": None, "update_flag": None}, methods=["GET"])
@toys.route("/<string:subcategory>", defaults={"o_id": None, "update_flag": None}, methods=["GET"])
@toys.route("/<string:subcategory>/<int:o_id>/", defaults={"update_flag": None}, methods=["GET"])
@toys.route("/<string:subcategory>/<int:o_id>/<int:update_flag>/", methods=["GET"])
@login_required
@user_activated
def index(subcategory: str | None = None, o_id: int | None = None, update_flag: int | None = None):
    return helper_toys_index(subcategory=subcategory, o_id=o_id, update_flag=update_flag)


@toys.route("/<string:subcategory>/<int:o_id>/copy_order/<int:p_id>", defaults={"edit_order": None}, methods=["GET"])
@toys.route("/<string:subcategory>/<int:o_id>/copy_order/<int:p_id>/<string:edit_order>/", methods=["GET"])
@login_required
@user_activated
def copy_order(subcategory: str, o_id: int, p_id: int, edit_order: str | None = None):
    copied_order = (
        Toys.query
        .join(Order, Toys.order_id == Order.id)
        .filter(
            Toys.id == p_id,
            Toys.subcategory == subcategory,
            Order.user_id == current_user.id,
            ~Order.to_delete,
        )
        .first()
    )
    if not copied_order:
        flash(message=settings.Messages.NO_SUCH_ORDER, category="error")
        return redirect(url_for("toys.index", subcategory=subcategory))
    return helper_toys_index(
        subcategory=subcategory,
        o_id=o_id,
        p_id=p_id,
        copied_order=copied_order,
        edit_order=edit_order,
    )


@toys.route("/<string:subcategory>/preprocess_order/", defaults={"o_id": None}, methods=["POST"])
@toys.route("/<string:subcategory>/preprocess_order/<int:o_id>", defaults={"p_id": None}, methods=["POST"])
@toys.route("/<string:subcategory>/preprocess_order/<int:o_id>/<int:p_id>", methods=["POST"])
@login_required
@user_activated
def preprocess_order(subcategory: str, o_id: int | None = None, p_id: int | None = None):
    return preprocess_order_category(o_id=o_id, p_id=p_id, category=settings.Toys.CATEGORY)


@toys.route("/<string:subcategory>/<int:o_id>/delete_order/<int:c_id>", defaults={"async_type": None}, methods=["POST"])
@toys.route("/<string:subcategory>/<int:o_id>/delete_order/<int:c_id>/<int:async_type>", methods=["POST"])
@login_required
@user_activated
def delete_order_pos(subcategory: str, o_id: int, c_id: int, async_type: int | None = None):
    return helper_delete_order_pos(
        o_id=o_id,
        m_id=c_id,
        async_type=async_type,
        category=settings.Toys.CATEGORY,
        model=Toys,
    )


@toys.route("/<string:subcategory>/<int:o_id>/clean_orders/", methods=["GET"])
@login_required
@user_activated
def clean_orders(subcategory: str, o_id: int):
    common_process_delete_order(o_id=o_id, stage=settings.OrderStage.CREATING)
    return redirect(url_for("toys.index", subcategory=subcategory))


@toys.route("/<string:subcategory>/process_order/<int:o_id>", methods=["POST"])
@login_required
@user_activated
def process_order(subcategory: str, o_id: int):
    user = current_user
    order_comment = request.form.to_dict().get("order_comment", "")
    order = user.orders.filter_by(category=settings.Toys.CATEGORY, processed=False, id=o_id).filter(~Order.to_delete).first()
    return helper_process_category_order(
        user=user,
        order=order,
        category=settings.Toys.CATEGORY,
        order_comment=order_comment,
    )


@toys.route("/preload/<int:o_id>/<int:stage>/", methods=["GET"])
@login_required
@user_activated
def preload(o_id: int, stage: int):
    return helper_preload_common(
        o_id=o_id,
        stage=stage,
        category=settings.Toys.CATEGORY,
        category_process_name=settings.Toys.CATEGORY_PROCESS,
    )
