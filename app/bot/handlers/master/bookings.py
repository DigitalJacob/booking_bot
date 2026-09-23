from contextlib import suppress
from datetime import date, datetime, time, timedelta, timezone

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.filters.filters import UserRoleFilter
from app.bot.handlers.common.hub import return_from_list
from app.bot.keyboards.bookings import (
    MasterAppointmentCallback,
    get_master_booking_card_kb,
    get_master_bookings_day_kb,
    get_master_bookings_week_kb,
    is_slot_past,
)
from app.bot.keyboards.schedule import WEEKDAY_KEYS
from app.bot.utils.format import (
    client_contact,
    combine_local,
    format_dt,
    local_week_bounds,
    status_label,
    to_local,
)
from app.bot.utils.hub_nav import HUB_MESSAGE_ID_KEY, show_hub
from app.bot.utils.hub_registry import register
from app.bot.utils.notify import notify_appointment, supersede_master_action_push
from app.domain.enums import AppointmentStatus, UserRole
from app.domain.exceptions import (
    AppointmentNotFound,
    ForbiddenBookingAction,
    InvalidAppointmentStatus,
)
from app.domain.models import Appointment, User
from app.domain.services.booking import BookingService
from app.infrastructure.database.repositories import Repositories


bookings_router = Router(name="master_bookings")
bookings_router.message.filter(UserRoleFilter(UserRole.MASTER))
bookings_router.callback_query.filter(UserRoleFilter(UserRole.MASTER))

_BUTTON_LABEL_MAX = 64
_WEEK_START_KEY = "bookings_week_start"
_DAY_KEY = "bookings_day"


def _parse_iso_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _week_range_label(week_start: date) -> str:
    last = week_start + timedelta(days=6)
    return f"{week_start.strftime('%d.%m')}–{last.strftime('%d.%m')}"


def _day_label(*, day: date, i18n: dict[str, str]) -> str:
    weekday = i18n.get(WEEKDAY_KEYS[day.isoweekday()])
    return f"{weekday} {day.strftime('%d.%m')}"


def _truncate_button(text: str) -> str:
    if len(text) > _BUTTON_LABEL_MAX:
        return text[: _BUTTON_LABEL_MAX - 1] + "…"
    return text


def _active_only(appointments: list[Appointment]) -> list[Appointment]:
    return [
        a for a in appointments
        if a.status in (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED)
    ]


def _counts_by_local_day(
        *,
        appointments: list[Appointment],
        bot_timezone: str,
) -> dict[date, int]:
    counts: dict[date, int] = {}
    for appointment in appointments:
        day = to_local(appointment.starts_at, bot_timezone).date()
        counts[day] = counts.get(day, 0) + 1
    return counts


async def _load_week_active(
        *,
        repos: Repositories,
        user: User,
        bot_timezone: str,
        week_start: date | None,
) -> tuple[date, list[Appointment], bool]:
    from_dt, to_dt, week_start = local_week_bounds(
        bot_timezone,
        week_start=week_start,
    )
    appointments = await repos.appointments.list_by_master(
        master_user_id=user.user_id,
        from_dt=from_dt,
        to_dt=to_dt,
    )
    active = _active_only(appointments)
    _, _, current_week_start = local_week_bounds(bot_timezone)
    return week_start, active, week_start == current_week_start


async def show_master_bookings_week(
        *,
        message: Message,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
        edit: bool,
) -> None:
    data = await state.get_data()
    week_start = _parse_iso_date(data.get(_WEEK_START_KEY))
    week_start, active, is_current_week = await _load_week_active(
        repos=repos,
        user=user,
        bot_timezone=bot_timezone,
        week_start=week_start,
    )
    await state.update_data(
        {
            _WEEK_START_KEY: week_start.isoformat(),
            _DAY_KEY: None,
        }
    )
    week_label = _week_range_label(week_start)
    by_day = _counts_by_local_day(
        appointments=active,
        bot_timezone=bot_timezone,
    )

    if not by_day:
        text = i18n.get("master_bookings_empty").format(week=week_label)
        day_buttons: list[tuple[date, str]] = []
    else:
        lines: list[str] = []
        day_buttons = []
        for day in sorted(by_day):
            count = by_day[day]
            day_text = _day_label(day=day, i18n=i18n)
            day_line = i18n.get("master_bookings_day_button").format(
                day=day_text,
                count=count,
            )
            lines.append(day_line)
            day_buttons.append((day, _truncate_button(day_line)))
        text = (
            i18n.get("master_bookings_header").format(week=week_label)
            + "\n\n"
            + "\n".join(lines)
        )

    kb = get_master_bookings_week_kb(
        day_buttons=day_buttons,
        i18n=i18n,
        is_current_week=is_current_week,
    )
    if edit:
        await message.edit_text(text=text, reply_markup=kb)
    else:
        await message.answer(text=text, reply_markup=kb)


async def show_master_bookings_day(
        *,
        message: Message,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
        day: date,
        edit: bool,
) -> None:
    day_start = combine_local(day, time.min, bot_timezone)
    day_end = day_start + timedelta(days=1)
    appointments = await repos.appointments.list_by_master(
        master_user_id=user.user_id,
        from_dt=day_start,
        to_dt=day_end,
    )
    active = _active_only(appointments)
    await state.update_data({_DAY_KEY: day.isoformat()})
    day_text = _day_label(day=day, i18n=i18n)

    if not active:
        text = i18n.get("master_bookings_day_empty").format(day=day_text)
        kb = get_master_bookings_day_kb(
            appointments=[],
            labels={},
            i18n=i18n,
        )
    else:
        labels: dict[int, str] = {}
        lines: list[str] = []
        for appointment in active:
            service = await repos.services.get_service(
                service_id=appointment.service_id,
            )
            title = service.title if service else "?"
            local = to_local(appointment.starts_at, bot_timezone)
            slot_time = local.strftime("%H:%M")
            labels[appointment.id] = _truncate_button(
                i18n.get("master_bookings_slot_button").format(
                    time=slot_time,
                    title=title,
                )
            )
            lines.append(
                i18n.get("master_bookings_day_item").format(
                    time=slot_time,
                    title=title,
                    status=status_label(appointment.status, i18n),
                )
            )
        text = (
            i18n.get("master_bookings_day_header").format(day=day_text)
            + "\n\n"
            + "\n".join(lines)
        )
        kb = get_master_bookings_day_kb(
            appointments=active,
            labels=labels,
            i18n=i18n,
        )

    if edit:
        await message.edit_text(text=text, reply_markup=kb)
    else:
        await message.answer(text=text, reply_markup=kb)


async def _set_week_start(
        *,
        state: FSMContext,
        bot_timezone: str,
        delta_weeks: int = 0,
        to_current: bool = False,
) -> None:
    if to_current:
        _, _, week_start = local_week_bounds(bot_timezone)
    else:
        data = await state.get_data()
        week_start = _parse_iso_date(data.get(_WEEK_START_KEY))
        _, _, week_start = local_week_bounds(
            bot_timezone,
            week_start=week_start,
        )
        week_start = week_start + timedelta(weeks=delta_weeks)
    await state.update_data(
        {
            _WEEK_START_KEY: week_start.isoformat(),
            _DAY_KEY: None,
        }
    )


async def _show_booking_card(
        *,
        message: Message,
        state: FSMContext,
        appointment: Appointment,
        repos: Repositories,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    day = to_local(appointment.starts_at, bot_timezone).date()
    await state.update_data({_DAY_KEY: day.isoformat()})

    service = await repos.services.get_service(service_id=appointment.service_id)
    title = service.title if service else "?"
    client = await repos.users.get_user_by_id(user_id=appointment.client_user_id)
    client_name, client_phone = client_contact(client)
    now = datetime.now(timezone.utc)
    past = is_slot_past(slot_ends_at=appointment.ends_at, now=now)
    text_key = (
        "master_bookings_card_past" if past else "master_bookings_card"
    )
    text = i18n.get(text_key).format(
        when=format_dt(appointment.starts_at, bot_timezone),
        title=title,
        status=status_label(appointment.status, i18n),
        client_name=client_name,
        client_phone=client_phone,
    )
    await message.edit_text(
        text=text,
        reply_markup=get_master_booking_card_kb(
            appointment=appointment,
            i18n=i18n,
            now=now,
        ),
    )


async def _reject_if_slot_past(
        *,
        callback: CallbackQuery,
        repos: Repositories,
        appointment_id: int,
        i18n: dict[str, str],
) -> bool:
    """Return True if the handler should stop"""
    appointment = await repos.appointments.get_appointment(
        appointment_id=appointment_id,
    )
    if appointment is None:
        await callback.answer(
            text=i18n.get("master_action_failed"),
            show_alert=True,
        )
        return True

    if is_slot_past(
        slot_ends_at=appointment.ends_at,
        now=datetime.now(timezone.utc),
    ):
        await callback.answer(
            text=i18n.get("master_action_past"),
            show_alert=True,
        )
        with suppress(TelegramBadRequest):
            await callback.message.edit_reply_markup(reply_markup=None)
        return True
    return False


async def _disarm_stale_master_push(
        *,
        callback: CallbackQuery,
        bot: Bot,
        repos: Repositories,
        appointment_id: int,
        translations: dict,
        bot_timezone: str,
) -> None:
    """Turn a stale confirm/cancel push into status+OK or strip its keyboard."""
    appointment = await repos.appointments.get_appointment(
        appointment_id=appointment_id,
    )
    if appointment is not None and appointment.status == AppointmentStatus.CANCELLED:
        if await supersede_master_action_push(
            bot=bot,
            repos=repos,
            appointment=appointment,
            translations=translations,
            text_key="master_booking_cancelled_by_client",
            bot_timezone=bot_timezone,
        ):
            return

    with suppress(TelegramBadRequest):
        await callback.message.edit_reply_markup(reply_markup=None)
    if appointment is not None and appointment.master_notify_message_id is not None:
        await repos.appointments.set_master_notify_message_id(
            appointment_id=appointment.id,
            message_id=None,
        )


async def _finish_master_decision(
        *,
        callback: CallbackQuery,
        user: User,
        i18n: dict[str, str],
        state: FSMContext,
        repos: Repositories,
        appointment_id: int,
        bot_timezone: str,
        ack_text: str,
) -> None:
    """
    Sticky card: refresh the day list in place.
    Push notification: restore hub and delete the push.
    """
    await repos.appointments.set_master_notify_message_id(
        appointment_id=appointment_id,
        message_id=None,
    )
    data = await state.get_data()
    sticky_id = data.get(HUB_MESSAGE_ID_KEY)
    on_sticky = (
        sticky_id is not None
        and callback.message is not None
        and callback.message.message_id == sticky_id
    )
    if on_sticky:
        day = _parse_iso_date(data.get(_DAY_KEY))
        if day is not None:
            await show_master_bookings_day(
                message=callback.message,
                state=state,
                repos=repos,
                user=user,
                i18n=i18n,
                bot_timezone=bot_timezone,
                day=day,
                edit=True,
            )
        else:
            await show_master_bookings_week(
                message=callback.message,
                state=state,
                repos=repos,
                user=user,
                i18n=i18n,
                bot_timezone=bot_timezone,
                edit=True,
            )
        await callback.answer(text=ack_text)
        return

    await show_hub(
        message=callback.message,
        user=user,
        i18n=i18n,
        state=state,
    )
    data = await state.get_data()
    sticky_id = data.get(HUB_MESSAGE_ID_KEY)
    if sticky_id is None or callback.message.message_id != sticky_id:
        with suppress(TelegramBadRequest):
            await callback.message.delete()
    await callback.answer(text=ack_text)


@bookings_router.message(Command(commands="bookings"))
async def process_bookings_command(
        message: Message,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    await state.update_data(
        list_return="root",
        hub_screen="bookings",
        hub_back="root",
    )
    _, _, week_start = local_week_bounds(bot_timezone)
    await state.update_data(
        {
            _WEEK_START_KEY: week_start.isoformat(),
            _DAY_KEY: None,
        }
    )
    await show_master_bookings_week(
        message=message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=False,
    )


@bookings_router.callback_query(MasterAppointmentCallback.filter(F.action == "open_day"))
async def process_open_day(
        callback: CallbackQuery,
        callback_data: MasterAppointmentCallback,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    day = _parse_iso_date(callback_data.day)
    if day is None:
        await callback.answer(
            text=i18n.get("master_action_failed"),
            show_alert=True,
        )
        return
    await show_master_bookings_day(
        message=callback.message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        day=day,
        edit=True,
    )
    await callback.answer()


@bookings_router.callback_query(MasterAppointmentCallback.filter(F.action == "open"))
async def process_open(
        callback: CallbackQuery,
        callback_data: MasterAppointmentCallback,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    appointment = await repos.appointments.get_appointment(
        appointment_id=callback_data.appointment_id,
    )
    if (
        appointment is None
        or appointment.master_user_id != user.user_id
    ):
        await callback.answer(
            text=i18n.get("master_action_failed"),
            show_alert=True,
        )
        return

    await _show_booking_card(
        message=callback.message,
        state=state,
        appointment=appointment,
        repos=repos,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    await callback.answer()


@bookings_router.callback_query(MasterAppointmentCallback.filter(F.action == "back"))
async def process_back(
        callback: CallbackQuery,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    data = await state.get_data()
    day = _parse_iso_date(data.get(_DAY_KEY))
    if day is None:
        await show_master_bookings_week(
            message=callback.message,
            state=state,
            repos=repos,
            user=user,
            i18n=i18n,
            bot_timezone=bot_timezone,
            edit=True,
        )
    else:
        await show_master_bookings_day(
            message=callback.message,
            state=state,
            repos=repos,
            user=user,
            i18n=i18n,
            bot_timezone=bot_timezone,
            day=day,
            edit=True,
        )
    await callback.answer()


@bookings_router.callback_query(
    MasterAppointmentCallback.filter(F.action == "back_week"),
)
async def process_back_week(
        callback: CallbackQuery,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    await show_master_bookings_week(
        message=callback.message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=True,
    )
    await callback.answer()


@bookings_router.callback_query(
    MasterAppointmentCallback.filter(F.action == "week_prev"),
)
async def process_week_prev(
        callback: CallbackQuery,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    await _set_week_start(
        state=state,
        bot_timezone=bot_timezone,
        delta_weeks=-1,
    )
    await show_master_bookings_week(
        message=callback.message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=True,
    )
    await callback.answer()


@bookings_router.callback_query(
    MasterAppointmentCallback.filter(F.action == "week_next"),
)
async def process_week_next(
        callback: CallbackQuery,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    await _set_week_start(
        state=state,
        bot_timezone=bot_timezone,
        delta_weeks=1,
    )
    await show_master_bookings_week(
        message=callback.message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=True,
    )
    await callback.answer()


@bookings_router.callback_query(
    MasterAppointmentCallback.filter(F.action == "week_current"),
)
async def process_week_current(
        callback: CallbackQuery,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    await _set_week_start(
        state=state,
        bot_timezone=bot_timezone,
        to_current=True,
    )
    await show_master_bookings_week(
        message=callback.message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=True,
    )
    await callback.answer()


@bookings_router.callback_query(MasterAppointmentCallback.filter(F.action == "close"))
async def process_close(
        callback: CallbackQuery,
        state: FSMContext,
        user: User,
        i18n: dict[str, str],
) -> None:
    await return_from_list(
        message=callback.message,
        user=user,
        i18n=i18n,
        state=state,
    )
    await callback.answer()


@bookings_router.callback_query(MasterAppointmentCallback.filter(F.action == "confirm"))
async def process_confirm(
        callback: CallbackQuery,
        callback_data: MasterAppointmentCallback,
        bot: Bot,
        translations: dict,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
        state: FSMContext,
) -> None:
    if await _reject_if_slot_past(
        callback=callback,
        repos=repos,
        appointment_id=callback_data.appointment_id,
        i18n=i18n,
    ):
        return

    booking = BookingService(repos)
    try:
        appointment = await booking.confirm(
            appointment_id=callback_data.appointment_id,
            master_user_id=user.user_id,
        )
    except (
        AppointmentNotFound, ForbiddenBookingAction, InvalidAppointmentStatus
    ):
        await _disarm_stale_master_push(
            callback=callback,
            bot=bot,
            repos=repos,
            appointment_id=callback_data.appointment_id,
            translations=translations,
            bot_timezone=bot_timezone,
        )
        await callback.answer(
            text=i18n.get("master_action_failed"),
            show_alert=True,
        )
        return

    await notify_appointment(
        bot=bot,
        repos=repos,
        appointment=appointment,
        recipient_user_id=appointment.client_user_id,
        translations=translations,
        text_key="client_booking_confirmed",
        bot_timezone=bot_timezone,
        with_dismiss=True,
    )
    await _finish_master_decision(
        callback=callback,
        user=user,
        i18n=i18n,
        state=state,
        repos=repos,
        appointment_id=appointment.id,
        bot_timezone=bot_timezone,
        ack_text=i18n.get("master_confirmed").format(id=appointment.id),
    )


@bookings_router.callback_query(MasterAppointmentCallback.filter(F.action == "cancel"))
async def process_cancel(
        callback: CallbackQuery,
        callback_data: MasterAppointmentCallback,
        bot: Bot,
        translations: dict,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
        state: FSMContext,
) -> None:
    if await _reject_if_slot_past(
        callback=callback,
        repos=repos,
        appointment_id=callback_data.appointment_id,
        i18n=i18n,
    ):
        return

    booking = BookingService(repos)
    try:
        appointment = await booking.cancel(
            appointment_id=callback_data.appointment_id,
            actor_user_id=user.user_id,
        )
    except (
        AppointmentNotFound, ForbiddenBookingAction, InvalidAppointmentStatus
    ):
        await _disarm_stale_master_push(
            callback=callback,
            bot=bot,
            repos=repos,
            appointment_id=callback_data.appointment_id,
            translations=translations,
            bot_timezone=bot_timezone,
        )
        await callback.answer(
            text=i18n.get("master_action_failed"),
            show_alert=True,
        )
        return

    await notify_appointment(
        bot=bot,
        repos=repos,
        appointment=appointment,
        recipient_user_id=appointment.client_user_id,
        translations=translations,
        text_key="client_booking_cancelled_by_master",
        bot_timezone=bot_timezone,
        with_dismiss=True,
    )
    await _finish_master_decision(
        callback=callback,
        user=user,
        i18n=i18n,
        state=state,
        repos=repos,
        appointment_id=appointment.id,
        bot_timezone=bot_timezone,
        ack_text=i18n.get("master_cancelled").format(id=appointment.id),
    )


async def _hub_bookings(
        *,
        message: Message,
        user: User,
        i18n: dict[str, str],
        state: FSMContext,
        repos: Repositories | None = None,
        bot_timezone: str | None = None,
        **_,
) -> None:
    if user.role != UserRole.MASTER or repos is None or bot_timezone is None:
        return
    _, _, week_start = local_week_bounds(bot_timezone)
    await state.update_data(
        hub_screen="bookings",
        hub_back="root",
        list_return="root",
        **{
            _WEEK_START_KEY: week_start.isoformat(),
            _DAY_KEY: None,
        },
    )
    await show_master_bookings_week(
        message=message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=True,
    )


register("bookings", _hub_bookings)
