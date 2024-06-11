from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from src.schemas.keyboard import ButtonListSchema


async def get_reply_keyboard(button_list: list[dict[str, str]]) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(
        *[
            KeyboardButton(text=button.text)
            for button in ButtonListSchema(buttons=button_list).buttons
        ]
    )

    return builder.adjust().as_markup(resize_keyboard=True, is_persistent=True)
