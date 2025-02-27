from flask import Blueprint, flash, redirect, url_for, request
from flask_login import current_user, login_required

from config import settings
from models import Clothes, Order
from utilities.helpers.h_categories import h_category_sba
from views.main.categories.clothes.support import h_bck_clothes_tnved
from utilities.categories_data.subcategories_logic import get_subcategory
from utilities.support import (check_order_pos, preprocess_order_category, common_process_delete_order,
    helper_delete_order_pos, user_activated, helper_process_category_order,
    helper_preload_common, manager_forbidden)
from utilities.upload_order.upload_clothes import UploadClothes
from utilities.upload_order.upload_logic import helper_upload_common_get, helper_upload_common_post
from views.main.categories.clothes.support import helper_clothes_index

clothes = Blueprint('clothes', __name__)


@clothes.route('/', defaults={'o_id': None}, methods=['GET', ])
@clothes.route('/<int:o_id>/', defaults={'update_flag': None}, methods=['GET', ])
@clothes.route('/<int:o_id>/<int:update_flag>', methods=['GET', ])
@login_required
@user_activated
@manager_forbidden
def index(o_id: int = None, update_flag: int = None):

    return helper_clothes_index(o_id=o_id, update_flag=update_flag)


@clothes.route('/<int:o_id>/copy_order/<int:p_id>', defaults={'edit_order': None}, methods=['GET', ])
@clothes.route('/<int:o_id>/copy_order/<int:p_id>/<string:edit_order>/', methods=['GET', ])
@login_required
@user_activated
def copy_order(o_id: int, p_id: int, edit_order: str = None):
    copied_order = Clothes.query.filter_by(id=p_id).first()
    if not copied_order:
        flash(message=settings.Messages.NO_SUCH_ORDER, category='error')
        return redirect(url_for('clothes.index'))
    return helper_clothes_index(o_id=o_id, p_id=p_id, copied_order=copied_order, edit_order=edit_order)


@clothes.route('/preprocess_order/', defaults={'o_id': None}, methods=['POST', ])
@clothes.route('/preprocess_order/<int:o_id>', defaults={'p_id': None}, methods=['POST', ])
@clothes.route('/preprocess_order/<int:o_id>/<int:p_id>', methods=['POST', ])
@login_required
@user_activated
def preprocess_order(o_id: int = None, p_id: int = None):
    return preprocess_order_category(o_id=o_id, p_id=p_id, category=settings.Clothes.CATEGORY)


@clothes.route('<int:o_id>/delete_order/<int:c_id>', defaults={'async_type': None}, methods=['POST', ])
@clothes.route('<int:o_id>/delete_order/<int:c_id>/<int:async_type>', methods=['POST', ])
@login_required
@user_activated
def delete_order_pos(o_id: int, c_id: int, async_type: int = None):
    return helper_delete_order_pos(o_id=o_id, m_id=c_id, async_type=async_type, category=settings.Clothes.CATEGORY,
                                   model=Clothes)


@clothes.route('<int:o_id>/clean_orders/', methods=['GET', ])
@login_required
@user_activated
def clean_orders(o_id: int):
    common_process_delete_order(o_id=o_id, stage=settings.OrderStage.CREATING)
    subcategory = get_subcategory(order_id=o_id, category=settings.Clothes.CATEGORY)
    return redirect(url_for('clothes.index', subcategory=subcategory))


# @clothes.route('/download_order/<int:o_id>', methods=['POST', ])
# @login_required
# @user_activated
# def download_order(o_id: int):
#     user = current_user
#
#     if not o_id:
#         flash(message=settings.Messages.EMPTY_ORDER, category='error')
#         return redirect(url_for('clothes.index'))
#     return orders_download_common(user=user, o_id=o_id)


@clothes.route('/process_order/<int:o_id>', methods=['POST', ])
@login_required
@user_activated
def process_order(o_id: int):
    user = current_user
    order_comment = request.form.to_dict().get("order_comment", "")

    order = (user.orders.filter_by(category=settings.Clothes.CATEGORY, processed=False, id=o_id)
             .filter(~Order.to_delete).first())

    return helper_process_category_order(user=user, order=order, category=settings.Clothes.CATEGORY,
                                         order_comment=order_comment)


@clothes.route('/search_by_article/<int:o_id>', methods=['POST', ])
@login_required
@user_activated
def search_by_article(o_id: int):
    return h_category_sba(u_id=current_user.id, o_id=o_id, model_c=Clothes, category=settings.Clothes.CATEGORY_PROCESS)


@clothes.route('/upload', methods=['GET', ])
@login_required
@user_activated
def upload():
    return helper_upload_common_get(category=settings.Clothes.CATEGORY,
                                    category_process_name=settings.Clothes.CATEGORY_PROCESS)


@clothes.route('/process_upload', methods=['POST', ])
@login_required
def process_upload():
    return helper_upload_common_post(category=settings.Clothes.CATEGORY,
                                     category_process_name=settings.Clothes.CATEGORY_PROCESS,
                                     upload_model=UploadClothes)


@clothes.route('/preload/<int:o_id>/<int:stage>', methods=['GET', ])
@user_activated
@login_required
def preload(o_id: int, stage: int):
    return helper_preload_common(o_id=o_id, stage=stage, category=settings.Clothes.CATEGORY,
                                 category_process_name=settings.Clothes.CATEGORY_PROCESS)


@clothes.route('/bck_clothes_tnved', methods=['POST', ])
@user_activated
@login_required
def bck_clothes_tnved():
    """
        returns modal block with tnveds
    """
    return h_bck_clothes_tnved()
