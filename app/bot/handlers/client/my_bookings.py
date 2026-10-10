from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from app.bot.handlers.common.appointment_cancel import (
    SOURCE_MY_BOOKINGS,
    start_appointment_cancel,
)
from app.bot.handlers.common.hub import return_from_list
from app.bot.keyboards.my_bookings import (
    ClientAppointmentCallback,
    get_my_booking_card_kb,
    get_my_bookings_list_kb,
)
from app.bot.keyboards.schedule import WEEKDAY_KEYS
from app.bot.utils.format import format_dt, status_label, to_local
from app.bot.utils.hub_registry import register
from app.domain.enums import AppointmentStatus, UserRole
from app.domain.models import Appointment, User
from app.domain.services.booking import BookingService
from app.infrastructure.database.repositories import Repositories

my_bookings_router = Router(name="client_my_bookings")

_BUTTON_LABEL_MAX = 64


def _booking_when_parts(
        *,
        appointment: Appointment,
        i18n: dict[str, str],
        bot_timezone: str,
) -> tuple[str, str]:
    local = to_local(appointment.starts_at, bot_timezone)
    weekday = i18n.get(WEEKDAY_KEYS[local.isoweekday()])
    when = local.strftime("%d.%m %H:%M")
    return weekday, when


def _list_button_label(
        *,
        weekday: str,
        when: str,
        title: str,
        i18n: dict[str, str],
) -> str:
    text = i18n.get("my_bookings_list_button").format(
        weekday=weekday,
        when=when,
        title=title,
    )
    if len(text) > _BUTTON_LABEL_MAX:
        return text[: _BUTTON_LABEL_MAX - 1] + "…"
    return text


async def build_my_bookings_list(
        *,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
) -> tuple[str, InlineKeyboardMarkup]:
    booking = BookingService(repos)
    appointments = await booking.list_client_appointments(
        client_user_id=user.user_id,
    )
    if not appointments:
        return (
            i18n.get("my_bookings_empty"),
            get_my_bookings_list_kb(
                appointments=[],
                labels={},
                i18n=i18n,
            ),
        )

    labels: dict[int, str] = {}
    lines: list[str] = []
    for appointment in appointments:
        service = await repos.services.get_service(
            service_id=appointment.service_id,
        )
        title = service.title if service else "?"
        weekday, when = _booking_when_parts(
            appointment=appointment,
            i18n=i18n,
            bot_timezone=bot_timezone,
        )
        labels[appointment.id] = _list_button_label(
            weekday=weekday,
            when=when,
            title=title,
            i18n=i18n,
        )
        lines.append(
            i18n.get("my_bookings_item").format(
                weekday=weekday,
                when=when,
                title=title,
                status=status_label(appointment.status, i18n),
            )
        )
    text = i18n.get("my_bookings_header") + "\n\n" + "\n".join(lines)
    kb = get_my_bookings_list_kb(
        appointments=appointments,
        labels=labels,
        i18n=i18n,
    )
    return text, kb


async def show_my_bookings_list(
        *,
        message: Message,
        repos: Repositories,
        user: User,
        i18n: dict[str, str],
        bot_timezone: str,
        edit: bool,
) -> None:
    text, kb = await build_my_bookings_list(
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    if edit:
        await message.edit_text(text=text, reply_markup=kb)
    else:
        await message.answer(text=text, reply_markup=kb)


async def build_my_booking_card(
        *,
        appointment: Appointment,
        repos: Repositories,
        i18n: dict[str, str],
        bot_timezone: str,
) -> tuple[str, InlineKeyboardMarkup]:
    service = await repos.services.get_service(service_id=appointment.service_id)
    title = service.title if service else "?"
    text = i18n.get("my_bookings_card").format(
        when=format_dt(appointment.starts_at, bot_timezone),
        title=title,
        status=status_label(appointment.status, i18n),
    )
    return text, get_my_booking_card_kb(appointment=appointment, i18n=i18n)


async def show_my_booking_card(
        *,
        message: Message,
        appointment: Appointment,
        repos: Repositories,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    text, kb = await build_my_booking_card(
        appointment=appointment,
        repos=repos,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    await message.edit_text(text=text, reply_markup=kb)


@my_bookings_router.callback_query(
    ClientAppointmentCallback.filter(F.action == "open"),
)
async def process_open(
        callback: CallbackQuery,
        callback_data: ClientAppointmentCallback,
        repos: Repositories,
        user: User | None,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    if user is None:
        await callback.answer(
            text=i18n.get("book_need_start"),
            show_alert=True,
        )
        return

    appointment = await repos.appointments.get_appointment(
        appointment_id=callback_data.appointment_id,
    )
    if (
        appointment is None
        or appointment.client_user_id != user.user_id
    ):
        await callback.answer(
            text=i18n.get("my_bookings_action_failed"),
            show_alert=True,
        )
        return

    await show_my_booking_card(
        message=callback.message,
        appointment=appointment,
        repos=repos,
        i18n=i18n,
        bot_timezone=bot_timezone,
    )
    await callback.answer()


@my_bookings_router.callback_query(
    ClientAppointmentCallback.filter(F.action == "back"),
)
async def process_back(
        callback: CallbackQuery,
        repos: Repositories,
        user: User | None,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    if user is None:
        await callback.answer(
            text=i18n.get("book_need_start"),
            show_alert=True,
        )
        return

    await show_my_bookings_list(
        message=callback.message,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone,
        edit=True,
    )
    await callback.answer()


@my_bookings_router.callback_query(
    ClientAppointmentCallback.filter(F.action == "close"),
)
async def process_close(
        callback: CallbackQuery,
        state: FSMContext,
        user: User | None,
        i18n: dict[str, str],
) -> None:
    if user is None:
        await callback.answer(
            text=i18n.get("book_need_start"),
            show_alert=True,
        )
        return

    await return_from_list(
        message=callback.message,
        user=user,
        i18n=i18n,
        state=state,
    )
    await callback.answer()


@my_bookings_router.callback_query(
    ClientAppointmentCallback.filter(F.action == "cancel"),
)
async def process_client_cancel(
        callback: CallbackQuery,
        callback_data: ClientAppointmentCallback,
        translations: dict,
        repos: Repositories,
        user: User | None,
        i18n: dict[str, str],
        bot_timezone: str,
) -> None:
    await start_appointment_cancel(
        callback=callback,
        repos=repos,
        user=user,
        i18n=i18n,
        translations=translations,
        bot_timezone=bot_timezone,
        appointment_id=callback_data.appointment_id,
        source=SOURCE_MY_BOOKINGS,
        mode="cancel",
        allowed_statuses=frozenset(
            {
                AppointmentStatus.PENDING,
                AppointmentStatus.CONFIRMED,
            }
        ),
    )


async def _hub_my_bookings(
        *,
        message: Message,
        user: User,
        i18n: dict[str, str],
        state: FSMContext,
        repos: Repositories | None = None,
        bot_timezone: str | None = None,
        **_,
) -> None:
    if user.role != UserRole.CLIENT or repos is None:
        return
    await state.update_data(
        hub_screen="my_bookings",
        hub_back="root",
        list_return="root",
    )
    await show_my_bookings_list(
        message=message,
        repos=repos,
        user=user,
        i18n=i18n,
        bot_timezone=bot_timezone or "UTC",
        edit=True,
    )


register("my_bookings", _hub_my_bookings)
