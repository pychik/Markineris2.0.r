import click
from flask.cli import with_appcontext
from sqlalchemy.exc import IntegrityError

from config import settings
from logger import logger
from utilities.support import resolve_automated_crm_flag


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


@click.command(name="backfill_is_automated_crm")
@click.option("--dry-run", is_flag=True, help="Только показать, что будет изменено, без сохранения в БД.")
@click.option("--limit", default=0, type=int, help="Ограничить число обрабатываемых заказов (0 = без ограничений).")
@with_appcontext
def backfill_is_automated_crm(dry_run: bool, limit: int):
    from models import Order
    from .start import db

    query = (
        Order.query
        .filter(Order.is_moderation.is_(True), Order.to_delete.isnot(True))
        .order_by(Order.id.asc())
    )

    if limit and limit > 0:
        query = query.limit(limit)

    orders = query.all()
    if not orders:
        click.echo("Подходящие moderation-заказы не найдены.")
        return

    scanned = 0
    changed = 0
    unchanged = 0

    for order in orders:
        scanned += 1
        target_value = resolve_automated_crm_flag(order.is_moderation, order.user_comment)

        if bool(order.is_automated_crm) == target_value:
            unchanged += 1
            continue

        changed += 1
        click.echo(
            f"[{'DRY-RUN' if dry_run else 'UPDATE'}] "
            f"order_id={order.id} order_idn={order.order_idn or '-'} "
            f"comment={'yes' if (order.user_comment or '').strip() else 'no'} "
            f"is_automated_crm: {bool(order.is_automated_crm)} -> {target_value}"
        )

        if not dry_run:
            order.is_automated_crm = target_value

    if dry_run:
        click.echo(
            f"Готово (DRY-RUN). scanned={scanned}, changed={changed}, unchanged={unchanged}"
        )
        return

    try:
        db.session.commit()
        click.echo(
            f"Готово (APPLY). scanned={scanned}, changed={changed}, unchanged={unchanged}"
        )
    except Exception as exc:
        db.session.rollback()
        logger.exception("Ошибка при backfill is_automated_crm")
        click.echo(f"Ошибка при сохранении изменений: {exc}")
