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
                    order_stages=settings.OrderStage, contacts=contacts)

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