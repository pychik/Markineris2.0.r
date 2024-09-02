from aiogram.fsm.state import StatesGroup, State


class UserState(StatesGroup):
    check_email = State()
    # [check_email]
    # check_email -> user_created

    user_created = State()
    # [user_created]
    # user_created -> verification_code_generated

    verification_code_generated = State()
    # [verification_code_generated]
    # verification_code_generated -> start_transaction
    # verification_code_generated -> bonus_waiting

    start_transaction = State()
    # [start_transaction]
    # start_transaction -> amount_waiting
    # start_transaction -> bonus_waiting

    amount_waiting = State()
    # [amount_waiting]
    # amount_waiting -> promo_waiting

    promo_waiting = State()
    # [promo_waiting]
    # promo_waiting -> photo_waiting

    photo_waiting = State()
    # [photo_waiting]
    # photo_waiting -> start_transaction

    bonus_waiting = State()
    # [bonus_waiting]
    # bonus_waiting -> start_transaction
