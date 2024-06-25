import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

from utilities.clothes_tnveds import CLOTHES_TNVED_DICT
from utilities.param_lists import SHOE_GENDERS, SHOE_MATERIALS_UP_LINEN, SHOE_MATERIALS_BOTTOM, \
    SHOE_MATERIALS_CORRECT, SHOE_PRELOAD_START, SHOE_SIZES, SHOES_SIZES_DESCRIPTION, \
    SHOE_AL, SHOE_OT, SHOE_NL, SHOE_START, SHOE_TNVED, SHOE_TYPES, SHOE_SIZES_FULL, \
    LINEN_TNVED, LINEN_TYPES, LINEN_CUSTOMER_AGES, LINEN_START, \
    LINEN_PRELOAD_START, LINEN_TEXTILE_TYPES, PARFUM_MATERIAL_PACKAGES, PARFUM_PACKAGE_TYPES, \
    PARFUM_START, PARFUM_PRELOAD_START, PARFUM_TNVED, PARFUM_TYPES, PARFUM_VOLUMES, \
    CLOTHES_DICT, CLOTHES_GENDERS, \
    CLOTHES_GENDERS_ORDER, CLOTHES_START, CLOTHES_PRELOAD_START, CLOTHES_TNVED, CLOTHES_TYPES, \
    COUNTRIES_LIST, COUNTRIES_LIST_C, TEMPLATE_TABLES_DICT, ORDER_EDIT_DESCRIPTION, \
    SHOE_TNVED_CHECK_LIST, CLOTHES_TYPES_SIZES_DICT, CATEGORIES_DICT, \
    BIG_TNVED_LIST, BIG_TNVED_DICT, ADMIN_REPORT_HEAD, AGENT_DEFAULT_NOTE, ORDER_STAGES, \
    CHECK_ORDER_STAGES, COMMON_COLORS, SHOE_START_EXT, LINEN_START_EXT, PARFUM_START_EXT, \
    CLOTHES_START_EXT, CRM_PS_DICT, CLOTHES_CONTENT, CLOTHES_NAT_CONTENT, CLOTHES_UPPER, \
    USER_TRANSLATE_DICT, CLOTHES_SIZES_FULL, CLOTHES_SIZES_DESCRIPTION, CLOTHES_OLD_TNVED, ALL_CLOTHES_TNVED, \
    COMPLICATED_COLORS, ALL_COLORS, UT_REPORT_START

CUR_PATH = os.path.dirname(os.path.abspath(__file__))


class Settings(BaseSettings):
    LOG_PATH: str = Path('/var/log/flask-app/').resolve().as_posix()
    LOG_FORMAT: str = '{time} | [{level}] | {name}::{function}: line {line} | {message}'

    APM_IS_DEBUG: str = False
    ELASTIC_APM_SECRET_TOKEN: str
    APM_SERVER_URL: str

    DATA_DOWNLOAD_URL_FROM_MARKINERS_1: str
    SALT: SecretStr

    MARKINERS_V2_TOKEN: str
    SECRET_KEY: str
    ENCRYPT_KEY: str

    SU_EMAIL: str
    SU_NAME: str
    SU_PHONE: str
    SU_PASSWORD: str
    TELEGRAM_BOT_TOKEN: str
    NU_BOT_TOKEN: str  # new user message tg bot @markineris_notify_bot
    RB_BOT_TOKEN: str  # refill balance message tg bot @M2balancebot
    VERIFY_NOTIFICATION_BOT_API_TOKEN: str  # notification and verify status bot
    MAIL_API_TOKEN: str
    DADATA_TOKEN: str
    MARKINERIS_SECRET: str
    MARKINERIS_CHECK_OI_LINK: str
    MARKINERIS_CHECK_CROSS_OI_LINK: str
    TELEGRAMM_GROUP_LINK: str = "https://t.me/markinerisss"
    TELEGRAMM_USER_NOTIFY_LINK: str = "https://t.me/markiservice_un_bot"
    MAIL_LINK: str = "mailto:markineris@gmail.com"
    WHATSAPP_LINK: str = "https://chat.whatsapp.com/CuORC1cadb68OsH7ZFnezF"
    TURTORIAL_VIDEO_LINK: str = "https://disk.yandex.com/i/RR0pBhCYVRc1Kw"
    INFO_CENTER_LINK: str = "https://info.markineris.com"
    DADATA_INFO_IDN_LINK: str = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party"
    SU_PARTNER: str = "IAMSUPERUSER"
    AU_PARTNER: str = "IAMADMIN"
    MU_PARTNER: str = "IAMMANAGER"
    AU_CLIENT_CODE: str = "AGENT_CODE"
    SU_COMPANY: str = "Суперпользователи сервиса"
    MANAGER_EMAIL_POSTFIX: str = "@m2rservice.com"
    ADMIN_COMPANY: str = "Администраторы сервиса"
    MANAGER_COMPANY: str = "Менеджеры crm"
    NO_PARTNER_CODE: str = "NO_PARTNER_CODE"
    DEFAULT_CLIENT_CODE: str = "NO_CODE"
    FILE_SIZE: int = 100
    ORDER_LIMIT_ARTICLES: int = 1600
    ORDER_LIMIT_UPLOAD_ARTICLES: int = 1700
    ORDER_BATCH_QUANTITY: int = 400
    EMAIL_USER_SEND_LIMIT: int = 10
    PAGINATION_PER_PAGE: int = 50
    PAGINATION_PER_PAGE_HISTORY_ORDERS: int = 10
    PAGINATION_PER_PROMOS: int = 10
    PAGINATION_PER_PAGE_PRELOAD: int = 400
    RESULT_RQ_TTL: int = 180
    AGENT_FEE_MIN: int = 0
    AGENT_FEE_MAX: int = 40

    RQ_DEFAULT_QUEUE_NAME: str = "default"
    RQ_SCHEDULER_QUEUE_NAME: str = "scheduled"
    RQ_DYNSCHEDULER_QUEUE_NAME: str = "dynamic_scheduled"
    NOTIFICATION_QUEUE_NAME: str = "tg_notifications"
    GT_QUEUE_NAME: str = "gt_notifications"  # google tables

    USERS_ID_NOBANNER: tuple = (7, 8, 9, 11, 15,)
    SUPER_USER: str = 'superuser'
    SUPER_MANAGER: str = 'supermanager'
    ADMIN_USER: str = 'admin'
    MARKINERIS_ADMIN_USER: str = 'm2r_admin'
    MANAGER_USER: str = 'manager'
    ORD_USER: str = 'ordinary_user'
    USER_TRANSLATE: dict = USER_TRANSLATE_DICT
    USER_ROLES: list = [ORD_USER, MANAGER_USER, SUPER_MANAGER, ADMIN_USER, MARKINERIS_ADMIN_USER, SUPER_USER]
    ADMIN_USER_POSTFIX: str = "@agentsm2r.com"

    SQ_CATEGORIES: list = ['обувь', 'одежда', 'белье']
    CATEGORIES_PROCESS_NAMES: list = ['shoes', 'clothes', 'linen', 'parfum', 'send_table']
    CATEGORIES_UPLOAD: tuple = ('обувь', 'одежда', 'парфюм', 'белье')
    COMPANY_TYPES: list = ["ИП", "ООО", "АО"]
    CATEGORIES_DICT: dict = CATEGORIES_DICT
    COUNTRIES_LIST: list = COUNTRIES_LIST
    COUNTRIES_LIST_C: list = COUNTRIES_LIST_C
    EDO_TYPES: list = ["СБИС", "КОНТУР", "ТАКСКОМ", "КАЛУГА АСТРАЛ"]
    DOWNLOAD_DIR: str = f"{CUR_PATH}/download_dir"
    DOWNLOAD_DIR_CRM: str = f"{CUR_PATH}/download_dir/crm/"
    DOWNLOAD_DIR_STATIC: str = f"{CUR_PATH}/static/"
    DOWNLOAD_QA_BASIC: str = f"qr_imgs/"
    DOWNLOAD_BILL_BASIC: str = f"bill_imgs/"
    DOWNLOAD_DIR_SA_QR: str = f"{DOWNLOAD_DIR_STATIC}{DOWNLOAD_QA_BASIC}"
    DOWNLOAD_DIR_BILLS: str = f"{DOWNLOAD_DIR}/{DOWNLOAD_BILL_BASIC}"
    TEMPLATES_DICT: dict = TEMPLATE_TABLES_DICT
    UPLOAD_ORDER_EXCEL_INSTRUCTION: str = 'Инструкция_загрузка_excel_заказа.docx'
    TAX_LIST: list = [20, 10]
    # MARKETPLACE_TYPES: tuple = ('wildberries', 'ozon')
    SQL_DATABASE_URL: str
    REDIS_CONN: str = os.getenv('REDIS_URL', 'redis://localhost:6379')
    REDIS_HOST: str = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT: int = os.getenv('REDIS_PORT', 6379)
    REDIS_TG_NOTIFY_DB_NUMBER: int = os.getenv('REDIS_BOT_STORAGE_DB', 5)
    QUEUES: list = ['default']
    REPORT_EXCEL_FILENAME: str = f"{CUR_PATH}/"
    SHEET_NAME_2: str = "Доп. информация"
    NO_VALUE: str = "Нет информации в базе"
    PRICES_TEXT: list = ["Цены Розница",
                         "- до 500 шт.- 12,0 руб.",
                         "- от 500 до 1000 шт.- 8,0 руб.",
                         "- от 1000 до 3000 шт.- 5,5 руб.",
                         "- от 3000 шт. - 5,0 руб.",
                         "- от 10000 шт. - 4 руб.",
                         "- от 20000 шт. - 3,3 руб.",
                         "- от 50000 шт. - 2,8 руб."]
    PRICE_DESCRIPTION: list = ["Указание ценовых характеристик обязательно для всех позиций"
                               " для ПОДСЧЕТА суммы накладной, либо не указывайте цену артикула ни в одной позиции"]
    TNVED_DESCRIPTION: list = ["Определяется системой автоматически. Вводится для некоторых позиций в случае,"
                               " если клиент хочет указать свой собственный ТНВЭД"]
    RD_DESCRIPTION: list = ["Если у вас есть разрешительный документ для позиции заказа,"
                            " укажите тип документа, его название и дату получения документа"]
    RD_TYPES: tuple = ('Декларация соответствия', 'Отказное письмо', 'Сертификат',)
    EXP_PARTNERS: str = 'partners'
    EXP_USERS: str = 'users'
    EXP_TELEGRAM: str = 'telegram'
    ACTIVATE_USER: str = 'activate_user'
    ACTIVATE_IS_SEND_EXCEL: str = 'activate_is_send'
    DEACTIVATE_USER: str = 'deactivate_user'
    DEACTIVATE_IS_SEND_EXCEL: str = 'deactivate_is_send'
    SQL_EXPR_CHECK: tuple = ("select", "--", "update", "insert", "delete", "truncate", "remove")
    COMMON_COLORS: tuple = COMMON_COLORS
    COMPLICATED_COLORS: tuple = COMPLICATED_COLORS
    ALL_COLORS: tuple = ALL_COLORS
    ORDER_EDIT_DESCRIPTION: tuple = ORDER_EDIT_DESCRIPTION
    ALLOWED_EXTENSIONS: tuple = ('xlsx',)
    ALLOWED_IMG_EXTENSIONS: tuple = ('png', 'jpg', 'jpeg', )
    ALLOWED_BILL_EXTENSIONS: tuple = ('png', 'jpg', 'jpeg', 'pdf', )
    CRM_ALLOWED_EXTENSIONS: tuple = ('rar', )
    UPLOAD_TABLE_ERRORS_FILE: str = "Ошибки_загрузки_заказа.txt"
    SEND_TABLE_NAME: str = "таблица_заказ.xlsx"
    ADMIN_REPORT_HEAD: dict = ADMIN_REPORT_HEAD
    AGENT_DEFAULT_NOTE: str = AGENT_DEFAULT_NOTE
    POS_INDEX_EXCEPTION: str = 'positional indexers are out-of-bounds'
    SO_CON_SYMB_LIMIT: int = 300
    ARCHIVE_CHECK_DAYS: int = 30
    CSRF_LIMIT: int = 3600
    UPLOAD_VALUE_LENGTH_LIMIT: int = 100
    PA_STAGES: tuple = ('0', 'fill_account', 'price', 'transactions_history')
    BANK_ACCOUNTS_LIMIT: int = 10
    UPLOAD_BACKGROUND: int = 111
    TRUST_LIMIT_DEFAULT: int = 100000
    TRUST_LIMIT_MINIMUM: int = 10000
    TRUST_LIMIT_MAXIMUM: int = 1000000
    TG_VERIFICATION_LENGTH: int = 32
    PA_REFILL_MIN: int = 1
    CAPTCHA_CONFIG: dict = {'SECRET_CAPTCHA_KEY': 'LONG_KEY',
                            'CAPTCHA_LENGTH': 6,
                            'CAPTCHA_DIGITS': False,
                            'EXPIRE_SECONDS': 600,
                            'BACKGROUND_COLOR': '#7c7c7c',  # RGB(A?) background color (default black)
                            'TEXT_COLOR': (255, 255, 255)
                            }
    AR_ORDERS_DAYS_DEFAULT: int = 7
    ALL_CATEGORY_TYPES: str = 'ALL_CATEGORY_TYPES'
    ORDERS_REPORT_TIMEDELTA: int = 7
    PROMO_HISTORY_TIMEDELTA: int = 7

    class OrderStage:
        @staticmethod
        def minutes_to_cron(minutes) -> str:
            if minutes < 1 or minutes > 1600:
                raise ValueError("Minutes must be between 1 and 1600.")

            if minutes == 1:
                return "* * * * *"

            # Calculate hours and days
            hours = minutes // 60
            minutes %= 60
            days = hours // 24
            hours %= 24

            # Construct cron string
            cron_string = "*/{} * * * *".format(minutes)
            if hours > 0:
                cron_string = "{} */{} * * *".format(minutes, hours)
            if days > 0:
                cron_string = "{} {} */{} * *".format(minutes, hours, days)

            return cron_string

        CREATING: int = 0
        NEW: int = 1
        POOL: int = 2
        MANAGER_START: int = 3
        MANAGER_EDO: int = 4
        MANAGER_PROCESSED: int = 5
        MANAGER_PROBLEM: int = 6
        MANAGER_SOLVED: int = 7
        SENT: int = 8
        CANCELLED: int = 9
        TELEGRAM_PROCESSED: int = 10
        CRM_PROCESSED: int = 11
        STAGES: tuple = ORDER_STAGES
        STAGES_TF: dict = {SENT: 'sent_at', CANCELLED: 'cc_created', CRM_PROCESSED: 'closed_at'}
        CHECK_TUPLE: tuple = CHECK_ORDER_STAGES
        CHECK_CHANGING_STAGES: tuple = ((NEW, POOL), (MANAGER_PROCESSED, SENT), (MANAGER_SOLVED, SENT), )
        ORDER_PROCESS_CRM: str = 'process_crm'
        ORDER_PROCESS_AT2: str = 'process_at2'
        DAYS_CONTENT: int = 2
        DAYS_SEARCH_CONTENT: int = 30
        DAYS_UPDATE_CONTENT: int = 30
        DAYS_SENT_CONTENT: int = 1
        AUTO_HOURS_CP: int = 24  # quantity of hours before changing order stage from MANAGER PROBLEM TO CANCEL
        AUTO_MINUTES_CP: int = 30  # quantity of minutes before changing order stage from MANAGER PROBLEM TO CANCEL
        MANAGER_ORDERS_LIMIT: int = 10
        PS_DICT = CRM_PS_DICT
        PO_LIMIT = 'po_limit'
        MAX_PS_LIMIT: int = 360
        MAX_ORDER_FILE_SIZE: int = 104857600  # 10мб

        DEFAULT_PS_LIMIT: int = 10  # problem solving limit in minutes
        DEFAULT_MO_LIMIT: int = 10  # default quantity limit for taking orders
        DEFAULT_PO_LIMIT: int = 5  # default quantity for problem orders
        DEFAULT_AP_ROWS: int = 100  # default max quantity of rows for order to auto change stage to pool
        DEFAULT_AP_MARKS: int = 1000  # default max quantity of marks for order to auto change stage to pool
        DEFAULT_AS_MINUTES: int = 20  # default max minutes for order to auto change stage to sent from manager ready
        DEFAULT_AS_CRON_STRING: str = minutes_to_cron(minutes=DEFAULT_AS_MINUTES)  # default max minutes for order to auto change stage to sent from manager ready
        DEFAULT_ORDER_FILE_TO_REMOVE: int = 45  # days for cleaning files from server

        # tg user messages
        M_ORDER_ADDED: str = "M2R: Заказ <b>{order_idn}</b>: <u>отправлен в работу!</u>"
        M_ORDER_OPERATING: str = "M2R: Заказ <b>{order_idn}</b>: <u>принят в работу!</u>"
        M_ORDER_AGAIN_OPERATING: str = "M2R: Заказ <b>{order_idn}</b>: <u>обрабатывается!</u>"
        M_ORDER_READY: str = "M2R: Заказ <b>{order_idn}</b>: <u>файлы готовы к скачиванию!</u>"
        M_ORDER_PROBLEM_ENCOUNTERED: str = "M2R: Заказ <b>{order_idn}</b>: <u>проблема решается!</u>"
        M_ORDER_PROBLEM_SOLVED: str = "M2R: Заказ <b>{order_idn}</b>: <u>Проблема решена!</u>"
        M_ORDER_CANCELLED: str = "M2R: Заказ <b>{order_idn}</b>: <u>отменен!</u>"
        M_ORDER_MSG_DICT: dict = {
            NEW: M_ORDER_ADDED, POOL: M_ORDER_OPERATING, SENT: M_ORDER_READY,
            MANAGER_PROBLEM: M_ORDER_PROBLEM_ENCOUNTERED, MANAGER_SOLVED: M_ORDER_PROBLEM_SOLVED,
            CANCELLED: M_ORDER_CANCELLED, MANAGER_START: M_ORDER_AGAIN_OPERATING
        }
        APCO_NOORDERS: str = "Нет заказов для отмены"  # AUTO PROBLEM TO CANCELL  ORDERS
        APCO_MESSAGE: str = "Отменен автоматически по истечению срока решения вопроса"
        APCO_SUCCESS: str = "Перенос проблемных заказов в отмененные завершен успешно"

    class Telegram:
        URL: str = "https://api.telegram.org/bot"
        TELEGRAM_MAIN_GROUP_ID: str = "-1001858559646"
        USERS_GROUP: str = "-1002064886835"  # group for sending messsages about new users
        RB_GROUP: str = "-1002092657810"  # group for sending messages about new refillments checkout
        WO_GROUP: str = "-1002092657810"  # group for sending messages about new refillments checkout
        TELEGRAM_ALERTS_GROUP_ID: str = "-1001969475944"
        TELEGRAMM_ORDER_INFO_SERVICE: str = os.environ.get('TELEGRAMM_ORDER_INFO_SERVICE')  # orig is "-1002124706398" # channel for service admin notifications
        SPEC_SYMBOLS_LIST: tuple = (('&', '&amp;'), ('<', '&lt;'), ('>', '&gt;'))

    class Process:
        DOWNLOAD: str = "download"
        PROCESS: str = "process"
        TIMEOUT: float = 3.500

    class ServiceAccounts:
        QUANTITY_LIMIT: int = 8
        SUMM_LIMIT: int = 500000
        TYPES: tuple = (('qr_code', 'qr код'), ('requisites', 'Реквизиты вручную'),)
        TYPES_KEYS: tuple = ('qr_code', 'requisites',)
        TYPES_DICT: dict = {'qr_code': 'qr код', 'requisites': 'Реквизиты вручную'}
        DEFAULT_QR_ACCOUNT_TYPE: str = 'qr_code'

    class YandexMetrics:
        sign_up_goal: str = "<script>document.onload=ym(96964075,'reachGoal','signup');</script>"

    class Prices:
        F_LTE_100: int = 18
        F_100_500: int = 16
        F_500_1K: int = 9
        F_1K_3K: int = 7
        F_3K_10K: int = 6
        BASIC_PRICES: tuple = ('BASIC', F_LTE_100, F_100_500, F_500_1K, F_1K_3K, F_3K_10K, F_3K_10K)

        # F_10K_20K: float = 6
        # F_20K_50K: float = 3.3
        # F_GTE_50K: float = 2.8

        TEXT: list = ["Цены Розница",
                      "- до 499 шт.- 12,0 руб.",
                      "- от 500 до 999 шт.- 8,0 руб.",
                      "- от 1000 до 3000 шт.- 5,5 руб.",
                      "- от 3001 шт. - 5,0 руб.",
                      "- от 10000 шт. - 4 руб.",
                      "- от 20000 шт. - 3,3 руб.",
                      "- от 50000 шт. - 2,8 руб."]
        # "- до 100 шт. - 18 руб.
        # - от 100 шт. - 16 руб.
        # - от 500 шт. - 9 руб.
        # - от 1000 шт. - 7 руб.
        # - от 3000 шт. - 6 руб."
        C_LT100: int = 99
        C_100_500: int = 499
        C_500_1K: int = 999
        C_1K_3K: int = 2999
        C_3K_10K: int = 9999
        # C_10K_20K: int = 20000
        # C_20K_50K: int = 50000
        RANGES: tuple = (C_LT100, C_100_500, C_500_1K, C_1K_3K, C_3K_10K)

    class Users:
        DEFAULT_DAYS_RANGE: int = 30
        FILTER_DATE_HOURS: str = 'Часов'
        FILTER_DATE_DAYS: str = 'Дней'
        FILTER_DATE_MONTH: str = 'Месяцев'
        FILTER_DATE_TYPES: tuple = (FILTER_DATE_HOURS, FILTER_DATE_DAYS, FILTER_DATE_MONTH,)
        FILTER_DATE_DICT: dict = {FILTER_DATE_HOURS: 'Час(ов)', FILTER_DATE_DAYS: 'День(Дней)',
                                  FILTER_DATE_MONTH: 'Месяц(ев)'}
        FILTER_MAX_QUANTITY: int = 30

    class Transactions:
        CANCELLED: int = 0
        PENDING: int = 1
        SUCCESS: int = 2
        SUCCESS_RETURN: int = 3
        DEFAULT_DAYS_RANGE: int = 90
        TRANSACTIONS: dict = {PENDING: 'Ожидается подтверждение', CANCELLED: 'Отменена', SUCCESS: 'Успешно проведена',
                              SUCCESS_RETURN: 'Возврат средств отмененного заказа'}
        TRANSACTION_WRITEOFF: int = 0
        TRANSACTION_REFILL: int = 1
        TRANSACTION_TYPES: dict = {TRANSACTION_REFILL: 'Пополнение', TRANSACTION_WRITEOFF: 'Снятие средств'}
        TRANSACTIONS_TYPES_LATIN1: dict = {'Пополнение': 'refill', 'Снятие средств': 'write_off'}

    class Tnved:
        BIG_TNVED_LIST: tuple = BIG_TNVED_LIST
        BIG_TNVED_DICT: dict = BIG_TNVED_DICT

    class GoogleTables:
        CREDENTIALS_FILE = f"{CUR_PATH}/utilities/google_settings/smart-orders-380418-2b53a29bb857.json"
        SPREADSHEET_ID = "1n-VcgDzIDpWqZEqUWfWtVv2G0DNDKSwp8JTGlpaeeEE"
        SHEET_NAME_ORDERS: str = "Заказы"
        FC_ORDERS: str = "A"  # first column of orders table
        LC_ORDERS: str = "L"  # last column of orders table
        SHEET_RANGE_ORDERS: str = f"{SHEET_NAME_ORDERS}!{FC_ORDERS}1:{LC_ORDERS}"
        SHEET_NAME_PROMOS: str = "Промокоды"
        FC_PROMOS: str = "A"  # first column of orders table
        LC_PROMOS: str = "E"  # last column of orders table
        SHEET_RANGE_PROMOS: str = f"{SHEET_NAME_PROMOS}!{FC_PROMOS}1:{LC_PROMOS}"
        GT_JSON_SET: dict = {
            "type": "service_account",
            "project_id": "smart-orders-380418",
            "private_key_id": "2b53a29bb857ea719ef89c992d31103e0abb1d42",
            "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgE"
                           "AAoIBAQDHQTlGACb9/xPH\nt8ihAT1wh6Oep+bgOj1EgctFVncOjMhe6Y6eSAUCjmL9giH6ER"
                           "76mUxMN1e0xLVQ\n5FENbEGnmZqGrMvtX+IYC7hROO1BJBEH8vtL0PQ55wpxSLTGxvJGETLjG"
                           "Zbx1DRt\nfSK6tiBbY5dHX0ddBXfygSQeOren4F0bjc+b4/2Qgay/onLlQW8vEp6aZna9xdT"
                           "u\nG4HTSu63/NUdhv5EKMEWRfie9cQQKX1nbmFKg0nDVh1mXc5kaFs3gMRPEKvyy8rv\naY50"
                           "z6Ox8lh1Fz7TT+ptGlBD33Wn/YFmTxVvwoeBnNFrvq3u5O4Nd86ig74sbpUS\nqEx1nO6hAgM"
                           "BAAECggEAAmDlIHCZ5o4p//hB2AisEWTgG1GrJg3x62h+ev7Yy9ra\nvTXN5NYsn6LAHCE2mz"
                           "3jNBf6fv4p4Qu4U51vGYE7YScabu0+/6/VYsa4ifkrTVvT\nK3hvPyDg2nRXZcHpvQX00EjuJ"
                           "eN5P5yiLdSoooiQJzEflhu1Pg81tuaLXiRCqxmD\nVDdWLLq8TWVPaswMqPdwtDVRRkTlBqCw"
                           "7d4wIs5LCnZkTwjOrb8v0ZDbGocBUrwJ\nK2zL3TfjnTjAWOCYcB/L/vOjbGer9Kh33PcW5I5"
                           "FPS+h1HWNtW7y1noUAiZh1QOS\ni5oTVIUCHGdSq1MHTtaXtGfhHDoXWBQb4kK4uctBgQKBgQ"
                           "DnksdnkIvRJJv7feje\ngF3FWZBp1Vaqs7YDTdVNYr4ezRBkk6bdTwrsnzbApucwHBOH04zT"
                           "vdiaYhAJjjky\nl8Huz1HgJPJp2jREDmHSlShqmhlBBWNHIoijBiqc6vJqdqdXW66aGaLHjFt"
                           "ciOz7\nyo7iG4Zz/hxa0CTsT2co45l5YQKBgQDcRb1sNyQ27ozEI9B1kUIYwkwIr/tEzV"
                           "mc\nt6dUvFQBWUj/z1BHt5Q6B56n3DTU30APkJQ13bz2efZvQ63NCan2mlQyLOjSQgMT\n9aQ"
                           "d6jGrb2J2sXQ5eBMMHXqoVK/wQBKsTki5JxiRvpaTQA6pVGktBE1CzRQlHB/J\nFDXqR1k9Q"
                           "QKBgEU5bGB6JkGr5vEED4PL7bwb7P6mJpU6yZMtRjEu7lR4yoi2VrBb\ne5GGerCWdA++pNv6"
                           "kmONod1sqQyiNlj4YqHH2dreUJTyBKO/hOCVdBKB5EC6opXW\nLfBF3KEx3quSsq17m7M3LKD"
                           "oRTthNy6Bu7q9rbCo6sL+67q0dcsUVoGhAoGAIP3x\nGTxJGFEylE4o8vMGy16OtN5m7C81tN"
                           "ttHKv4iRsua+JJS/SbJvXtNYcuApRNrAcj\nq83Cd8hcuN2SMpu38U+8PKetV5C7lUm9gx2Iw"
                           "vyz6sM5fUIW2EGyFXRZxcpTAavY\nCKNqcqnxM6zshUA3YJ68U70Tv1svB5cXXDfDjgECgYAf"
                           "ZDHrS19Z9Y92djQWEwRE\nMYaeUCDH5tlUyITTNcU1JKHmUAhrkZiiL++uq8ayGCy+GRtvJ9t"
                           "yyMKlQxsPLIJZ\ng1JKHnPF/JSh220gpJHQZLSEMms7RniPUKJExi3vJ+4V7DcK9voAdekcJq"
                           "mAlraf\nGi0Co4p8XKlkUo+i5kfG6w==\n-----END PRIVATE KEY-----\n",
            "client_email": "smart-889@smart-orders-380418.iam.gserviceaccount.com",
            "client_id": "101663767257215535149",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/smart-889%40s"
                                    "mart-orders-380418.iam.gserviceaccount.com"
        }

        class RuZnak:
            SPREADSHEET_ID_RUZNAK = "1UQq_DncaALZwx57Sn5TytTo2Ja0-tQ5GYKIzv5ZgsfU"
            SHEET_NAME_RUZNAK: str = "Заказы"
            FC_RUZNAK: str = "A"  # first column of ruznak orders table
            LC_RUZNAK: str = "I"  # last column of ruznak orders table
            SHEET_RANGE_RUZNAK: str = f"{SHEET_NAME_RUZNAK}!{FC_RUZNAK}1:{LC_RUZNAK}"

    class Messages:
        @staticmethod
        def answer_refill_balance(balance: int, current_price: int, sum_count: int, is_at2: bool = False) -> str:
            """
                helps to make user message with balance and orders info
            :return:
            """
            # mes_part = f"Недостаточно средств на счете агента  для оформления заказа. Баланс агента: {balance} р. <br>" if agent_at2 else f"Недостаточно средств на личном счете для оформления заказа. Баланс пользователя: {balance} р. <br>"
            mes_part = f"Недостаточно средств на личном счете для оформления заказа. Баланс пользователя: {balance} р. <br>"
            return f"{mes_part}" \
                   f"Общее количество марок под заказ со всеми непроведенными заказами - {sum_count} шт. <br>" \
                   f"Цена за марку - {current_price} р./шт.<br>" \
                   f"Всего нужно - {current_price * sum_count} р.<br>"

        AUTH_OR_SIGNUP: str = "Пожалуйста авторизуйтесь для работы с сервисом!"
        INCORRECT_AUTH: str = "Введены некорректные данные учетной записи! Проверьте email или пароль!"
        ACTIVATED_ADMIN: str = "Успешно активирован агент с ником "
        ACTIVATED_USER: str = "Успешно активирован пользователь с ником "
        ACTIVATED_USER_ERROR: str = "Во время активации произошла ошибка !"
        ACTIVATED_USER_ND_ERROR: str = "Попытка активировать клиента другого агента!"
        ACTIVATED_EXCEL_UPLOAD_USER: str = "Успешно активирована отправка заказов в таблице EXCEL напрямую " \
                                           "для пользователя с ником "
        ACTIVATED_EXCEL_UPLOAD_ERROR: str = "Невозможно включить отправку таблиц напрямую для агентов с формой " \
                                            "обработки crm"
        USER_CP_ERROR: str = "Во время активности в профиле пользователя произошла ошибка! "
        CHANGE_PASSWORD_ERROR: str = "Во время редактирования пароля возникла ошибка! "
        CHANGE_PASSWORD_STRANGE_ACTIONS: str = "Замечена подозрительная активность при формировании нового пароля"
        CHANGE_PASSWORD_SUCCESS: str = "Успешно изменил пароль!"
        USER_PROCESS_TYPE: str = "Сменен тип обработки заказов для агента "
        USER_PROCESS_TYPE_ERROR: str = "Во время изменения типа обработки заказов произошла ошибка"
        DEACTIVATED_ADMIN: str = "Успешно деактивирован агент с ником "
        DEACTIVATED_USER: str = "Успешно деактивирован пользователь с ником "
        DEACTIVATED_ND_USER_ERROR: str = "Попытка деактивировать пользователя другого агента "
        DEACTIVATED_EXCEL_UPLOAD_USER: str = "Успешно деактивирована функция отправки таблиц EXCEL напрямую для" \
                                             " пользователя с ником "
        DEACTIVATED_USER_ERROR: str = "Во время деактивации произошла ошибка! "
        DELETE_USER: str = "Успешно удален пользователь с ником "
        DELETE_USER_ERROR: str = "Во время удаления пользователя произошла ошибка !"
        DELETE_USER_ND_ERROR: str = "Зафиксирована попытка удаления пользователя другого агента!"
        DELETE_MANAGER_ERROR: str = "У менеджера есть незавершенные заказы. Всего "
        GET_RESTORE_LINK_ADMINS_ERROR: str = "Администраторам сервиса нельзя получать ссылку для смены пароля." \
                                             " Обратитесь к разработчику"
        GET_RESTORE_LINK_USERS_ERROR: str = "Вы уже авторизованы! попробуйте сменить пароль через форму смены или " \
                                            "выйдите из своей учетной записи и попробуйте снова!"
        GET_RESTORE_LINK_EMAIL_ERROR: str = "При регистрации вы не указывали свой email." \
                                            " Обратитесь к своему агенту для получения ссылки на смену пароля"
        GET_RESTORE_LINK_EMAIL_DUPLICATE_ERROR: str = "В системе несколько пользователей с таким email." \
                                                      " Обратитесь к своему агенту для получения ссылки на смену пароля"
        GET_RESTORE_LINK_COMMON_ERROR: str = "Во время генерации ссылки на создание нового праоля возникли ошибки: "
        EMAIL_SEND_LIMIT_ERROR: str = "Достигнут лимит отправки сообщений на почту за этот день." \
                                      " Попробуйте завтра или обратитесь к своему агенту!"
        EMAIL_EXIST_ERROR: str = "Такой  Email  уже зарегистрирован в системе- введите другой"
        EMAIL_MANAGER_ERROR: str = "Email не может начинаться с \"manager_\" (зарезервирован для сервиса)"\
                                    "- введите другой"
        WRONG_RESTORE_LINK: str = "Неверная ссылка для восстановления!"
        GET_RESTORE_LINK_SUCCESS: str = "успешно отправлена ссылка на создание нового пароля!"
        RESTORE_LINK_EXPIRED: str = "Ссылка на восстановление пароля устарела- попробуйте повторить процесс создание нового пароля!"
        RESTORE_LINK_ABSENT: str = "Ваша ссылка на замену пароля отсутствует и некорректна!"
        RESTORE_LINK_ABSENT_USER: str = "Ваша ссылка на замену пароля отсутствует и некорректна! Нет такого  пользователя"
        ACTIVATE_ALL_USERS_SUCCESS: str = "Все пользователи текущего агента активированы!"
        ACTIVATE_ALL_USERS_ERROR: str = "Во время активации всех пользователей текущего агента произошла ошибка! "
        EMPTY_ORDER: str = "Для того чтобы оформить заказ, сначала создайте его:" \
                           " заполните форму и нажмите на кнопку \"Добавить\""
        CATEGORY_UNKNOWN_ERROR: str = "Ошибка обработки запроса. Неизвестная категория!"
        ORDER_UPLOAD_SUCCESS: str = "В базу успешно загружен заказ из таблицы. Вы перенаправлены на страницу заказа. Проверьте позиции и нажмите кнопку оформить заказ!"
        ORDER_UPLOAD_POS_LIMIT: str = f"Вы превысили максимальное количество строк заказа. Лимит- 1600! В вашем заказе: "
        ORDER_UPLOAD_CONFLICT: str = "При загрузке таблицы в базу произошли ошибки!"
        ORDER_ADD_ERROR: str = "Ошибка добавления заказа. Обратитесь к администратору или разработчику." \
                               " Сервер вернул следующее: "
        ORDER_LIMIT: str = "Вы превысили лимит заполнения заказа! Пожалуйста, оформите текущий" \
                           " и продолжайте в следующем. Текущий лимит "
        ORDER_COPY_SUCCESS: str = "Успешно скопирован заказ категории "
        USER_WHATSAPP_LOGO_LINK: str = f"<a href=\"https://wa.me/79959146126\" target=\"_blank\">" \
                                       f"<svg width=\"42\" height=\"42\" viewBox=\"0 0 42 42\" fill=\"white\"" \
                                       f" xmlns=\"http://www.w3.org/2000/svg\">" \
                                       f"<g clip-path=\"url(#clip0_1_110)\"><path fill-rule=\"evenodd\" " \
                                       f"clip-rule=\"evenodd\" d=\"M26.1358 24.6238C25.9193 25.2315 24.8798 25.7853 " \
                                       f"24.3797 25.8602C23.9321 25.9271 23.3651 25.9547 22.7417 25.7578C22.2386" \
                                       f" 25.6008 21.7439 25.4177 21.2599 25.2092C18.6506 24.083 16.9457 21.4567" \
                                       f" 16.8158 21.2835C16.6858 21.1102 15.754 19.8738 15.754 18.5942C15.754 17.3145" \
                                       f" 16.426 16.6845 16.6648 16.4246C16.9024 16.1647 17.1846 16.0991 17.3578" \
                                       f" 16.0991C17.5311 16.0991 17.7043 16.1004 17.8566 16.1083C18.0167 16.1162 18.2306" \
                                       f" 16.0479 18.442 16.5545C18.6585 17.0756 19.1783 18.3553 19.2439 18.4852C19.3082" \
                                       f" 18.6152 19.3515 18.7674 19.2649 18.9407C19.1783 19.1139 19.135 19.2228 19.005" \
                                       f" 19.3751C18.8751 19.526 18.732 19.7137 18.6152 19.8305C18.4853 19.9592 18.3488" \
                                       f" 20.1009 18.501 20.3608C18.6533 20.6207 19.1743 21.4725 19.9474 22.1615C20.941" \
                                       f" 23.0475 21.7796 23.3218 22.0395 23.453C22.2994 23.583 22.4516 23.5607 22.6026" \
                                       f" 23.3874C22.7548 23.2142 23.2536 22.6288 23.4268 22.3676C23.6001 22.1077" \
                                       f" 23.7733 22.151 24.0122 22.2377C24.2498 22.3243 25.5295 22.953 25.7893" \
                                       f" 23.0842C26.0492 23.2142 26.2225 23.2785 26.2881 23.3874C26.3524 23.4963" \
                                       f" 26.3524 24.0161 26.1358 24.6238ZM21.0473 12.2574C16.275 12.2574 12.3926" \
                                       f" 16.1372 12.3913 20.9055C12.3913 22.5395 12.8481 24.1316 13.7143" \
                                       f" 25.5084L13.9204 25.8352L13.0463 29.0272L16.321 28.1688L16.636 28.3552C17.9688" \
                                       f" 29.1455 19.4899 29.5621 21.0394 29.5614H21.0433C25.8116 29.5614 29.6927" \
                                       f" 25.6817 29.6953 20.912C29.6988 19.7754 29.4768 18.6493 29.0422 17.599C28.6076" \
                                       f" 16.5487 27.9691 15.5951 27.1635 14.7932C26.3623 13.9871 25.4092 13.348 24.3594" \
                                       f" 12.9127C23.3095 12.4774 22.1838 12.2547 21.0473 12.2574Z\" fill=\"#67D449\">" \
                                       f"</path><path fill-rule=\"evenodd\" clip-rule=\"evenodd\" d=\"M21.0433" \
                                       f" 31.3189H21.0394C19.2964 31.3189 17.5849 30.8818 16.065 30.0523L10.5459" \
                                       f" 31.5L12.0238 26.1069C11.1108 24.5252 10.6313 22.7305 10.6339 20.9042C10.6365" \
                                       f" 15.1673 15.3051 10.5 21.0433 10.5C22.4115 10.496 23.7669 10.7637 25.0309" \
                                       f" 11.2875C26.2948 11.8113 27.4422 12.5809 28.4064 13.5516C29.3758 14.5162" \
                                       f" 30.1442 15.6636 30.6671 16.9273C31.19 18.191 31.457 19.5458 31.4528" \
                                       f" 20.9134C31.4501 26.6503 26.7803 31.3189 21.0433 31.3189ZM21 0C9.40144 0 0" \
                                       f" 9.40144 0 21C0 32.5973 9.40144 42 21 42C32.5973 42 42 32.5973 42 21C42 9.40144" \
                                       f" 32.5973 0 21 0Z\" fill=\"#67D449\"></path></g><defs><clipPath " \
                                       f"id=\"clip0_1_110\"><rect width=\"42\" height=\"42\" fill=\"white\"></rect>" \
                                       f"</clipPath></defs></svg></a>"
        USER_NOT_EXIST: str = "Пользователя, которого вы пытаетесь отредактировать нет в системе!"
        USER_NOT_ACTIVATED: str = "Ваш профиль пока не активирован. Администратор активирует вас в ближайшее время!"
        USER_NOT_ACTIVATED_1: str = "Вы уже зарегистрированы в системе как "
        USER_NOT_ACTIVATED_2: str = f". Ожидайте , пока администратор активирует ваш аккаунт или сразу обратитесь " \
                                    f"к What's Up менеджеру {USER_WHATSAPP_LOGO_LINK}"

        USER_ORDERS_LIMIT: str = "Пользователь может одновременно создавать не более 5 заказов! " \
                                 "Вы перенаправлены на ваш первый заказ. Оформите хотя бы один и продолжайте"
        USER_ORDERS_COPY_LIMIT: str = "Пользователь может одновременно создавать не более 5 заказов! " \
                                      "Выберите заказ из списка активных заказов .Удалите или оформите хотя бы один и" \
                                      " продолжайте"
        USER_SIGNUP_ERROR_UNIQUE_VIOLATION: str = "Во время регистрации пользователя произошла ошибка дублирования:" \
                                                  " Пользователь с email "
        USER_SIGNUP_CAPTCHA_ERROR: str = "Во время регистрации пользователя произошла ошибка:" \
                                                  " Некорректная капча"
        USER_SIGNUP_ERROR_UNKNOWN: str = "Во время регистрации пользователя произошла непредвиденная ошибка: "
        SECONDARY_SIGN_UP_ERROR: str = "Вы уже авторизованы. Вам не нужна регистрация!"
        USER_SIGHNUP_SUCCESS_1: str = f"Вы успешно прошли регистрацию. Ожидайте, пока администратор активирует ваш " \
                                      f"аккаунт или сразу обратитесь к Whatsapp менеджеру {USER_WHATSAPP_LOGO_LINK}"
        USER_SIGHNUP_SUCCESS_PARTNER: str = f"Вы успешно прошли регистрацию. Желаем приятного пользования сервисом! "
        USER_SIGHNUP_SUCCESS_2: str = "Ожидайте регистрации. Администратор активирует вас в ближайшее время!"
        USER_IS_AUTHENTICATED: str = "Вы уже авторизованы!"
        SUPERUSER_REQUIRED: str = "Для того, чтобы контролировать пользователей нужна роль суперпользователя." \
                                  "Вы уверены что вы суперпользователь?"
        SUPERUM_REQUIRED: str = "Для того, чтобы контроллировать менеджеров нужна роль " \
                                "суперпользователя или суперменеджера. "
        CRM_MANAGER_USER_REQUIRED: str = "Для работы и просмотра CRM нужна роль менеджера или суперпользователя, суперменеджера!"
        CRM_MANAGER_AGENT_USER_REQUIRED: str = "Для работы и просмотра CRM нужна роль менеджера или суперпользователя,  агента, суперменеджера!"
        CRM_MANAGER_USER_FORBIDDEN: str = "Менеджеры и суперменеджеры не могут пользоваться основной платформой!"
        CRM_FILENAME_ERROR: str = "Во время загрузки файла произошла ошибка. Проблема с названием файла! Попробуйте латинские буквы и расширение .rar !"
        CRM_CHANGE_STAGE_AT2_BALANCE_ERROR: str = "Пополните баланс. Общее количество этикеток и стоимость их проведения "
        CRM_SEARCH_ORDER_ERROR: str = "Такого заказа нет в системе! {comment}"
        SUPERADMINUSER_REQUIRED: str = "Для того, чтобы контроллировать нужно быть админом или суперпользователем. " \
                                       "Вы уверены, что вы админ или суперпользователь?"
        PARTNER_CODE_CREATE: str = "Успешно создан код партнера "
        SUPERADMIN_MADMIN_USER_REQUIRED: str = "Для того, чтобы контроллировать CRM нужно быть админом или суперпользователем. " \
                                               "Вы уверены, что вы админ или суперпользователь?"
        SUPER_MOD_REQUIRED: str = "Для того, чтобы продолжить нужна роль супера или модератора"
        PARTNER_CODE_ERROR: str = "Ошибка сохранения кода партнера! "
        PARTNER_CODE_DELETE_SUCCESS: str = "Успешно удален партнер код {partner_code}"
        PARTNER_CODE_DELETE_ERROR: str = "Ошибка удаления кода партнера! Есть привязанные пользователи."
        PARTNER_CODE_DUPLICATE_ERROR: str = "Ошибка сохранения кода партнера! В базе уже есть партнер код "
        PROMO_CREATE: str = "Успешно создан промокод "
        PROMO_ERROR: str = "Ошибка сохранения промокода! "
        PROMO_DUPLICATE_ERROR: str = "Ошибка сохранения промокода! В базе уже есть такой код! "
        PROMO_TYPE_ERROR: str = "Ошибка сохранения промокода! Проверьте вводимое значение "
        PROMO_NE_ERROR: str = 'Такого промо кода не существует'
        PROMO_USED_ERROR: str = 'Вы уже использовали этот промокод'
        PROMO_ADD_USER_ERROR: str = 'Ошибка добавления промокода к списку использованных пользователем '
        PRICE_CREATE: str = "Успешно создан ценовой пакет "
        PRICE_ERROR: str = "Ошибка сохранения промокода! "
        PRICE_DUPLICATE_ERROR: str = "Ошибка сохранения промокода! В базе уже есть такой код! "
        PRICE_TYPE_ERROR: str = "Ошибка сохранения ценового пакета! Проверьте вводимое значение "
        SA_CREATE: str = "Успешно создан счет "
        SA_QUANTITY_LIMIT: str = "Достигнут максимальный лимит счетов на сервисе! "
        SA_ERROR: str = "Ошибка сохранения счета! "
        SA_DUPLICATE_ERROR: str = "Ошибка сохранения счета! В базе уже есть такой код! "
        SA_TYPE_ERROR: str = "Ошибка сохранения счета! Проверьте вводимое значение "
        SA_LIMIT_ERROR: str = "Ошибка сохранения счета! Превышен лимит счетов "
        SA_TYPE_CHANGE: str = "Настройки расчетного счет изменены"
        SA_TYPE_CHANGE_ERROR: str = "При изменении расчетного счета произошла ошибка "
        SA_TYPE_FILE_ERROR: str = "Ошибка сохранения счета! Проверьте файл с qr кодом." \
                                  " Разрешенные форматы .png, .jpg, .jpeg "
        SA_UPDATE_FIRST_CHANGE: str = "Во время первичного обновления приоритетного счета пополнения произошла ошибка: "
        SA_UPDATE_CHANGE: str = "Во время первичного обновления приоритетного счета пополнения произошла ошибка: "
        SP_UPDATE_ERROR: str = "Ошибка сохранения параметров сервиса "
        USER_TRANSACTION_CREATE: str = "Сервис зарегистрировал транзакцию. Администратор проверит вашу транзакцию в ближайшее время"
        USER_TRANSACTION_ERROR: str = "Ошибка сохранения транзакции! "
        USER_TRANSACTION_AGENT_ERROR: str = "Ошибка пополнения счета клиента! Пользователя  агентов с единым счетом не используют личный счет. Обратитесь к агенту "
        SU_TRANSACTION_CHANGE: str = "Статус транзакции успешно изменен"
        SU_TRANSACTION_CHANGE_ERROR: str = "При изменении статуса транзакции произошла ошибка"
        UT_TYPE_FILE_ERROR: str = "Ошибка сохранения транзакции! Проверьте файл с картинкой счета." \
                                  " Разрешенные форматы .png, .jpg, .jpeg, .pdf "
        TELEGRAM_SET_SUCCESS: str = "Успешно сохранен новый телеграмм канал для агентов!"
        TELEGRAM_SET_ERROR: str = "Ошибка сохранения телеграмм группы/канала! "
        TELEGRAM_MPSET_SUCCESS: str = "Успешно сохранены настройки сообщения телеграмм канала агента! "
        TELEGRAM_MPSET_ERROR: str = "Ошибка сохранения настроек сообщения телеграмм канала агента! "
        TELEGRAM_DELETE_ERROR: str = "Ошибка удаления телеграмм группы/канала! "
        TELEGRAM_BIND_ERROR: str = "Ошибка привязки телеграмм группы/канала! "
        TELEGRAM_SEND_ERROR: str = "Ошибка отправки сообщения менеджеру"
        TELEGRAM_REQUEST_ERROR: str = "Ошибка, некорректный запрос информации телеграмм группы!"
        CHECK_ORDER_REQUEST_ABS_ERROR: str = "Ошибка, у вас нет заказа для проверки!"
        CHECK_ORDER_REQUEST_NO_MATCH: str = "Схожих заказов нет"
        CHECK_ORDER_MATCH: str = "Система определила, что среди оформленных заказов есть идентичный по артикулам "
        FORM_CONTENT_ERROR: str = "Ошибка, некорректные данные в теле запроса формы!"
        SUPERUSER_NOT_EDIT: str = "Нельзя редактировать суперпользователя! Обратитесь к разработчику!"
        ADMIN_TG_CREATE_SUCCESS: str = "Успешно создан новый пользователь с ролью агент, работающий через ТГ"
        ADMIN_CRM_CREATE_SUCCESS: str = "Успешно создан новый пользователь с ролью агент, работающий через CRM"
        ADMIN_CREATE_ERROR: str = "Во время создания агента произошла ошибка: "
        MANAGER_CREATE_SUCCESS: str = "Успешно создан новый пользователь с ролью менеджер "
        MANAGER_CREATE_ERROR: str = "Во время создания пользователя с ролью менеджер произошла ошибка "
        SUPERMANAGER_SET: str = "Успешна поменяна роль пользователя на супер менеджер"
        SUPERMANAGER_SET_ERROR: str = "Во время смены роли на супер менеджера произошла ошибка"
        MANAGER_SET: str = "Успешна поменяна роль пользователя на менеджер"
        MANAGER_SET_ERROR: str = "Во время смены роли на менеджера произошла ошибка"
        NO_SUCH_PARTNER_CODE_1: str = "ошибка кода партнера"
        NO_SUCH_PARTNER_CODE_2: str = "Попробуйте заново или обратитесь к вашему администратору"
        NO_SUCH_USER: str = "Вы пытаетесь отредактировать несуществующего пользователя"
        NO_SUCH_USER_SERVICE: str = "Вы пытаетесь воспользоваться неактивированной для вас услугой"
        NO_USER_PASSWORD: str = "Не указан пароль"
        USER_PASSWORD_CHANGE: str = "Успешно изменен пароль пользователя"
        USER_PASSWORD_CHANGE_ERROR: str = "Во время изменения пароля пользователя произошла ошибка"
        ORDER_RESTORED_SENT: str = "Восстановленный заказ отправлен"
        NO_SUCH_ORDER: str = "Ошибка! Такого заказа нет в БД, он может быть на оформлении " \
                             "(проверьте через вкладку заказы), или он помечен на удаление!"
        NO_SUCH_BG_TASK: str = "Такой фоновой задачи нет в хранилище!"
        NO_SUCH_SIGNUP_LINK: str = "Используется некорректная ссылка для регистрации!"
        NO_SUCH_ORDER_REMOVE: str = "Вы пытаетесь удалить не ваш заказ. Запрещено"
        PROCESS_SUCCESS: str = "Заказ оформлен. Проверйте статус в истории заказов. " \
                                  "Номер заказа "
        PROCESS_SUCCESS_TG: str = "Задание отправлено на обработку. Агент уведомлен через телеграмм. " \
                                  " Ваш номер заказа "
        PROCESS_SUCCESS_CRM: str = "Задание отправлено на обработку через CRM. Таблица позиций очищена. Номер заказа "
        PROCESS_ERROR: str = "При отправке задания на обработку произошла ошибка"
        PROCESS_ARCHIVE_ERROR: str = "При добавлении зак в историю заказов произошла ошибка"
        DOWNLOAD_ADMIN_ERROR: str = "При формировании отчета по агенту произошла ошибка. Отчет пуст."
        CHANGE_AGENT_FEE_SUCCESS: str = "Успешно изменена ставка агента "
        CHANGE_TRUST_LIMIT_SUCCESS: str = "Успешно изменена ставка агента "
        CHANGE_AGENT_FEE_ERROR: str = "При изменении лимита отрицательного баланса агента произошла ошибка "
        CHANGE_TRUST_LIMIT_ERROR: str = "При изменении лимита отрицательного баланса агента произошла ошибка "
        CONNECTION_CRM: str = "Нет соединения с сервером регистрации заказов"
        CONNECTION_MARKINERIS_ERROR: str = "Нет соединения с сервером проверки заказов маркинерис"
        CLEAN_EMPTY: str = "Нет позиций для удаления"
        ORDER_DELETE_ERROR: str = "Во время удаления заказа произошла ошибка"
        ORDER_DELETE_STAGE: str = "Заказ уже в обработке. Чтобы его отменить свяжитесь с ваши менеджером!"
        ORDER_DELETE_POS_SUCCESS: str = "Успешно удалена позиция "
        ORDER_ADD_POS_SUCCESS: str = "Успешно добавлена позиция "
        ORDER_ADD_POS_ERROR: str = "Во время сохранения позиции возникла ошибка сохранения в БД "
        ORDER_EDIT_POS_SUCCESS: str = "Успешно изменена позиция "
        ORDER_DELETE_SUCCESS: str = "Удален заказ "
        BG_TASK_DELETE_SUCCESS: str = "Успешно удалена фоновая задача "
        ORDER_NOTE_UPDATE_SUCCESS: str = "Успешно обновлено уведомление оформления заказа!"
        SEND_FILE_SUCCESS: str = "Успешно отправлена таблица"
        SEND_FILE_ERROR: str = "Во время отправки сообщения в Телеграмм произошла ошибка: "
        SEND_FILE_EXTEXSION_ERROR: str = "Проверьте разрешение загружаемого файла. Отправляем только .xlsx!"
        UPLOAD_FILE_TYPE_ERROR: str = "Загружаемый файл не соответствует параметрам Excel 2007 - 365" \
                                      " с расширением .xlsx! Используйте microsoft Excel или libre office," \
                                      " сохраните файл с расширением xlsx!"
        UPLOAD_CATEGORY_TEMPLATE_TYPE_ERROR: str = "Загружаемый файл не соответствует параметрам шаблона категории." \
                                                   " Скачайте шаблонную таблицу, заполните ее и загрузите!"
        UPLOAD_FILE_EXTEXSION_ERROR: str = "Загружаемый файл не соответствует шаблону," \
                                           " либо в вашем заказе отсутствуют позиции!" \
                                           " Скачайте шаблон и скопируйте в него данные из вашего файла!"
        UPLOAD_FILE_UNKNOWN_ERROR: str = "Во время загрузки файла произошла ошибка! "
        UPLOAD_FILES_ERROR: str = "Внимание! Во время загрузки файла возникли ошибки! " \
                                  "Прочитайте скачавшийся текстовый файл с ошибками \"Ошибки_загрузки_заказа.txt\"." \
                                  " Исправьте ошибки и попробуйте снова!"
        UPLOAD_RD_GENERAL_ERROR: str = "Разрешительная Документация - заполнены не все поля"
        UPLOAD_RD_TYPE_ERROR: str = "Разрешительная Документация. Проверьте правильность типа РД (справочник)"
        UPLOAD_RD_DATE_ERROR: str = "Разрешительная Документация - проверьте формат даты dd.mm.yyyy"
        UPLOAD_EMPTY_FILE_ERROR: str = "Нет ни одной информационной строки"
        UPLOAD_EMPTY_VALUE_ERROR: str = "Пустое значение!"
        UPLOAD_VALUE_LIMIT_ERROR: str = "Превышено количество знаков (max 100)"
        UPLOAD_EMPTY_VALUE_FORM_ERROR: str = "Пустое значение в форме!"
        UPLOAD_NOT_STR_VALUE_ERROR: str = "Вводимое значение должно быть строкой"
        UPLOAD_TNVED_ERROR: str = " Проверьте ваш код здесь https://www.alta.ru/tnved/?ysclid=ley5fa8rg7766035472"
        UPDATE_ORG_ERROR: str = "Во время обновления карточки организации произошла ошибка!"
        UPDATE_ORG_SUCCESS: str = "Карточка организации успешно обновлена!"

        AUTO_IDN_SUCCESS: str = "Данные компании по ИНН получены! "
        AUTO_IDN_ERROR_DATA: str = "По данному ИНН данные не найдены!"
        AUTO_IDN_ERROR_CON: str = "Произошла ошибка подключения к провайдеру данных"

        STRANGE_REQUESTS: str = "Замечена подозрительная активность! Вы уверены, что делаете все корректно?"
        STRANGE_REQUESTS_ENG: str = "Spotted strange user activity!"
        GOOGLE_TABLES_SEND_SUCCESS: str = "Успешная отправка информации в Google tables "
        GOOGLE_TABLES_SEND_ERROR: str = "Отправка информации в Google tables информации "
        TNVED_INPUT_ERROR_10: str = " -некорректен. ТНВЭД должен состоять из 10 цифр"
        TNVED_INPUT_ERROR_DIGITS: str = f" -некорректен. <br>ТНВЭД должен состоять из цифр"
        TNVED_INPUT_ERROR_4DIGITS: str = f" первые 4 цифры должны быть в списке: "
        TNVED_INPUT_ERROR_CT: str = f" -некорректен. <br>В списке ТНВЭД нет такого типа одежды"
        TNVED_INPUT_SUCCESS: str = "Пользователь ввел корректный ТНВЭД который есть в базе"
        TNVED_INPUT_SUCCESS_4DIGIT: str = "Пользователь ввел корректный ТНВЭД которого нет в базе, но он подходит по" \
                                          " условиям"
        TNVED_INPUT_ERROR_NF: str = "\n- отсутствует в базе ТНВЭД ЕАЭС или не подлежит маркировке!\n" \
                                    "Прочитайте инструкцию ниже и подберите другой код!"
        TNVED_CLOTHES_INPUT_ERROR_NF: str = "\n- отсутствует в списке подходящих ТНВЭД для данного типа одежды!" \
                                            " Посмотрите вкладку ТНВЭД в таблице шаблона!"
        TNVED_INPUT_ERROR_EMPTY: str = "Пустое поле ТНВЭД"
        TNVED_ABSENCE_ERROR: str = "Проверьте что корректно заполняете ТНВЭД. Почему то ваш тнвед либо пустой, либо не подходит типу одежды"
        MANUAL_TNVED_SUCCESS: str = "Успешно подгружены тнвэд коды! "
        MANUAL_TNVED_ERROR: str = "Во время обработки запроса ТНВЭ произошла ошибка! Вы отправили на сервис неизвестный тип одежды!"
        ORDER_STAGE_CHANGE: str = "Успешно изменен статус заказа"
        ORDER_STAGE_MULTI_CHANGE: str = "Успешно изменены статусы заказов"
        ORDER_STAGE_CHANGE_EMPTY: str = "Нет заказов для переноса"
        ORDER_STAGE_CHANGE_ERROR: str = "Во время изменения статуса заказа произошла ошибка. Обратитесь к администратору"
        ORDER_CANCEL: str = "Успешно отменен заказ"
        ORDER_PROBLEM: str = "Успешно перенесен заказ в проблемные"
        ORDER_CANCEL_ERROR: str = "Во время отмены заказа произошла ошибка. Обратитесь к администратору "
        ORDER_PROBLEM_ERROR: str = "Во время переноса заказа в проблемные произошла ошибка. Обратитесь к администратору "
        ORDER_MANAGER_TAKE: str = "Менеджер взял заказ в обработку"
        ORDER_MANAGER_PROCESSED: str = "Заказ переведен в готовые"
        ORDER_MANAGER_PS: str = "Заказ переведен в ПРОБЛЕМЫ РЕШЕНЫ"
        ORDER_MANAGER_BP: str = "Заказ переведен в ЗАКАЗ В ОБРАБОТКЕ"
        ORDER_ATTACH_FILE: str = "К заказу успешно прикреплен файл "
        ORDER_ATTACH_FILE_LINK: str = "К заказу успешно прикреплена ссылка на файл "
        ORDER_DELETE_FILE: str = "Успешно удален файл заказа"
        ORDER_MANAGER_TAKE_ERROR: str = "Во время привязки заказа к менеджеру произошла ошибка. Обратитесь к администратору "
        ORDER_MANAGER_TAKE_ABS_ERROR: str = "Во время привязки заказа к менеджеру произошла ошибка. Нет такого заказа"
        ORDER_MANAGER_PROCESSED_ABS_ERROR: str = "Во время переноса заказа в готовые произошла ошибка. Нет такого заказа"
        ORDER_MANAGER_PS_ABS_ERROR: str = "Во время переноса заказа в ПРОБЛЕМЫ РЕШЕНЫ произошла ошибка. Нет такого заказа"
        ORDER_MANAGER_PROCESSED_ABS_FILE_ERROR: str = "Во время переноса заказа в готовые произошла ошибка. К текущему заказу не прикреплен файл."
        ORDER_MANAGER_PS_ABS_FILE_ERROR: str = "Во время переноса заказа в ПРОБЛЕМЫ РЕШЕНЫ произошла ошибка. К текущему заказу не прикреплен файл."
        ORDER_MANAGER_PROCESSED_ERROR: str = "Во время переноса заказа в готовые произошла неизвестная ошибка. "
        ORDER_MANAGER_BP_ERROR: str = "Во время переноса заказа в ЗАКАЗ В ОБРАБОТКЕ произошла неизвестная ошибка. "
        ORDER_MANAGER_PS_ERROR: str = "Во время переноса заказа в ПРОБЛЕМЫ РЕШЕНЫ произошла неизвестная ошибка. "
        ORDER_ATTACH_FILE_ERROR: str = "Во время привзязки файла к заказу произошла ошибка. "
        ORDER_ATTACH_FILE_LINK_ERROR: str = "Во время привзязки ссылки файла к заказу произошла ошибка. "
        ORDER_DELETE_FILE_ERROR: str = "Во время удаления файла заказа произошла ошибка. "
        ORDER_ATTACH_FILE_ABS_ERROR: str = "Во время привязки файла к заказу произошла ошибка. Нет такого заказа"
        ORDER_ATTACH_FILE_EXCEED_ERROR: str = "Во время привязки файла к заказу произошла ошибка. Слишком большой файл. "
        ORDER_ATTACH_FILE_LINK_ABS_ERROR: str = "Во время привязки ссылки файла к заказу произошла ошибка. Нет такого заказа"
        ORDER_FILE_ABS_ERROR: str = "Отсутствует файл заказа!"
        ORDER_DELETE_FILE_ABS_ERROR: str = "Во время удаления файла заказа произошла ошибка. Нет такого заказа"
        ORDER_DOWNLOAD_FILE_ABS_ERROR: str = "Во время скачивания файла заказа произошла ошибка. Нет такого заказа"
        ORDER_MANAGER_FEXT: str = "Во время привязки файла к заказу произошла ошибка. Можно прикреплять только архивы с расширением .rar. Ваш файл-"
        ORDERS_MANAGER_LIMIT: str = "Во время взятия заказа в обработку произошла ошибка. Превышен лимит заказов для менеджера! Фактом закрытия является отправка агентом заказа клиенту! Закройте хотя бы один заказ! "
        ORDER_MANAGER_CHANGE: str = "Успешно изменен менеджер к заказу "
        ORDER_MANAGER_CHANGE_ERROR: str = "Во время изменения менеджера заказа произошла ошибка базы. "
        ORDER_MANAGER_CHANGE_ABS_ERROR: str = "Во время изменения менеджера заказа произошла ошибка. Такого заказа нет"
        ORDER_PROCESSED_NOT_PAID: str = "Заказ не оплачен. Нельзя перевести в завершенные."
        ORDER_CEPS_SUCCESS: str = "Успешно изменен флаг внешней проблемы заказа!"
        ORDER_CEPS_ERROR: str = "Во время смены флага внешней проблемы заказа произошла ошибка"
        NO_SUCH_ORDER_CRM: str = "Ошибка! Такого заказа нет в CRM"
        OCO_REMOVED: str = "Из бд удалены старые отмененные заказы! "
        OCO_REMOVED_ERROR: str = "Во время удаления старых отмененных заказов произошла ошибка! "
        OS_CHANGE_SUCCESS: str = "Успешно изменены статусы заказов из {stage_from} в {stage_to}"
        OS_CHANGE_EMPTY: str = "Нет заказов для изменения статуса {stage_from} в {stage_to}"
        OSR_CHANGE_ERROR: str = "Во время изменения статуса заказов из ОТПРАВЛЕНО в ОФОРМЛЕНО произошла ошибка! "
        OS_CHANGE_STAGE_ERROR: str = "Во время изменения статуса заказов произошла ошибка! "
        LIMIT_SUCCESS: str = "Успешно изменены лимиты  "
        LIMIT_INPUT_ERROR: str = "Изменение лимита не произведено!" \
                                 " Некорректные данные! Убедитесь что вводите корректно значение лимита!"
        LIMIT_DYN_SCH_ERROR: str = "Изменение в планировщике не произведено"
        LIMIT_ERROR: str = "Во время изменения лимита " \
                           "произошла ошибка сохранения в базу!  "
        PO_LIMIT_EXCCED_MO: str = "Во время изменения лимита. Количество проблемных заказов должно быть " \
                                  "меньше максимального количества заказов, которе менеджер может взять. вы ввели  "
        NO_FILES_TO_DOWNLOAD: str = "Нет файлов для скачивания"
        NO_FILES_TO_DOWNLOAD_ENG: str = "No files to download"
        FILE_DOWNLOAD_LINK: str = "Файл в систему не загружался. "
        SO_ORG_IDN_USER_MATCH: str = "На <b>smart-orders</b> есть пользователи <b>работающие</b> с ИНН: "
        SO_ORG_IDN_USER_SIGN_UP_MATCH: str = "На <b>smart-orders</b> есть пользователи <b>зарегистрировавшиеся</b> с ИНН: "
        DELETE_PROMO: str = "Успешно удален промокод "
        DELETE_NE_PROMO: str = "Попытка удаления несуществующего промо "
        DELETE_PROMO_ERROR: str = "Во время удаления промокода произошла ошибка!"
        DELETE_PRICE: str = "Успешно удален ценовой пакет "
        DELETE_NE_PRICE: str = "Попытка удаления несуществующего ценового пакета "
        DELETE_PRICE_ERROR: str = "Во время удаления ценового пакета произошла ошибка!"
        DELETE_SA: str = "Успешно удален расчетный счет сервиса "
        DELETE_NE_SA: str = "Попытка удаления несуществующего расчетного счета сервиса "
        DELETE_SA_ERROR: str = "Во время удаления расчетного счета сервиса произошла ошибка!"
        DELETE_SA_UT_ERROR: str = "У этого счета уже есть транзакции, его нельзя удалить. Обратитесь к админу!"
        CHANGE_SA_ACTIVITY: str = "Успешно изменен статус счета на {status} "
        CHANGE_NE_SA_ACTIVITY: str = "Попытка изменения статуса активности несуществующего расчетного счета сервиса "
        CHANGE_SA_ACTIVITY_ERROR: str = "Во время изменения статуса активности счета сервиса произошла ошибка!"
        WO_TRANSACTION_USER_ERROR: str = "Во время формирования транзакции списания произошла ошибка. Нет такого пользователя"
        WO_TRANSACTION_BALANCE_ERROR_1: str = "Во время формирования транзакции списания произошла ошибка."
        WO_TRANSACTION_BALANCE_ERROR_2: str = " На балансе меньше средств чем указано в в сумме всех транзакций на списание.<br> Суммарный запрос {request_summ} р > Баланс {balance} р "
        WO_TRANSACTION_BALANCE_ERROR: str = WO_TRANSACTION_BALANCE_ERROR_1 + WO_TRANSACTION_BALANCE_ERROR_2
        WO_TRANSACTION_PENDING_AMOUNT_ERROR: str = "Во время проверки все транзакций на списание произошло исключение. Обратитесь к администратору!"
        USER_PRICE_PLUG: str = "Успешно обновлен ценовой пакет для пользователя "
        USER_PRICE_TYPE_ERROR: str = "Во время обновления ценового пакета произошла ошибка. Обратитесь к администратору"
        USER_PRICE_TYPE_ADMIN_ERROR: str = "Во время обновления ценового пакета произошла ошибка. Этот пользователь не может корректировать значения"
        USER_PRICE_TYPE_VALUE_ERROR: str = "Во время обновления ценового пакета произошла ошибка. Некорректное значение."
        USER_PRICE_TYPE_DUPLICATE_ERROR: str = "Во время обновления ценового пакета произошла ошибка дублирования"
        TG_VERIFICATION_SUCCESS: str = "Успешно пройдена верификация для получения уведомлений от сервиса M2R."
        TG_VERIFICATION_NO_NEED: str = "Вы уже верифицированы для получения уведомлений от сервиса M2R."
        TG_VERIFICATION_ERROR: str = "Во время верификации произошла ошибка."
        TG_VERIFICATION_EXISTS: str = "Ваш ТГ уже зарезервирован за другим пользователем."
        TG_VERIFICATION_ASK_BOT: str = "Введен некорреткный код. Пройдите по <a href=\"{tg_link}\" target=\"_blank\">ссылке</a> бот сервиса маркировки для получения кода верификации"
        TG_VERIF_DELETE_SUCCESS: str = "Успешно завершено отключение от уведомлений бота сервиса Маркировки"
        TG_VERIF_DELETE_ERROR: str = "Во время отключения от бота сервиса Маркировки произошла ошибка  "

    class Mail:
        RESTORE_LINK_SUBJECT: str = "Письмо смены пароля от сервиса Маркировки"
        RESTORE_LINK_TEXT: str = "Не отвечайте на это письмо, оно создано автоматически! Пройдите по "
        SENDER_NAME = "MARKISERVICE"
        CLIENT_NAME = "Клиент сервиса маркировки"
        SENDER_EMAIL = "markiservice@best.com"
        EXPIRATION_RESTORE_LINK: int = 10800

    class Pdf:
        PDF_FOLDER_NAME = 'ЭтикеткиPDF'
        TEXT_FONT_SIZE = 6.9
        TEXT_TX = 73.2 / 100  # X position as a percentage absolete 135
        TEXT_TY = 5 / 100  # Y position as a percentage absolete 10

    class Reports:
        UT_START: list = UT_REPORT_START

    class Upload:
        STANDART: str = 'standart'
        EXTENDED: str = 'extended'
        SHEET_NAME: str = "Данные"
        TYPE_UPLOADS: list = ['standart', 'extended']

    class Shoes:
        CATEGORY: str = 'обувь'
        CATEGORY_PROCESS: str = 'shoes'
        TYPES: list = SHOE_TYPES
        COLORS: tuple = COMMON_COLORS
        GENDERS: list = SHOE_GENDERS
        MATERIALS_UP_LINEN: list = SHOE_MATERIALS_UP_LINEN
        MATERIALS_BOTTOM: list = SHOE_MATERIALS_BOTTOM

        MATERIALS_CORRECT: dict = SHOE_MATERIALS_CORRECT

        SHOE_AL: tuple = SHOE_AL
        SHOE_OT: tuple = SHOE_OT
        SHOE_NL: tuple = SHOE_NL
        TNVED_CODE: tuple = SHOE_TNVED  # "6405209900"
        TNVED_CHECK_LIST: list = SHOE_TNVED_CHECK_LIST
        SIZES: tuple = SHOE_SIZES
        SIZES_ALL: list = SHOE_SIZES_FULL
        SHOE_SIZE_DESC: tuple = SHOES_SIZES_DESCRIPTION
        BOX_DESCRIPTION: list = ["Если вы собираете заказ <b>коробами</b>, ",
                                 "то в поле <i><u>Количество коробов</u></i>",
                                 "укажите количество коробов. ",
                                 "Если вы собираете заказ <b>по размерам</b>, то",
                                 " укажите в данном поле нужное количество пар,",
                                 " а в графе <i><u>Количество в коробе</u></i> ",
                                 "оставьте цифру 1."]
        START: list = SHOE_START
        START_EXT: list = SHOE_START_EXT
        START_PRELOAD: list = SHOE_PRELOAD_START
        START_CRM_PRELOAD: list = SHOE_PRELOAD_START[1:11] + SHOE_PRELOAD_START[12:]
        SHEET_NAME_STANDART: str = "IMPORT_TNVED_6405"
        SHEET_NAME_EXT: str = "Данные"
        UPLOAD_STANDART_ROW: int = 7
        MAX_QUANTITY: int = 100000000
        UPLOAD_TYPE_ERROR: str = "Проверьте правильность выбора типа обуви (посмотрите вкладку справочник)"
        UPLOAD_COLOR_ERROR: str = "Проверьте правильность указанного цвета обуви (посмотрите вкладку справочник)"
        UPLOAD_SIZE_ERROR: str = "Проверьте правильность указанного размера обуви (диапазон от 16 до 56, шаг 0.5)" \
                                 "т.е. 16, 16.5, 17, 17.5 ... 55.5, 56, 56.5, либо размеры особого вида:" \
                                 "16-17, 17-18 ... 54-55, 55-56"
        UPLOAD_SIZES_QUANTITIES_ERROR: str = "Проверьте корректность указанных размеров и количеств обуви " \
                                             "(диапазон размеров  от 16 до 56.5, шаг 0.5)"
        UPLOAD_SIZES_QUANTITIES_DATA_INPUT_ERROR: str = "Проверьте корреткность указанной размерной сетки"
        UPLOAD_SIZES_QUANTITIES_LEN_ERROR: str = "Проверьте корректность указанных размеров и количеств обуви, " \
                                                 "список размеров не совпадает со списком количеств"
        UPLOAD_MATERIAL_ERROR: str = "Проверьте правильность указанного материала обуви (посмотрите вкладку справочник)"
        UPLOAD_GENDER_ERROR: str = "Проверьте правильность указанного пола (посмотрите вкладку справочник)"
        UPLOAD_QUANTITY_ERROR: str = "Проверьте правильность указанного количества (Это должно быть число )"
        UPLOAD_COUNTRY_ERROR: str = "Проверьте правильность указанной страны (посмотрите вкладку справочник)"

    class Linen:
        CATEGORY: str = 'белье'
        CATEGORY_PROCESS: str = 'linen'
        TYPES: list = LINEN_TYPES
        COLORS: tuple = COMMON_COLORS
        TEXTILE_TYPES: list = LINEN_TEXTILE_TYPES
        CUSTOMER_AGES: list = LINEN_CUSTOMER_AGES
        BOX_QUANTITY_DESCRIPTION: list = ["Указание комплектов необязательно",
                                          "Исходное значение равно 1"]

        TNVED_CODE: str = LINEN_TNVED
        TNVED_CHECK_LIST: list = ["6302", ]
        NUMBER_STANDART: str = "ТР ТС 017/2011 \"О безопасности продукции легкой промышленности\""
        START: list = LINEN_START
        START_EXT: list = LINEN_START_EXT
        START_PRELOAD: list = LINEN_PRELOAD_START
        START_CRM_PRELOAD: list = LINEN_PRELOAD_START[1:11] + LINEN_PRELOAD_START[12:]

        UPLOAD_STANDART_ROW: int = 7
        MAX_QUANTITY: int = 100000000
        UPLOAD_TYPE_ERROR: str = "Проверьте правильность выбора вида товара (посмотрите вкладку справочник)"
        UPLOAD_COLOR_ERROR: str = "Проверьте правильность указанного цвета белья (посмотрите вкладку справочник)"
        UPLOAD_SIZE_ERROR: str = "Проверьте правильность указанного размера белья (это должно быть целое число )"
        UPLOAD_TEXTYLE_TYPE_ERROR: str = "Проверьте правильность указанного типа текстиля (посмотрите вкладку справочник)"
        UPLOAD_CUSTOMER_AGE_ERROR: str = "Проверьте правильность указанного возраста (посмотрите вкладку справочник)"
        UPLOAD_BOX_QUANTITY_ERROR: str = "Проверьте правильность указанного количества комплектов (Это должно быть число )"
        UPLOAD_QUANTITY_ERROR: str = "Проверьте правильность указанного количества (Это должно быть число )"
        UPLOAD_COUNTRY_ERROR: str = "Проверьте правильность указанной страны (посмотрите вкладку справочник)"

    class Parfum:
        CATEGORY: str = 'парфюм'
        CATEGORY_PROCESS: str = 'parfum'
        TYPES: list = PARFUM_TYPES
        VOLUMES: list = PARFUM_VOLUMES
        PACKAGE_TYPES: list = PARFUM_PACKAGE_TYPES
        MATERIAL_PACKAGES: list = PARFUM_MATERIAL_PACKAGES
        TNVED_CODE: tuple = PARFUM_TNVED  # "3303001000"
        TNVED_CHECK_LIST: list = ['3303']
        START: list = PARFUM_START
        START_EXT: list = PARFUM_START_EXT
        START_PRELOAD: list = PARFUM_PRELOAD_START
        START_CRM_PRELOAD: list = PARFUM_PRELOAD_START[1:8] + PARFUM_PRELOAD_START[9:]

        MAX_VOLUME: int = 1000000
        MAX_QUANTITY: int = 100000000
        NUMBER_STANDART: str = "ТР ТС 009/2011 \"О безопасности парфюмерно-косметической продукции\""
        STATUS: str = "Черновик"
        UPLOAD_STANDART_ROW: int = 7
        UPLOAD_TYPE_ERROR: str = "Проверьте правильность выбора типа парфюма (посмотрите вкладку справочник)"
        UPLOAD_COLOR_ERROR: str = "Проверьте правильность указанного цвета одежды (посмотрите вкладку справочник)"
        UPLOAD_SIZE_TYPE_ERROR: str = "Проверьте правильность указанного типа размера одежды (справочник)"

        UPLOAD_SIZE_ERROR: str = "Проверьте правильность указанного размера одежды (диапазон от 12 до 72, шаг 2)" \
                                 "т.е. 12, 14, 16, 18 ... 68, 70, 72"

        UPLOAD_QUANTITY_ERROR: str = "Проверьте правильность указанного количества (Это должно быть число )"
        UPLOAD_VOLUME_ERROR: str = "Проверьте правильность указанного объема (Это должно быть число )"
        UPLOAD_VOLUME_TYPE_ERROR: str = "Проверьте правильность указанного типа объема (посмотрите вкладку справочник)"
        UPLOAD_PACKAGE_TYPE_ERROR: str = "Проверьте правильность указанного типа упаковки (посмотрите вкладку справочник)"
        UPLOAD_MATERIAL_PACKAGE_TYPE_ERROR: str = "Проверьте правильность указанного материала упаковки (посмотрите вкладку справочник)"
        UPLOAD_COUNTRY_ERROR: str = "Проверьте правильность указанной страны (посмотрите вкладку справочник)"

    class Clothes:
        CATEGORY: str = 'одежда'
        CATEGORY_PROCESS: str = 'clothes'
        TYPES: list = CLOTHES_TYPES
        UPPER_TYPES: list = CLOTHES_UPPER
        COLORS: tuple = COMMON_COLORS
        SIZES_ALL: list = CLOTHES_SIZES_FULL
        CLOTHES_SIZE_DESC: tuple = CLOTHES_SIZES_DESCRIPTION
        CLOTHES_CONTENT: list = CLOTHES_CONTENT
        CLOTHES_NAT_CONTENT: list = CLOTHES_NAT_CONTENT
        GENDERS: list = CLOTHES_GENDERS
        GENDERS_ORDER: list = CLOTHES_GENDERS_ORDER
        DEC: dict = CLOTHES_DICT

        SIZE_ALL_DICT: dict = CLOTHES_TYPES_SIZES_DICT
        DEFAULT_SIZE_TYPE: str = "РОССИЯ"
        UNITE_SIZE_VALUE: str = "ЕДИНЫЙ РАЗМЕР"
        SIZE_TYPES_ALL: list = CLOTHES_TYPES_SIZES_DICT.keys()  # temporary before all types are ok to use
        TNVED_CODE: tuple = CLOTHES_TNVED  # "6202900001"
        # TNVED_CHECK_LIST: tuple = BIG_CLOTHES_TNVED_4DIGIT
        TNVED_ALL: tuple = ALL_CLOTHES_TNVED
        START: list = CLOTHES_START
        START_EXT: list = CLOTHES_START_EXT
        START_PRELOAD: list = CLOTHES_PRELOAD_START
        START_CRM_PRELOAD: list = CLOTHES_PRELOAD_START[1:11] + CLOTHES_PRELOAD_START[12:]
        UPLOAD_STANDART_ROW: int = 7
        MAX_QUANTITY: int = 100000000
        NUMBER_STANDART: str = "ТР ТС 017/2011 \"О безопасности продукции легкой промышленности\""

        UPLOAD_TYPE_ERROR: str = "Проверьте правильность выбора типа одежды (посмотрите вкладку справочник)"
        UPLOAD_COLOR_ERROR: str = "Проверьте правильность указанного цвета одежды (посмотрите вкладку справочник)"
        UPLOAD_SIZE_TYPE_ERROR: str = "Проверьте правильность указанного типа размера одежды (справочник)"

        UPLOAD_SIZE_ERROR: str = "Проверьте правильность указанного размера одежды во вкладке справочник"

        UPLOAD_CONTENT_ERROR: str = "Проверьте правильность указанного состава одежды (это не может быть цифра или пустое поле)"
        UPLOAD_GENDER_ERROR: str = "Проверьте правильность указанного пола (посмотрите вкладку справочник)"
        UPLOAD_QUANTITY_ERROR: str = "Проверьте правильность указанного количества (Это должно быть число )"
        UPLOAD_COUNTRY_ERROR: str = "Проверьте правильность указанной страны (посмотрите вкладку справочник)"
        CLOTHES_TNVED_DICT: dict = CLOTHES_TNVED_DICT
        OLD_TNVEDS: set = CLOTHES_OLD_TNVED
        # OLD_TNVEDS_SQL: str = ', '.join(list(map(lambda x: '\'' + x + '\'', CLOTHES_OLD_TNVED)))

    # class Config:
    #     env_file = '.env'


# -1001595209417
settings = Settings()
