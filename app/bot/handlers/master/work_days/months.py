from __future__ import annotations

from datetime import datetime

from aiogram import F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.common.hub import return_from_list
from app.bot.handlers.master.work_days.calendar import show_work_days_calendar
from app.bot.handlers.master.work_days.common import MONTH_CHOICES
from app.bot.handlers.master.work_days.router import work_days_router
from app.bot.keyboards.work_days import (
    WorkDaysMonthCallback,
    WorkDaysNavCallback,
    get_work_days_months_kb,
)
from app.bot.states.states import WorkDaysSG
from app.bot.utils.format import get_zone
from app.bot.utils.hub_nav import clear_state_keep_hub, show_hub_prompt
from app.bot.utils.hub_registry import register
from app.domain.enums import UserRole
from app.domain.models import User
from app.infrastructure.database.repositories import Repositories


def _month_choices(bot_timezone: str) -> list[tuple[int, int]]:
    today = datetime.now(get_zone(bot_timezone)).date()
    year, month = today.year, today.month
    result: list[tuple[int, int]] = []
    for _ in range(MONTH_CHOICES):
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
    await state.update_data(
        wd_year=callback_data.year,
        wd_month=callback_data.month,
        wd_days=selected,
        wd_days_initial=selected,
        wd_confirm_mode=None,
        # Hours come only from the starts/ends prompts for newly added days.
        wd_starts=None,
        wd_ends=None,
    )
    await show_work_days_calendar(
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
