from aiogram.fsm.state import State, StatesGroup


class LangSG(StatesGroup):
    lang = State()


class BookingSG(StatesGroup):
    choosing_service = State()
    choosing_day = State()
    choosing_window = State()
    confirming = State()


class AddServiceSG(StatesGroup):
    title = State()
    duration = State()
    price = State()


class EditServiceSG(StatesGroup):
    title = State()
    duration = State()
    price = State()


class ProfileSG(StatesGroup):
    first_name = State()
    last_name = State()
    phone = State()


class ScheduleSG(StatesGroup):
    starts_time = State()
    ends_time = State()
    weekdays = State()


class TimeOffSG(StatesGroup):
    starts_date = State()
    ends_date = State()
