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
    Harmless wrappers (markdown fences, leading/trailing prose, certificate
    encoded as a JSON object string) may be stripped; semantically invalid
    certificates are never invented or coerced from plain text.
    """
    stripped = raw_text.strip()
    if not stripped:
        return raw_text

    direct = _try_parse_object(stripped)
    if direct is not None:
        return _normalize_wrappers(direct)

    for match in _FENCE_PATTERN.finditer(stripped):
        candidate = match.group(1).strip()
        parsed = _try_parse_object(candidate)
        if parsed is not None:
            return _normalize_wrappers(parsed)
        balanced = _first_balanced_json_object(candidate)
        if balanced is not None:
            return balanced

    balanced = _first_balanced_json_object(stripped)
    if balanced is not None:
        return balanced

    return raw_text


def _first_balanced_json_object(text: str) -> dict[str, Any] | None:
    """Return the first top-level JSON object found via balanced decoding."""
    decoder = json.JSONDecoder()
    idx = 0
    while idx < len(text):
        brace = text.find("{", idx)
        if brace == -1:
            break
        try:
            obj, end = decoder.raw_decode(text, brace)
        except json.JSONDecodeError:
            idx = brace + 1
            continue
        if isinstance(obj, dict):
            return _normalize_wrappers(obj)
        idx = end
    return None


def _normalize_wrappers(payload: dict[str, Any]) -> dict[str, Any]:
    """Unwrap certificate when it is a safely parseable JSON object string."""
    certificate = payload.get("certificate")
    if not isinstance(certificate, str):
        return payload
    inner = _try_parse_object(certificate.strip())
    if inner is None:
        return payload
    normalized = dict(payload)
    normalized["certificate"] = inner
    return normalized


def _try_parse_object(text: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None
