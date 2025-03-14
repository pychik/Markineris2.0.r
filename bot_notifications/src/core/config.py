from pathlib import Path

from pydantic import SecretStr, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Setting(BaseSettings):
    ROOT_DIR: str = Path(__file__).resolve().parents[2].as_posix()

    API_HOST: str = "http://0.0.0.0:5555"
    MARKINERS_V2_TOKEN: str

    DB_USER: str = Field(..., alias="SU_NAME")
    DB_PASSWORD: str = Field(..., alias="SU_PASSWORD")
    DB_NAME: str
    DB_HOST: str
    DB_PORT: str

    ALLOWED_BILL_EXTENSIONS: tuple = ('png', 'jpg', 'jpeg', 'pdf',)

    BOT_API_TOKEN: SecretStr = Field(..., alias="VERIFY_NOTIFICATION_BOT_API_TOKEN")

    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_QUEUE_DB: int = 0
    REDIS_BOT_STORAGE_DB: int = 10

    LOG_FORMAT: str = '{time} | [{level}] | {name}::{function}: line {line} | {message}'

    # endpoints
    CHECK_PROMO: str = "/api/check_promo_code"
    GET_REQS: str = "/api/get_current_service_account"
    CREATE_TRANSACTION: str = "/api/create_transaction"

    AMOUNT_OF_MONEY_STORAGE_KEY: str = "amount_of_money"
    FLASK_USER_ID_STORAGE_KEY: str = "flask_user_id"
    PROMO_AMOUNT_STORAGE_KEY: str = "amount_add"
    PROMO_INFO_STORAGE_KEY: str = "promo_info"
    FILENAME_STORAGE_KEY: str = "filename"
    TG_CHAT_ID_STORAGE_KEY: str = "chat_id"
    REQUISITE_ID_STORAGE_KEY: str = "requisite_id"
    PROMO_CODE_ID_STORAGE_KEY: str = "promo_id"
    TRANSACTION_TYPE_STORAGE_KEY: str = "transaction_type_id"

    MAINTENANCE_MODE: bool = Field(default=False, alias="BOT_MAINTENANCE_MODE")
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10 мб

    MINIO_API_URL: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BILL_BUCKET_NAME: str

    @property
    def database_url(self) -> str:
        return (
            "postgresql+asyncpg://"
            f"{self.DB_USER}:{self.DB_PASSWORD}@"
            f"{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def log_path(self) -> str:
        log_path: Path = Path('/var/log/bot-notifications/')

        log_path.mkdir(parents=True, exist_ok=True)
        return log_path.as_posix()

    model_config = SettingsConfigDict(env_file=f"{ROOT_DIR}/.env", extra="ignore")


settings = Setting()
