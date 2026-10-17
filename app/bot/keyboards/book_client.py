from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class BookClientNavCallback(CallbackData, prefix="mbcn"):
    action: str  # cancel | new | create_manual


class BookClientPickCallback(CallbackData, prefix="mbcp"):
    kind: str  # tg | manual
    ref_id: int


def get_book_client_cancel_kb(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("book_client_cancel_button"),
                    callback_data=BookClientNavCallback(action="cancel").pack(),
                )
            ]
        ]
    )


def get_book_client_results_kb(
    *,
    hits: list[tuple[str, int, str]],
    i18n: dict[str, str],
) -> InlineKeyboardMarkup:
    """hits: (kind, ref_id, button_label)."""
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=label,
                callback_data=BookClientPickCallback(kind=kind, ref_id=ref_id).pack(),
            )
        ]
        for kind, ref_id, label in hits
    ]
    rows.append(
        [
            InlineKeyboardButton(
                text=i18n.get("book_client_new_button"),
                callback_data=BookClientNavCallback(action="new").pack(),
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text=i18n.get("book_client_cancel_button"),
                callback_data=BookClientNavCallback(action="cancel").pack(),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_book_client_existing_manual_kb(
    *,
    manual_client_id: int,
    i18n: dict[str, str],
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("book_client_use_existing_button"),
                    callback_data=BookClientPickCallback(
                        kind="manual",
                        ref_id=manual_client_id,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get("book_client_cancel_button"),
                    callback_data=BookClientNavCallback(action="cancel").pack(),
                )
            ],
        ]
    )


def get_book_client_tg_offer_kb(
    *,
    user_id: int,
    i18n: dict[str, str],
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("book_client_use_tg_button"),
                    callback_data=BookClientPickCallback(
                        kind="tg",
                        ref_id=user_id,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get("book_client_create_manual_button"),
                    callback_data=BookClientNavCallback(action="create_manual").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get("book_client_cancel_button"),
                    callback_data=BookClientNavCallback(action="cancel").pack(),
                )
            ],
        ]
    )
