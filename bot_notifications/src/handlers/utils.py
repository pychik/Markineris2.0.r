from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.core.config import settings
from src.core.messages import UserMessages
from src.core.states import UserState
from src.keyboards.buttons import MAIN_FUNCTIONS, CANCEL_BUTTON
from src.keyboards.reply import get_reply_keyboard
from src.schemas.user import TgUserSchema
from src.service.user import UserService
from src.infrastructure.logger import logger


async def check_user_existent_and_update_state_data(
        message: Message,
        state: FSMContext,
        user_service: UserService,
        tg_user_schema: TgUserSchema,
) -> bool:
    """
    Функция проверяет есть ли пользователь в базе бота и обновляет данные в хранилище.

    Если пользователя нет, то полностью обновляет состояние и предлагает пользователю пройти верификацию.
    Если пользователь существует, но не верифицирован, то отправляет код верификации
    и сменяет статус на verification_code_generated.
    Если пользователь есть и верифицирован, то обновляет его Маркинерис ID и Телеграм чат ID в хранилище.

    Args:
        message (Message): Объект полученного обновления.
        state (FSMContext): Объект машины состояний.
        user_service (UserService): Сервис для взаимодействия с пользователем.
        tg_user_schema (TgUserSchema): Схема с данными телеграм аккаунта пользователя.

    Returns:
        bool:
    """
    try:
        user = await user_service.get_user(user_id=tg_user_schema.tg_user_id)
        if not user:
            await message.answer(text=UserMessages.RETRY_VERIFY)
            await state.clear()
            return False

        if user.flask_user_id is None:
            verify_code = await user_service.get_verification_code(user)
            await message.answer(
                text=UserMessages.NEED_VERIFY.format(verify_code=verify_code),
                reply_markup=await get_reply_keyboard([*MAIN_FUNCTIONS, CANCEL_BUTTON]),
            )
            await state.set_state(UserState.verification_code_generated)
            return False

        await state.update_data({settings.FLASK_USER_ID_STORAGE_KEY: user.flask_user_id})
        await state.update_data({settings.TG_CHAT_ID_STORAGE_KEY: user.tg_chat_id})
        await state.set_state(UserState.start_transaction)

        return True
    except Exception:
        logger.exception("Ошибка проверки и обновления данных пользователя в хранилище")


async def clear_state_data(state: FSMContext):
    """ Функция очищает состояние и устанавливает новое состояние start_transaction. """
    current_data = await state.get_data()
    data_for_update = {}

    flask_user_id = current_data.get(settings.FLASK_USER_ID_STORAGE_KEY)
    tg_chat_id = current_data.get(settings.TG_CHAT_ID_STORAGE_KEY)

    if flask_user_id:
        data_for_update.update({settings.FLASK_USER_ID_STORAGE_KEY: flask_user_id})
    if tg_chat_id:
        data_for_update.update({settings.TG_CHAT_ID_STORAGE_KEY: tg_chat_id})

    await state.clear()
    await state.update_data(data_for_update)
    await state.set_state(UserState.start_transaction)
