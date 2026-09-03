from locales.en.txt import EN
from locales.ru.txt import RU


def get_translations() -> dict[str, str | dict[str, str]]:
    return {
        "default": "ru",
        "en": EN,
        "ru": RU,
    }


def resolve_language(*, language: str | None, translations: dict) -> str:
    if language is None or language == "default" or language not in translations:
        return translations["default"]
    return language


def resolve_i18n(*, language: str | None, translations: dict) -> dict[str, str]:
    return translations[resolve_language(language=language, translations=translations)]
