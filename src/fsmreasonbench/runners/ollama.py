"""Ollama HTTP client for local model inference."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol


class OllamaClient(Protocol):
    def generate(
        self,
        prompt: str,
        *,
        model: str,
        temperature: float,
        timeout: float,
    ) -> str:
        """Return the model response text."""


@dataclass(frozen=True, slots=True)
class OllamaConfig:
    base_url: str = "http://localhost:11434"
    model: str = "qwen2.5-coder:7b"
    temperature: float = 0.0
    timeout: float = 120.0


class HttpOllamaClient:
    """Minimal Ollama /api/generate client."""

    def __init__(self, config: OllamaConfig | None = None) -> None:
        self._config = config or OllamaConfig()

    def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float | None = None,
        timeout: float | None = None,
    ) -> str:
        resolved_model = model or self._config.model
        resolved_temperature = self._config.temperature if temperature is None else temperature
        resolved_timeout = self._config.timeout if timeout is None else timeout
        url = f"{self._config.base_url.rstrip('/')}/api/generate"
        body = json.dumps(
            {
                "model": resolved_model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": resolved_temperature},
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=resolved_timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"ollama request failed: {exc}") from exc

        text = payload.get("response")
        if not isinstance(text, str):
            raise RuntimeError("ollama response missing 'response' text field")
        return text
