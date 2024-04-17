import logging

from aiogram import Router, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.core.messages import AnswerMessage as answer_messages
from src.core.states import UserState
from src.handlers.user import create_user_handler
from src.keyboards.constants import GET_VERIFY_CODE_BUTTON_LIST
from src.keyboards.inline import get_inline_keyboard
from src.schemas.user import TgUserSchema
from src.service.user import UserService

router = Router()


@router.message(CommandStart(), StateFilter(None))
async def cmd_start_handler(
        message: Message,
        state: FSMContext,
) -> None:
    await state.set_state(UserState.check_email)

    await message.answer(
        text=answer_messages.GREETING,
    )


@router.message(F.text.regexp(r"\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*"), UserState.check_email)
async def check_user_by_email_handler(
        message: Message,
        state: FSMContext,
        user_service: UserService,
        tg_user_schema: TgUserSchema,
) -> None:
    is_user_exist = await user_service.check_user_exist_by_email(email=message.text.lower().strip())

    if is_user_exist:
        return await create_user_handler(message, state, user_service, tg_user_schema)

    await message.answer(
        text=answer_messages.WRONG_MESSAGE.format(email=message.text),
    )


@router.message(F.text.startswith('/'), UserState.check_email)
async def check_email_help_command_handler(
        message: Message,
) -> None:

    await message.answer(
        text=answer_messages.EMAIL_REQUEST,
    )


@router.message(UserState.check_email)
async def check_user_by_email_handler(
        message: Message,
) -> None:
    await message.answer(
        text=answer_messages.WRONG_MESSAGE.format(email=message.text),
    )


@router.message(F.text.in_({'/help', 'help'}), UserState.user_created)
async def cmd_help_handler(
        message: Message,
        user_service: UserService,
        tg_user_schema: TgUserSchema,
) -> None:
    text = answer_messages.GENERATE_VERIFICATION_CODE
    buttons = await get_inline_keyboard(GET_VERIFY_CODE_BUTTON_LIST)

    await user_service.get_user(user_id=tg_user_schema.tg_user_id)

    await message.answer(
        text=text,
        reply_markup=buttons,
    )


@router.message(F.text.in_({'/help', 'help'}), UserState.verification_code_generated)
async def cmd_help_handler(
        message: Message,
        state: FSMContext,
        user_service: UserService,
        tg_user_schema: TgUserSchema,
) -> None:
    user = await user_service.get_user(user_id=tg_user_schema.tg_user_id)
    if not user:
        # text = answer_messages.NEED_VERIFY.format(verify_code=user.verification_code)
        await message.answer(
            text=answer_messages.GREETING,
        )
        await state.set_state(UserState.check_email)

    else:
        await message.answer(
            text=answer_messages.INFO,
        )
        await state.set_state(UserState.verification_code_generated)


@router.message(F.text.in_({'/help', 'help'}))
async def cmd_help_handler(message: Message,
                           state: FSMContext,
                           user_service: UserService,
                           tg_user_schema: TgUserSchema,
                           ) -> None:
    user = await user_service.get_user(user_id=tg_user_schema.tg_user_id)
    if not user:
        # text = answer_messages.NEED_VERIFY.format(verify_code=user.verification_code)
        await message.answer(
            text=answer_messages.GREETING,
        )
        await state.set_state(UserState.check_email)

    else:
        await message.answer(
            text=answer_messages.INFO,
        )
        await state.set_state(UserState.verification_code_generated)


