from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.domain.models import Service


class CatalogServiceCallback(CallbackData, prefix="csvc"):
    service_id: int


class CatalogNavCallback(CallbackData, prefix="csvnav"):
    action: str  # close | back_list


def get_catalog_list_kb(
        *,
        services: list[Service],
        i18n: dict[str, str],
) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=service.title,
                callback_data=CatalogServiceCallback(
                    service_id=service.id,
                ).pack(),
            )
        ]
        for service in services
    ]
    buttons.append(
        [
            InlineKeyboardButton(
                text=i18n.get("catalog_back_button"),
                callback_data=CatalogNavCallback(action="close").pack(),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_catalog_card_kb(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("catalog_to_list_button"),
                    callback_data=CatalogNavCallback(action="back_list").pack(),
                )
            ]
        ]
    )
