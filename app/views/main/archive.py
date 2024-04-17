from flask import Blueprint
from flask_login import login_required

from config import settings
from utilities.helpers.h_archive import h_delete_order, h_copy_order, h_category, h_download_oa, h_download_opdf, h_download_opdf_common
from utilities.support import user_activated

orders_archive = Blueprint('orders_archive', __name__)


@orders_archive.route('/', defaults={'category': settings.Shoes.CATEGORY}, methods=['GET', ])
@orders_archive.route('/<string:category>/', defaults={'upload_flag': None}, methods=['GET', ])
@orders_archive.route('/<string:category>/<int:upload_flag>', methods=['GET', ])
@login_required
@user_activated
def index(category: str = settings.Shoes.CATEGORY, upload_flag: int = None):
    # using upload bck flag as 111
    return h_category(category=category, upload_flag=upload_flag)


@orders_archive.route('/delete_complete_order/<int:o_id>/<int:stage>/<string:category>', methods=['POST'])
@login_required
@user_activated
def delete_order(o_id: int, stage: int, category: str):
    return h_delete_order(o_id=o_id, stage=stage, category=category)


@orders_archive.route('/copy_order/<int:o_id>/<category>', methods=['POST'])
@login_required
@user_activated
def copy_order(o_id: int, category: str):
    return h_copy_order(o_id=o_id, category=category)


@orders_archive.route('/download_oa/<int:o_id>/<string:category>', methods=['POST'])
@login_required
@user_activated
def download_oa(o_id: int, category: str):
    """
     returns Io stream to download file or redirect with message
     download_oa - download order archive
    :param o_id:
    :param category:
    :return:
    """
    return h_download_oa(o_id=o_id, category=category)


# @orders_archive.route('/download_opdf/<int:o_id>/<string:category>', methods=['POST'])
# @login_required
# @user_activated
# def download_opdf(o_id: int, category: str):
#     """
#      returns Io stream to download united and processed pdf or redirect with message
#      download_opdf - download order pdf
#     :param o_id:
#     :param category:
#     :return:
#     """
#     return h_download_opdf(o_id=o_id, category=category)

@orders_archive.route('/download_opdf_common/<int:o_id>/<string:category>', methods=['GET'])
@login_required
@user_activated
def download_opdf_common(o_id: int, category: str):
    """
     returns Io stream to download united and processed pdf or redirect with message
     download_opdf - download order pdf
    :param o_id:
    :param category:
    :return:
    """
    return h_download_opdf_common(o_id=o_id, category=category)
