from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class GapNavCallback(CallbackData, prefix="gap"):
    action: str  # edit | close | cancel


def get_gap_view_kb(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("gap_edit_button"),
                    callback_data=GapNavCallback(action="edit").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get("gap_back_button"),
                    callback_data=GapNavCallback(action="close").pack(),
                )
            ],
        ]
    )


def get_gap_cancel_kb(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("gap_cancel_button"),
                    callback_data=GapNavCallback(action="cancel").pack(),
                )
            ]
        ]
    )
