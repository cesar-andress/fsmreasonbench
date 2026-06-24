"""Anthropic Messages API backend for frontier R0/R1/R2 runs.

R1/R2 use the same JSON two-phase track protocol as Ollama (tool_plan then
final_submission); the runner executes registered tools locally between phases.
This module does not use Anthropic native ``tool_use`` blocks.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from fsmreasonbench.runners.provider_errors import classify_http_error

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"
DEFAULT_ANTHROPIC_MODEL = "claude-opus-4-20250514"


@dataclass(frozen=True, slots=True)
class AnthropicConfig:
    api_key: str
    model: str
    temperature: float = 0.0
    timeout: float | None = 120.0
    max_tokens: int = 8192


def require_anthropic_api_key() -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY environment variable is required for provider=anthropic"
        )
    return api_key


def resolve_anthropic_model(model: str) -> str:
    candidate = model.strip()
    if not candidate or candidate.lower() in {"default", "opus", "claude-opus"}:
        return os.environ.get("ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL).strip() or (
            DEFAULT_ANTHROPIC_MODEL
        )
    return candidate


def build_anthropic_messages_request(
    *,
    prompt: str,
    model: str,
    max_tokens: int,
    temperature: float,
) -> dict[str, Any]:
    return {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}],
    }


def extract_anthropic_response_text(payload: dict[str, Any]) -> str:
    """Map Anthropic Messages API JSON to plain text for the existing extractor."""
    content = payload.get("content")
    if not isinstance(content, list):
        raise ValueError("anthropic response missing content array")
    parts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text" and isinstance(block.get("text"), str):
            parts.append(block["text"])
    if not parts:
        raise ValueError("anthropic response contained no text blocks")
    return "".join(parts)


class HttpAnthropicClient:
    """Minimal Anthropic Messages API client using stdlib HTTP."""

    def __init__(self, config: AnthropicConfig) -> None:
        if not config.api_key.strip():
            raise ValueError("anthropic api_key must be non-empty")
        if config.max_tokens < 1:
            raise ValueError("max_tokens must be >= 1")
        self._config = config

    def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float | None = None,
        timeout: float | None = None,
    ) -> str:
        resolved_model = resolve_anthropic_model(model or self._config.model)
        resolved_temperature = (
            self._config.temperature if temperature is None else temperature
        )
        resolved_timeout = self._config.timeout if timeout is None else timeout
        body = build_anthropic_messages_request(
            prompt=prompt,
            model=resolved_model,
            max_tokens=self._config.max_tokens,
            temperature=resolved_temperature,
        )
        request = urllib.request.Request(
            ANTHROPIC_MESSAGES_URL,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": self._config.api_key,
                "anthropic-version": ANTHROPIC_API_VERSION,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=resolved_timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except TimeoutError as exc:
            if resolved_timeout is None:
                raise TimeoutError("anthropic request timed out") from exc
            raise TimeoutError(
                f"anthropic request exceeded timeout of {resolved_timeout:g}s"
            ) from exc
        except urllib.error.HTTPError as exc:
            raise classify_http_error(provider="anthropic", exc=exc) from exc
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, TimeoutError):
                if resolved_timeout is None:
                    raise TimeoutError("anthropic request timed out") from exc
                raise TimeoutError(
                    f"anthropic request exceeded timeout of {resolved_timeout:g}s"
                ) from exc
            raise RuntimeError(f"anthropic request failed: {exc}") from exc

        if not isinstance(payload, dict):
            raise RuntimeError("anthropic response was not a JSON object")
        return extract_anthropic_response_text(payload)
