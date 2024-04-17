from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.schemas.keyboard import ButtonListSchema


async def get_inline_keyboard(button_list: list[dict[str, str]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        *[
            InlineKeyboardButton(text=button.text, callback_data=button.data)
            for button in ButtonListSchema(buttons=button_list).buttons
        ]
    )

    return builder.adjust().as_markup()
