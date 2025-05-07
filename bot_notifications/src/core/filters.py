import logging

from aiogram.types import Message
from aiogram.filters import BaseFilter

from src.service.user import UserService

logger = logging.getLogger(__name__)


class TextFilter(BaseFilter):
    def __init__(self, text: str):
        self.text = text

    async def __call__(self, message: Message) -> bool:
        return message.text == self.text


class IsCanEditBalanceFilter(BaseFilter):
    async def __call__(self, message: Message, **kwargs) -> bool:
        user_service: UserService = kwargs.get("user_service")
        if not user_service:
            logger.error("UserService not found in kwargs")
            return False

        user_id = message.from_user.id
        user = await user_service.get_user(user_id=user_id)
        if not user:
            logger.warning(f"User not found for telegram_id={user_id}")
            return True

        return await user_service.is_edit_balance_available(user.flask_user_id)
