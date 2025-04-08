from flask import Blueprint, render_template, send_file, Response, request
from flask_login import login_required, current_user

from config import settings
from data_migrations.etl_service import ETLMigrateUserData
from models import db
from utilities.support import user_activated, manager_forbidden, su_required

main = Blueprint('main', __name__)


@main.route('/')
def index():
    # flash(message='Привет). Это обычное сообщение')
    # flash(message='Привет). Это обычное предупреждение', category='warning')
    # flash(message='Привет). Это обычное ошибко', category='error')
    return render_template('main/index.html')


@main.route('/enter')
@login_required
@user_activated
@manager_forbidden
def enter():
    user = current_user
    ym_sign_up_goal = ''
    # yandex metrics for reaching goals of getting info about new sign ups
    # ym_sign_up_goal = settings.YandexMetrics.sign_up_goal \
    #     if ('success', settings.Messages.USER_SIGHNUP_SUCCESS_PARTNER) in session.get('_flashes', []) else ''
    return render_template('main/enter_v2.html', **locals())


# @main.route('/video_instructions')
# @login_required
# @user_activated
# @manager_forbidden
# def video_instructions():
#     user = current_user
#     # ruznak hardcode condition
#     if (user.role == 'ordinary_user' and current_user.admin_parent_id == 2) or current_user.id == 2:
#         return redirect(url_for('main.enter'))
#     return render_template('main/video_instructions.html', **locals())


@main.route('/check_csrf')
def check_csrf():
    return render_template('error_pages/csrf_error.html')


@main.route('/download/<path:filename>')
@login_required
@user_activated
def download_template_table(filename: str):
    path = f"{settings.DOWNLOAD_DIR}/system_files/{filename}"
    return send_file(path_or_file=path, as_attachment=True)
