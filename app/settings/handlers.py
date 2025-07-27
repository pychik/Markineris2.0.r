# handlers.py
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager
from flask_login import current_user
from flask_wtf.csrf import CSRFError
from config import settings
from models import User


def register_handlers(app: Flask) -> None:
    @app.before_request
    def check_maintenance():
        if app.config['MAINTENANCE_MODE']:
            return render_template('error_pages/maintenance.html')

    @app.context_processor
    def pass_arguments_to_templates() -> dict:
        contacts = dict(telegramm_group_link=settings.TELEGRAMM_GROUP_LINK,
                        mail_link=settings.MAIL_LINK,
                        whatsapp_link=settings.WHATSAPP_LINK,
                        info_center_link=settings.INFO_CENTER_LINK)
        return dict(categories_dict=settings.CATEGORIES_DICT, categories_upload=settings.CATEGORIES_UPLOAD,
                    subcategories_dict=settings.SUB_CATEGORIES_DICT,
                    user_translate_dict=settings.USER_TRANSLATE,
                    order_stages=settings.OrderStage, contacts=contacts,
                    excepted_articles=settings.ExceptionOrders.EXCEPTED_ARTICLES)

    @app.before_request
    def manager_forbidden_handler():
        if not current_user.is_authenticated:
            return
        if current_user.role not in [settings.MANAGER_USER, settings.SUPER_MANAGER, settings.MARKINERIS_ADMIN_USER]:
            return
        if request.path == url_for('auth.logout') or request.path.startswith('/static/') or request.path.startswith(
                '/_debug_toolbar/'):
            return
        if current_user.role == settings.SUPER_MANAGER and request.path.startswith('/crm_uoc'):
            return
        if current_user.role == settings.MARKINERIS_ADMIN_USER:
            allowed_reanimate_url = [
                url_for('admin_control.bck_control_reanimate'),
                url_for('admin_control.bck_reanimate_save_call_result'),
                url_for('admin_control.bck_su_control_reanimate_excel'),
            ]
            allowed_transaction_url = [
                url_for('admin_control.su_bck_control_ut'),
                # url_for('admin_control.update_transaction_account', transaction_id=1)[:-3],
                url_for('admin_control.su_control_ut'),
                url_for('admin_control.su_bck_ut_report'),
                url_for('admin_control.bck_su_transaction_detail', u_id=1, t_id=1)[:-3],
                # just only need url so it's ok
                url_for('admin_control.bck_su_pending_transaction_update', u_id=1, t_id=1)[:-3],
                url_for('user_cp.bck_transaction_detail', u_id=1, t_id=1)[:-3],
            ]
            allowed_finance_url = [
                url_for('admin_control.su_add_promo'),
                url_for('admin_control.su_bck_promo'),
                # url_for('admin_control.get_accounts'),
                url_for('admin_control.su_delete_promo', p_id=1),
                url_for('admin_control.su_fin_promo_history'),
                url_for('admin_control.su_control_finance'),
                url_for('admin_control.su_bck_fin_promo_history'),
            ]

            allowed_user_control_url = [
                url_for('admin_control.index'),
                url_for('admin_control.su_user_search'),
                url_for('user_cp.bck_transaction_detail', u_id=1, t_id=1),
                url_for('admin_control.client_orders_stats', admin_id=1, client_id=1),
                url_for('admin_control.cross_user_search'),
                url_for('admin_control.bck_change_user_password', u_id=1),
            ]

            allowed_url = allowed_transaction_url + allowed_reanimate_url + allowed_finance_url + allowed_user_control_url
            if any(request.path.startswith(path) for path in allowed_url):
                return

        if '/crm_dashboard' not in request.path:
            flash(message=settings.Messages.CRM_MANAGER_USER_FORBIDDEN, category='error')
            return redirect(
                url_for('crm_d.managers')) if not current_user.role == settings.MARKINERIS_ADMIN_USER else redirect(
                url_for('crm_d.agents'))

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error: str) -> tuple:
        return render_template('error_pages/csrf_error.html'), 400


def setup_login(app: Flask) -> None:
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = settings.Messages.AUTH_OR_SIGNUP
    login_manager.login_message_category = "warning"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))