"""Shared helpers for Telegram message edit/delete edge cases."""

from __future__ import annotations

from contextlib import suppress

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message


def is_not_modified(exc: TelegramBadRequest) -> bool:
    return "message is not modified" in str(exc).lower()


async def delete_user_input(message: Message) -> None:
    with suppress(TelegramBadRequest):
        await message.delete()
