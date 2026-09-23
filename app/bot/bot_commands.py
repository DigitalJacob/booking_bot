from aiogram.types import BotCommand

from app.domain.enums import UserRole


def get_main_menu_commands(i18n: dict[str, str], role: UserRole) -> list[BotCommand]:
    """Telegram ☰ menu: /start only. Hub navigation is inline buttons."""
    _ = role  # Callers still pass role; menu no longer differs by role.
    return [
        BotCommand(
            command="/start",
            description=i18n.get("/start_description"),
        ),
    ]
