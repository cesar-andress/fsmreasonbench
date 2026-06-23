"""Shared provider HTTP error classification for batch runners."""

from __future__ import annotations

import urllib.error

TRANSIENT_HTTP_STATUSES = frozenset({429, 500, 502, 503, 504})


class ProviderTransientError(Exception):
    """Retryable provider HTTP failure (rate limit or server unavailable)."""

    def __init__(
        self,
        *,
        http_status: int,
        detail: str,
        provider: str,
    ) -> None:
        self.http_status = http_status
        self.detail = detail
        self.provider = provider
        tag = f"provider_http_{http_status}"
        clipped = detail.strip().replace("\n", " ")
        if len(clipped) > 240:
            clipped = clipped[:237] + "..."
        super().__init__(f"{tag}: {provider} transient API error HTTP {http_status}: {clipped}")


def is_transient_http_status(status_code: int) -> bool:
    return status_code in TRANSIENT_HTTP_STATUSES


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
        )
    return RuntimeError(
        f"{provider} request failed with HTTP {exc.code}: {detail}"
    )
