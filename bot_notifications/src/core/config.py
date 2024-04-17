from pathlib import Path

from pydantic import SecretStr, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Setting(BaseSettings):
    ROOT_DIR: str = Path(__file__).resolve().parents[3].as_posix()

    DB_USER: str = Field(..., alias="SU_NAME")
    DB_PASSWORD: str = Field(..., alias="SU_PASSWORD")
    DB_NAME: str
    DB_HOST: str
    DB_PORT: str

    BOT_API_TOKEN: SecretStr = Field(..., alias="VERIFY_NOTIFICATION_BOT_API_TOKEN")

    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_QUEUE_DB: int = 0
    REDIS_BOT_STORAGE_DB: int = 10

    LOG_PATH: Path = Path('/var/log/bot-notifications/')
    LOG_FORMAT: str = '{time} | [{level}] | {name}::{function}: line {line} | {message}'

    LOG_PATH.mkdir(parents=True, exist_ok=True)

    @property
    def database_url(self) -> str:
        return (
            "postgresql+asyncpg://"
            f"{self.DB_USER}:{self.DB_PASSWORD}@"
            f"{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    model_config = SettingsConfigDict(env_file=f"{ROOT_DIR}/.env", extra="ignore")


settings = Setting()
