"""Shared provider HTTP error classification for batch runners."""

from __future__ import annotations

import email.utils
import json
import re
import time
import urllib.error
from dataclasses import dataclass
from typing import Any

TRANSIENT_HTTP_STATUSES = frozenset({429, 500, 502, 503, 504})
QUOTA_KEYWORDS = ("quota", "billing", "resource_exhausted", "exceeded your current quota")
INSUFFICIENT_CREDIT_KEYWORDS = (
    "credit balance is too low",
    "credit balance too low",
    "insufficient credit",
    "insufficient balance",
)
PROVIDER_INFRASTRUCTURE_ERROR_TYPES = frozenset(
    {"quota_exceeded", "insufficient_credit", "authentication_error"}
)
NON_RETRYABLE_PROVIDER_ERROR_TYPES = frozenset({"quota_exceeded", "insufficient_credit"})
DEFAULT_MAX_PROVIDER_RETRY_DELAY_SECONDS = 120.0

_PROVIDER_HTTP_RUNTIME = re.compile(
    r"(?P<provider>anthropic|gemini|openai) request failed with HTTP (?P<status>\d+):\s*(?P<detail>.*)",
    re.DOTALL,
)
_PROVIDER_HTTP_TRANSIENT = re.compile(
    r"provider_http_(?P<status>\d+):\s*(?P<provider>anthropic|gemini|openai)\s+transient API error "
    r"HTTP \d+ \((?P<error_type>[a-z_]+)\)",
    re.IGNORECASE,
)


class ProviderTransientError(Exception):
    """Provider HTTP failure surfaced to batch runners (retryable or fail-fast)."""

    def __init__(
        self,
        *,
        http_status: int,
        detail: str,
        provider: str,
        error_type: str,
        retry_after_seconds: float | None = None,
    ) -> None:
        self.http_status = http_status
        self.detail = detail
        self.provider = provider
        self.error_type = error_type
        self.retry_after_seconds = retry_after_seconds
        tag = f"provider_http_{http_status}"
        clipped = detail.strip().replace("\n", " ")
        if len(clipped) > 240:
            clipped = clipped[:237] + "..."
        super().__init__(
            f"{tag}: {provider} transient API error HTTP {http_status} "
            f"({error_type}): {clipped}"
        )


@dataclass(frozen=True, slots=True)
class ProviderFailureClassification:
    provider_error_type: str
    http_status: int | None
    message: str


def is_transient_http_status(status_code: int) -> bool:
    return status_code in TRANSIENT_HTTP_STATUSES


def _parse_provider_error_json_type(detail: str) -> str | None:
    try:
        payload = json.loads(detail)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    error = payload.get("error")
    if not isinstance(error, dict):
        return None
    error_type = error.get("type")
    if error_type == "rate_limit_error":
        return "rate_limit"
    if error_type in {"insufficient_quota", "rate_limit_exceeded"}:
        return "quota_exceeded" if "quota" in str(error_type) else "rate_limit"
    if error_type in {"invalid_request_error", "authentication_error"}:
        message = str(error.get("message", "")).lower()
        if any(keyword in message for keyword in INSUFFICIENT_CREDIT_KEYWORDS):
            return "insufficient_credit"
        if error_type == "authentication_error":
            return "authentication_error"
    return None


def infer_429_error_type(detail: str) -> str:
    parsed = _parse_provider_error_json_type(detail)
    if parsed is not None:
        return parsed
    lowered = detail.lower()
    if any(keyword in lowered for keyword in QUOTA_KEYWORDS):
        return "quota_exceeded"
    if "rate_limit" in lowered:
        return "rate_limit"
    return "rate_limit"


def infer_provider_error_type(status_code: int, detail: str) -> str:
    parsed = _parse_provider_error_json_type(detail)
    if parsed is not None:
        return parsed
    lowered = detail.lower()
    if status_code == 429:
        return infer_429_error_type(detail)
    if status_code == 400 and any(keyword in lowered for keyword in INSUFFICIENT_CREDIT_KEYWORDS):
        return "insufficient_credit"
    if status_code in {401, 403}:
        return "authentication_error"
    return "unavailable"


def is_provider_infrastructure_error(status_code: int, detail: str) -> bool:
    if is_transient_http_status(status_code):
        return True
    return infer_provider_error_type(status_code, detail) in PROVIDER_INFRASTRUCTURE_ERROR_TYPES


def is_retryable_provider_error(error_type: str) -> bool:
    """Quota/credit exhaustion will not recover during a single run; do not backoff-retry it."""
    return error_type not in NON_RETRYABLE_PROVIDER_ERROR_TYPES


def parse_retry_after_seconds(headers: Any | None) -> float | None:
    if headers is None:
        return None
    raw = headers.get("Retry-After") or headers.get("retry-after")
    if raw is None:
        return None
    value = raw.strip()
    if not value:
        return None
    try:
        return max(0.0, float(int(value)))
    except ValueError:
        try:
            parsed = email.utils.parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
        return max(0.0, parsed.timestamp() - time.time())


def classify_http_error(
    *,
    provider: str,
    exc: urllib.error.HTTPError,
) -> Exception:
    detail = exc.read().decode("utf-8", errors="replace")
    error_type = infer_provider_error_type(exc.code, detail)
    if is_provider_infrastructure_error(exc.code, detail):
        return ProviderTransientError(
            http_status=exc.code,
            detail=detail,
            provider=provider,
            error_type=error_type,
            retry_after_seconds=parse_retry_after_seconds(exc.headers),
        )
    return RuntimeError(
        f"{provider} request failed with HTTP {exc.code}: {detail}"
    )


def infer_provider_error_from_message(message: str) -> ProviderFailureClassification | None:
    """Detect provider/API failures recorded in runner error strings."""
    text = message.strip()
    if not text:
        return None

    transient_match = _PROVIDER_HTTP_TRANSIENT.search(text)
    if transient_match is not None:
        return ProviderFailureClassification(
            provider_error_type=transient_match.group("error_type"),
            http_status=int(transient_match.group("status")),
            message=text,
        )

    runtime_match = _PROVIDER_HTTP_RUNTIME.match(text)
    if runtime_match is None:
        return None
    status_code = int(runtime_match.group("status"))
    detail = runtime_match.group("detail")
    if not is_provider_infrastructure_error(status_code, detail):
        return None
    return ProviderFailureClassification(
        provider_error_type=infer_provider_error_type(status_code, detail),
        http_status=status_code,
        message=text,
    )


def classify_generate_failure(exc: Exception) -> ProviderFailureClassification | None:
    if isinstance(exc, ProviderTransientError):
        return ProviderFailureClassification(
            provider_error_type=exc.error_type,
            http_status=exc.http_status,
            message=str(exc),
        )
    if isinstance(exc, RuntimeError):
        return infer_provider_error_from_message(str(exc))
    return None


def resolve_provider_retry_delay_seconds(
    attempt: int,
    base_seconds: float,
    *,
    retry_after_seconds: float | None = None,
    max_delay_seconds: float = DEFAULT_MAX_PROVIDER_RETRY_DELAY_SECONDS,
) -> float:
    """Exponential backoff with jitter, honoring Retry-After up to a cap."""
    from fsmreasonbench.runners.item_watchdog import provider_retry_delay_seconds

    backoff = min(provider_retry_delay_seconds(attempt, base_seconds), max_delay_seconds)
    if retry_after_seconds is None:
        return backoff
    return min(max(backoff, retry_after_seconds), max_delay_seconds)
