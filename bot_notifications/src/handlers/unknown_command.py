from aiogram import Router
from aiogram.types import Message

from src.core.filters import IsCanEditBalanceFilter
from src.core.messages import UserMessages
from src.keyboards.buttons import HELP_BUTTON, MAIN_FUNCTIONS
from src.keyboards.reply import get_reply_keyboard

router = Router()


@router.message(~IsCanEditBalanceFilter())
async def unknown_command_with_filter_handler(
        message: Message,
) -> None:
    await message.answer(
        text="У вас нет доступа к этой функции, вам доступны только уведомления по статусам ваших заказов",
        reply_markup=None,
    )


@router.message()
async def unknown_command_handler(
        message: Message,
) -> None:
    await message.answer(
        text=UserMessages.UNKNOWN,
        reply_markup=await get_reply_keyboard([*MAIN_FUNCTIONS, HELP_BUTTON])
    )
