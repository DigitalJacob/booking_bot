"""Unit tests for reschedule funnel helpers."""

from datetime import UTC, datetime, time
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from app.bot.handlers.common.appointment_cancel.common import BOOKINGS_NAV_KEYS
from app.bot.handlers.common.booking_steps import (
    RESCHEDULE_APPOINTMENT_ID_KEY,
    RESCHEDULE_ORIGINAL_STARTS_AT_KEY,
)
from app.bot.handlers.common.reschedule_steps import (
    clear_reschedule_state,
    start_reschedule_funnel,
)
from app.bot.states.states import MasterRescheduleSG
from app.bot.utils.hub_nav import HUB_MESSAGE_ID_KEY
from app.domain.enums import AppointmentStatus
from app.domain.models import MasterSettings, WorkingHours

from tests.factories import (
    CLIENT_ID,
    MASTER_ID,
    make_appointment,
    make_repos,
    make_service,
)

NOW = datetime(2026, 9, 10, 5, 0, tzinfo=UTC)
SLOT_09 = datetime(2026, 9, 10, 6, 0, tzinfo=UTC)
I18N = {
    "book_choose_month": "Choose a month:",
    "book_back_button": "← Back",
    "book_cancel_button": "Cancel",
    "reschedule_no_windows": "No other free times.",
    "reschedule_old_line": "Was: {when}",
}


def _settings(**kwargs) -> MasterSettings:
    base = {
        "master_user_id": MASTER_ID,
        "timezone": "Europe/Moscow",
        "slot_step_minutes": None,
        "gap_minutes": 0,
        "min_lead_minutes": 0,
        "booking_horizon_days": 1,
        "created_at": NOW,
        "updated_at": NOW,
    }
    base.update(kwargs)
    return MasterSettings(**base)


def _thursday_morning() -> WorkingHours:
    return WorkingHours(
        id=1,
        master_user_id=MASTER_ID,
        weekday=4,
        starts_time=time(9, 0),
        ends_time=time(12, 0),
        created_at=NOW,
    )


def _fsm() -> FSMContext:
    return FSMContext(
        storage=MemoryStorage(),
        key=StorageKey(bot_id=1, chat_id=1, user_id=MASTER_ID),
    )


def _message() -> MagicMock:
    message = MagicMock(spec=Message)
    message.message_id = 10
    message.edit_text = AsyncMock()
    message.answer = AsyncMock()
    return message


@pytest.mark.asyncio
async def test_start_reschedule_funnel_no_windows_keeps_state():
    # Only one slot in the day — filtering original start leaves nothing.
    repos = make_repos(
        services=[make_service(duration_minutes=180)],
        settings=_settings(booking_horizon_days=1),
        working_hours=[
            WorkingHours(
                id=1,
                master_user_id=MASTER_ID,
                weekday=4,
                starts_time=time(9, 0),
                ends_time=time(12, 0),
                created_at=NOW,
            ),
        ],
        appointments=[
            make_appointment(
                appointment_id=1,
                client_user_id=CLIENT_ID,
                starts_at=SLOT_09,
                ends_at=datetime(2026, 9, 10, 9, 0, tzinfo=UTC),  # 3h → fills day
                status=AppointmentStatus.CONFIRMED,
            ),
        ],
    )
    state = _fsm()
    await state.update_data({HUB_MESSAGE_ID_KEY: 99, "bookings_week_start": "keep"})
    message = _message()
    appointment = await repos.appointments.get_appointment(appointment_id=1)

    started = await start_reschedule_funnel(
        message=message,
        state=state,
        repos=repos,
        appointment=appointment,
        states=MasterRescheduleSG,
        for_master=True,
        i18n=I18N,
        bot_timezone="Europe/Moscow",
        schedule_mode="weekly",
        now=NOW,
    )

    assert started is False
    assert await state.get_state() is None
    data = await state.get_data()
    assert data[HUB_MESSAGE_ID_KEY] == 99
    assert data["bookings_week_start"] == "keep"
    message.edit_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_start_reschedule_funnel_enters_month():
    repos = make_repos(
        services=[make_service(duration_minutes=60)],
        settings=_settings(),
        working_hours=[_thursday_morning()],
        appointments=[
            make_appointment(
                appointment_id=1,
                starts_at=SLOT_09,
                ends_at=datetime(2026, 9, 10, 7, 0, tzinfo=UTC),
                status=AppointmentStatus.CONFIRMED,
            ),
        ],
    )
    state = _fsm()
    message = _message()
    appointment = await repos.appointments.get_appointment(appointment_id=1)

    started = await start_reschedule_funnel(
        message=message,
        state=state,
        repos=repos,
        appointment=appointment,
        states=MasterRescheduleSG,
        for_master=True,
        i18n=I18N,
        bot_timezone="Europe/Moscow",
        schedule_mode="weekly",
        now=NOW,
    )

    assert started is True
    assert await state.get_state() == MasterRescheduleSG.choosing_month.state
    data = await state.get_data()
    assert data[RESCHEDULE_APPOINTMENT_ID_KEY] == 1
    assert data[RESCHEDULE_ORIGINAL_STARTS_AT_KEY] == SLOT_09.isoformat()
    assert data["service_duration"] == 60
    message.edit_text.assert_awaited()


@pytest.mark.asyncio
async def test_clear_reschedule_state_keeps_bookings_nav():
    state = _fsm()
    await state.set_state(MasterRescheduleSG.choosing_month)
    await state.update_data(
        {
            HUB_MESSAGE_ID_KEY: 42,
            "hub_screen": "bookings",
            BOOKINGS_NAV_KEYS[0]: "2026-09-07",
            BOOKINGS_NAV_KEYS[1]: "2026-09",
            BOOKINGS_NAV_KEYS[2]: "2026-09-10",
            RESCHEDULE_APPOINTMENT_ID_KEY: 1,
            "service_id": 1,
        }
    )

    await clear_reschedule_state(state)

    assert await state.get_state() is None
    data = await state.get_data()
    assert data[HUB_MESSAGE_ID_KEY] == 42
    assert data["hub_screen"] == "bookings"
    assert data[BOOKINGS_NAV_KEYS[0]] == "2026-09-07"
    assert data[BOOKINGS_NAV_KEYS[1]] == "2026-09"
    assert data[BOOKINGS_NAV_KEYS[2]] == "2026-09-10"
    assert RESCHEDULE_APPOINTMENT_ID_KEY not in data
    assert "service_id" not in data
