from datetime import date, timedelta

from flask import Blueprint, flash, render_template, redirect, url_for, request
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from config import settings
from logger import logger
from models import User, Order, db
from utilities.support import user_activated, su_required, susmu_required, susmumu_required, manager_exist_check
from views.crm.helpers import helper_clean_oco, check_manager_orders, helper_change_manager_limit, helper_get_limits, \
                              helper_change_auto_order_pool, helper_change_auto_order_sent


# crm user order control
crm_uoc = Blueprint('crm_uoc', __name__)


@crm_uoc.route('/', methods=["GET"])
@login_required
@user_activated
@susmumu_required
def index():

    user = current_user
    managers_list = User.query.filter(User.role.in_([settings.SUPER_MANAGER, settings.MANAGER_USER])) \
        .with_entities(User.id, User.status, User.role, User.login_name ).order_by(User.id).all()

    dt_co = date.today() - timedelta(days=settings.OrderStage.DAYS_CONTENT)
    cancelled_orders = Order.query.with_entities(Order.id) \
        .filter(Order.stage == settings.OrderStage.CANCELLED, Order.cc_created < dt_co).count()

    if managers_list:
        new_manager_name = managers_list[-1].login_name.split('_')[0] + '_' + str(
            int(managers_list[-1].login_name.split('_')[1]) + 1)

    crm_defaults = helper_get_limits()

    return render_template('crm/crm_uoc.html', **locals())


@crm_uoc.route('/create_manager/', methods=['POST'])
@login_required
@user_activated
@susmu_required
def create_manager():

    form_dict = request.form.to_dict()
    login_name = form_dict.get("manager_login_name")
    password = form_dict.get("manager_password")

    try:
        new_manager = User(admin_order_num=0, login_name=login_name, phone=settings.SU_PHONE,
                           email=login_name + settings.MANAGER_EMAIL_POSTFIX,
                           is_crm=True, is_send_excel=True,
                           password=generate_password_hash(password, method='sha256'),
                           role=settings.MANAGER_USER, client_code=settings.MU_PARTNER, status=True)

        db.session.add(new_manager)
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        message = f"{settings.Messages.MANAGER_CREATE_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)

        return redirect(url_for('crm_uoc.index'))

    return redirect(url_for('crm_uoc.index'))


@crm_uoc.route('/delete_manager/<int:u_id>', methods=['POST'])
@login_required
@susmu_required
@manager_exist_check
def delete_manager(u_id: int):
    user = User.query.filter_by(id=u_id).first()
    order_count = check_manager_orders(u_id=u_id)
    if order_count != 0:
        flash(message=f'{settings.Messages.DELETE_USER_ERROR} {settings.Messages.DELETE_MANAGER_ERROR} {order_count}',
              category='error')
        return redirect(url_for('crm_uoc.index'))

    try:
        user.telegram = []
        db.session.delete(user)
        db.session.commit()
        flash(message=f"{settings.Messages.DELETE_USER} {user.login_name}")
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.DELETE_USER_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)

    return redirect(url_for('crm_uoc.index'))


@crm_uoc.route('/activate_manager/<int:u_id>', methods=['POST'])
@login_required
@susmu_required
def activate_manager(u_id: int):
    user = User.query.filter_by(id=u_id).first()
    if not user:
        flash(message=f"{settings.Messages.ACTIVATED_USER_ERROR}", category='error')
        return redirect(url_for('main.index'))
    try:
        user.status = True
        db.session.commit()

        flash(message=f"{settings.Messages.ACTIVATED_USER} {user.login_name}")
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.ACTIVATED_USER_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)

    return redirect(url_for('crm_uoc.index'))


@crm_uoc.route('/set_supermanager/<int:u_id>', methods=['POST'])
@login_required
@su_required
def set_supermanager(u_id: int):
    user = User.query.filter_by(id=u_id).first()
    if not user:
        flash(message=f"{settings.Messages.NO_SUCH_USER}", category='error')
        return redirect(url_for('main.index'))
    try:
        user.role = settings.SUPER_MANAGER
        db.session.commit()

        flash(message=f"{settings.Messages.SUPERMANAGER_SET} {user.login_name}")
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.SUPERMANAGER_SET_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)

    return redirect(url_for('crm_uoc.index'))


@crm_uoc.route('/set_manager/<int:u_id>', methods=['POST'])
@login_required
@su_required
def set_manager(u_id: int):
    user = User.query.filter_by(id=u_id).first()
    if not user:
        flash(message=f"{settings.Messages.NO_SUCH_USER}", category='error')
        return redirect(url_for('main.index'))
    try:
        user.role = settings.MANAGER_USER
        db.session.commit()

        flash(message=f"{settings.Messages.MANAGER_SET} {user.login_name}")
    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.MANAGER_SET_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)

    return redirect(url_for('crm_uoc.index'))


@crm_uoc.route('/deactivate_manager/<int:u_id>', methods=['POST'])
@login_required
@susmu_required
@manager_exist_check
def deactivate_manager(u_id: int):

    user = User.query.filter_by(id=u_id).first()
    try:
        user.status = False
        db.session.commit()
        flash(message=f"{settings.Messages.DEACTIVATED_USER} {user.login_name}")

    except Exception as e:
        db.session.rollback()
        message = f"{settings.Messages.DEACTIVATED_USER_ERROR} {e}"
        flash(message=message, category='error')
        logger.error(message)

    return redirect(url_for('crm_uoc.index'))


# clean old cancelled orders
@crm_uoc.route('/clean_oco', methods=['POST'])
@login_required
@su_required
def clean_oco():
    return helper_clean_oco()


@crm_uoc.route('/change_manager_limit/<string:limit_param>', methods=['POST'])
@login_required
@su_required
def change_manager_limit(limit_param: str):
    return helper_change_manager_limit(limit_param=limit_param)


@crm_uoc.route('/change_auto_order_pool', methods=['POST'])
@login_required
@su_required
def change_auto_order_pool():
    return helper_change_auto_order_pool()


@crm_uoc.route('/change_auto_order_sent', methods=['POST'])
@login_required
@su_required
def change_auto_order_sent():
    return helper_change_auto_order_sent()
