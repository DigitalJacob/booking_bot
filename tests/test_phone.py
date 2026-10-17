from app.bot.utils.phone import normalize_phone, phone_digits


def test_phone_digits_strips_non_digits():
    assert phone_digits("+7 (999) 123-45-67") == "79991234567"
    assert phone_digits("abc") == ""


def test_normalize_phone_accepts_plus_and_digits():
    assert normalize_phone(" +7 999 123-45-67 ") == "+79991234567"
    assert normalize_phone("79991234567") == "79991234567"


def test_normalize_phone_rejects_invalid():
    assert normalize_phone("12345") is None
    assert normalize_phone("not-a-phone") is None
    assert normalize_phone("+1234567890123456") is None
