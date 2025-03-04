from src.core.config import settings
from src.keyboards.buttons import CANCEL_BUTTON
from src.keyboards.keyboard_events_data import START_COMMAND_TEXT


class UserMessages:
    # верификация
    EMAIL_REQUEST: str = "Введите свой адрес электронной почты зарегистрированной в марка- сервис."
    USER_NOT_FOUND: str = "Пользователя с почтой '{email}' не найдено, попробуйте ввести еще раз."
    INVALID_EMAIL_ADDRESS: str = "Введите корректный адрес электронной почты. Пример: ivan1968@main.ru."
    PUSH_VERIFY_BUTTON: str = "Для того чтобы получить код верификации, нажмите на кнопку."
    GENERATE_VERIFICATION_CODE: str = "Нажмите на кнопку чтоб получить свой код верификации."
    VERIFY_CODE: str = (
        "Ваш код верификации, нажмите на него, чтоб скопировать\n\n"
        "код верификации: `{verify_code}`"
    )
    NEED_VERIFY: str = (
        "Вам нужно пройти верификацию в личном кабинете сервиса!\n\n"
        "код верификации: `{verify_code}`"
    )
    HELP_NEED_VERIFY: str = "Вам нужно пройти верификацию в личном кабинете сервиса!"
    RETRY_VERIFY: str = (
        f"Похоже что ваша учетная запись устарела, "
        f"Вам нужно пройти верификацию снова, нажмите кнопку '{START_COMMAND_TEXT}'."
    )
    VERIFY_CANCEL: str = (
        "Процесс верификации отменен.\n\nЕсли вы хотите пройти верификацию введите"
        " адрес электронной почты"
    )

    # пополнение баланса
    QR_CODE_REQUISITE_HELP_TEXT: str = "Отсканируйте qr-код и оплатите сумму."
    NUMBER_REQUISITE_HELP_TEXT: str = "Реквизиты для оплаты `{requisite}`."
    ENTER_AMOUNT_OF_MONEY: str = "Введите сумму"
    ENTER_INCORRECT_AMOUNT_OF_MONEY: str = "Введите пожалуйста корректное число, например 342.55"
    ENTER_PROMO_CODE: str = "Введите промокод(необязательно)"
    PROMO_CODE_VALIDATE_SUCCESS: str = "Промокод успешно применен"
    PROMO_CODE_NOT_FOUND: str = (
        "Промокод {promo} не найден.\n\n"
        "Попробуйте ввести еще раз. Если у вас нет промокода нажмите кнопку 'Нет промокода'"
    )
    PROMO_ALREADY_USED: str = (
        "Промокод {promo} уже использован.\n\n"
        "Введите другой промокод. Если у вас нет промокода нажмите кнопку 'Нет промокода'"
    )
    BONUS_CODE_VALIDATE_SUCCESS: str = "Бонус код успешно применен"
    ENTER_BONUS_CODE: str = "Введите бонус код"
    BONUS_CODE_NOT_FOUND: str = (
        "Бонус код {bonus_code} не найден.\n\n"
        f"Попробуйте ввести еще раз. Если у вас нет - "
        f"нажмите кнопку `{CANCEL_BUTTON['text']}`"
    )
    BONUS_CODE_ALREADY_USED: str = (
        "Бонус код {bonus_code} уже использован.\n\n"
        f"Введите другой бонус код. Если у вас нет - "
        f"нажмите кнопку `{CANCEL_BUTTON['text']}`"
    )
    SEND_RECEIPT_PHOTO: str = "Отправьте чек"
    INVALID_FORMAT_PHOTO: str = f"Чек должен быть формате {', '.join(settings.ALLOWED_BILL_EXTENSIONS)}"
    SEND_RECEIPT_PHOTO_HELP_TEXT: str = (
        f"Отправьте чек в формате {', '.join(settings.ALLOWED_BILL_EXTENSIONS)}\n"
        f"Размер файла должен быть не более {settings.MAX_FILE_SIZE // (1024 ** 2)} мб"
    )
    PHOTO_PROCESSING_ERROR: str = "Ошибка загрузки, попробуйте отправить чек снова."
    TRANSACTION_CREATE_SUCCESSFULLY: str = "Транзакция успешно создана"
    TRANSACTION_CREATE_FAILED: str = "Транзакция не создана. Попробуйте еще раз"
    BAD_REQUEST_ERROR: str = "Некорректный запрос, попробуйте снова."

    # общие
    AVAILABLE_FUNCTIONS: str = "Доступные функции"
    ALREADY_IN_MAIN_MENU: str = "Вы уже находитесь в главном меню."
    GREETING: str = f"Привет, Я бот уведомлений марка- сервис!\n{EMAIL_REQUEST}"
    INFO_VERIFICATION_CODE_GENERATED: str = f"Вы верифицированы. {AVAILABLE_FUNCTIONS}"
    CANCEL: str = "Действие отменено, возвращаемся в главное меню."
    NO_STATE_HELP_MESSAGE: str = "Вам нужно пройти верификацию, нажмите на кнопку 'start'"
    UNKNOWN: str = "Я не знаю такой команды."
    # ошибки связанные с марка- сервис
    INTERNAL_SERVER_ERROR = "Сервис временно не отвечает, попробуйте позже."
    CANT_CANCEL = "Не получилось отменить действие."
