from contextlib import suppress
from datetime import date, datetime, time

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.filters.filters import UserRoleFilter
from app.bot.handlers.common.hub import return_from_list
from app.bot.keyboards.hub import get_hub_dismiss_kb
from app.bot.keyboards.work_days import (
    WorkDaysDayCallback,
    WorkDaysMonthCallback,
    WorkDaysNavCallback,
    WorkDaysPadCallback,
    get_work_days_calendar_kb,
    get_work_days_cancel_kb,
    get_work_days_confirm_kb,
    get_work_days_months_kb,
    month_label,
)
from app.bot.states.states import WorkDaysSG
from app.bot.utils.format import get_zone
from app.bot.utils.hub_nav import clear_state_keep_hub, show_hub_prompt
from app.bot.utils.hub_registry import register
from app.domain.enums import UserRole
from app.domain.models import User
from app.infrastructure.database.repositories import Repositories


work_days_router = Router(name="master_work_days")
work_days_router.message.filter(UserRoleFilter(UserRole.MASTER))
work_days_router.callback_query.filter(UserRoleFilter(UserRole.MASTER))

_MONTH_CHOICES = 3


def _parse_time(value: str) -> time | None:
    value = value.strip()
    for fmt in ("%H:%M", "%H.%M"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    return None


def _format_hm(value: time) -> str:
    return value.strftime("%H:%M")


def _format_day_list(values: list[str] | set[str]) -> str:
    days = sorted(date.fromisoformat(value) for value in values)
    return ", ".join(day.strftime("%d.%m") for day in days)


def _day_sets(data: dict) -> tuple[set[str], set[str], set[str], set[str]]:
    current = set(data.get("wd_days") or [])
    initial = set(data.get("wd_days_initial") or [])
    removed = initial - current
    added = current - initial
    return current, initial, removed, added


async def _delete_user_input(message: Message) -> None:
    with suppress(TelegramBadRequest):
        await message.delete()


def _month_choices(bot_timezone: str) -> list[tuple[int, int]]:
    today = datetime.now(get_zone(bot_timezone)).date()
    year, month = today.year, today.month
    result: list[tuple[int, int]] = []
    for _ in range(_MONTH_CHOICES):
        result.append((year, month))
        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1
    return result


async def _marked_months(
        *,
        repos: Repositories,
        master_user_id: int,
        months: list[tuple[int, int]],
) -> set[tuple[int, int]]:
    marked: set[tuple[int, int]] = set()
    for year, month in months:
        rows = await repos.work_dates.list_month(
            master_user_id=master_user_id,
            year=year,
            month=month,
        )
        if rows:
            marked.add((year, month))
    return marked


async def show_work_days_months(
        *,
        message: Message,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    months = _month_choices(bot_timezone)
    marked = await _marked_months(
        repos=repos,
        master_user_id=user.user_id,
        months=months,
    )
    await state.set_state(WorkDaysSG.choosing_month)
    await show_hub_prompt(
        message=message,
        state=state,
        text=i18n.get("work_days_choose_month"),
        reply_markup=get_work_days_months_kb(
            months=months,
            marked=marked,
            i18n=i18n,
        ),
    )


async def _show_calendar(
        *,
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
) -> None:
    data = await state.get_data()
    year = int(data["wd_year"])
    month = int(data["wd_month"])
    selected = {date.fromisoformat(value).day for value in data.get("wd_days") or []}
    await state.set_state(WorkDaysSG.choosing_days)
    await show_hub_prompt(
        message=message,
        state=state,
        text=i18n.get("work_days_choose_days").format(
            month=month_label(year, month, i18n),
        ),
        reply_markup=get_work_days_calendar_kb(
            year=year,
            month=month,
            selected_days=selected,
            i18n=i18n,
        ),
    )


async def _show_starts_prompt(
        *,
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
) -> None:
    data = await state.get_data()
    await state.set_state(WorkDaysSG.starts_time)
    starts_iso = data.get("wd_starts")
    ends_iso = data.get("wd_ends")
    if starts_iso and ends_iso:
        text = i18n.get("work_days_enter_starts_hint").format(
            starts=_format_hm(time.fromisoformat(starts_iso)),
            ends=_format_hm(time.fromisoformat(ends_iso)),
        )
    else:
        text = i18n.get("work_days_enter_starts")
    await show_hub_prompt(
        message=message,
        state=state,
        text=text,
        reply_markup=get_work_days_cancel_kb(i18n),
    )


async def _show_ends_prompt(
        *,
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
) -> None:
    await state.set_state(WorkDaysSG.ends_time)
    await show_hub_prompt(
        message=message,
        state=state,
        text=i18n.get("work_days_enter_ends"),
        reply_markup=get_work_days_cancel_kb(i18n),
    )


async def _show_confirm(
        *,
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
        mode: str | None = None,
) -> None:
    """mode: clear | off | set. If None, infer from current selection."""
    data = await state.get_data()
    year = int(data["wd_year"])
    month = int(data["wd_month"])
    days = data.get("wd_days") or []
    _, _, removed, added = _day_sets(data)
    await state.set_state(WorkDaysSG.confirming)

    if mode is None:
        if not days:
            mode = "clear"
        elif removed and not added:
            mode = "off"
        else:
            mode = "set"

    if mode == "clear":
        text = i18n.get("work_days_confirm_clear").format(
            month=month_label(year, month, i18n),
        )
    elif mode == "off":
        starts = time.fromisoformat(data["wd_starts"])
        ends = time.fromisoformat(data["wd_ends"])
        text = i18n.get("work_days_confirm_off").format(
            dates=_format_day_list(removed),
            starts=_format_hm(starts),
            ends=_format_hm(ends),
        )
    else:
        starts = time.fromisoformat(data["wd_starts"])
        ends = time.fromisoformat(data["wd_ends"])
        text = i18n.get("work_days_confirm").format(
            count=len(days),
            month=month_label(year, month, i18n),
            starts=_format_hm(starts),
            ends=_format_hm(ends),
        )

    await state.update_data(wd_confirm_mode=mode)
    await show_hub_prompt(
        message=message,
        state=state,
        text=text,
        reply_markup=get_work_days_confirm_kb(i18n),
    )


@work_days_router.callback_query(WorkDaysPadCallback.filter())
async def process_work_days_pad(callback: CallbackQuery) -> None:
    await callback.answer()


@work_days_router.callback_query(
    WorkDaysNavCallback.filter(F.action == "close"),
)
async def process_work_days_close(
        callback: CallbackQuery,
        state: FSMContext,
        user: User,
        i18n: dict[str, str],
        schedule_mode: str,
) -> None:
    await clear_state_keep_hub(state)
    await return_from_list(
        message=callback.message,
        user=user,
        i18n=i18n,
        state=state,
        schedule_mode=schedule_mode,
    )
    await callback.answer()


@work_days_router.callback_query(
    WorkDaysNavCallback.filter(F.action == "cancel"),
    StateFilter(WorkDaysSG),
)
async def process_work_days_cancel(
        callback: CallbackQuery,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    await clear_state_keep_hub(state)
    await state.update_data(
        hub_screen="work_days",
        hub_back="schedule",
        list_return="schedule",
    )
    await show_work_days_months(
        message=callback.message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    await callback.answer()


@work_days_router.callback_query(
    WorkDaysMonthCallback.filter(),
    StateFilter(WorkDaysSG.choosing_month),
)
async def process_work_days_month(
        callback: CallbackQuery,
        callback_data: WorkDaysMonthCallback,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    allowed = set(_month_choices(bot_timezone))
    if (callback_data.year, callback_data.month) not in allowed:
        await callback.answer(
            text=i18n.get("work_days_month_unavailable"),
            show_alert=True,
        )
        return

    rows = await repos.work_dates.list_month(
        master_user_id=user.user_id,
        year=callback_data.year,
        month=callback_data.month,
    )
    selected = sorted(row.work_date.isoformat() for row in rows)
    payload: dict = {
        "wd_year": callback_data.year,
        "wd_month": callback_data.month,
        "wd_days": selected,
        "wd_days_initial": selected,
        "wd_confirm_mode": None,
    }
    if rows:
        payload["wd_starts"] = rows[0].starts_time.isoformat()
        payload["wd_ends"] = rows[0].ends_time.isoformat()
    else:
        payload["wd_starts"] = None
        payload["wd_ends"] = None
    await state.update_data(payload)
    await _show_calendar(message=callback.message, state=state, i18n=i18n)
    await callback.answer()


@work_days_router.callback_query(
    WorkDaysDayCallback.filter(),
    StateFilter(WorkDaysSG.choosing_days),
)
async def process_work_days_toggle(
        callback: CallbackQuery,
        callback_data: WorkDaysDayCallback,
        state: FSMContext,
        i18n: dict[str, str],
) -> None:
    data = await state.get_data()
    year = int(data["wd_year"])
    month = int(data["wd_month"])
    day = callback_data.day
    try:
        selected_date = date(year, month, day)
    except ValueError:
        await callback.answer()
        return

    selected = {
        date.fromisoformat(value)
        for value in data.get("wd_days") or []
    }
    if selected_date in selected:
        selected.remove(selected_date)
    else:
        selected.add(selected_date)
    await state.update_data(
        wd_days=sorted(value.isoformat() for value in selected),
    )
    await _show_calendar(message=callback.message, state=state, i18n=i18n)
    await callback.answer()


@work_days_router.callback_query(
    WorkDaysNavCallback.filter(F.action == "next"),
    StateFilter(WorkDaysSG.choosing_days),
)
async def process_work_days_next(
        callback: CallbackQuery,
        state: FSMContext,
        i18n: dict[str, str],
) -> None:
    data = await state.get_data()
    current, _initial, removed, added = _day_sets(data)

    if not current:
        await _show_confirm(
            message=callback.message,
            state=state,
            i18n=i18n,
            mode="clear",
        )
        await callback.answer()
        return

    if not removed and not added:
        await callback.answer(
            text=i18n.get("work_days_no_changes"),
            show_alert=True,
        )
        return

    # Only days off (no new open days) → keep hours, skip time prompts.
    if removed and not added and data.get("wd_starts") and data.get("wd_ends"):
        await _show_confirm(
            message=callback.message,
            state=state,
            i18n=i18n,
            mode="off",
        )
        await callback.answer()
        return

    # New open day(s) (or first fill) → ask hours for the whole selection.
    await _show_starts_prompt(
        message=callback.message,
        state=state,
        i18n=i18n,
    )
    await callback.answer()


@work_days_router.callback_query(
    WorkDaysNavCallback.filter(F.action == "back"),
    StateFilter(WorkDaysSG.choosing_days),
)
async def process_work_days_back_to_months(
        callback: CallbackQuery,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    await clear_state_keep_hub(state)
    await state.update_data(
        hub_screen="work_days",
        hub_back="schedule",
        list_return="schedule",
    )
    await show_work_days_months(
        message=callback.message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    await callback.answer()


@work_days_router.message(StateFilter(WorkDaysSG.starts_time))
async def process_work_days_starts(
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
) -> None:
    starts = _parse_time(message.text or "")
    await _delete_user_input(message)
    if starts is None:
        await show_hub_prompt(
            message=message,
            state=state,
            text=i18n.get("schedule_invalid_time"),
            reply_markup=get_work_days_cancel_kb(i18n),
        )
        return
    await state.update_data(wd_starts=starts.isoformat())
    await _show_ends_prompt(message=message, state=state, i18n=i18n)


@work_days_router.message(StateFilter(WorkDaysSG.ends_time))
async def process_work_days_ends(
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
) -> None:
    ends = _parse_time(message.text or "")
    await _delete_user_input(message)
    if ends is None:
        await show_hub_prompt(
            message=message,
            state=state,
            text=i18n.get("schedule_invalid_time"),
            reply_markup=get_work_days_cancel_kb(i18n),
        )
        return

    data = await state.get_data()
    starts = time.fromisoformat(data["wd_starts"])
    if ends <= starts:
        await show_hub_prompt(
            message=message,
            state=state,
            text=i18n.get("schedule_invalid_range"),
            reply_markup=get_work_days_cancel_kb(i18n),
        )
        return

    await state.update_data(wd_ends=ends.isoformat())
    await _show_confirm(message=message, state=state, i18n=i18n)


@work_days_router.callback_query(
    WorkDaysNavCallback.filter(F.action == "confirm_no"),
    StateFilter(WorkDaysSG.confirming),
)
async def process_work_days_confirm_no(
        callback: CallbackQuery,
        state: FSMContext,
        i18n: dict[str, str],
) -> None:
    await _show_calendar(message=callback.message, state=state, i18n=i18n)
    await callback.answer()


@work_days_router.callback_query(
    WorkDaysNavCallback.filter(F.action == "confirm_yes"),
    StateFilter(WorkDaysSG.confirming),
)
async def process_work_days_confirm_yes(
        callback: CallbackQuery,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    data = await state.get_data()
    year = int(data["wd_year"])
    month = int(data["wd_month"])
    days = [date.fromisoformat(value) for value in data.get("wd_days") or []]
    _, _, removed, _ = _day_sets(data)
    confirm_mode = data.get("wd_confirm_mode") or ("clear" if not days else "set")

    if days:
        starts = time.fromisoformat(data["wd_starts"])
        ends = time.fromisoformat(data["wd_ends"])
        await repos.work_dates.replace_month(
            master_user_id=user.user_id,
            year=year,
            month=month,
            work_dates=days,
            starts_time=starts,
            ends_time=ends,
        )
        if confirm_mode == "off":
            saved_text = i18n.get("work_days_off_saved").format(
                dates=_format_day_list(removed),
            )
        else:
            saved_text = i18n.get("work_days_saved").format(
                count=len(days),
                month=month_label(year, month, i18n),
                starts=_format_hm(starts),
                ends=_format_hm(ends),
            )
    else:
        await repos.work_dates.replace_month(
            master_user_id=user.user_id,
            year=year,
            month=month,
            work_dates=[],
        )
        saved_text = i18n.get("work_days_cleared").format(
            month=month_label(year, month, i18n),
        )

    await clear_state_keep_hub(state)
    await state.update_data(
        hub_screen="work_days",
        hub_back="schedule",
        list_return="schedule",
    )
    await show_work_days_months(
        message=callback.message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    await callback.answer()
    await callback.message.answer(
        text=saved_text,
        reply_markup=get_hub_dismiss_kb(i18n),
    )


async def _hub_work_days(
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
    await state.update_data(
        hub_screen="work_days",
        hub_back="schedule",
        list_return="schedule",
    )
    await show_work_days_months(
        message=message,
        state=state,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )


register("work_days", _hub_work_days)
