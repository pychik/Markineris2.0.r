from aiogram import Router, F
from aiogram.filters import CommandStart, StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from src.core.config import settings
from src.core.filters import TextFilter
from src.core.messages import UserMessages
from src.core.states import UserState
from src.handlers.utils import check_user_existent_and_update_state_data
from src.handlers.utils import clear_state_data
from src.handlers.verification import create_user_handler
from src.infrastructure.logger import logger
from src.keyboards.buttons import (
    GET_VERIFY_CODE_INLINE_BUTTON,
    CANCEL_BUTTON,
    NO_PROMO_INLINE_BUTTON,
    CANCEL_INLINE_BUTTON,
    START_BUTTON,
    HELP_BUTTON,
    MAIN_FUNCTIONS,
)
from src.keyboards.inline import get_inline_keyboard
from src.keyboards.keyboard_events_data import CANCEL_COMMAND_TEXT, HELP_COMMAND_TEXT, START_COMMAND_TEXT
from src.keyboards.reply import get_reply_keyboard
from src.schemas.user import TgUserSchema
from src.service.user import UserService

router = Router()


@router.message(or_f(CommandStart(), TextFilter(START_COMMAND_TEXT)), StateFilter(None))
async def cmd_start_handler(message: Message, state: FSMContext) -> None:
    """ Обработчик для новых пользователей или тех у кого протухло состояние. """
    await state.set_state(UserState.check_email)

    await message.answer(
        text=UserMessages.GREETING,
        reply_markup=await get_reply_keyboard([HELP_BUTTON]),
    )


@router.message(StateFilter(None))
async def user_with_none_state_handler(message: Message) -> None:
    """ Обработчик для любых событий от пользователя у которого нет активного состояния в хранилище. """
    await message.answer(
        text=UserMessages.RETRY_VERIFY,
        reply_markup=await get_reply_keyboard([START_BUTTON, HELP_BUTTON]),
    )


@router.message(F.text.regexp(r"\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*"), UserState.check_email)
async def check_user_by_email_handler(
        message: Message,
        state: FSMContext,
        user_service: UserService,
        tg_user_schema: TgUserSchema,
) -> None:
    """
    Обработчик срабатывает для проверки почты в базе Маркинериса и создает запись для пользователя в базе бота.

    Args:
        message (Message):
        state (FSMContext):
        user_service (UserService): Сервис для взаимодействия с пользователем.
        tg_user_schema (TgUserSchema): Схема с данными телеграм аккаунта пользователя.

    Returns:

    """
    try:
        flask_app_user = await user_service.check_user_exist_by_email(email=message.text.strip())

        if flask_app_user:
            user = await create_user_handler(user_service, tg_user_schema)

            if user:
                if flask_app_user.id == user.flask_user_id:
                    await message.answer(
                        text=UserMessages.INFO_VERIFICATION_CODE_GENERATED,
                        reply_markup=await get_reply_keyboard([*MAIN_FUNCTIONS, HELP_BUTTON]),
                    )
                    await state.update_data({settings.FLASK_USER_ID_STORAGE_KEY: user.flask_user_id})
                    await state.update_data({settings.TG_CHAT_ID_STORAGE_KEY: user.tg_chat_id})
                    await state.set_state(UserState.start_transaction)
                    return

                user.flask_user_id = None
                await message.answer(
                    text=UserMessages.PUSH_VERIFY_BUTTON,
                    reply_markup=await get_inline_keyboard(
                        [GET_VERIFY_CODE_INLINE_BUTTON, CANCEL_INLINE_BUTTON],
                        rows=1,
                    ),
                )
                await state.set_state(UserState.user_created)
                return

        await message.answer(
            text=UserMessages.USER_NOT_FOUND.format(email=message.text),
            reply_markup=await get_reply_keyboard([HELP_BUTTON]),
        )
    except Exception as e:
        logger.exception("Ошибка проверки пользователя по email и создание.")


@router.message(or_f(F.text.startswith('/'), TextFilter(HELP_COMMAND_TEXT)), UserState.check_email)
async def check_email_state_any_command_handler(message: Message) -> None:
    """ Обрабатывает события с командами в состоянии check_email. """
    await message.answer(
        text=UserMessages.EMAIL_REQUEST,
    )


@router.message(UserState.check_email)
async def check_email_state_any_message_handler(message: Message) -> None:
    """ Обрабатывает любые события с состоянием check_email. """
    await message.answer(
        text=UserMessages.INVALID_EMAIL_ADDRESS,
    )


@router.message(F.text.in_({HELP_COMMAND_TEXT, '/help'}), UserState.user_created)
async def user_created_state_help_command_handler(
        message: Message,
) -> None:
    """ Обрабатывает команду help в состоянием user_created. """
    await message.answer(
        text=UserMessages.GENERATE_VERIFICATION_CODE,
        reply_markup=await get_inline_keyboard([GET_VERIFY_CODE_INLINE_BUTTON, CANCEL_INLINE_BUTTON], rows=1),
    )


@router.message(F.text.in_({HELP_COMMAND_TEXT, '/help'}), UserState.verification_code_generated)
async def verification_code_generated_state_help_command_handler(
        message: Message,
        state: FSMContext,
        user_service: UserService,
        tg_user_schema: TgUserSchema,
) -> None:
    """
    Обрабатывает команду help в состоянием verification_code_generated.

    Args:
        message (Message):
        state (FSMContext):
        user_service (UserService): Сервис для взаимодействия с пользователем.
        tg_user_schema (TgUserSchema): Схема с данными телеграм аккаунта пользователя.

    Returns:

    """
    try:
        if not await check_user_existent_and_update_state_data(message, state, user_service, tg_user_schema):
            return
    except Exception:
        logger.exception("Ошибка проверки пользователя из состояния verification_code_generated на команде help.")
        return

    await message.answer(
        text=UserMessages.INFO_VERIFICATION_CODE_GENERATED,
        bottons=await get_reply_keyboard([*MAIN_FUNCTIONS, CANCEL_BUTTON]),
    )


@router.message(F.text.in_({HELP_COMMAND_TEXT, '/help'}), UserState.start_transaction)
async def start_transaction_state_help_command_handler(
        message: Message,
) -> None:
    """ Обрабатывает команду help для состоянии start_transaction. """
    await message.answer(
        text=UserMessages.AVAILABLE_FUNCTIONS,
        reply_markup=await get_reply_keyboard(MAIN_FUNCTIONS),
    )


@router.message(F.text.in_({HELP_COMMAND_TEXT, '/help'}), UserState.amount_waiting)
async def amount_waiting_state_help_command_handler(
        message: Message,
) -> None:
    """ Обрабатывает команду help для состоянии amount_waiting. """
    await message.answer(
        text=UserMessages.ENTER_AMOUNT_OF_MONEY,
        reply_markup=await get_reply_keyboard([CANCEL_BUTTON]),
    )


@router.message(F.text.in_({HELP_COMMAND_TEXT, '/help'}), UserState.promo_waiting)
async def promo_waiting_state_help_command_handler(
        message: Message,
) -> None:
    """ Обрабатывает команду help для состоянии promo_waiting. """
    await message.answer(
        text=UserMessages.ENTER_PROMO_CODE,
        reply_markup=await get_inline_keyboard([NO_PROMO_INLINE_BUTTON, CANCEL_INLINE_BUTTON]),
    )


@router.message(F.text.in_({HELP_COMMAND_TEXT, '/help'}), UserState.bonus_waiting)
async def bonus_waiting_state_help_command_handler(
        message: Message,
) -> None:
    """ Обрабатывает команду help для состоянии bonus_waiting. """
    await message.answer(
        text=UserMessages.ENTER_BONUS_CODE,
        reply_markup=await get_inline_keyboard([CANCEL_INLINE_BUTTON]),
    )


@router.message(F.text.in_({HELP_COMMAND_TEXT, '/help'}), UserState.photo_waiting)
async def photo_waiting_state_help_command_handler(
        message: Message,
) -> None:
    """ Обрабатывает команду help для состоянии photo_waiting. """
    await message.answer(
        text=UserMessages.SEND_RECEIPT_PHOTO_HELP_TEXT,
        reply_markup=await get_reply_keyboard([CANCEL_BUTTON]),
    )


@router.message(F.text.in_({HELP_COMMAND_TEXT, '/help'}), StateFilter(None))
async def none_state_help_command_handler(message: Message) -> None:
    """ Обрабатывает команду help когда состояние равно None. """
    await message.answer(
        text=UserMessages.NO_STATE_HELP_MESSAGE,
        reply_markup=await get_reply_keyboard([START_BUTTON]),
    )


@router.message(F.text.in_({CANCEL_COMMAND_TEXT, "/cancel"}), UserState.start_transaction)
async def start_transaction_state_cancel_handler(
        message: Message,
        state: FSMContext,
) -> None:
    """ Обрабатывает команду cancel и отмена из состояния start_transaction. """
    await message.answer(
        text=UserMessages.ALREADY_IN_MAIN_MENU,
        reply_markup=await get_reply_keyboard(MAIN_FUNCTIONS),
    )
    await clear_state_data(state)


@router.message(
    F.text.in_({CANCEL_COMMAND_TEXT, "/cancel"}),
    or_f(UserState.verification_code_generated, UserState.user_created),
)
async def verification_code_generated_or_user_created_states_cancel_handler(
        message: Message,
        state: FSMContext,
        user_service: UserService,
        tg_user_schema: TgUserSchema,
) -> None:
    """ Обрабатывает команду cancel и отмена из состояния verification_code_generated или user_created. """

    try:
        await user_service.delete_user(tg_user_schema.tg_user_id)
    except Exception:
        logger.exception("Ошибка удаления пользователя при отмене верификации по cancel команде")
        await message.answer(
            text=UserMessages.CANT_CANCEL,
        )
        return

    await message.answer(
        text=UserMessages.VERIFY_CANCEL,
        reply_markup=await get_reply_keyboard([HELP_BUTTON]),
    )
    await state.clear()
    await state.set_state(UserState.check_email)


@router.message(F.text.in_({CANCEL_COMMAND_TEXT, "/cancel"}))
async def any_state_cancel_handler(
        message: Message,
        state: FSMContext,
) -> None:
    """ Обрабатывает команду cancel и отмена из любого состояния. """
    await message.answer(
        text=UserMessages.CANCEL,
        reply_markup=await get_reply_keyboard(MAIN_FUNCTIONS),
    )
    await clear_state_data(state)


@router.callback_query(F.data == CANCEL_COMMAND_TEXT, UserState.user_created)
async def callback_user_created_state_cancel_handler(
        callback: CallbackQuery,
        state: FSMContext,
        user_service: UserService,
        tg_user_schema: TgUserSchema,
) -> None:
    """ Обрабатывает событие по нажатию на инлайн кнопку 'Отмена' из состояния user_created. """
    try:
        await user_service.delete_user(tg_user_schema.tg_user_id)
    except Exception:
        logger.exception("Ошибка удаления пользователя при отмене верификации по cancel команде")
        await callback.message.answer(
            text=UserMessages.CANT_CANCEL,
        )
        return

    await callback.message.answer(
        text=UserMessages.VERIFY_CANCEL,
        reply_markup=await get_reply_keyboard([HELP_BUTTON]),
    )
    await state.clear()
    await state.set_state(UserState.check_email)
    await callback.answer()


@router.callback_query(F.data == CANCEL_COMMAND_TEXT)
async def callback_cancel_handler(
        callback: CallbackQuery,
        state: FSMContext,
) -> None:
    """ Обрабатывает событие по нажатию на инлайн кнопку 'Отмена' из любого состояния. """
    await callback.message.answer(
        text=UserMessages.CANCEL,
        reply_markup=await get_reply_keyboard(MAIN_FUNCTIONS),
    )
    await clear_state_data(state)
    await callback.answer()
