from flask import Blueprint, redirect, url_for
from flask_login import login_required, logout_user

from utilities.helpers.h_auth import h_login, h_sign_up, h_login_post, h_sign_up_post

auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', ])
def login():
    return h_login()


@auth.route('/logout', methods=['GET', ])
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))


@auth.route('/login_post', methods=['POST', ])
def login_post():
    return h_login_post()


@auth.route('/sign_up/', defaults={'p_link': None}, methods=['GET'])
@auth.route('/sign_up/<p_link>', methods=['GET'])
def sign_up(p_link: str = None):
    return h_sign_up(p_link=p_link)


@auth.route('/sign_up', methods=['POST'])
def sign_up_post():
    return h_sign_up_post()
