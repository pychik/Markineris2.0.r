from aiogram import Router
from aiogram.types import Message

from src.core.messages import AnswerMessage as answer_messages

router = Router()


@router.message()
async def unknown_command_handler(
        message: Message,
) -> None:
    await message.answer(
        text=answer_messages.UNKNOWN,
    )
