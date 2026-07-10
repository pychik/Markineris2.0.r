from flask import Blueprint, flash, redirect, request, url_for
from flask_login import current_user, login_required

from config import settings
from models import Cosmetics, Order
from utilities.support import (
    common_process_delete_order,
    helper_delete_order_pos,
    helper_process_category_order,
    helper_preload_common,
    preprocess_order_category,
    user_activated,
    manager_forbidden,
)
from views.main.categories.cosmetics.support import helper_cosmetics_index


cosmetics = Blueprint("cosmetics", __name__)


@cosmetics.route("/", defaults={"subcategory": None, "o_id": None, "update_flag": None}, methods=["GET"])
@cosmetics.route("/<string:subcategory>", defaults={"o_id": None, "update_flag": None}, methods=["GET"])
@cosmetics.route("/<string:subcategory>/<int:o_id>/", defaults={"update_flag": None}, methods=["GET"])
@cosmetics.route("/<string:subcategory>/<int:o_id>/<int:update_flag>/", methods=["GET"])
@login_required
@user_activated
@manager_forbidden
def index(subcategory: str | None = None, o_id: int | None = None, update_flag: int | None = None):
    return helper_cosmetics_index(subcategory=subcategory, o_id=o_id, update_flag=update_flag)


@cosmetics.route("/search_by_article/<int:o_id>", methods=["POST"])
@login_required
@user_activated
def search_by_article(o_id: int):
    from utilities.helpers.h_categories import h_category_trademark_sba

    return h_category_trademark_sba(
        u_id=current_user.id,
        o_id=o_id,
        model_c=Cosmetics,
        category=settings.Cosmetics.CATEGORY_PROCESS,
    )


@cosmetics.route("/<string:subcategory>/<int:o_id>/copy_order/<int:p_id>", defaults={"edit_order": None}, methods=["GET"])
@cosmetics.route("/<string:subcategory>/<int:o_id>/copy_order/<int:p_id>/<string:edit_order>/", methods=["GET"])
@login_required
@user_activated
def copy_order(subcategory: str, o_id: int, p_id: int, edit_order: str | None = None):
    copied_order = (
        Cosmetics.query
        .join(Order, Cosmetics.order_id == Order.id)
        .filter(
            Cosmetics.id == p_id,
            Cosmetics.subcategory == subcategory,
            Order.user_id == current_user.id,
            ~Order.to_delete,
        )
        .first()
    )
    if not copied_order:
        flash(message=settings.Messages.NO_SUCH_ORDER, category="error")
        return redirect(url_for("cosmetics.index", subcategory=subcategory))
    return helper_cosmetics_index(
        subcategory=subcategory,
        o_id=o_id,
        p_id=p_id,
        copied_order=copied_order,
        edit_order=edit_order,
    )


@cosmetics.route("/<string:subcategory>/preprocess_order/", defaults={"o_id": None}, methods=["POST"])
@cosmetics.route("/<string:subcategory>/preprocess_order/<int:o_id>", defaults={"p_id": None}, methods=["POST"])
@cosmetics.route("/<string:subcategory>/preprocess_order/<int:o_id>/<int:p_id>", methods=["POST"])
@login_required
@user_activated
def preprocess_order(subcategory: str, o_id: int | None = None, p_id: int | None = None):
    return preprocess_order_category(o_id=o_id, p_id=p_id, category=settings.Cosmetics.CATEGORY)


@cosmetics.route("/<string:subcategory>/<int:o_id>/delete_order/<int:c_id>", defaults={"async_type": None}, methods=["POST"])
@cosmetics.route("/<string:subcategory>/<int:o_id>/delete_order/<int:c_id>/<int:async_type>", methods=["POST"])
@login_required
@user_activated
def delete_order_pos(subcategory: str, o_id: int, c_id: int, async_type: int | None = None):
    return helper_delete_order_pos(
        o_id=o_id,
        m_id=c_id,
        async_type=async_type,
        category=settings.Cosmetics.CATEGORY,
        model=Cosmetics,
    )


@cosmetics.route("/<string:subcategory>/<int:o_id>/clean_orders/", methods=["GET"])
@login_required
@user_activated
def clean_orders(subcategory: str, o_id: int):
    common_process_delete_order(o_id=o_id, stage=settings.OrderStage.CREATING)
    return redirect(url_for("cosmetics.index", subcategory=subcategory))


@cosmetics.route("/<string:subcategory>/process_order/<int:o_id>", methods=["POST"])
@login_required
@user_activated
def process_order(subcategory: str, o_id: int):
    user = current_user
    order_comment = request.form.to_dict().get("order_comment", "")
    order = user.orders.filter_by(category=settings.Cosmetics.CATEGORY, processed=False, id=o_id).filter(~Order.to_delete).first()
    return helper_process_category_order(
        user=user,
        order=order,
        category=settings.Cosmetics.CATEGORY,
        order_comment=order_comment,
    )


@cosmetics.route("/preload/<int:o_id>/<int:stage>/", methods=["GET"])
@login_required
@user_activated
def preload(o_id: int, stage: int):
    return helper_preload_common(
        o_id=o_id,
        stage=stage,
        category=settings.Cosmetics.CATEGORY,
        category_process_name=settings.Cosmetics.CATEGORY_PROCESS,
    )
