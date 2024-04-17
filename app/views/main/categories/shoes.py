from flask import Blueprint, flash, redirect, url_for, request
from flask_login import current_user, login_required

from config import settings
from models import Shoe
from utilities.download import orders_download_common
from utilities.helpers.h_categories import h_category_sba
from utilities.support import check_order_pos, preprocess_order_category, common_process_delete_order, \
    helper_delete_order_pos, user_activated, manager_forbidden, \
    helper_process_category_order, helper_shoes_index, helper_preload_common
from utilities.upload_order.upload_logic import helper_upload_common_get, helper_upload_common_post
from utilities.upload_order.upload_shoes import UploadShoes

shoes = Blueprint('shoes', __name__)


@shoes.route('/', defaults={'o_id': None}, methods=['GET', ])
@shoes.route('/<int:o_id>/', defaults={'update_flag': None}, methods=['GET', ])
@shoes.route('/<int:o_id>/<int:update_flag>/', methods=['GET', ])
@login_required
@user_activated
@manager_forbidden
def index(o_id: int = None, update_flag: int = None):
    return helper_shoes_index(o_id=o_id, update_flag=update_flag)


@shoes.route('/<int:o_id>/copy_order/<int:p_id>', defaults={'edit_order': None}, methods=['GET', ])
@shoes.route('/<int:o_id>/copy_order/<int:p_id>/<string:edit_order>/', methods=['GET', ])
@login_required
@user_activated
def copy_order(o_id: int, p_id: int = None, edit_order: str = None):
    copied_order = Shoe.query.filter_by(id=p_id).first()

    if not copied_order:
        flash(message=settings.Messages.NO_SUCH_ORDER, category='error')
        return redirect(url_for('shoes.index'))
    return helper_shoes_index(o_id=o_id, p_id=p_id, copied_order=copied_order, edit_order=edit_order)


@shoes.route('/preprocess_order/', defaults={'o_id': None}, methods=['POST', ])
@shoes.route('/preprocess_order/<int:o_id>', defaults={'p_id': None}, methods=['POST', ])
@shoes.route('/preprocess_order/<int:o_id>/<int:p_id>',  methods=['POST', ])
@login_required
@user_activated
def preprocess_order(o_id: int = None, p_id: int = None):
    return preprocess_order_category(o_id=o_id, p_id=p_id, category=settings.Shoes.CATEGORY)


@shoes.route('<int:o_id>/delete_order/<int:s_id>', defaults={'async_type': None}, methods=['POST', ])
@shoes.route('<int:o_id>/delete_order/<int:s_id>/<int:async_type>', methods=['POST', ])
@login_required
@user_activated
def delete_order_pos(o_id: int, s_id: int, async_type: int = None):
    return helper_delete_order_pos(o_id=o_id, m_id=s_id, async_type=async_type, category=settings.Shoes.CATEGORY,
                                   model=Shoe)


@shoes.route('<int:o_id>/clean_orders/', methods=['GET', ])
@login_required
@user_activated
def clean_orders(o_id: int):
    common_process_delete_order(o_id=o_id, stage=settings.OrderStage.CREATING)

    return redirect(url_for('shoes.index'))


@shoes.route('/download_order/<int:o_id>', methods=['POST', ])
@login_required
@user_activated
def download_order(o_id: int):
    user = current_user
    if not o_id:
        flash(message=settings.Messages.EMPTY_ORDER, category='error')
        return redirect(url_for('shoes.index'))
    return orders_download_common(user=user, o_id=o_id)


@shoes.route('/process_order/<int:o_id>', methods=['POST', ])
@login_required
@user_activated
def process_order(o_id):
    user = current_user
    order_comment = request.form.to_dict().get("order_comment", "")

    order = user.orders.filter_by(category=settings.Shoes.CATEGORY, processed=False, id=o_id).first()

    # check order
    if not order:
        flash(message=settings.Messages.EMPTY_ORDER, category='error')
        return redirect(url_for('shoes.index'))
    if not check_order_pos(category=settings.Shoes.CATEGORY, order=order):
        return redirect(url_for('shoes.index', o_id=order.id))

    return helper_process_category_order(user=user, category=settings.Shoes.CATEGORY,
                                         o_id=o_id, order_comment=order_comment)


@shoes.route('/search_by_article/<int:o_id>', methods=['POST', ])
@login_required
@user_activated
def search_by_article(o_id: int):
    return h_category_sba(o_id=o_id, model_c=Shoe, category=settings.Shoes.CATEGORY_PROCESS)


@shoes.route('/upload', methods=['GET', ])
@login_required
@user_activated
def upload():
    return helper_upload_common_get(category=settings.Shoes.CATEGORY,
                                    category_process_name=settings.Shoes.CATEGORY_PROCESS)


@shoes.route('/process_upload', methods=['POST', ])
@login_required
def process_upload():
    return helper_upload_common_post(category=settings.Shoes.CATEGORY,
                                     category_process_name=settings.Shoes.CATEGORY_PROCESS, upload_model=UploadShoes)


@shoes.route('/preload/<int:o_id>/<int:stage>', methods=['GET', ])
@user_activated
@login_required
def preload(o_id: int, stage: int):

    return helper_preload_common(o_id=o_id, stage=stage, category=settings.Shoes.CATEGORY,
                                 category_process_name=settings.Shoes.CATEGORY_PROCESS)
