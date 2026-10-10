from contextlib import suppress
from datetime import datetime, date, time, timedelta

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup

from app.bot.filters.filters import UserRoleFilter
from app.bot.handlers.common.hub import return_from_list
from app.bot.keyboards.hub import get_hub_dismiss_kb
from app.bot.keyboards.time_off import (
    TimeOffDayCallback,
    TimeOffNavCallback,
    TimeOffPadCallback,
    TimeOffDeleteCallback,
    TimeOffConfirmCallback,
    format_time_off_line,
    get_time_off_day_calendar_kb,
    get_time_off_edit_kb,
    get_time_off_confirm_delete_kb,
    get_time_off_cancel_kb,
    get_time_off_kind_kb,
    get_time_off_warn_kb,
)
from app.bot.keyboards.work_days import month_label
from app.bot.states.states import TimeOffSG
from app.bot.utils.format import (
    client_contact,
    combine_local,
    format_dt,
    get_zone,
    local_month_bounds,
)
from app.bot.utils.hub_nav import (
    HUB_MESSAGE_ID_KEY,
    clear_state_keep_hub,
    show_hub_prompt,
)
from app.bot.utils.hub_registry import register
from app.domain.enums import AppointmentStatus, UserRole
from app.domain.models import Appointment, User
from app.infrastructure.database.repositories import Repositories


time_off_router = Router(name="master_time_off")
time_off_router.message.filter(UserRoleFilter(UserRole.MASTER))
time_off_router.callback_query.filter(UserRoleFilter(UserRole.MASTER))

_MONTH_KEY = "toff_month"  # YYYY-MM
_MAX_WARN_LINES = 8
_PENDING_STARTS_KEY = "toff_starts_at"
_PENDING_ENDS_KEY = "toff_ends_at"
_PENDING_WHEN_KEY = "toff_when"
_PENDING_KIND_KEY = "toff_kind"  # hours | days


def _is_breaks_mode(schedule_mode: str) -> bool:
    return schedule_mode == "monthly"


def _intervals_overlap(
        start: datetime,
        end: datetime,
        other_start: datetime,
        other_end: datetime,
) -> bool:
    return start < other_end and end > other_start


def _parse_year_month(raw: str | None) -> tuple[int, int] | None:
    if not raw:
        return None
    try:
        year_s, month_s = raw.split("-", 1)
        year, month = int(year_s), int(month_s)
    except ValueError:
        return None
    if not 1 <= month <= 12:
        return None
    return year, month


def _format_year_month(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = year * 12 + (month - 1) + delta
    return idx // 12, idx % 12 + 1


def _list_from_dt(bot_timezone: str) -> datetime:
    zone = get_zone(bot_timezone)
    now_local = datetime.now(zone)
    return now_local.replace(hour=0, minute=0, second=0, microsecond=0)


def _today_local(bot_timezone: str) -> date:
    return _list_from_dt(bot_timezone).date()


def _parse_date(value: str) -> date | None:
    value = value.strip()
    for fmt in ("%d.%m.%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_time(value: str) -> time | None:
    value = value.strip()
    for fmt in ("%H:%M", "%H.%M"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    return None


def _format_day_range(starts: date, ends: date) -> str:
    start_d = starts.strftime("%d.%m.%Y")
    end_d = ends.strftime("%d.%m.%Y")
    if start_d == end_d:
        return start_d
    return f"{start_d}-{end_d}"


def _format_hours_when(day: date, starts: time, ends: time) -> str:
    return (
        f"{day.strftime('%d.%m.%Y')} "
        f"{starts.strftime('%H:%M')}–{ends.strftime('%H:%M')}"
    )


def _is_not_modified(exc: TelegramBadRequest) -> bool:
    return "message is not modified" in str(exc).lower()


async def _delete_user_input(message: Message) -> None:
    with suppress(TelegramBadRequest):
        await message.delete()


async def _show_time_off_prompt(
        *,
        message: Message,
        state: FSMContext,
        text: str,
        i18n: dict[str, str],
        reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """Show FSM prompt on the tapped hub message / sticky when possible."""
    kb = reply_markup if reply_markup is not None else get_time_off_cancel_kb(i18n)
    await show_hub_prompt(
        message=message,
        state=state,
        text=text,
        reply_markup=kb,
    )


async def _finish_time_off_add(
        *,
        message: Message,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
        when: str,
        schedule_mode: str = "weekly",
) -> None:
    await clear_state_keep_hub(state)
    await show_time_off_list(
        message=message,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=False,
        state=state,
        prefer_sticky=True,
        schedule_mode=schedule_mode,
    )
    ok_key = (
        "time_off_breaks_add_ok"
        if _is_breaks_mode(schedule_mode)
        else "time_off_add_ok"
    )
    await message.answer(
        text=i18n.get(ok_key).format(when=when),
        reply_markup=get_hub_dismiss_kb(i18n),
    )


async def _appointments_overlapping_block(
        *,
        repos: Repositories,
        master_user_id: int,
        starts_at: datetime,
        ends_at: datetime,
) -> list[Appointment]:
    # list_by_master filters on starts_at; widen left so a slot that began
    # before the block but still overlaps is included, then filter precisely.
    rows = await repos.appointments.list_by_master(
        master_user_id=master_user_id,
        from_dt=starts_at - timedelta(days=1),
        to_dt=ends_at,
    )
    result: list[Appointment] = []
    for appointment in rows:
        if appointment.status not in (
            AppointmentStatus.PENDING,
            AppointmentStatus.CONFIRMED,
        ):
            continue
        if _intervals_overlap(
            starts_at,
            ends_at,
            appointment.starts_at,
            appointment.ends_at,
        ):
            result.append(appointment)
    return result


async def _warn_bookings_text(
        *,
        repos: Repositories,
        appointments: list[Appointment],
        i18n: dict[str, str],
        bot_timezone: str,
) -> str:
    lines: list[str] = []
    for appointment in appointments[:_MAX_WARN_LINES]:
        client = await repos.users.get_user_by_id(
            user_id=appointment.client_user_id,
        )
        name, _ = client_contact(client)
        lines.append(
            i18n.get("time_off_warn_item").format(
                when=format_dt(appointment.starts_at, bot_timezone),
                client=name,
            )
        )
    extra = len(appointments) - _MAX_WARN_LINES
    if extra > 0:
        lines.append(i18n.get("time_off_warn_more").format(n=extra))
    return i18n.get("time_off_warn_header").format(list="\n".join(lines))


async def _show_warn_bookings(
        *,
        message: Message,
        state: FSMContext,
        repos: Repositories,
        appointments: list[Appointment],
        i18n: dict[str, str],
        bot_timezone: str,
        starts_at: datetime,
        ends_at: datetime,
        when: str,
        kind: str,
) -> None:
    await state.update_data(
        {
            _PENDING_STARTS_KEY: starts_at.isoformat(),
            _PENDING_ENDS_KEY: ends_at.isoformat(),
            _PENDING_WHEN_KEY: when,
            _PENDING_KIND_KEY: kind,
        }
    )
    text = await _warn_bookings_text(
        repos=repos,
        appointments=appointments,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    await state.set_state(TimeOffSG.warn_bookings)
    await _show_time_off_prompt(
        message=message,
        state=state,
        text=text,
        i18n=i18n,
        reply_markup=get_time_off_warn_kb(i18n),
    )


async def _apply_pending_time_off(
        *,
        message: Message,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
        schedule_mode: str,
) -> None:
    data = await state.get_data()
    starts_raw = data.get(_PENDING_STARTS_KEY)
    ends_raw = data.get(_PENDING_ENDS_KEY)
    when = data.get(_PENDING_WHEN_KEY)
    if not starts_raw or not ends_raw or not when:
        await clear_state_keep_hub(state)
        await show_time_off_list(
            message=message,
            repos=repos,
            user=user,
            i18n=i18n,
            bot_timezone=bot_timezone,
            edit=True,
            state=state,
            prefer_sticky=True,
            schedule_mode=schedule_mode,
        )
        return

    starts_at = datetime.fromisoformat(str(starts_raw))
    ends_at = datetime.fromisoformat(str(ends_raw))
    await repos.time_off.add(
        master_user_id=user.user_id,
        starts_at=starts_at,
        ends_at=ends_at,
        note=None,
    )
    await _finish_time_off_add(
        message=message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        when=str(when),
        schedule_mode=schedule_mode,
    )


async def _save_time_off_or_warn(
        *,
        message: Message,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
        schedule_mode: str,
        starts_at: datetime,
        ends_at: datetime,
        when: str,
        kind: str,
) -> None:
    conflicting = await _appointments_overlapping_block(
        repos=repos,
        master_user_id=user.user_id,
        starts_at=starts_at,
        ends_at=ends_at,
    )
    if conflicting:
        await _show_warn_bookings(
            message=message,
            state=state,
            repos=repos,
            appointments=conflicting,
            i18n=i18n,
            bot_timezone=bot_timezone,
            starts_at=starts_at,
            ends_at=ends_at,
            when=when,
            kind=kind,
        )
        return

    await repos.time_off.add(
        master_user_id=user.user_id,
        starts_at=starts_at,
        ends_at=ends_at,
        note=None,
    )
    await _finish_time_off_add(
        message=message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        when=when,
        schedule_mode=schedule_mode,
    )


async def _start_hours_add(
        *,
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    """Weekly: typed DD.MM.YYYY for hours-in-one-day."""
    await state.set_state(TimeOffSG.hours_day)
    example = _today_local(bot_timezone).strftime("%d.%m.%Y")
    await _show_time_off_prompt(
        message=message,
        state=state,
        text=i18n.get("time_off_enter_hours_day").format(example=example),
        i18n=i18n,
    )


async def _show_break_day_calendar(
        *,
        message: Message,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    data = await state.get_data()
    parsed = _parse_year_month(data.get(_MONTH_KEY))
    year = parsed[0] if parsed else None
    month = parsed[1] if parsed else None
    _, _, year, month = local_month_bounds(
        bot_timezone,
        year=year,
        month=month,
    )
    _, _, current_year, current_month = local_month_bounds(bot_timezone)
    if (year, month) < (current_year, current_month):
        year, month = current_year, current_month

    await state.update_data({_MONTH_KEY: _format_year_month(year, month)})
    await state.set_state(TimeOffSG.choosing_day)

    today = _today_local(bot_timezone)
    work_rows = await repos.work_dates.list_month(
        master_user_id=user.user_id,
        year=year,
        month=month,
    )
    open_days = {
        row.work_date.day
        for row in work_rows
        if row.work_date >= today
    }
    month_text = month_label(year, month, i18n)
    if open_days:
        text = i18n.get("time_off_choose_open_day").format(month=month_text)
    else:
        text = i18n.get("time_off_month_no_open_days").format(month=month_text)

    kb = get_time_off_day_calendar_kb(
        year=year,
        month=month,
        open_days=open_days,
        i18n=i18n,
        is_current_month=(year, month) == (current_year, current_month),
    )
    await _show_time_off_prompt(
        message=message,
        state=state,
        text=text,
        i18n=i18n,
        reply_markup=kb,
    )


async def _set_break_month(
        *,
        state: FSMContext,
        bot_timezone: str,
        delta_months: int = 0,
        to_current: bool = False,
) -> None:
    _, _, current_year, current_month = local_month_bounds(bot_timezone)
    if to_current:
        year, month = current_year, current_month
    else:
        data = await state.get_data()
        parsed = _parse_year_month(data.get(_MONTH_KEY))
        year = parsed[0] if parsed else None
        month = parsed[1] if parsed else None
        _, _, year, month = local_month_bounds(
            bot_timezone,
            year=year,
            month=month,
        )
        year, month = _shift_month(year, month, delta_months)
        if (year, month) < (current_year, current_month):
            year, month = current_year, current_month
    await state.update_data({_MONTH_KEY: _format_year_month(year, month)})


async def show_time_off_list(
        *,
        message: Message,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
        edit: bool,
        state: FSMContext | None = None,
        prefer_sticky: bool = False,
        schedule_mode: str = "weekly",
) -> None:
    rows = await repos.time_off.list_by_master(
        master_user_id=user.user_id,
        from_dt=_list_from_dt(bot_timezone),
    )
    if _is_breaks_mode(schedule_mode):
        header_key = "time_off_breaks_header"
        empty_key = "time_off_breaks_empty"
    else:
        header_key = "time_off_header"
        empty_key = "time_off_empty"
    if rows:
        body = "\n".join(
            format_time_off_line(row, i18n, bot_timezone) for row in rows
        )
        text = i18n.get(header_key) + "\n\n" + body
    else:
        text = i18n.get(empty_key)

    kb = get_time_off_edit_kb(
        rows=rows,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )

    if prefer_sticky and state is not None:
        data = await state.get_data()
        sticky_id = data.get(HUB_MESSAGE_ID_KEY)
        if sticky_id is not None:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=int(sticky_id),
                    text=text,
                    reply_markup=kb,
                )
                return
            except TelegramBadRequest as exc:
                if _is_not_modified(exc):
                    return
                # Sticky gone or not editable — fall through and re-point.
                with suppress(TelegramBadRequest):
                    await message.bot.edit_message_reply_markup(
                        chat_id=message.chat.id,
                        message_id=int(sticky_id),
                        reply_markup=None,
                    )

        sent = await message.answer(text=text, reply_markup=kb)
        await state.update_data({HUB_MESSAGE_ID_KEY: sent.message_id})
        return

    if edit:
        await message.edit_text(text=text, reply_markup=kb)
    else:
        await message.answer(text=text, reply_markup=kb)


@time_off_router.callback_query(TimeOffNavCallback.filter(F.action == "close"))
async def process_time_off_close(
        callback: CallbackQuery,
        state: FSMContext,
        user: User,
        i18n: dict[str, str],
        schedule_mode: str,
) -> None:
    """Back → hub schedule section."""
    await return_from_list(
        message=callback.message,
        user=user,
        i18n=i18n,
        state=state,
        schedule_mode=schedule_mode,
    )
    await callback.answer()


@time_off_router.callback_query(TimeOffDeleteCallback.filter())
async def process_time_off_delete(
        callback: CallbackQuery,
        callback_data: TimeOffDeleteCallback,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
        schedule_mode: str,
) -> None:
    row = await repos.time_off.get(
        time_off_id=callback_data.time_off_id,
    )
    if row is None or row.master_user_id != user.user_id:
        await callback.answer(
            text=i18n.get("time_off_delete_not_found"),
            show_alert=True,
        )
        return

    item = format_time_off_line(row, i18n, bot_timezone).lstrip("• ").strip()
    confirm_key = (
        "time_off_breaks_confirm_delete"
        if _is_breaks_mode(schedule_mode)
        else "time_off_confirm_delete"
    )
    await callback.message.edit_text(
        text=i18n.get(confirm_key).format(item=item),
        reply_markup=get_time_off_confirm_delete_kb(
            time_off_id=row.id,
            i18n=i18n,
        ),
    )
    await callback.answer()


@time_off_router.callback_query(
    TimeOffConfirmCallback.filter(F.action == "yes"),
)
async def process_time_off_delete_yes(
        callback: CallbackQuery,
        callback_data: TimeOffConfirmCallback,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
        schedule_mode: str,
) -> None:
    deleted = await repos.time_off.delete(
        time_off_id=callback_data.time_off_id,
        master_user_id=user.user_id,
    )
    if not deleted:
        await callback.answer(
            text=i18n.get("time_off_delete_not_found"),
            show_alert=True,
        )
        return
    deleted_key = (
        "time_off_breaks_deleted"
        if _is_breaks_mode(schedule_mode)
        else "time_off_deleted"
    )
    await callback.answer(text=i18n.get(deleted_key))
    await show_time_off_list(
        message=callback.message,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=True,
        schedule_mode=schedule_mode,
    )


@time_off_router.callback_query(
    TimeOffConfirmCallback.filter(F.action == "no"),
)
async def process_time_off_delete_no(
        callback: CallbackQuery,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
        schedule_mode: str,
) -> None:
    await show_time_off_list(
        message=callback.message,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=True,
        schedule_mode=schedule_mode,
    )
    await callback.answer()


@time_off_router.callback_query(TimeOffNavCallback.filter(F.action == "add"))
async def process_time_off_add(
        callback: CallbackQuery,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
        schedule_mode: str,
) -> None:
    await clear_state_keep_hub(state)
    if _is_breaks_mode(schedule_mode):
        # Monthly: pick an open work day on the calendar, then hours.
        await _show_break_day_calendar(
            message=callback.message,
            state=state,
            repos=repos,
            user=user,
            i18n=i18n,
            bot_timezone=bot_timezone,
        )
        await callback.answer()
        return

    await state.set_state(TimeOffSG.choosing_kind)
    await _show_time_off_prompt(
        message=callback.message,
        state=state,
        text=i18n.get("time_off_choose_kind"),
        i18n=i18n,
        reply_markup=get_time_off_kind_kb(i18n),
    )
    await callback.answer()


@time_off_router.callback_query(
    TimeOffNavCallback.filter(F.action == "days"),
    StateFilter(TimeOffSG.choosing_kind),
)
async def process_time_off_kind_days(
        callback: CallbackQuery,
        state: FSMContext,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    await state.set_state(TimeOffSG.starts_date)
    example = _today_local(bot_timezone).strftime("%d.%m.%Y")
    await _show_time_off_prompt(
        message=callback.message,
        state=state,
        text=i18n.get("time_off_enter_starts").format(example=example),
        i18n=i18n,
    )
    await callback.answer()


@time_off_router.callback_query(
    TimeOffNavCallback.filter(F.action == "hours"),
    StateFilter(TimeOffSG.choosing_kind),
)
async def process_time_off_kind_hours(
        callback: CallbackQuery,
        state: FSMContext,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    await _start_hours_add(
        message=callback.message,
        state=state,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    await callback.answer()


@time_off_router.callback_query(
    TimeOffNavCallback.filter(F.action == "month_prev"),
    StateFilter(TimeOffSG.choosing_day),
)
async def process_break_month_prev(
        callback: CallbackQuery,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    await _set_break_month(
        state=state,
        bot_timezone=bot_timezone,
        delta_months=-1,
    )
    await _show_break_day_calendar(
        message=callback.message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    await callback.answer()


@time_off_router.callback_query(
    TimeOffNavCallback.filter(F.action == "month_next"),
    StateFilter(TimeOffSG.choosing_day),
)
async def process_break_month_next(
        callback: CallbackQuery,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    await _set_break_month(
        state=state,
        bot_timezone=bot_timezone,
        delta_months=1,
    )
    await _show_break_day_calendar(
        message=callback.message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    await callback.answer()


@time_off_router.callback_query(
    TimeOffNavCallback.filter(F.action == "month_current"),
    StateFilter(TimeOffSG.choosing_day),
)
async def process_break_month_current(
        callback: CallbackQuery,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    await _set_break_month(
        state=state,
        bot_timezone=bot_timezone,
        to_current=True,
    )
    await _show_break_day_calendar(
        message=callback.message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    await callback.answer()


@time_off_router.callback_query(
    TimeOffDayCallback.filter(),
    StateFilter(TimeOffSG.choosing_day),
)
async def process_break_day(
        callback: CallbackQuery,
        callback_data: TimeOffDayCallback,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    try:
        day = date.fromisoformat(callback_data.value)
    except ValueError:
        await callback.answer(
            text=i18n.get("time_off_day_not_work_day"),
            show_alert=True,
        )
        return

    today = _today_local(bot_timezone)
    if day < today:
        await callback.answer(
            text=i18n.get("time_off_invalid_past"),
            show_alert=True,
        )
        return

    work_rows = await repos.work_dates.list_month(
        master_user_id=user.user_id,
        year=day.year,
        month=day.month,
    )
    open_dates = {row.work_date for row in work_rows}
    if day not in open_dates:
        await callback.answer(
            text=i18n.get("time_off_day_not_work_day"),
            show_alert=True,
        )
        return

    await state.update_data(hours_day=day.isoformat())
    await state.set_state(TimeOffSG.starts_time)
    await _show_time_off_prompt(
        message=callback.message,
        state=state,
        text=i18n.get("time_off_enter_hours_starts"),
        i18n=i18n,
    )
    await callback.answer()


@time_off_router.callback_query(TimeOffPadCallback.filter())
async def process_break_day_pad(callback: CallbackQuery) -> None:
    await callback.answer()


@time_off_router.callback_query(
    TimeOffNavCallback.filter(F.action == "cancel"),
    StateFilter(TimeOffSG),
)
async def process_time_off_cancel_cb(
        callback: CallbackQuery,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
        schedule_mode: str,
) -> None:
    await clear_state_keep_hub(state)
    await show_time_off_list(
        message=callback.message,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=True,
        state=state,
        prefer_sticky=True,
        schedule_mode=schedule_mode,
    )
    await callback.answer()


@time_off_router.message(StateFilter(TimeOffSG.starts_date))
async def process_time_off_starts(
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    starts = _parse_date(message.text or "")
    await _delete_user_input(message)
    if starts is None:
        await message.answer(text=i18n.get("time_off_invalid_date"))
        return

    await state.update_data(starts_date=starts.isoformat())
    await state.set_state(TimeOffSG.ends_date)
    example = max(starts, _today_local(bot_timezone)).strftime("%d.%m.%Y")
    await _show_time_off_prompt(
        message=message,
        state=state,
        text=i18n.get("time_off_enter_ends").format(example=example),
        i18n=i18n,
    )


@time_off_router.message(StateFilter(TimeOffSG.ends_date))
async def process_time_off_ends(
        message: Message,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
        schedule_mode: str,
) -> None:
    ends = _parse_date(message.text or "")
    await _delete_user_input(message)
    if ends is None:
        await message.answer(text=i18n.get("time_off_invalid_date"))
        return

    data = await state.get_data()
    starts = date.fromisoformat(data["starts_date"])
    if ends < starts:
        await message.answer(text=i18n.get("time_off_invalid_range"))
        return

    if ends < _today_local(bot_timezone):
        await message.answer(text=i18n.get("time_off_invalid_past"))
        return

    starts_at = combine_local(starts, time(0, 0), bot_timezone)
    ends_at = combine_local(ends + timedelta(days=1), time(0, 0), bot_timezone)

    await _save_time_off_or_warn(
        message=message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        schedule_mode=schedule_mode,
        starts_at=starts_at,
        ends_at=ends_at,
        when=_format_day_range(starts, ends),
        kind="days",
    )


@time_off_router.message(StateFilter(TimeOffSG.hours_day))
async def process_time_off_hours_day(
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    day = _parse_date(message.text or "")
    await _delete_user_input(message)
    if day is None:
        await message.answer(text=i18n.get("time_off_invalid_date"))
        return

    if day < _today_local(bot_timezone):
        await message.answer(text=i18n.get("time_off_invalid_past"))
        return

    await state.update_data(hours_day=day.isoformat())
    await state.set_state(TimeOffSG.starts_time)
    await _show_time_off_prompt(
        message=message,
        state=state,
        text=i18n.get("time_off_enter_hours_starts"),
        i18n=i18n,
    )


@time_off_router.message(StateFilter(TimeOffSG.starts_time))
async def process_time_off_hours_starts(
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
) -> None:
    starts = _parse_time(message.text or "")
    await _delete_user_input(message)
    if starts is None:
        await message.answer(text=i18n.get("time_off_invalid_time"))
        return

    await state.update_data(starts_time=starts.isoformat())
    await state.set_state(TimeOffSG.ends_time)
    await _show_time_off_prompt(
        message=message,
        state=state,
        text=i18n.get("time_off_enter_hours_ends"),
        i18n=i18n,
    )


@time_off_router.message(StateFilter(TimeOffSG.ends_time))
async def process_time_off_hours_ends(
        message: Message,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
        schedule_mode: str,
) -> None:
    ends = _parse_time(message.text or "")
    await _delete_user_input(message)
    if ends is None:
        await message.answer(text=i18n.get("time_off_invalid_time"))
        return

    data = await state.get_data()
    day = date.fromisoformat(data["hours_day"])
    starts = time.fromisoformat(data["starts_time"])
    if ends <= starts:
        await message.answer(text=i18n.get("time_off_invalid_time_range"))
        return

    starts_at = combine_local(day, starts, bot_timezone)
    ends_at = combine_local(day, ends, bot_timezone)
    now_local = datetime.now(get_zone(bot_timezone))
    if ends_at <= now_local:
        await message.answer(text=i18n.get("time_off_invalid_hours_past"))
        return

    await _save_time_off_or_warn(
        message=message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        schedule_mode=schedule_mode,
        starts_at=starts_at,
        ends_at=ends_at,
        when=_format_hours_when(day, starts, ends),
        kind="hours",
    )


@time_off_router.callback_query(
    TimeOffNavCallback.filter(F.action == "save_anyway"),
    StateFilter(TimeOffSG.warn_bookings),
)
async def process_time_off_save_anyway(
        callback: CallbackQuery,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
        schedule_mode: str,
) -> None:
    await _apply_pending_time_off(
        message=callback.message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        schedule_mode=schedule_mode,
    )
    await callback.answer()


@time_off_router.callback_query(
    TimeOffNavCallback.filter(F.action == "warn_back"),
    StateFilter(TimeOffSG.warn_bookings),
)
async def process_time_off_warn_back(
        callback: CallbackQuery,
        state: FSMContext,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    data = await state.get_data()
    kind = data.get(_PENDING_KIND_KEY)
    if kind == "hours":
        await state.set_state(TimeOffSG.ends_time)
        await _show_time_off_prompt(
            message=callback.message,
            state=state,
            text=i18n.get("time_off_enter_hours_ends"),
            i18n=i18n,
        )
    else:
        await state.set_state(TimeOffSG.ends_date)
        example = _today_local(bot_timezone).strftime("%d.%m.%Y")
        starts_raw = data.get("starts_date")
        if starts_raw:
            starts = date.fromisoformat(str(starts_raw))
            example = max(starts, _today_local(bot_timezone)).strftime("%d.%m.%Y")
        await _show_time_off_prompt(
            message=callback.message,
            state=state,
            text=i18n.get("time_off_enter_ends").format(example=example),
            i18n=i18n,
        )
    await callback.answer()


async def _hub_time_off(
        *,
        message: Message,
        user: User,
        i18n: dict[str, str],
        state: FSMContext,
        repos: Repositories | None = None,
        bot_timezone: str | None = None,
        schedule_mode: str = "weekly",
        **_,
) -> None:
    if user.role != UserRole.MASTER or repos is None or bot_timezone is None:
        return
    await state.update_data(
        hub_screen="time_off",
        hub_back="schedule",
        list_return="schedule",
    )
    await show_time_off_list(
        message=message,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=True,
        state=state,
        schedule_mode=schedule_mode,
    )


register("time_off", _hub_time_off)
