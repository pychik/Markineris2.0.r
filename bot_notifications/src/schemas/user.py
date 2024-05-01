from pydantic import BaseModel
from aiogram.types import Message, User


class TgUserSchema(BaseModel):
    tg_user_id: int
    tg_chat_id: int
    tg_username: str | None = None

    @classmethod
    def create(cls, user_from_tg: User) -> "TgUserSchema":
        return cls(
            tg_user_id=user_from_tg.id,
            tg_chat_id=user_from_tg.id,
            tg_username=user_from_tg.username if user_from_tg.username else None,
        )
