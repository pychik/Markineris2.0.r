from src.keyboards.inline_events_data import NO_PROMO_CODE
from src.keyboards.keyboard_events_data import (
    REFILL_BALANCE_COMMAND_TEXT,
    CANCEL_COMMAND_TEXT,
    START_COMMAND_TEXT,
    HELP_COMMAND_TEXT,
)

REFILL_BALANCE: dict[str, str] = {"text": REFILL_BALANCE_COMMAND_TEXT}
START_BUTTON: dict[str, str] = {"text": START_COMMAND_TEXT}
HELP_BUTTON: dict[str, str] = {"text": HELP_COMMAND_TEXT}
CANCEL_BUTTON: dict[str, str] = {"text": CANCEL_COMMAND_TEXT}

NO_PROMO_INLINE_BUTTON: dict[str, str] = {"text": "Нет промокода", "data": NO_PROMO_CODE}
CANCEL_INLINE_BUTTON: dict[str, str] = {"text": "Отмена", "data": CANCEL_COMMAND_TEXT}
GET_VERIFY_CODE_INLINE_BUTTON: dict[str, str] = {
    'text': 'Получить код верификации',
    'data': "generate_verification_code"
}
