"""OpenAI Chat Completions API backend for frontier R0/R1/R2 runs.

Endpoint: ``POST https://api.openai.com/v1/chat/completions`` (Chat Completions API).
This is **not** the Responses API. Newer models (e.g. gpt-5, o-series) reject
``max_tokens`` on Chat Completions and require ``max_completion_tokens`` instead.

R1/R2 use the same JSON two-phase track protocol as Ollama and Anthropic
(tool_plan then final_submission); the runner executes registered tools locally
between phases. This module does not use OpenAI native function/tool calling.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from fsmreasonbench.runners.provider_errors import classify_http_error

OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_API_KIND = "chat_completions"
DEFAULT_OPENAI_MODEL = "gpt-4.1"
PREFERRED_OPENAI_MODEL = "gpt-5"


@dataclass(frozen=True, slots=True)
class OpenAIConfig:
    api_key: str
    model: str
    temperature: float = 0.0
    timeout: float | None = 120.0
    max_tokens: int = 8192


@dataclass(frozen=True, slots=True)
class OpenAICompletionResult:
    text: str
    response_id: str | None
    finish_reason: str | None
    usage: dict[str, Any]
    request_payload: dict[str, Any]
    endpoint: str


def require_openai_api_key() -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY environment variable is required for provider=openai"
        )
    return api_key


def resolve_openai_model(model: str) -> str:
    candidate = model.strip()
    env_default = os.environ.get("OPENAI_MODEL", "").strip()
    if not candidate or candidate.lower() in {"default", "gpt", "openai"}:
        return env_default or PREFERRED_OPENAI_MODEL
    lowered = candidate.lower()
    if lowered in {"gpt-5", "gpt5"}:
        return env_default or PREFERRED_OPENAI_MODEL
    if lowered in {"gpt-4.1", "gpt4.1", "gpt-4-1"}:
        return "gpt-4.1"
    return candidate


def openai_output_limit_param(model: str) -> str:
    """Return the Chat Completions output limit field supported by ``model``."""
    lowered = resolve_openai_model(model).lower()
    if lowered.startswith(("gpt-5", "o1", "o3", "o4")):
        return "max_completion_tokens"
    return "max_tokens"


def openai_uses_default_temperature_only(model: str) -> bool:
    """Models that reject custom ``temperature`` on Chat Completions (default only)."""
    lowered = resolve_openai_model(model).lower()
    return lowered.startswith(("gpt-5", "o1", "o3", "o4"))


def openai_temperature_policy(
    model: str,
    temperature: float,
) -> tuple[float | None, float, str | None]:
    """Map experiment temperature to Chat Completions request fields.

    Returns ``(temperature_for_request, effective_temperature, warning)``.
    When ``temperature_for_request`` is ``None``, the field is omitted and the API
    uses its default (1.0) — required for gpt-5 and o-series reasoning models.
    """
    resolved_model = resolve_openai_model(model)
    if not openai_uses_default_temperature_only(resolved_model):
        return temperature, temperature, None

    effective = 1.0
    if abs(temperature - effective) > 1e-9:
        return (
            None,
            effective,
            (
                f"{resolved_model} only supports default temperature=1 on Chat Completions; "
                f"omitting temperature (experiment requested {temperature:g}). "
                "For T=0.2 Claude-parity runs, set OPENAI_MODEL=gpt-4.1."
            ),
        )
    return None, effective, None


def build_openai_chat_completions_request(
    *,
    prompt: str,
    model: str,
    max_tokens: int,
    temperature: float,
) -> dict[str, Any]:
    resolved_model = resolve_openai_model(model)
    limit_param = openai_output_limit_param(resolved_model)
    request_temperature, _, _ = openai_temperature_policy(resolved_model, temperature)
    body: dict[str, Any] = {
        "model": resolved_model,
        "messages": [{"role": "user", "content": prompt}],
        limit_param: max_tokens,
    }
    if request_temperature is not None:
        body["temperature"] = request_temperature
    return body


def describe_openai_request(
    *,
    model: str,
    max_tokens: int,
    temperature: float,
    prompt_preview: str | None = None,
) -> dict[str, Any]:
    resolved_model = resolve_openai_model(model)
    request_temperature, effective_temperature, temperature_warning = (
        openai_temperature_policy(resolved_model, temperature)
    )
    payload = build_openai_chat_completions_request(
        prompt=prompt_preview or "<prompt omitted>",
        model=resolved_model,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    info: dict[str, Any] = {
        "provider": "openai",
        "api_kind": OPENAI_API_KIND,
        "endpoint": OPENAI_CHAT_COMPLETIONS_URL,
        "resolved_model": resolved_model,
        "model_arg": model if model != resolved_model else None,
        "output_limit_param": openai_output_limit_param(resolved_model),
        "temperature_requested": temperature,
        "temperature_in_request": request_temperature,
        "effective_temperature": effective_temperature,
        "request_parameters": payload,
    }
    if temperature_warning:
        info["temperature_warning"] = temperature_warning
    return info


def print_openai_startup_validation(
    *,
    model: str,
    max_tokens: int,
    temperature: float,
    stream: Any | None = None,
) -> dict[str, Any]:
    """Print provider/endpoint/model/parameters before the first scored item."""
    info = describe_openai_request(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    out = stream or sys.stderr
    print("openai-startup-validation:", file=out)
    print(f"  provider: {info['provider']}", file=out)
    print(f"  api_kind: {info['api_kind']}", file=out)
    print(f"  endpoint: {info['endpoint']}", file=out)
    print(f"  resolved_model: {info['resolved_model']}", file=out)
    if info.get("model_arg"):
        print(f"  model_arg: {info['model_arg']}", file=out)
    print(f"  output_limit_param: {info['output_limit_param']}", file=out)
    print(f"  temperature_requested: {info['temperature_requested']}", file=out)
    print(f"  temperature_in_request: {info['temperature_in_request']}", file=out)
    print(f"  effective_temperature: {info['effective_temperature']}", file=out)
    if info.get("temperature_warning"):
        print(f"  temperature_warning: {info['temperature_warning']}", file=out)
    print(
        f"  request_parameters: {json.dumps(info['request_parameters'], ensure_ascii=False)}",
        file=out,
    )
    return info


def extract_openai_response_text(payload: dict[str, Any]) -> str:
    """Map OpenAI chat.completions JSON to plain text for the existing extractor."""
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("openai response missing choices")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise ValueError("openai response missing message")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("openai response contained no message content")
    return content


def extract_openai_response_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    choices = payload.get("choices")
    finish_reason = None
    if isinstance(choices, list) and choices:
        finish_reason = choices[0].get("finish_reason")
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        usage = {}
    return {
        "response_id": payload.get("id"),
        "finish_reason": finish_reason,
        "usage": usage,
    }


def post_openai_chat_completion(
    *,
    api_key: str,
    prompt: str,
    model: str,
    max_tokens: int,
    temperature: float,
    timeout: float | None,
) -> OpenAICompletionResult:
    body = build_openai_chat_completions_request(
        prompt=prompt,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    request = urllib.request.Request(
        OPENAI_CHAT_COMPLETIONS_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except TimeoutError as exc:
        if timeout is None:
            raise TimeoutError("openai request timed out") from exc
        raise TimeoutError(
            f"openai request exceeded timeout of {timeout:g}s"
        ) from exc
    except urllib.error.HTTPError as exc:
        raise classify_http_error(provider="openai", exc=exc) from exc
    except urllib.error.URLError as exc:
        reason = exc.reason
        if isinstance(reason, TimeoutError):
            if timeout is None:
                raise TimeoutError("openai request timed out") from exc
            raise TimeoutError(
                f"openai request exceeded timeout of {timeout:g}s"
            ) from exc
        raise RuntimeError(f"openai request failed: {exc}") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("openai response was not a JSON object")
    meta = extract_openai_response_metadata(payload)
    return OpenAICompletionResult(
        text=extract_openai_response_text(payload),
        response_id=meta["response_id"],
        finish_reason=meta["finish_reason"],
        usage=meta["usage"],
        request_payload=body,
        endpoint=OPENAI_CHAT_COMPLETIONS_URL,
    )


def run_openai_smoke_test(
    *,
    model: str,
    max_tokens: int = 256,
    temperature: float = 0.0,
    timeout: float | None = 120.0,
    prompt: str = 'Return ONLY this JSON object: {"smoke":"ok"}',
) -> dict[str, Any]:
    """Send a single Chat Completions request to validate provider wiring."""
    api_key = require_openai_api_key()
    resolved_model = resolve_openai_model(model)
    request_info = describe_openai_request(
        model=resolved_model,
        max_tokens=max_tokens,
        temperature=temperature,
        prompt_preview=prompt[:120],
    )
    if request_info.get("temperature_warning"):
        print(
            f"openai-smoke: {request_info['temperature_warning']}",
            file=sys.stderr,
        )
    result = post_openai_chat_completion(
        api_key=api_key,
        prompt=prompt,
        model=resolved_model,
        max_tokens=max_tokens,
        temperature=temperature,
        timeout=timeout,
    )
    return {
        "provider": "openai",
        "api_kind": OPENAI_API_KIND,
        "endpoint": result.endpoint,
        "resolved_model": resolved_model,
        "model_arg": model if model != resolved_model else None,
        "temperature_requested": request_info["temperature_requested"],
        "temperature_in_request": request_info["temperature_in_request"],
        "effective_temperature": request_info["effective_temperature"],
        "temperature_warning": request_info.get("temperature_warning"),
        "request_payload": result.request_payload,
        "response_id": result.response_id,
        "usage": result.usage,
        "finish_reason": result.finish_reason,
        "response_text_preview": result.text[:240],
    }


class HttpOpenAIClient:
    """Minimal OpenAI chat.completions client using stdlib HTTP."""

    def __init__(self, config: OpenAIConfig) -> None:
        if not config.api_key.strip():
            raise ValueError("openai api_key must be non-empty")
        if config.max_tokens < 1:
            raise ValueError("max_tokens must be >= 1")
        self._config = config
        self._resolved_model = resolve_openai_model(config.model)

    @property
    def resolved_model(self) -> str:
        return self._resolved_model

    def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float | None = None,
        timeout: float | None = None,
    ) -> str:
        resolved_model = resolve_openai_model(model or self._config.model)
        resolved_temperature = (
            self._config.temperature if temperature is None else temperature
        )
        resolved_timeout = self._config.timeout if timeout is None else timeout
        result = post_openai_chat_completion(
            api_key=self._config.api_key,
            prompt=prompt,
            model=resolved_model,
            max_tokens=self._config.max_tokens,
            temperature=resolved_temperature,
            timeout=resolved_timeout,
        )
        return result.text
