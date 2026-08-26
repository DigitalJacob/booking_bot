from aiogram import Router
from aiogram.types import Message


others_router = Router(name="others")


@others_router.message()
async def process_unsupported_message(
        message: Message,
        i18n: dict[str, str],
) -> None:
    await message.answer(text=i18n.get("unsupported_message"))
