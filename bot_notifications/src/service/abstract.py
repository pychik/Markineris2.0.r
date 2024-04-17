from abc import ABC, abstractmethod

from src.schemas.user import TgUserSchema
from src.gateways.db.models.user import TgUser
from src.gateways.db.repositories.abstract import AbstractUserRepository


class AbstractUserService(ABC):
    repo: AbstractUserRepository

    @abstractmethod
    async def get_user(self, user_id: int) -> TgUser:
        """Get user by telegram user id."""

    @abstractmethod
    async def get_or_create(self, user_schema: TgUserSchema) -> TgUser:
        """Create new telegram user."""
