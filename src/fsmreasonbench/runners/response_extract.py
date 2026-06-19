"""Extract JSON submissions from free-form model text."""

from __future__ import annotations

import json
import re
from typing import Any

_FENCE_PATTERN = re.compile(
    r"```(?:json)?\s*\n?(.*?)\n?```",
    re.DOTALL | re.IGNORECASE,
)


def extract_submission_payload(raw_text: str) -> Any:
    """
    Best-effort extraction of a submission object from model output.

    Returns the parsed dict when possible, otherwise the original string.
    """
    stripped = raw_text.strip()
    if not stripped:
        return raw_text

    direct = _try_parse_object(stripped)
    if direct is not None:
        return direct

    for match in _FENCE_PATTERN.finditer(stripped):
        candidate = match.group(1).strip()
        parsed = _try_parse_object(candidate)
        if parsed is not None:
            return parsed

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end > start:
        parsed = _try_parse_object(stripped[start : end + 1])
        if parsed is not None:
            return parsed

    return raw_text


def _try_parse_object(text: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None
