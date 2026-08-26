from aiogram.types import BotCommand

from app.bot.enums.roles import UserRole


def get_main_menu_commands(i18n: dict[str, str], role: UserRole) -> list[BotCommand]:
    commands = [
        BotCommand(
            command="/start",
            description=i18n.get("/start_description"),
        ),
        BotCommand(
            command="/lang",
            description=i18n.get("/lang_description"),
        ),
        BotCommand(
            command="/help",
            description=i18n.get("/help_description"),
        ),
    ]

    # role does not affect the list yet — placeholder for master/admin commands later.
    _ = role
    return commands
