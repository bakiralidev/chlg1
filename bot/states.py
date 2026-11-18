from aiogram.fsm.state import State, StatesGroup


class RegistrationState(StatesGroup):
    waiting_consent = State()
    waiting_phone = State()
    waiting_full_name = State()
    waiting_level = State()
    waiting_age = State()
    waiting_region = State()
    waiting_source = State()
    waiting_interest = State()


class SupportState(StatesGroup):
    waiting_message = State()
