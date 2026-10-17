"""Phone normalization shared by profile and master book-client flows."""

from __future__ import annotations

import re

PHONE_RE = re.compile(r"^\+?\d{10,15}$")


def phone_digits(value: str) -> str:
    """Keep digits only — used for storage and lookup keys."""
    return "".join(ch for ch in value if ch.isdigit())


def normalize_phone(raw: str) -> str | None:
    """Strip spaces/dashes; return display phone or None if invalid."""
    phone = raw.strip().replace(" ", "").replace("-", "")
    if not PHONE_RE.match(phone):
        return None
    return phone
