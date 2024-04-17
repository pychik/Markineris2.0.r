from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from src.core.messages import AnswerMessage as answer_messages
from src.core.states import UserState
from src.keyboards.constants import GET_VERIFY_CODE_BUTTON_LIST
from src.keyboards.inline import get_inline_keyboard
from src.schemas.user import TgUserSchema
from src.service.user import UserService

router = Router()


@router.callback_query(F.data == "generate_verification_code", UserState.user_created)
async def get_verify_code_handler(
        callback: CallbackQuery,
        state: FSMContext,
        user_service: UserService,
        tg_user_schema: TgUserSchema,
) -> None:
    user = await user_service.get_user(user_id=tg_user_schema.tg_user_id)

    if user:
        user = await user_service.generate_verification_code(user_id=tg_user_schema.tg_user_id)

        await callback.message.answer(
            text=answer_messages.VERIFY_CODE.format(verify_code=user.verification_code),
        )
        await callback.answer()
        await state.set_state(UserState.verification_code_generated)
    else:
        await callback.message.answer(
            text=answer_messages.RETRY_VERIFY,
        )
        await callback.answer()
        await state.clear()


async def create_user_handler(
        message: Message,
        state: FSMContext,
        user_service: UserService,
        tg_user_schema: TgUserSchema,
) -> None:
    await user_service.get_or_create(tg_user_schema)

    buttons = await get_inline_keyboard(GET_VERIFY_CODE_BUTTON_LIST)

    await message.answer(
        text=answer_messages.PUSH_VERIFY_BUTTON,
        reply_markup=buttons
    )
    await state.set_state(UserState.user_created)
