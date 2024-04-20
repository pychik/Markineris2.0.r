from flask import Flask, render_template
from flask_debugtoolbar import DebugToolbarExtension
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_simple_captcha import CAPTCHA
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect, CSRFError
from jinja2.filters import FILTERS
from elasticapm.contrib.flask import ElasticAPM
import urllib3

from config import settings
from models import db
from .commands import create_superuser, create_superuser_custom, set_server_default_params
from .jinja_filters import count_quantity


urllib3.disable_warnings()


def sql_debug(app: Flask) -> None:
    # sql_debugger
    app.config['SQLALCHEMY_RECORD_QUERIES'] = True
    app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
    app.debug = True
    toolbar = DebugToolbarExtension(app)


def create_app(db: SQLAlchemy, migrate_handler: Migrate):
    # compress = Compress()
    csrf = CSRFProtect()


    app = Flask(__name__,
                static_folder="../static",
                template_folder="../templates/")

    app.config['SECRET_KEY'] = settings.SECRET_KEY
    app.config['MAINTENANCE_MODE'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = settings.SQL_DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"] = settings.DOWNLOAD_DIR
    app.config['MAX_CONTENT_LENGTH'] = settings.FILE_SIZE * 1024 * 1024
    app.config['UPLOAD_EXTENSIONS'] = settings.ALLOWED_EXTENSIONS
    app.config['WTF_CSRF_TIME_LIMIT'] = settings.CSRF_LIMIT
    app.config['RQ_REDIS_URL'] = settings.REDIS_CONN
    app.config['ELASTIC_APM'] = {
        'DEBUG': settings.APM_IS_DEBUG,
        'SERVICE_NAME': 'M2R',
        'SECRET_TOKEN': settings.ELASTIC_APM_SECRET_TOKEN,
        "SERVER_URL": settings.APM_SERVER_URL,
        "VERIFY_SERVER_CERT": False,
        "CAPTURE_BODY": "all",
    }

    sql_debug(app=app) if app.debug else None
    db.init_app(app)
    migrate_handler.init_app(app, db)
    csrf.init_app(app)

    if not app.debug:
        apm = ElasticAPM()
        apm.init_app(app)

    # blueprints
    from views.main.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    from views.main.main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    with app.app_context():
        from views.main.admin_control import admin_control as ac_blueprint
        app.register_blueprint(ac_blueprint, url_prefix='/admin_control')

    from views.main.user_cp import user_cp as ucp_blueprint
    app.register_blueprint(ucp_blueprint, url_prefix='/user_control_panel')

    from views.main.archive import orders_archive as orders_archive_blueprint
    app.register_blueprint(orders_archive_blueprint, url_prefix='/orders_archive')

    from views.main.categories.shoes import shoes as shoes_blueprint
    app.register_blueprint(shoes_blueprint, url_prefix='/shoes')

    from views.main.categories.linen import linen as linen_blueprint
    app.register_blueprint(linen_blueprint, url_prefix='/linen')

    from views.main.categories.parfum import parfum as parfum_blueprint
    app.register_blueprint(parfum_blueprint, url_prefix='/parfum')

    from views.main.categories.clothes import clothes as clothes_blueprint
    app.register_blueprint(clothes_blueprint, url_prefix='/clothes')

    with app.app_context():
        from views.main.requests_common import requests_common as requests_common_blueprint
        app.register_blueprint(requests_common_blueprint, url_prefix='/rc')

    from views.crm.crm_dash import crm_d as crm_d_blueprint
    app.register_blueprint(crm_d_blueprint, url_prefix='/crm_dashboard')

    from views.crm.crm_uoc import crm_uoc as crm_uoc_blueprint
    app.register_blueprint(crm_uoc_blueprint, url_prefix='/crm_uoc')

    from models import User

    # Flask login methods
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = settings.Messages.AUTH_OR_SIGNUP
    login_manager.login_message_category = "warning"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app


# jinja template filter adding
FILTERS["count_quantity"] = count_quantity

migrate_handler = Migrate()
SIMPLE_CAPTCHA = CAPTCHA(config=settings.CAPTCHA_CONFIG)
# Then later on.

app = create_app(db=db, migrate_handler=migrate_handler)

SIMPLE_CAPTCHA.init_app(app)

app.cli.add_command(create_superuser)
app.cli.add_command(create_superuser_custom)
app.cli.add_command(set_server_default_params)


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
                user_translate_dict=settings.USER_TRANSLATE,
                order_stages=settings.OrderStage, contacts=contacts)


@app.errorhandler(CSRFError)
def handle_csrf_error(error: str) -> tuple:
    return render_template('error_pages/csrf_error.html'), 400


if __name__ == '__main__':
    app.run(debug=True)
