from aiogram.fsm.state import StatesGroup, State


class UserState(StatesGroup):
    check_email = State()
    user_created = State()
    verification_code_generated = State()
