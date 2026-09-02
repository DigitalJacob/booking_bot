from aiogram.fsm.state import State, StatesGroup


class LangSG(StatesGroup):
    lang = State()


class BookingSG(StatesGroup):
    choosing_service = State()
    choosing_day = State()
    choosing_slot = State()
    confirming = State()


class AddSlotSG(StatesGroup):
    date = State()
    start_time = State()
    duration = State()


class AddServiceSG(StatesGroup):
    title = State()
    duration = State()
    price = State()
