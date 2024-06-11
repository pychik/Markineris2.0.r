from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.gateways.db.models.user import TgUser, FlaskUserModel


class AbstractUserRepository(ABC):
    session: AsyncSession

    @abstractmethod
    async def get_flask_user_obj(self, email: str) -> FlaskUserModel:
        """Checking the existence of a user in the database by email."""
    @abstractmethod
    async def get_users(self) -> list[TgUser]:
        """Get all telegram users."""

    @abstractmethod
    async def get_user(self, user_id: int) -> TgUser:
        """Get user by telegram user id."""

    @abstractmethod
    async def create(self, user_data: dict[str, Any]) -> TgUser:
        """Create new telegram user."""

    async def update(self, user_id: int, data: dict[str, Any]) -> TgUser:
        """Update telegram user."""

    async def delete_user(self, user_id: int,) -> None:
        """Delete telegram user."""
