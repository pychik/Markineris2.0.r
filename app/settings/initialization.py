from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from elasticapm.contrib.flask import ElasticAPM
from flask_debugtoolbar import DebugToolbarExtension
from config import settings
from models import db
import urllib3

urllib3.disable_warnings()


def sql_debug(app: Flask) -> None:
    app.config['SQLALCHEMY_RECORD_QUERIES'] = True
    app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
    app.debug = True
    toolbar = DebugToolbarExtension(app)


def create_app() -> tuple[Flask, SQLAlchemy]:
    app = Flask(__name__,
                static_folder="../static",
                template_folder="../templates/")
    app.config['SECRET_KEY'] = settings.SECRET_KEY
    app.config['MAINTENANCE_MODE'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = settings.SQL_DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 1800,
        'pool_size': 5,
        'max_overflow': 5,
        'connect_args': {
            'connect_timeout': 40
        }
    }
    app.config["UPLOAD_FOLDER"] = settings.DOWNLOAD_DIR
    app.config['MAX_CONTENT_LENGTH'] = settings.FILE_SIZE * 1024 * 1024
    app.config['UPLOAD_EXTENSIONS'] = settings.ALLOWED_EXTENSIONS
    app.config['WTF_CSRF_TIME_LIMIT'] = settings.CSRF_LIMIT
    app.config['RQ_REDIS_URL'] = settings.REDIS_CONN
    app.config['ELASTIC_APM'] = {
        'DEBUG': settings.APM_IS_DEBUG,
        'SERVICE_NAME': 'Markineris',
        'SECRET_TOKEN': settings.ELASTIC_APM_SECRET_TOKEN,
        "SERVER_URL": settings.APM_SERVER_URL,
        "VERIFY_SERVER_CERT": False,
        "CAPTURE_BODY": "all",
    }
    sql_debug(app=app) if app.debug else None
    db.init_app(app)
    Migrate().init_app(app, db)
    CSRFProtect().init_app(app)
    if not app.debug:
        ElasticAPM().init_app(app)
    return app, db
