from typing import Any

from sqlalchemy import insert, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.gateways.db.models.user import TgUser, FlaskUserModel
from src.gateways.db.repositories.abstract import AbstractUserRepository
from src.infrastructure.logger import logger

class UserRepository(AbstractUserRepository):

    def __init__(self, session: AsyncSession):
        self.session = session
        self.model = TgUser
        self.flask_user_model = FlaskUserModel

    async def get_flask_user_obj(self, email: str) -> FlaskUserModel:
        stmt = select(self.flask_user_model).where(self.flask_user_model.email == email)
        user = await self.session.scalars(stmt)

        return user.first()

    async def get_users(self) -> list[TgUser]:
        stmt = select(self.model)
        users = await self.session.scalars(stmt)

        return [user for user in users]

    async def get_user(self, user_id: int) -> TgUser:
        stmt = select(self.model).where(self.model.tg_user_id == user_id)
        user = await self.session.scalars(stmt)

        return user.first()

    async def create(self, user_data: dict[str, Any]) -> TgUser:
        stmt = insert(self.model).values(**user_data).returning(self.model)
        user = await self.session.execute(stmt)

        return user.scalars().first()

    async def update(self, user_id: int, data: dict[str, Any]) -> TgUser:
        stmt = (
            update(self.model).
            where(self.model.tg_user_id == user_id).
            values(**data).
            returning(self.model)
        )
        user = await self.session.scalars(stmt)

        return user.first()

    async def get_flask_user_by_id(self, user_id: int) -> FlaskUserModel:
        stmt = select(self.flask_user_model).where(self.flask_user_model.id == user_id)
        user = await self.session.scalars(stmt)

        return user.first()

    async def delete_user(self, user_id: int) -> None:
        user = await self.get_user(user_id)

        if user:
            await self.session.delete(user)
