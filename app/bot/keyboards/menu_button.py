from aiogram.types import BotCommand

from app.bot.enums import UserRole


def get_main_menu_commands(i18n: dict[str, str], role: UserRole) -> list[BotCommand]:
    commands = [
        BotCommand(
            command="/start",
            description=i18n.get("/start_description"),
        ),
    ]
    if role in (UserRole.CLIENT, UserRole.ADMIN):
        commands.append(
            BotCommand(
                command='/book',
                description=i18n.get("/book_description"),
            )
        )
    if role == UserRole.MASTER:
        commands.insert(
            1,
            BotCommand(
                command="/today",
                description=i18n.get("/today_description"),
            ),
        )
        commands.insert(
            2,
            BotCommand(
                command="/add_slot",
                description=i18n.get("/add_slot_description")
            )
        )
        commands.insert(
            3,
            BotCommand(
                command="/services",
                description=i18n.get("/services_description")
            )
        )
    commands.extend(
        [
            BotCommand(
                command="/lang",
                description=i18n.get("/lang_description"),
            ),
            BotCommand(
                command="/help",
                description=i18n.get("/help_description"),
            ),
        ]
    )
    return commands
