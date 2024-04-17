import os

from pydantic_settings import BaseSettings


CUR_PATH = os.path.dirname(os.path.abspath(__file__))

NOTIFICATION_GT_JOB_PARAMS = {
    "queue": 'settings.GT_QUEUE_NAME',
    "retry": 'Retry(max=3)',
    "connection": 'conn',
    "on_success": 'on_success_gt',
    "on_failure": 'on_failure_gt',
}


class Settings(BaseSettings):

    class GoogleTables:
        CREDENTIALS_FILE = f"{CUR_PATH}/utilities/google_settings/smart-orders-380418-2b53a29bb857.json"
        SPREADSHEET_ID = "1YC7Z399nyO39zL8DeZp9jlefbHbehH3wcQyzgLdZACU"
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
            LC_RUZNAK: str = "H"  # last column of ruznak orders table
            SHEET_RANGE_RUZNAK: str = f"{SHEET_NAME_RUZNAK}!{FC_RUZNAK}1:{LC_RUZNAK}"

    class Messages:

        GOOGLE_TABLES_SEND_SUCCESS: str = "Успешная отправка информации в Google tables с заказом "
        GOOGLE_TABLES_SEND_ERROR: str = "Отправка информации в Google tables информации с заказом "

    # class Config:
    #     env_file = '.env'


# -1001595209417
settings = Settings()
