from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.domain.models import Service


class MasterServiceCallback(CallbackData, prefix="msvc"):
    service_id: int


class MasterServiceNavCallback(CallbackData, prefix="msvcnav"):
    # add | close | back | toggle | edit | cancel |
    # description | photo | clear_description | clear_photo
    action: str
    service_id: int = 0


def get_service_fsm_cancel_kb(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("services_cancel_button"),
                    callback_data=MasterServiceNavCallback(action="cancel").pack(),
                )
            ]
        ]
    )


def get_service_description_kb(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("services_clear_description_button"),
                    callback_data=MasterServiceNavCallback(
                        action="clear_description",
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get("services_cancel_button"),
                    callback_data=MasterServiceNavCallback(action="cancel").pack(),
                )
            ],
        ]
    )


def get_service_photo_kb(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("services_clear_photo_button"),
                    callback_data=MasterServiceNavCallback(
                        action="clear_photo",
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get("services_cancel_button"),
                    callback_data=MasterServiceNavCallback(action="cancel").pack(),
                )
            ],
        ]
    )


def get_services_list_kb(
        *,
        services: list[Service],
        i18n: dict[str, str],
) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    for service in services:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=service.title,
                    callback_data=MasterServiceCallback(
                        service_id=service.id,
                    ).pack(),
                )
            ]
        )
    buttons.append(
        [
            InlineKeyboardButton(
                text=i18n.get("services_back_button"),
                callback_data=MasterServiceNavCallback(action="close").pack(),
            ),
            InlineKeyboardButton(
                text=i18n.get("services_add_button"),
                callback_data=MasterServiceNavCallback(action="add").pack(),
            ),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_service_card_kb(
        *,
        service: Service,
        i18n: dict[str, str],
) -> InlineKeyboardMarkup:
    toggle_text = (
        i18n.get("services_deactivate_button")
        if service.is_active
        else i18n.get("services_activate_button")
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("services_edit_button"),
                    callback_data=MasterServiceNavCallback(
                        action="edit",
                        service_id=service.id,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get("services_description_button"),
                    callback_data=MasterServiceNavCallback(
                        action="description",
                        service_id=service.id,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get("services_photo_button"),
                    callback_data=MasterServiceNavCallback(
                        action="photo",
                        service_id=service.id,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=toggle_text,
                    callback_data=MasterServiceNavCallback(
                        action="toggle",
                        service_id=service.id,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get("services_back_button"),
                    callback_data=MasterServiceNavCallback(
                        action="back",
                        service_id=service.id,
                    ).pack(),
                )
            ]
        ]
    )
