from __future__ import annotations

import json
import re
from json import JSONDecodeError
from typing import Any


_CODE_BLOCK_RE = re.compile(r"^```(?:json)?\s*|\s*```$", flags=re.IGNORECASE | re.MULTILINE)


def strip_code_fences(raw_text: str) -> str:
    return _CODE_BLOCK_RE.sub("", raw_text.strip()).strip()


def _extract_first_json_object(raw_text: str) -> str:
    start = raw_text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in model response")

    depth = 0
    in_string = False
    escaped = False

    for idx in range(start, len(raw_text)):
        ch = raw_text[idx]

        if escaped:
            escaped = False
            continue

        if ch == "\\":
            escaped = True
            continue

        if ch == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return raw_text[start : idx + 1]

    raise ValueError("Unbalanced JSON object in model response")


def parse_json_response(raw_text: str) -> dict[str, Any]:
    cleaned = strip_code_fences(raw_text)

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except JSONDecodeError:
        pass

    extracted = _extract_first_json_object(cleaned)
    parsed = json.loads(extracted)
    if not isinstance(parsed, dict):
        raise ValueError("Expected JSON object response")
    return parsed
