from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.domain.enums import UserRole


class AdminRoleCallback(CallbackData, prefix="admrole"):
    role: str


class AdminNavCallback(CallbackData, prefix="admnav"):
    action: str  # cancel


def get_admin_cancel_kb(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("admin_cancel_button"),
                    callback_data=AdminNavCallback(action="cancel").pack(),
                )
            ]
        ]
    )


def get_admin_role_kb(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("admin_role_client_button"),
                    callback_data=AdminRoleCallback(role=UserRole.CLIENT).pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get("admin_role_master_button"),
                    callback_data=AdminRoleCallback(role=UserRole.MASTER).pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get("admin_role_admin_button"),
                    callback_data=AdminRoleCallback(role=UserRole.ADMIN).pack(),
                ),
            ],
        ]
    )
