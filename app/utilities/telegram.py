from io import BytesIO

import telebot
from rq.decorators import job
from telebot import types
from werkzeug.datastructures import FileStorage

from config import settings
from logger import logger
from models import User, TelegramMessage, db, TgUser
from redis_queue.constants import TELEGRAM_JOB_PARAMS, NOTIFICATION_TG_JOB_PARAMS


def convert_spec_symbols(converted_string: str) -> str:
    for el in settings.Telegram.SPEC_SYMBOLS_LIST:
        converted_string = converted_string.replace(el[0], el[1])
    return converted_string


class TelegramProcessor:

    @staticmethod
    def make_message_tg(user: User, admin_user: User, order_comment: str, company_type: str, company_name: str,
                        company_idn: str, edo_type: str, edo_id: str, mark_type: str,
                        pos_count: str, orders_pos_count: str, rd_exist: bool, tg_order_num: str = None,
                        su_exec_order_name: str = None, reports_quantity: int = 1):
        telegram_message: TelegramMessage = admin_user.telegram_message[0]

        # message = f"В обработку добавлен заказ:\n" \
        reports_decl = TelegramProcessor.helper_get_reports_decl(reports_quantity=reports_quantity)
        report_info = f"<b>Итого:  {reports_quantity} файл{reports_decl}</b>\n"
        order_info = f"<i>Номер заказа</i>: <b>{tg_order_num}</b>\n" \
            if not su_exec_order_name else f"<b>! ! ! ! ! ВОССТАНОВЛЕННЫЙ ЗАКАЗ ! ! ! ! ! !</b>\n" \
                                           f"<b>! ! ! ! ! ВОССТАНОВЛЕННЫЙ ЗАКАЗ ! ! ! ! ! !</b>\n" \
                                           f"<b>! ! ! ! ! ВОССТАНОВЛЕННЫЙ ЗАКАЗ ! ! ! ! ! !</b>\n" \
                                           f"<i>НОМЕР ЗАКАЗА</i>: <b>{su_exec_order_name}</b>\n"

        admin_info = "<i>Админ</i>: {admin_login}\n".format(
            admin_login=convert_spec_symbols(admin_user.login_name) if admin_user else None) \
            if telegram_message.send_admin_info else ''
        client_code = f"<i>Код клиента</i>: {user.client_code}\n" if telegram_message.send_client_code else ''
        organization_info = f"<i>Отгрузка на </i>: {company_type} {company_name}\n" \
            if telegram_message.send_organization_name else ''

        organization_idn = f"<i>ИНН</i>: {company_idn}\n" if telegram_message.send_organization_idn else ''
        order_numbers = f"КС - {pos_count} КМ - {orders_pos_count}\n"
        login_name = "<i>Логин</i>: {u_login}\n".format(
            u_login=convert_spec_symbols(user.login_name)) if telegram_message.send_login_name else ''
        email = "<i>email</i>: {u_email}\n".format(
            u_email=convert_spec_symbols(user.email)) if telegram_message.send_email else ''
        phone = f"<i>Телефон</i>: {user.phone}\n" \
            if telegram_message.send_phone else ''
        order_comment_send = f"<i>Комментарий к заказу</i>: \n{order_comment}\n" if order_comment else ''
        edo_id_send = '' if not edo_id else f"<code>{edo_id}</code>📖\n"
        edo_block = f"*******************\n" \
                    f"<code>{edo_type}</code>\n" \
                    f"{edo_id_send}" \
                    f"*******************"
        rd_exist_block = "<b>Есть позиции с разрешительной документацией!</b>\n" if rd_exist else ""
        mark_type_block = f"<i>Тип этикетки</i>\n" \
                          f"<code>{mark_type}</code>\n"
        message = f"{report_info}{order_info}{admin_info}{client_code}{organization_info}{organization_idn}" \
                  f"{order_numbers}{login_name}{email}{phone}" \
                  f"{order_comment_send}{mark_type_block}{rd_exist_block}{edo_block}"

        return message

    @staticmethod
    def helper_get_reports_decl(reports_quantity: int) -> str:
        if 1 < reports_quantity <= 4:
            return "а"
        if reports_quantity >= 5:
            return "ов"
        return " "

    @staticmethod
    def send_message_idn(message: str) -> None:
        tg_bot = telebot.TeleBot(token=settings.TELEGRAM_BOT_TOKEN)
        try:
            tg_bot.send_message(chat_id=settings.Telegram.TELEGRAM_ALERTS_GROUP_ID, text=message, parse_mode='HTML')
        except Exception as e:
            logger.error(f"{settings.Messages.TELEGRAM_SEND_ERROR}: {e}")

    @staticmethod
    @job(**TELEGRAM_JOB_PARAMS)
    def send_message_text(message: str, chat_id: str) -> None:
        tg_bot = telebot.TeleBot(token=settings.TELEGRAM_BOT_TOKEN)
        try:
            tg_bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
        except Exception as e:
            logger.error(f"{settings.Messages.TELEGRAM_SEND_ERROR}: {e}")

    @staticmethod
    def make_message_send_file(user: User, admin_user: User, company_type: str, company_name: str,
                               company_idn: str, edo_type: str, edo_id: str, mark_type: str):

        admin_info = "<i>Админ</i>: {admin_login}\n".format(admin_login=convert_spec_symbols(admin_user.login_name)
                                                            if admin_user else None)

        client_code = f"<i>Код клиента</i>: {user.client_code}\n"
        organization_info = f"<i>Отгрузка на </i>: {company_type} {company_name}\n"
        organization_idn = f"<i>ИНН</i>: {company_idn}\n"
        login_name = "<i>Логин</i>: {u_login}\n".format(u_login=convert_spec_symbols(user.login_name))
        email = "<i>email</i>: {u_email}\n".format(u_email=convert_spec_symbols(user.email))
        phone = f"<i>Телефон</i>: <a href='http://wa.me/{user.phone}'>{user.phone}</a>\n"

        edo_id_send = '' if not edo_id else f"<code>{edo_id}</code>📖\n"
        edo_block = f"*******************\n" \
                    f"<code>{edo_type}</code>\n" \
                    f"{edo_id_send}" \
                    f"*******************"
        mark_type_block = f"<i>Тип этикетки</i>\n" \
                          f"<code>{mark_type}</code>\n"
        message = f"{admin_info}{client_code}{organization_info}{organization_idn}" \
                  f"{login_name}{email}{phone}" \
                  f"{mark_type_block}{edo_block}"
        return message

    @staticmethod
    @job(**TELEGRAM_JOB_PARAMS)
    def send_message_file(
            user: User,
            admin_user: User,
            company_type: str,
            company_name: str,
            company_idn: str,
            edo_type: str,
            edo_id: str,
            mark_type: str,
            telegram_id: str,
            vfn: str,
            document: FileStorage,
    ) -> None:

        message = TelegramProcessor.make_message_send_file(
            user=user,
            admin_user=admin_user,
            company_type=company_type,
            company_name=company_name,
            company_idn=company_idn,
            edo_type=edo_type,
            edo_id=edo_id,
            mark_type=mark_type,
        )

        try:
            tg_bot = telebot.TeleBot(settings.TELEGRAM_BOT_TOKEN)
            tg_bot.send_document(
                chat_id=telegram_id,
                visible_file_name=vfn,
                document=document,
                caption=message,
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"{settings.Messages.TELEGRAM_SEND_ERROR}: {e}")

    @staticmethod
    @job(**TELEGRAM_JOB_PARAMS)
    def send_message_tg(message: str, group_id: str, files_list: list[BytesIO, str]) -> None:

        try:
            tg_bot = telebot.TeleBot(settings.TELEGRAM_BOT_TOKEN)

            # media_group = list(map(lambda x: types.InputMediaDocument(x[0]), files_list))
            # media_group[-1] = types.InputMediaDocument(files_list[-1][0], caption=message, parse_mode='HTML')
            # tg_bot.send_media_group(chat_id=group_id, media=media_group, )
            tg_bot.send_document(
                chat_id=group_id,
                visible_file_name=files_list[1],
                document=files_list[0],
                caption=message,
                parse_mode="HTML",
            )

        except Exception as e:
            logger.error(f"{settings.Messages.TELEGRAM_SEND_ERROR}: {e}")


class NewUser:

    @staticmethod
    def make_message(
            username: str,
            email: str,
            phone: str,
            partner_code: str = None,
            new_password: str = None
    ) -> str:
        partner_string = f"🤝 - <i>{partner_code}</i>\n\n" if partner_code and partner_code != settings.NO_PARTNER_CODE \
            else ''
        message_title = f"<b>Новый пользователь с M2R!</b>\n\n" if not new_password \
            else f"<b>Запрос нового пароля</b>\n\n"

        message_body = "👨‍💼 - <i>{u_login}</i>\n" \
                       "📪 - <i>{u_email}</i>\n" \
                       "☎️ - <i>{phone}</i>\n\n".format(u_login=convert_spec_symbols(username),
                                                        u_email=convert_spec_symbols(email), phone=phone)
        message_fin = f"{partner_string}********************\n" if not new_password \
            else f"🥸 - {new_password}\n\n********************\n"

        message = f"{message_title}{message_body}{message_fin}"

        return message

    @staticmethod
    def send_message_start(bot: telebot.TeleBot, change_password: bool = False) -> None:
        try:
            bot.send_message(chat_id=settings.Telegram.USERS_GROUP, text='🆕' if not change_password else '🔐'
                             , parse_mode='HTML')

        except Exception as e:
            logger.error(f"{settings.Messages.TELEGRAM_SEND_ERROR}: {e}")

    @staticmethod
    def send_message_new(bot: telebot.TeleBot, message: str, ) -> None:

        try:

            bot.send_message(chat_id=settings.Telegram.USERS_GROUP, text=message, parse_mode='HTML',
                             disable_web_page_preview=True)
        except Exception as e:
            logger.error(f"message_2 {settings.Messages.TELEGRAM_SEND_ERROR}: {e}\n {message}")

    @staticmethod
    @job(**TELEGRAM_JOB_PARAMS)
    def send_messages_nu_all(username: str, email: str, phone: str, partner_code: str) -> None:

        message_new_user = NewUser.make_message(
            username=username,
            email=email,
            phone=phone,
            partner_code=partner_code,
        )

        tb = telebot.TeleBot(settings.NU_BOT_TOKEN)

        NewUser.send_message_start(bot=tb)

        NewUser.send_message_new(bot=tb, message=message_new_user)


class RefillBalance:

    @staticmethod
    def make_message(
            username: str,
            email: str,
            phone: str,
            amount: int,
            promo_code: str = None,
            amount_add: int = 0
    ) -> str:

        promo_string = f"\n👑- <i>{promo_code}</i>\n<b>Добавочное</b>- <i>{amount_add} р</i>\n" if amount_add else '\n'
        amount_string = f"💰 - <i>{amount} р</i>\n"

        message_title = f"<b>Новое ПОПОЛНЕНИЕ счета на Марка сервис!</b>\n\n"

        message_body = "👨‍💼 - <i>{u_login}</i>\n" \
                       "📪 - <i>{u_email}</i>\n" \
                       "☎️ - <i>{phone}</i>\n\n".format(u_login=convert_spec_symbols(username),
                                                        u_email=convert_spec_symbols(email), phone=phone)
        message_fin = f"{amount_string}{promo_string}********************\n"

        message = f"{message_title}{message_body}{message_fin}"

        return message

    @staticmethod
    def send_message_start(bot: telebot.TeleBot, ) -> None:
        try:
            bot.send_message(chat_id=settings.Telegram.RB_GROUP, text='🆕', parse_mode='HTML')

        except Exception as e:
            logger.error(f"{settings.Messages.TELEGRAM_SEND_ERROR}: {e}")

    @staticmethod
    def send_message_new(bot: telebot.TeleBot, message: str) -> None:
        try:
            bot.send_message(chat_id=settings.Telegram.RB_GROUP, text=message, parse_mode='HTML',
                             disable_web_page_preview=True)

        except Exception as e:
            logger.error(f"{settings.Messages.TELEGRAM_SEND_ERROR}: {e}")

    @staticmethod
    @job(**TELEGRAM_JOB_PARAMS)
    def send_messages_refill_balance(
            username: str,
            email: str,
            phone: str,
            amount: int,
            promo_code: str = None,
            amount_add: int = 0,
    ) -> None:

        message_new_rb = RefillBalance.make_message(
            username=username,
            email=email,
            phone=phone,
            amount=amount,
            promo_code=promo_code,
            amount_add=amount_add,
        )

        tb = telebot.TeleBot(settings.RB_BOT_TOKEN)

        RefillBalance.send_message_start(bot=tb)

        RefillBalance.send_message_new(bot=tb, message=message_new_rb)


class WriteOffBalance:

    @staticmethod
    def make_message(username: str, email: str, phone: str, amount: int, wo_account_info: str) -> str:

        amount_string = f"💰 - <i>{amount} р</i>\n"

        message_title = f"<b>Новый запрос на СПИСАНИЕ со счета агента Марка сервис!</b>\n\n"

        message_body = "👨‍💼 - <i>{u_login}</i>\n" \
                       "📪 - <i>{u_email}</i>\n" \
                       "☎️ - <i>{phone}</i>\n\n".format(u_login=convert_spec_symbols(username),
                                                        u_email=convert_spec_symbols(email), phone=phone)
        wo_account = f"💳 - \n{wo_account_info}\n"
        message_fin = f"{amount_string}{wo_account}********************\n"

        message = f"{message_title}{message_body}{message_fin}"

        return message

    @staticmethod
    def send_message_start(bot: telebot.TeleBot, ) -> None:
        try:
            bot.send_message(chat_id=settings.Telegram.WO_GROUP, text='🆕', parse_mode='HTML')

        except Exception as e:
            logger.error(f"{settings.Messages.TELEGRAM_SEND_ERROR}: {e}")

    @staticmethod
    def send_message_new(bot: telebot.TeleBot, message: str) -> None:
        try:
            bot.send_message(chat_id=settings.Telegram.WO_GROUP, text=message, parse_mode='HTML',
                             disable_web_page_preview=True)

        except Exception as e:
            logger.error(f"{settings.Messages.TELEGRAM_SEND_ERROR}: {e}")

    @staticmethod
    @job(**TELEGRAM_JOB_PARAMS)
    def send_messages_wo_balance(username: str, email: str, phone: str, amount: int, wo_account_info: str) -> None:

        message_new_wo = WriteOffBalance.make_message(
            username=username,
            email=email,
            phone=phone,
            amount=amount,
            wo_account_info=wo_account_info,
        )

        tb = telebot.TeleBot(settings.RB_BOT_TOKEN)

        WriteOffBalance.send_message_start(bot=tb)

        WriteOffBalance.send_message_new(bot=tb, message=message_new_wo)


class NotificationTgUser:

    @staticmethod
    @job(**NOTIFICATION_TG_JOB_PARAMS)
    def send_notification(chat_id: int, message: str) -> None:
        tb = telebot.TeleBot(settings.VERIFY_NOTIFICATION_BOT_API_TOKEN)

        tb.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode='HTML',
        )


class MarkinerisInform:

    @staticmethod
    def make_message(order_idn: str, problem_order_flag: bool = False):
        message_body = f"<i>Заказ</i>: <b>{order_idn}</b>\n"
        if not problem_order_flag:
            message = f"🆕\n M2R: В обработку  добавлен <b>новый заказ</b>\n{message_body}"
        else:
            message = f"🛠\nM2R: <b>Проблема в заказе</b>\n{message_body}"
        return message

    @staticmethod
    @job(**TELEGRAM_JOB_PARAMS)
    def send_message_tg(order_idn: str,
                        group_id: str = settings.Telegram.TELEGRAMM_ORDER_INFO_SERVICE,
                        problem_order_flag: bool = False) -> None:

        try:
            tg_bot = telebot.TeleBot(settings.TELEGRAM_BOT_TOKEN)

            tg_bot.send_message(chat_id=group_id,
                                text=MarkinerisInform.make_message(order_idn=order_idn,
                                                                   problem_order_flag=problem_order_flag),
                                parse_mode='HTML')

        except Exception as e:
            logger.error(f"{settings.Messages.TELEGRAM_SEND_ERROR}: {e}")
