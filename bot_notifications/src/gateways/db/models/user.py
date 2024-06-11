from sqlalchemy import BigInteger, String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from src.gateways.db.models import Base


class TgUser(Base):
    __tablename__ = "notification_telegram_user"

    tg_user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, nullable=True)
    tg_chat_id: Mapped[int] = mapped_column(BigInteger)
    tg_username: Mapped[str] = mapped_column(String(255))
    verification_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # flask_user_id выполняет логику верификации
    flask_user_id: Mapped[int] = mapped_column(Integer, nullable=True, default=None)

    def __repr__(self) -> str:
        return f"User(user_id={self.tg_user_id}, username={self.tg_username}"


class FlaskUserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    login_name: Mapped[str] = mapped_column(String(128), nullable=True)

    def __repr__(self) -> str:
        return f"FlaskUser(id={self.id}, login_name={self.login_name}, email={self.email}"
