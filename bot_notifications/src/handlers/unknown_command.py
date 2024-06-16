from aiogram import Router
from aiogram.types import Message

from src.core.messages import UserMessages
from src.keyboards.buttons import HELP_BUTTON, REFILL_BALANCE
from src.keyboards.reply import get_reply_keyboard

router = Router()


@router.message()
async def unknown_command_handler(
        message: Message,
) -> None:
    await message.answer(
        text=UserMessages.UNKNOWN,
        reply_markup=await get_reply_keyboard([HELP_BUTTON, REFILL_BALANCE])
    )
