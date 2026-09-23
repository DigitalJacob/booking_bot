from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.domain.enums import UserRole


class HubCallback(CallbackData, prefix="hub"):
    action: str


def _btn(text: str, action: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=text,
        callback_data=HubCallback(action=action).pack(),
    )


def get_hub_home_kb(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    """Single Home button (e.g. after a successful operation)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _btn(i18n.get("hub_home_button"), "root")
            ],
        ]
    )


def get_hub_dismiss_kb(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    """OK on status / book_ok: delete push or restore sticky hub."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn(i18n.get("hub_ok_button"), "dismiss")],
        ]
    )


def get_hub_back_home_row(i18n: dict[str, str]) -> list[InlineKeyboardButton]:
    return [
        _btn(i18n.get("hub_back_button"), "back"),
        _btn(i18n.get("hub_home_button"), "root"),
    ]


def get_hub_back_home_kb(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            get_hub_back_home_row(i18n)
        ],
    )


def get_hub_root_kb(
        *,
        role: UserRole,
        i18n: dict[str, str],
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    if role == UserRole.MASTER:
        rows.append([_btn(i18n.get("hub_bookings_button"), "bookings")])
        rows.append([_btn(i18n.get("hub_services_button"), "services")])
        rows.append([_btn(i18n.get("hub_schedule_section_button"), "schedule")])
    else:
        # client and admin
        rows.append([_btn(i18n.get("hub_book_button"), "book")])
        rows.append([_btn(i18n.get("hub_my_bookings_button"), "my_bookings")])
        rows.append([_btn(i18n.get("hub_profile_section_button"), "profile")])

    if role == UserRole.ADMIN:
        rows.append(
            [
                _btn(i18n.get("hub_moderation_section_button"), "moderation")
            ],
        )

    rows.append([_btn(i18n.get("hub_settings_section_button"), "settings")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_hub_settings_kb(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _btn(i18n.get("hub_lang_button"), "lang")
            ],
            [
                _btn(i18n.get("hub_help_button"), "help")
            ],
            [
                _btn(i18n.get("hub_back_button"), "back")
            ],
        ]
    )


def get_hub_profile_kb(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _btn(i18n.get("hub_profile_show_button"), "profile_show")
            ],
            [
                _btn(i18n.get("hub_profile_edit_button"), "profile_edit")
            ],
            [
                _btn(i18n.get("hub_back_button"), "back")
            ],
        ]
    )


def get_hub_schedule_kb(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _btn(i18n.get("hub_working_hours_button"), "working_hours")
            ],
            [
                _btn(i18n.get("hub_time_off_button"), "time_off")
            ],
            [
                _btn(i18n.get("hub_back_button"), "back")
            ],
        ]
    )


def get_hub_moderation_kb(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn(i18n.get("hub_admin_user_button"), "admin_user")],
            [_btn(i18n.get("hub_admin_set_role_button"), "admin_set_role")],
            [_btn(i18n.get("hub_admin_ban_button"), "admin_ban")],
            [_btn(i18n.get("hub_admin_unban_button"), "admin_unban")],
            get_hub_back_home_row(i18n),
        ]
    )
