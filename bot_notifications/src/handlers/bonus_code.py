from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import or_f

from src.core.config import settings
from src.core.filters import IsCanEditBalanceFilter
from src.core.messages import UserMessages
from src.core.states import UserState
from src.gateways.db.models.base import TransactionTypes
from src.handlers.account_refill_balance import create_transaction
from src.handlers.utils import check_user_existent_and_update_state_data, clear_state_data
from src.infrastructure.client import BaseClient
from src.infrastructure.utils import generate_verification_code
from src.keyboards.buttons import (
    CANCEL_INLINE_BUTTON,
    MAIN_FUNCTIONS,
    HELP_BUTTON,
    CANCEL_BUTTON,
)
from src.keyboards.inline import get_inline_keyboard
from src.keyboards.keyboard_events_data import BONUS_CODE_COMMAND_TEXT
from src.keyboards.reply import get_reply_keyboard
from src.schemas.account_refill_balance import (
    PromoCodeIn, PromoCodeOut, RequisiteIn,
)
from src.schemas.user import TgUserSchema
from src.service.user import UserService
from src.infrastructure.logger import logger

router = Router()
router.message.filter(IsCanEditBalanceFilter())
router.callback_query.filter(IsCanEditBalanceFilter())


@router.message(
    F.text == BONUS_CODE_COMMAND_TEXT,
    or_f(UserState.start_transaction, UserState.verification_code_generated),
)
async def start_use_bonus_code_handler(
        message: Message,
        state: FSMContext,
        user_service: UserService,
        tg_user_schema: TgUserSchema,
) -> None:
    """
    Обрабатывает запрос на пополнение баланса через телеграм бонус кодом,
    проверяем существует ли пользователь и его верификацию.

    Args:
        message (Message): Объект полученного обновления.
        state (FSMContext): Объект машины состояний.
        user_service (UserService): Сервис для взаимодействия с пользователем.
        tg_user_schema (TgUserSchema): Схема с данными телеграм аккаунта пользователя.
    Returns:

    """
    current_state = await state.get_state()
    state_data = await state.get_data()

    if (
            state_data.get(settings.FLASK_USER_ID_STORAGE_KEY) is None or
            state_data.get(settings.TG_CHAT_ID_STORAGE_KEY) is None
    ):
        try:
            if not await check_user_existent_and_update_state_data(message, state, user_service, tg_user_schema):
                return
        except Exception:
            logger.exception(f"Ошибка старта пополнения баланса из состояния {current_state}.")
            return

    await state.set_state(UserState.bonus_waiting)
    await message.answer(
        text=UserMessages.ENTER_BONUS_CODE,
        reply_markup=await get_reply_keyboard([HELP_BUTTON, CANCEL_BUTTON]),
    )


@router.message(UserState.bonus_waiting)
async def bonus_code_handler(
        message: Message,
        state: FSMContext,
        client: BaseClient,
) -> None:
    # todo: Дока
    """ Обрабатывает введенный пользователем бонус код. """
    state_data = await state.get_data()
    flask_user_id = state_data.get(settings.FLASK_USER_ID_STORAGE_KEY)
    amount_of_money = 0

    requisite: RequisiteIn = await client.get_current_requisites()

    if requisite.status_code == 200:
        req_id = requisite.requisite_id
    else:
        logger.exception(f"Ошибка при получении сервисного счета, статус код - {requisite.status_code}")
        await internal_error_handler(message, state)
        return

    await state.update_data({
        settings.REQUISITE_ID_STORAGE_KEY: req_id,
        "is_bonus": True,
        settings.AMOUNT_OF_MONEY_STORAGE_KEY: 0,
        settings.FILENAME_STORAGE_KEY: generate_verification_code(),
    })

    bonus_code = message.text
    try:
        payload = PromoCodeOut(code=bonus_code, user_id=flask_user_id, is_bonus=True)
        validated_bonus_code: PromoCodeIn = await client.check_promo_code_for_existence(payload.model_dump())
        if validated_bonus_code.status_code == 200:
            await state.update_data({settings.PROMO_AMOUNT_STORAGE_KEY: validated_bonus_code.amount})
            await state.update_data({settings.PROMO_CODE_ID_STORAGE_KEY: validated_bonus_code.promo_id})
            await state.update_data({settings.TRANSACTION_TYPE_STORAGE_KEY: TransactionTypes.promo.value})
            await state.update_data({settings.PROMO_INFO_STORAGE_KEY: (
                f"Бонус код - {bonus_code}: "
                f"{amount_of_money} + {validated_bonus_code.amount}"
            )},
            )
            # запрос на создание транзакции на пополнения баланса по бонус коду
            is_created = await create_transaction(client, state)
            if is_created:
                await message.answer(
                    text=UserMessages.TRANSACTION_CREATE_SUCCESSFULLY,
                    reply_markup=await get_reply_keyboard(MAIN_FUNCTIONS),
                )
            else:
                await message.answer(
                    text=UserMessages.TRANSACTION_CREATE_FAILED,
                    reply_markup=await get_reply_keyboard(MAIN_FUNCTIONS),
                )
            await clear_state_data(state)

        elif validated_bonus_code.status_code == 404:
            await message.answer(
                text=UserMessages.BONUS_CODE_NOT_FOUND.format(bonus_code=bonus_code.replace('_', '\\_')),
                reply_markup=await get_inline_keyboard([CANCEL_INLINE_BUTTON]),
            )
        elif validated_bonus_code.status_code == 409:
            await message.answer(
                text=UserMessages.BONUS_CODE_ALREADY_USED.format(bonus_code=bonus_code.replace('_', '\\_')),
                reply_markup=await get_inline_keyboard([CANCEL_INLINE_BUTTON]),
            )
        elif validated_bonus_code.status_code == 500:
            await internal_error_handler(message, state)
    except Exception:
        logger.exception("Ошибка применения бонус кода")
        await internal_error_handler(message, state)


async def internal_error_handler(message: Message, state: FSMContext):
    await clear_state_data(state)
    await message.answer(
        text=UserMessages.INTERNAL_SERVER_ERROR,
        reply_markup=await get_reply_keyboard(MAIN_FUNCTIONS),
    )
