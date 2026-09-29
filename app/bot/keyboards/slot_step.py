from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class SlotStepNavCallback(CallbackData, prefix="sstep"):
    action: str  # edit | close | cancel | default


def get_slot_step_view_kb(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("slot_step_edit_button"),
                    callback_data=SlotStepNavCallback(action="edit").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get("slot_step_back_button"),
                    callback_data=SlotStepNavCallback(action="close").pack(),
                )
            ],
        ]
    )


def get_slot_step_enter_kb(i18n: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get("slot_step_default_button"),
                    callback_data=SlotStepNavCallback(action="default").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=i18n.get("slot_step_cancel_button"),
                    callback_data=SlotStepNavCallback(action="cancel").pack(),
                )
            ],
        ]
    )
