import click
from flask.cli import with_appcontext
from sqlalchemy.exc import IntegrityError

from config import settings
from logger import logger


# adding custom command for creating superuser
@click.command(name="create_superuser")
@with_appcontext
def create_superuser():
    from models import User, PartnerCode, TelegramMessage
    from werkzeug.security import generate_password_hash
    from .start import db
    try:
        super_user = User(admin_order_num=0, phone=settings.SU_PHONE, login_name=settings.SU_NAME, email=settings.SU_EMAIL,
                          password=generate_password_hash(settings.SU_PASSWORD, method='sha256'),
                          role=settings.SUPER_USER, client_code=settings.SU_PARTNER, is_crm=True, status=True,
                          is_send_excel=True, agent_fee=20)

        partner_code = PartnerCode(name=settings.SU_PARTNER, code=settings.SU_PARTNER,
                                   phone=settings.SU_PHONE)
        nopartner_code = PartnerCode(name=settings.NO_PARTNER_CODE, code=settings.NO_PARTNER_CODE,
                                     phone=settings.SU_PHONE)
        telegram_message = TelegramMessage(send_admin_info=True)

        db.session.add(nopartner_code)
        super_user.partners.append(partner_code)
        super_user.telegram_message.append(telegram_message)
        db.session.add(super_user)
        db.session.commit()
    except IntegrityError as e:
        logger.error(e)
        db.session.rollback()


@click.command(name="create_superuser_custom")
@click.argument('name')
@click.argument('email')
@click.argument('password')
@with_appcontext
def create_superuser_custom(name: str, email: str, password: str):
    from models import User, PartnerCode, TelegramMessage
    from werkzeug.security import generate_password_hash
    from .start import db
    try:
        super_user = User(admin_order_num=0, phone=settings.SU_PHONE, login_name=name, email=email,
                          password=generate_password_hash(password, method='sha256'),
                          role=settings.SUPER_USER, client_code=settings.SU_PARTNER, is_crm=True, status=True,
                          is_send_excel=True, agent_fee=20)

        partner_code = PartnerCode.query.filter_by(code=settings.SU_PARTNER).first()
        telegram_message = TelegramMessage(send_admin_info=True)

        super_user.partners.append(partner_code)
        super_user.telegram_message.append(telegram_message)
        db.session.add(super_user)
        db.session.commit()
    except IntegrityError as e:
        logger.error(e)
        db.session.rollback()
# F.E. flask create_superuser_custom <name> <email> <phone> <password>


@click.command(name="set_server_default_params")
@with_appcontext
def set_server_default_params():
    from models import ServerParam
    from .start import db
    try:
        default_params = ServerParam(crm_manager_ps_limit=settings.OrderStage.DEFAULT_PS_LIMIT, id=1)

        db.session.add(default_params)
        db.session.commit()
    except IntegrityError as e:
        logger.error(e)
        db.session.rollback()
