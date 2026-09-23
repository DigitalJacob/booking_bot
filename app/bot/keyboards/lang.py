from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_lang_settings_kb(
        i18n: dict[str, str],
        locales: list[str],
        checked: str | None,
) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []

    for locale in sorted(locales):
        if locale == "default":
            continue
        label = i18n.get(locale, locale)
        prefix = "🔘" if locale == checked else "⚪️"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{prefix} {label}",
                    callback_data=locale,
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text=i18n.get("cancel_lang_button_text"),
                callback_data="cancel_lang_button_data",
            ),
            InlineKeyboardButton(
                text=i18n.get("save_lang_button_text"),
                callback_data="save_lang_button_data",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)
