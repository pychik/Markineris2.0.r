from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from src.core.config import settings
from src.core.messages import UserMessages
from src.core.states import UserState
from src.gateways.db.models.user import TgUser
from src.infrastructure.logger import logger
from src.keyboards.buttons import REFILL_BALANCE, CANCEL_BUTTON
from src.keyboards.reply import get_reply_keyboard
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
    """
    Обрабатывает события на нажатия инлайн кнопки generate_verification_code и состояние user_created.
    Берет существующий либо генерирует новый код верификации и отдает пользователю.

    Args:
        callback (CallbackQuery):
        state (FSMContext):
        user_service (UserService): Сервис для взаимодействия с пользователем.
        tg_user_schema (TgUserSchema): Схема с данными телеграм аккаунта пользователя.

    Returns:

    """
    try:
        user = await user_service.get_user(user_id=tg_user_schema.tg_user_id)
        if not user:
            await callback.message.answer(text=UserMessages.RETRY_VERIFY)
            await state.clear()
            await callback.answer()
            return

        if user.flask_user_id is None:
            verify_code = await user_service.get_verification_code(user)
            await callback.message.answer(
                text=UserMessages.VERIFY_CODE.format(verify_code=verify_code),
                reply_markup=await get_reply_keyboard([REFILL_BALANCE, CANCEL_BUTTON]),
            )
            await state.set_state(UserState.verification_code_generated)
            await callback.answer()
            return

        await state.update_data({settings.FLASK_USER_ID_STORAGE_KEY: user.flask_user_id})
        await state.update_data({settings.TG_CHAT_ID_STORAGE_KEY: user.tg_chat_id})
        await state.set_state(UserState.start_transaction)
    except Exception as e:
        logger.exception("Ошибка при попытке выдать пользователю верфикационный код")

    await callback.answer()


async def create_user_handler(
        user_service: UserService,
        tg_user_schema: TgUserSchema,
) -> TgUser:
    """
    Получает пользователя из базы бота если он там есть иначе создает пользователя и отдает.

    Args:
        user_service (UserService): Сервис для взаимодействия с пользователем.
        tg_user_schema (TgUserSchema): Схема с данными телеграм аккаунта пользователя.

    Returns:

    """
    try:
        return await user_service.get_or_create(tg_user_schema)
    except Exception as e:
        logger.exception("Ошибка при создать/получить пользователя из базы бота")
