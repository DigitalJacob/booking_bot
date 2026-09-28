from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class MinLeadNavCallback(CallbackData, prefix="mlead"):
    action: str  # edit | close | cancel


def get_min_lead_view_kb(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("min_lead_edit_button"),
                    callback_data=MinLeadNavCallback(action="edit").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get("min_lead_back_button"),
                    callback_data=MinLeadNavCallback(action="close").pack(),
                )
            ],
        ]
    )


def get_min_lead_cancel_kb(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("min_lead_cancel_button"),
                    callback_data=MinLeadNavCallback(action="cancel").pack(),
                )
            ]
        ]
    )
