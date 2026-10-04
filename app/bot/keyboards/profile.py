from aiogram.filters.callback_data import CallbackData
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)


class ProfileNavCallback(CallbackData, prefix="prof"):
    action: str  # cancel | consent_yes | consent_no


def get_profile_cancel_kb(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("profile_cancel_button"),
                    callback_data=ProfileNavCallback(action="cancel").pack(),
                )
            ]
        ]
    )


def get_profile_consent_kb(
        *,
        i18n: dict[str, str],
        policy_url: str = "",
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=i18n.get("profile_consent_accept"),
                callback_data=ProfileNavCallback(action="consent_yes").pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text=i18n.get("profile_consent_decline"),
                callback_data=ProfileNavCallback(action="consent_no").pack(),
            )
        ],
    ]
    if policy_url:
        rows.append(
            [
                InlineKeyboardButton(
                    text=i18n.get("profile_consent_terms_button"),
                    url=policy_url,
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text=i18n.get("profile_cancel_button"),
                callback_data=ProfileNavCallback(action="cancel").pack(),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_phone_kb(i18n: dict[str, str]) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text=i18n.get("profile_share_phone_button"),
                    request_contact=True,
                )
            ],
            [
                KeyboardButton(text=i18n.get("profile_cancel_button"))
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
