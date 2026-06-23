"""Google Gemini API backend for frontier R0 smoke runs."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from fsmreasonbench.runners.provider_errors import classify_http_error

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


@dataclass(frozen=True, slots=True)
class GeminiConfig:
    api_key: str
    model: str
    temperature: float = 0.0
    timeout: float | None = 120.0
    max_tokens: int = 8192


def require_gemini_api_key() -> str:
    for env_name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        api_key = os.environ.get(env_name, "").strip()
        if api_key:
            return api_key
    raise ValueError(
        "GEMINI_API_KEY or GOOGLE_API_KEY environment variable is required "
        "for provider=gemini"
    )


def resolve_gemini_model(model: str) -> str:
    candidate = model.strip()
    aliases = {"default", "flash", "gemini-flash", "gemini-2.5-flash"}
    if not candidate or candidate.lower() in aliases:
        return os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip() or (
            DEFAULT_GEMINI_MODEL
        )
    return candidate


def build_gemini_generate_content_request(
    *,
    prompt: str,
    max_tokens: int,
    temperature: float,
) -> dict[str, Any]:
    return {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            "responseMimeType": "application/json",
        },
    }


def gemini_generate_content_url(model: str, api_key: str) -> str:
    resolved_model = resolve_gemini_model(model)
    query = urllib.parse.urlencode({"key": api_key})
    return f"{GEMINI_API_BASE}/models/{resolved_model}:generateContent?{query}"


def extract_gemini_response_text(payload: dict[str, Any]) -> str:
    """Map Gemini generateContent JSON to plain text for the existing extractor."""
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("gemini response missing candidates")
    content = candidates[0].get("content")
    if not isinstance(content, dict):
        raise ValueError("gemini response missing candidate content")
    parts = content.get("parts")
    if not isinstance(parts, list):
        raise ValueError("gemini response missing content parts")
    texts: list[str] = []
    for part in parts:
        if isinstance(part, dict) and isinstance(part.get("text"), str):
            texts.append(part["text"])
    if not texts:
        raise ValueError("gemini response contained no text parts")
    return "".join(texts)


class HttpGeminiClient:
    """Minimal Gemini generateContent client using stdlib HTTP."""

    def __init__(self, config: GeminiConfig) -> None:
        if not config.api_key.strip():
            raise ValueError("gemini api_key must be non-empty")
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
        resolved_model = resolve_gemini_model(model or self._config.model)
        resolved_temperature = (
            self._config.temperature if temperature is None else temperature
        )
        resolved_timeout = self._config.timeout if timeout is None else timeout
        body = build_gemini_generate_content_request(
            prompt=prompt,
            max_tokens=self._config.max_tokens,
            temperature=resolved_temperature,
        )
        url = gemini_generate_content_url(resolved_model, self._config.api_key)
        request = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=resolved_timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except TimeoutError as exc:
            if resolved_timeout is None:
                raise TimeoutError("gemini request timed out") from exc
            raise TimeoutError(
                f"gemini request exceeded timeout of {resolved_timeout:g}s"
            ) from exc
        except urllib.error.HTTPError as exc:
            raise classify_http_error(provider="gemini", exc=exc) from exc
        except urllib.error.URLError as exc:
            reason = exc.reason
            if isinstance(reason, TimeoutError):
                if resolved_timeout is None:
                    raise TimeoutError("gemini request timed out") from exc
                raise TimeoutError(
                    f"gemini request exceeded timeout of {resolved_timeout:g}s"
                ) from exc
            raise RuntimeError(f"gemini request failed: {exc}") from exc

        if not isinstance(payload, dict):
            raise RuntimeError("gemini response was not a JSON object")
        return extract_gemini_response_text(payload)
