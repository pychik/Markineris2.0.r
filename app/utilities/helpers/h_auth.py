from typing import Union

from flask import Blueprint, render_template, redirect, url_for, request, Response, flash, Markup, session
from flask_login import login_user, logout_user, current_user
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash

from config import settings
from logger import logger
from models import User, PartnerCode, db
from settings.start import SIMPLE_CAPTCHA
from utilities.saving_uts import helper_check_partner_codes_admin
from utilities.support import url_decrypt, check_email
from utilities.telegram import NewUser
from utilities.validators import ValidatorProcessor

auth = Blueprint('auth', __name__)


def h_login() -> Union[Response, str]:
    if current_user.is_authenticated and current_user.status is True:
        flash(message=settings.Messages.USER_IS_AUTHENTICATED, category='warning')
        if current_user.role in [settings.MANAGER_USER, settings.SUPER_MANAGER]:
            return redirect(url_for('crm_d.managers'))
        return redirect(url_for('main.enter'))

    # yandex metrics for reaching goals of getting info about new sign ups
    ym_sign_up_goal = settings.YandexMetrics.sign_up_goal \
        if ('success', settings.Messages.USER_SIGHNUP_SUCCESS_PARTNER) in session.get('_flashes', []) else ''

    return render_template('auth/login_v2.html', **locals())


def h_logout() -> Response:
    logout_user()
    return redirect(url_for('main.index'))


def h_login_post() -> Response:
    email = request.form.get('email')
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False
    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password, password):
        message = Markup(f"<span class=\"text-secondary\"><b>{email}</span> {settings.Messages.INCORRECT_AUTH}")
        flash(message=message, category='error')
        return redirect(url_for('auth.login'))
    if user.status is not True:
        name = user.login_name
        message = Markup(f"{settings.Messages.USER_NOT_ACTIVATED_1}"
                                 f"\"<span class=\"text-danger\"><b>{name}</b></span>\"."
                                 f"{settings.Messages.USER_NOT_ACTIVATED_2}")
        flash(message=message, category='warning')
        return redirect(url_for('auth.login'))
    login_user(user=user, remember=remember)
    if current_user.role in [settings.MANAGER_USER, settings.SUPER_MANAGER]:
        return redirect(url_for('crm_d.managers'))
    return redirect(url_for('main.enter'))


def h_sign_up(p_link: str) -> Union[Response, str]:
    if current_user.is_authenticated:
        flash(message=settings.Messages.SECONDARY_SIGN_UP_ERROR)
        return redirect(url_for('main.enter'))
    partner_code_info = None
    if p_link:
        try:
            info_list = url_decrypt(p_link).split('__')
            admin_id, partner_code_id = int(info_list[0]), int(info_list[1])

            check_partner, admin_name = helper_check_partner_codes_admin(admin_id=admin_id, partner_id=partner_code_id)
            if not check_partner:
                raise Exception
            partner_code_info = PartnerCode.query.with_entities(PartnerCode.code).filter_by(id=partner_code_id).first()

        except Exception:
            logger.error(settings.Messages.NO_SUCH_SIGNUP_LINK)
            flash(message=settings.Messages.NO_SUCH_SIGNUP_LINK)
            return redirect(url_for('auth.login'))
    else:
        super_user = User.query.with_entities(User.id).filter(User.role == settings.SUPER_USER).first()
        partner_code_info = PartnerCode.query.filter_by(code=settings.NO_PARTNER_CODE).first()
        admin_id = super_user.id
        partner_code_id = partner_code_info.id

    required_phone, required_email = True, True

    full_captcha = SIMPLE_CAPTCHA.create()
    captcha_img = full_captcha.get('img')
    captcha_hash = full_captcha.get('hash')

    return render_template('auth/sign_up_v2.html', **locals())


def h_sign_up_post() -> Union[Response, str]:
    if current_user.is_authenticated:
        flash(message=settings.Messages.SECONDARY_SIGN_UP_ERROR, category='error')
        return redirect(url_for('main.enter'))

    # getting redirect_link
    data_tuple = ValidatorProcessor.sign_up(form_dict=request.form)
    if not data_tuple:
        flash(message=settings.Messages.STRANGE_REQUESTS, category='error')
        return redirect(url_for('main.enter'))
    else:
        sp_link, login_name, email, phone, password, partner_code_id, admin_id = data_tuple
    partner = None

    # check captcha
    c_hash = request.form.get('captcha-hash')
    c_text = request.form.get('captcha-text')
    if not SIMPLE_CAPTCHA.verify(c_text, c_hash):
        flash(message=settings.Messages.USER_SIGNUP_CAPTCHA_ERROR, category='error')
        return redirect(sp_link)

    if email.startswith('manager_'):
        flash(message=settings.Messages.EMAIL_MANAGER_ERROR, category='error')
        return redirect(sp_link)

    if not check_email(email=email):
        flash(message=settings.Messages.EMAIL_EXIST_ERROR, category='error')
        return redirect(sp_link)

    if partner_code_id:
        partner = PartnerCode.query.filter_by(id=partner_code_id).first()
        if not partner:
            flash(message=f"{settings.Messages.NO_SUCH_PARTNER_CODE_1} "
                          f"{settings.Messages.NO_SUCH_PARTNER_CODE_2}", category='error')
            return redirect(sp_link)
        partner_code = partner.code
    else:
        partner_code = settings.NO_PARTNER_CODE

    user_admin = User.query.filter_by(id=admin_id).first()

    is_at2 = user_admin.is_at2
    is_crm = user_admin.is_crm
    telegram = None
    if is_at2 and user_admin.telegram:
        telegram = user_admin.telegram[0]

    try:
        new_user = User(email=email, phone=phone, login_name=login_name,
                        role=settings.ORD_USER, is_crm=is_crm, is_at2=is_at2,
                        password=generate_password_hash(password, method='sha256'),
                        status=True)
        if telegram:
            new_user.telegram.append(telegram)
        if partner:
            new_user.partners.append(partner)
        user_admin.admin_group.append(new_user)
        db.session.add(user_admin)
        db.session.commit()

        NewUser.send_messages_nu_all.delay(
            username=login_name,
            email=email,
            phone=phone,
            partner_code=partner_code,
        )

        flash(message=settings.Messages.USER_SIGHNUP_SUCCESS_PARTNER, category='success')
    except IntegrityError as e:
        logger.error(e)
        db.session.rollback()
        if "psycopg2.errors.UniqueViolation" in str(e):
            flash(message=f"{settings.Messages.USER_SIGNUP_ERROR_UNIQUE_VIOLATION}"
                          f"{login_name} уже есть в базе.", category='error')
        else:
            flash(message=f"{settings.Messages.USER_SIGNUP_ERROR_UNKNOWN} {e}")

    return redirect(url_for('auth.login'))
