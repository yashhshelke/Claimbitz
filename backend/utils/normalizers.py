from __future__ import annotations

import re
from typing import Any


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        cleaned = value.strip().replace(",", "")
        cleaned = re.sub(r"[^0-9.\-]", "", cleaned)
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None

    return None


def to_int(value: Any) -> int | None:
    as_float = to_float(value)
    if as_float is None:
        return None
    return int(round(as_float))


def to_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"none", "null", "n/a", "na"}:
        return None
    return text


def to_str_list(value: Any) -> list[str] | None:
    if value is None:
        return None

    if isinstance(value, list):
        items = [to_str(item) for item in value]
        compact = [item for item in items if item]
        return compact or None

    text = to_str(value)
    if not text:
        return None

    # Graceful fallback for comma-separated output.
    parts = [chunk.strip() for chunk in text.split(",")]
    compact = [chunk for chunk in parts if chunk]
    return compact or None
