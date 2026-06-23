"""Shared provider HTTP error classification for batch runners."""

from __future__ import annotations

import email.utils
import time
import urllib.error

TRANSIENT_HTTP_STATUSES = frozenset({429, 500, 502, 503, 504})
QUOTA_KEYWORDS = ("quota", "billing", "resource_exhausted", "exceeded your current quota")


class ProviderTransientError(Exception):
    """Retryable provider HTTP failure (rate limit, quota, or server unavailable)."""

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


def is_transient_http_status(status_code: int) -> bool:
    return status_code in TRANSIENT_HTTP_STATUSES


def infer_429_error_type(detail: str) -> str:
    lowered = detail.lower()
    if any(keyword in lowered for keyword in QUOTA_KEYWORDS):
        return "quota_exceeded"
    return "rate_limit"


def infer_provider_error_type(status_code: int, detail: str) -> str:
    if status_code == 429:
        return infer_429_error_type(detail)
    return "unavailable"


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
    if is_transient_http_status(exc.code):
        return ProviderTransientError(
            http_status=exc.code,
            detail=detail,
            provider=provider,
            error_type=infer_provider_error_type(exc.code, detail),
            retry_after_seconds=parse_retry_after_seconds(exc.headers),
        )
    return RuntimeError(
        f"{provider} request failed with HTTP {exc.code}: {detail}"
    )


def resolve_provider_retry_delay_seconds(
    attempt: int,
    base_seconds: float,
    *,
    retry_after_seconds: float | None = None,
) -> float:
    """Exponential backoff with jitter, honoring Retry-After when present."""
    from fsmreasonbench.runners.item_watchdog import provider_retry_delay_seconds

    backoff = provider_retry_delay_seconds(attempt, base_seconds)
    if retry_after_seconds is None:
        return backoff
    return max(backoff, retry_after_seconds)
