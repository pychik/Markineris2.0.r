from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.types.input_file import BufferedInputFile

from src.core.config import settings
from src.core.messages import UserMessages
from src.core.states import UserState
from src.gateways.db.models.base import TransactionTypes
from src.handlers.utils import check_user_existent_and_update_state_data, clear_state_data
from src.infrastructure.client import BaseClient
from src.infrastructure.logger import logger
from src.infrastructure.utils import download_bill_img, get_qr_code, FileSizeError, FileExtensionError
from src.keyboards.buttons import (
    MAIN_FUNCTIONS,
    CANCEL_BUTTON,
    NO_PROMO_INLINE_BUTTON,
    CANCEL_INLINE_BUTTON,
    HELP_BUTTON,
)
from src.keyboards.inline import get_inline_keyboard
from src.keyboards.inline_events_data import NO_PROMO_CODE
from src.keyboards.keyboard_events_data import REFILL_BALANCE_COMMAND_TEXT
from src.keyboards.reply import get_reply_keyboard
from src.schemas.account_refill_balance import (
    PromoCodeIn,
    TransactionCreateOut,
    RequisiteIn, RequisiteType, PromoCodeOut,
)
from src.schemas.user import TgUserSchema
from src.service.user import UserService

router = Router()


@router.message(F.text == REFILL_BALANCE_COMMAND_TEXT, UserState.verification_code_generated)
async def start_transaction_of_account_refill_balance_first_time_handler(
        message: Message,
        state: FSMContext,
        user_service: UserService,
        tg_user_schema: TgUserSchema,
        client: BaseClient,
) -> None:
    """
    Обрабатывает первый запрос на пополнение баланса через телеграм,
    проверяем существует ли пользователь и его верификацию.

    Args:
        message (Message): Объект полученного обновления.
        state (FSMContext): Объект машины состояний.
        user_service (UserService): Сервис для взаимодействия с пользователем.
        tg_user_schema (TgUserSchema): Схема с данными телеграм аккаунта пользователя.
        client (BaseClient): Базовый клиент для взаимодействия с API марка- сервис.

    Returns:

    """
    try:
        if not await check_user_existent_and_update_state_data(message, state, user_service, tg_user_schema):
            return
    except Exception as e:
        logger.exception("Ошибка старта пополнения баланса из состояния verification_code_generated.")
        return

    await state.set_state(UserState.start_transaction)
    await refill_balance_start_transaction(message, state, client)


@router.message(F.text == REFILL_BALANCE_COMMAND_TEXT, UserState.start_transaction)
async def start_transaction_of_account_refill_balance_repeat_handler(
        message: Message,
        state: FSMContext,
        user_service: UserService,
        tg_user_schema: TgUserSchema,
        client: BaseClient,
) -> None:
    """
    Обрабатывает повторный запрос на пополнение,
    пользователь точно существует и верифицирован, иначе сюда не попадет.

    Args:
        message (Message): Объект полученного обновления.
        state (FSMContext): Объект машины состояний.
        user_service (UserService): Сервис для взаимодействия с пользователем.
        tg_user_schema (TgUserSchema): Схема с данными телеграм аккаунта пользователя.
        client (BaseClient): Базовый клиент для взаимодействия с API марка- сервис.

    Returns:

    """
    state_data = await state.get_data()

    if (
            state_data.get(settings.FLASK_USER_ID_STORAGE_KEY) is None or
            state_data.get(settings.TG_CHAT_ID_STORAGE_KEY) is None
    ):
        try:
            if not await check_user_existent_and_update_state_data(message, state, user_service, tg_user_schema):
                return
        except Exception as e:
            logger.exception("Ошибка старта пополнения баланса из состояния start_transaction.")
            return

    await refill_balance_start_transaction(message, state, client)


@router.message(UserState.amount_waiting)
async def amount_of_money_handler(
        message: Message,
        state: FSMContext,
) -> None:
    """ Обрабатывает введенную пользователем сумму. """
    try:
        amount_of_money = float(message.text)
    except ValueError:
        await message.answer(
            text=UserMessages.ENTER_INCORRECT_AMOUNT_OF_MONEY,
            reply_markup=await get_reply_keyboard([CANCEL_BUTTON]),
        )
    else:
        await state.update_data({settings.AMOUNT_OF_MONEY_STORAGE_KEY: amount_of_money})
        await message.answer(
            text=UserMessages.ENTER_PROMO_CODE,
            reply_markup=await get_inline_keyboard([NO_PROMO_INLINE_BUTTON, CANCEL_INLINE_BUTTON]),
        )
        await state.set_state(UserState.promo_waiting)


@router.callback_query(F.data == NO_PROMO_CODE, UserState.promo_waiting)
async def no_promo_code_callback_handler(
        callback: CallbackQuery,
        state: FSMContext,
) -> None:
    """ Обрабатывает событие когда пользователь нажал на инлайн кнопку NO_PROMO_CODE. """
    await callback.message.answer(
        text=UserMessages.SEND_RECEIPT_PHOTO,
        reply_markup=await get_reply_keyboard([CANCEL_BUTTON]),
    )
    await state.update_data({
        settings.PROMO_AMOUNT_STORAGE_KEY: 0,
        settings.PROMO_INFO_STORAGE_KEY: "",
    })
    await state.set_state(UserState.photo_waiting)
    await callback.answer()


@router.message(UserState.promo_waiting)
async def promo_code_handler(
        message: Message,
        state: FSMContext,
        client: BaseClient
) -> None:
    """
    Обрабатывает промо код, который пользователь ввел.

    Args:
        message (Message): Объект полученного обновления.
        state (FSMContext): Объект машины состояний.
        client (BaseClient): Базовый клиент для взаимодействия с API марка- сервис.

    Returns:

    """
    state_data = await state.get_data()
    flask_user_id = state_data.get(settings.FLASK_USER_ID_STORAGE_KEY)
    amount_of_money = state_data.get(settings.AMOUNT_OF_MONEY_STORAGE_KEY)

    promo = message.text
    try:
        payload = PromoCodeOut(code=promo, user_id=flask_user_id)
        validated_promo: PromoCodeIn = await client.check_promo_code_for_existence(payload.model_dump())
        if validated_promo.status_code == 200:
            await state.update_data({settings.PROMO_AMOUNT_STORAGE_KEY: validated_promo.amount})
            await state.update_data({settings.PROMO_CODE_ID_STORAGE_KEY: validated_promo.promo_id})
            await state.update_data(
                {settings.PROMO_INFO_STORAGE_KEY: f"{promo}: {amount_of_money} + {validated_promo.amount}"},
            )
            await message.answer(
                text=f"{UserMessages.PROMO_CODE_VALIDATE_SUCCESS}\n\n{UserMessages.SEND_RECEIPT_PHOTO}",
                reply_markup=await get_reply_keyboard([CANCEL_BUTTON]),
            )
            await state.set_state(UserState.photo_waiting)
        elif validated_promo.status_code == 404:
            await message.answer(
                text=UserMessages.PROMO_CODE_NOT_FOUND.format(promo=promo.replace('_', '\\_')),
                reply_markup=await get_inline_keyboard([NO_PROMO_INLINE_BUTTON, CANCEL_INLINE_BUTTON]),
            )
        elif validated_promo.status_code == 409:
            await message.answer(
                text=UserMessages.PROMO_ALREADY_USED.format(promo=promo.replace('_', '\\_')),
                reply_markup=await get_inline_keyboard([NO_PROMO_INLINE_BUTTON, CANCEL_INLINE_BUTTON]),
            )
        elif validated_promo.status_code == 500:
            await message.answer(
                text=UserMessages.INTERNAL_SERVER_ERROR,
                reply_markup=await get_inline_keyboard([CANCEL_INLINE_BUTTON]),
            )
    except Exception:
        logger.exception("Ошибка применения промокода")
        await message.answer(
            text=UserMessages.INTERNAL_SERVER_ERROR,
            reply_markup=await get_reply_keyboard(MAIN_FUNCTIONS),
        )


@router.message(UserState.photo_waiting)
async def photo_receipt_handler(
        message: Message,
        state: FSMContext,
        user_service: UserService,
        tg_user_schema: TgUserSchema,
        client: BaseClient,
) -> None:
    """
    Обрабатывает чек отправленный пользователем и делает запрос на создание транзакции в марка- сервис.

    Args:
        message (Message): Объект полученного обновления.
        state (FSMContext): Объект машины состояний.
        user_service (UserService): Сервис для взаимодействия с пользователем.
        tg_user_schema (TgUserSchema): Схема с данными телеграм аккаунта пользователя.
        client (BaseClient): Базовый клиент для взаимодействия с API марка- сервис.

    Returns:

    """
    try:
        filename = await download_bill_img(message, user_service=user_service, tg_user_schema=tg_user_schema)
    except (FileSizeError, FileExtensionError) as e:
        await message.answer(
            text=f"{UserMessages.PHOTO_PROCESSING_ERROR} Ошибка: {str(e)}",
            reply_markup=await get_reply_keyboard([HELP_BUTTON, CANCEL_BUTTON]),
        )
    except Exception:
        await message.answer(
            text=UserMessages.PHOTO_PROCESSING_ERROR,
            reply_markup=await get_reply_keyboard([HELP_BUTTON, CANCEL_BUTTON]),
        )
    else:
        if filename is not None:
            await state.update_data({settings.FILENAME_STORAGE_KEY: filename})
            await state.update_data({settings.TRANSACTION_TYPE_STORAGE_KEY: TransactionTypes.refill_balance.value})
            is_created = await create_transaction(client=client, state=state)
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

        else:
            await message.answer(
                text=UserMessages.INVALID_FORMAT_PHOTO,
                reply_markup=await get_reply_keyboard([HELP_BUTTON, CANCEL_BUTTON]),
            )


async def refill_balance_start_transaction(
        message: Message,
        state: FSMContext,
        client: BaseClient,
):
    """
    Функция старта пополнения баланса, получение и отправка реквизитов пользователю.

    Args:
        message (Message): Объект полученного обновления.
        state (FSMContext): Объект машины состояний.
        client (BaseClient): Базовый клиент для взаимодействия с API марка- сервис.

    Returns:

    """
    requisite: RequisiteIn = await client.get_current_requisites()
    if requisite.status_code == 200:

        await state.update_data({settings.REQUISITE_ID_STORAGE_KEY: requisite.requisite_id})

        if requisite.requisite_type.value == RequisiteType.qr_code.value:
            file_data = get_qr_code(requisite.requisite)
            if file_data:
                await message.answer_photo(
                    BufferedInputFile(file=file_data.data, filename=requisite.requisite),
                    caption=UserMessages.QR_CODE_REQUISITE_HELP_TEXT,
                )
            else:
                await message.answer(
                    text=UserMessages.INTERNAL_SERVER_ERROR,
                    reply_markup=await get_reply_keyboard([HELP_BUTTON, CANCEL_BUTTON])
                )
        else:
            await message.answer(
                text=UserMessages.NUMBER_REQUISITE_HELP_TEXT.format(requisite=requisite.requisite),
            )

        await message.answer(
            text=UserMessages.ENTER_AMOUNT_OF_MONEY,
            reply_markup=await get_reply_keyboard([CANCEL_BUTTON]),
        )

        await state.set_state(UserState.amount_waiting)

    elif requisite.status_code == 400:
        await message.answer(
            text=UserMessages.BAD_REQUEST_ERROR,
            reply_markup=await get_reply_keyboard(MAIN_FUNCTIONS),
        )
    elif requisite.status_code == 500:
        await message.answer(
            text=UserMessages.INTERNAL_SERVER_ERROR,
            reply_markup=await get_reply_keyboard(MAIN_FUNCTIONS)
        )


async def create_transaction(client: BaseClient, state: FSMContext) -> bool:
    """
    Функция формирует данные для запроса в API марка- сервис по созданию транзакции
    Args:
        client (BaseClient): Базовый клиент для взаимодействия с API марка- сервис.
        state (FSMContext): Объект машины состояний.

    Returns:

    """
    state_data = await state.get_data()
    is_bonus = state_data.get("is_bonus", False)
    transaction_create_data = TransactionCreateOut(
        **{
            "amount": (state_data.get(settings.AMOUNT_OF_MONEY_STORAGE_KEY)
                       + state_data.get(settings.PROMO_AMOUNT_STORAGE_KEY)),
            "status": 1,
            "promo_info": state_data.get(settings.PROMO_INFO_STORAGE_KEY),
            "user_id": state_data.get(settings.FLASK_USER_ID_STORAGE_KEY),
            "sa_id": state_data.get(settings.REQUISITE_ID_STORAGE_KEY),
            "bill_path": state_data.get(settings.FILENAME_STORAGE_KEY),
            "promo_id": state_data.get(settings.PROMO_CODE_ID_STORAGE_KEY, None),
            "transaction_type": state_data.get(
                settings.TRANSACTION_TYPE_STORAGE_KEY, TransactionTypes.refill_balance.value,
            ),
            "is_bonus": is_bonus,
        }
    )

    result = await client.create_transaction(data=transaction_create_data.model_dump())

    if result.status_code == 201:
        return True

    return False
