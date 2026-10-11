from __future__ import annotations

from datetime import date

from aiogram import F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.master.work_days.common import format_hm
from app.bot.handlers.master.work_days.router import work_days_router
from app.bot.keyboards.hub import get_hub_dismiss_kb
from app.bot.keyboards.work_days import (
    WorkDaysDayCallback,
    WorkDaysNavCallback,
    WorkDaysPadCallback,
    get_work_days_calendar_kb,
    month_label,
)
from app.bot.states.states import WorkDaysSG
from app.bot.utils.hub_nav import show_hub_prompt
from app.domain.models import User
from app.infrastructure.database.repositories import Repositories


async def show_work_days_calendar(
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


@work_days_router.callback_query(WorkDaysPadCallback.filter())
async def process_work_days_pad(callback: CallbackQuery) -> None:
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

    selected = {date.fromisoformat(value) for value in data.get("wd_days") or []}
    if selected_date in selected:
        selected.remove(selected_date)
    else:
        selected.add(selected_date)
    await state.update_data(
        wd_days=sorted(value.isoformat() for value in selected),
    )
    await show_work_days_calendar(message=callback.message, state=state, i18n=i18n)
    await callback.answer()


@work_days_router.callback_query(
    WorkDaysNavCallback.filter(F.action == "summary"),
    StateFilter(WorkDaysSG.choosing_days),
)
async def process_work_days_summary(
    callback: CallbackQuery,
    state: FSMContext,
    repos: Repositories,
    user: User,
    i18n: dict[str, str],
) -> None:
    data = await state.get_data()
    year = int(data["wd_year"])
    month = int(data["wd_month"])
    label = month_label(year, month, i18n)
    rows = await repos.work_dates.list_month(
        master_user_id=user.user_id,
        year=year,
        month=month,
    )
    if not rows:
        text = i18n.get("work_days_summary_empty").format(month=label)
    else:
        lines = [
            i18n.get("work_days_summary_header").format(month=label),
            "",
        ]
        for row in rows:
            lines.append(
                i18n.get("work_days_summary_item").format(
                    date=row.work_date.strftime("%d.%m"),
                    starts=format_hm(row.starts_time),
                    ends=format_hm(row.ends_time),
                )
            )
        text = "\n".join(lines)

    await callback.message.answer(
        text=text,
        reply_markup=get_hub_dismiss_kb(i18n),
    )
    await callback.answer()
