from aiogram import Router
from aiogram.types import Message


unsupported_router = Router(name="unsupported")


@unsupported_router.message()
async def process_unsupported_message(
        message: Message,
        i18n: dict[str, str],
) -> None:
    await message.answer(text=i18n.get("unsupported_message"))
