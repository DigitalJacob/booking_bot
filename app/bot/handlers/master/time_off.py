from datetime import datetime, date, time, timedelta

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.filters.filters import UserRoleFilter
from app.bot.keyboards.time_off import (
    TimeOffNavCallback,
    TimeOffDeleteCallback,
    TimeOffConfirmCallback,
    format_time_off_line,
    get_time_off_list_kb,
    get_time_off_confirm_delete_kb,
)
from app.bot.states.states import TimeOffSG
from app.bot.utils.format import get_zone, combine_local
from app.domain.enums import UserRole
from app.domain.models import User
from app.infrastructure.database.repositories import Repositories


time_off_router = Router(name="master_time_off")
time_off_router.message.filter(UserRoleFilter(UserRole.MASTER))
time_off_router.callback_query.filter(UserRoleFilter(UserRole.MASTER))


def _list_from_dt(bot_timezone: str) -> datetime:
    zone = get_zone(bot_timezone)
    now_local = datetime.now(zone)
    return now_local.replace(hour=0, minute=0, second=0, microsecond=0)


def _parse_date(value: str) -> date | None:
    value = value.strip()
    for fmt in ("%d.%m.%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _format_day_range(starts: date, ends: date) -> str:
    start_d = starts.strftime("%d.%m.%Y")
    end_d = ends.strftime("%d.%m.%Y")
    if start_d == end_d:
        return start_d
    return f"{start_d}-{end_d}"


async def _show_time_off(
        *,
        message: Message,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
        edit: bool,
) -> None:
    rows = await repos.time_off.list_by_master(
        master_user_id=user.user_id,
        from_dt=_list_from_dt(bot_timezone),
    )
    if rows:
        body = "\n".join(
            format_time_off_line(row, i18n, bot_timezone) for row in rows
        )
        text = i18n.get("time_off_header") + "\n\n" + body
    else:
        text = i18n.get("time_off_empty")

    kb = get_time_off_list_kb(
        rows=rows,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    if edit:
        await message.edit_text(text=text, reply_markup=kb)
    else:
        await message.answer(text=text, reply_markup=kb)


@time_off_router.message(Command(commands="time_off"))
async def process_time_off_command(
        message: Message,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    await _show_time_off(
        message=message,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=False,
    )


@time_off_router.callback_query(TimeOffNavCallback.filter(F.action == "close"))
async def process_time_off_close(
        callback: CallbackQuery,
        i18n: dict[str, str],
) -> None:
    await callback.message.edit_text(text=i18n.get("time_off_closed"))
    await callback.answer()


@time_off_router.callback_query(TimeOffDeleteCallback.filter())
async def process_time_off_delete(
        callback: CallbackQuery,
        callback_data: TimeOffDeleteCallback,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
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
    await callback.message.edit_text(
        text=i18n.get("time_off_confirm_delete").format(item=item),
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
    await callback.answer(text=i18n.get("time_off_deleted"))
    await _show_time_off(
        message=callback.message,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=True,
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
) -> None:
    await _show_time_off(
        message=callback.message,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=True,
    )
    await callback.answer()


@time_off_router.callback_query(TimeOffNavCallback.filter(F.action == "add"))
async def process_time_off_add(
        callback: CallbackQuery,
        state: FSMContext,
        i18n: dict[str, str],
) -> None:
    await state.clear()
    await state.set_state(TimeOffSG.starts_date)
    await callback.message.edit_text(text=i18n.get("time_off_enter_starts"))
    await callback.answer()


@time_off_router.message(Command(commands="cancel"), StateFilter(TimeOffSG))
async def process_time_off_cancel_cmd(
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
) -> None:
    await state.clear()
    await message.answer(text=i18n.get("time_off_cancelled"))


@time_off_router.message(StateFilter(TimeOffSG.starts_date))
async def process_time_off_starts(
        message: Message,
        state: FSMContext,
        i18n: dict[str, str],
) -> None:
    starts = _parse_date(message.text or "")
    if starts is None:
        await message.answer(text=i18n.get("time_off_invalid_date"))
        return

    await state.update_data(starts_date=starts.isoformat())
    await state.set_state(TimeOffSG.ends_date)
    await message.answer(text=i18n.get("time_off_enter_ends"))


@time_off_router.message(StateFilter(TimeOffSG.ends_date))
async def process_time_off_ends(
        message: Message,
        state: FSMContext,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    ends = _parse_date(message.text or "")
    if ends is None:
        await message.answer(text=i18n.get("time_off_invalid_date"))
        return

    data = await state.get_data()
    starts = date.fromisoformat(data["starts_date"])
    if ends < starts:
        await message.answer(text=i18n.get("time_off_invalid_range"))
        return

    starts_at = combine_local(starts, time(0, 0), bot_timezone)
    ends_at = combine_local(ends + timedelta(days=1), time(0, 0), bot_timezone)

    await repos.time_off.add(
        master_user_id=user.user_id,
        starts_at=starts_at,
        ends_at=ends_at,
        note=None,
    )

    await state.clear()
    await message.answer(
        text=i18n.get("time_off_add_ok").format(
            when=_format_day_range(starts, ends),
        ),
    )
    await _show_time_off(
        message=message,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=False,
    )
