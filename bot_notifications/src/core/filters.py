from aiogram.types import Message
from aiogram.filters import BaseFilter


class TextFilter(BaseFilter):
    def __init__(self, text: str):
        self.text = text

    async def __call__(self, message: Message) -> bool:
        return message.text == self.text
