"""Provider transient error and Gemini retry tests (no paid API calls)."""

from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest
import urllib.error

from fsmreasonbench.generator.reachability import generate_reachability_item
from fsmreasonbench.runners.item_watchdog import (
    ItemInfrastructureError,
    ItemWatchdogConfig,
    call_generate_with_watchdog,
    provider_retry_delay_seconds,
)
from fsmreasonbench.runners.ollama_batch import OllamaBatchConfig, run_ollama_batch
from fsmreasonbench.runners.provider_errors import (
    ProviderTransientError,
    classify_http_error,
    is_transient_http_status,
)
from fsmreasonbench.runners.providers.base import GenerateBackendConfig, build_generate_factory
from fsmreasonbench.runners.providers.gemini import HttpGeminiClient, GeminiConfig


def test_transient_http_status_classification() -> None:
    assert is_transient_http_status(503)
    assert is_transient_http_status(429)
    assert is_transient_http_status(500)
    assert not is_transient_http_status(401)
    assert not is_transient_http_status(404)


def test_classify_http_error_marks_gemini_503_transient() -> None:
    exc = urllib.error.HTTPError(
        "https://example.test",
        503,
        "UNAVAILABLE",
        hdrs=None,
        fp=io.BytesIO(b'{"error":{"message":"high demand"}}'),
    )
    err = classify_http_error(provider="gemini", exc=exc)
    assert isinstance(err, ProviderTransientError)
    assert err.http_status == 503
    assert "provider_http_503" in str(err)


def test_classify_http_error_non_transient_stays_runtime_error() -> None:
    exc = urllib.error.HTTPError(
        "https://example.test",
        400,
        "BAD REQUEST",
        hdrs=None,
        fp=io.BytesIO(b"invalid"),
    )
    err = classify_http_error(provider="gemini", exc=exc)
    assert isinstance(err, RuntimeError)
    assert not isinstance(err, ProviderTransientError)


def test_watchdog_retries_provider_503_then_succeeds() -> None:
    calls = {"n": 0}

    def generate(*_args, **_kwargs) -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise ProviderTransientError(
                http_status=503,
                detail="high demand",
                provider="gemini",
                error_type="unavailable",
            )
        return '{"item_id":"x","verdict":true,"certificate":{}}'

    sleeps: list[float] = []

    text = call_generate_with_watchdog(
        generate,
        prompt="hello",
        model="gemini-flash",
        temperature=0.0,
        timeout=30.0,
        config=ItemWatchdogConfig(
            item_timeout=30.0,
            provider_retries=2,
            skip_item_on_timeout=True,
            provider_retry_backoff_seconds=5.0,
            provider="gemini",
        ),
        sleep_fn=lambda seconds: sleeps.append(seconds),
    )
    assert "verdict" in text
    assert calls["n"] == 3
    assert len(sleeps) == 2
    assert sleeps[0] == pytest.approx(5.0, rel=0.2)
    assert sleeps[1] == pytest.approx(15.0, rel=0.2)


def test_watchdog_exhausted_503_skips_item_when_policy_enabled() -> None:
    def generate(*_args, **_kwargs) -> str:
        raise ProviderTransientError(
            http_status=503,
            detail="still unavailable",
            provider="gemini",
            error_type="unavailable",
        )

    with pytest.raises(ItemInfrastructureError, match="provider_http_503"):
        call_generate_with_watchdog(
            generate,
            prompt="hello",
            model="gemini-flash",
            temperature=0.0,
            timeout=30.0,
            config=ItemWatchdogConfig(
                item_timeout=30.0,
                provider_retries=1,
                skip_item_on_timeout=True,
                provider_retry_backoff_seconds=0.0,
                provider="gemini",
            ),
            sleep_fn=lambda _seconds: None,
        )


def test_run_ollama_batch_skips_exhausted_provider_transient_item(
    tmp_path: Path,
) -> None:
    item = generate_reachability_item(11)
    run_dir = tmp_path / "cell"
    run_dir.mkdir()

    def generate(*_args, **_kwargs) -> str:
        raise ProviderTransientError(
            http_status=503,
            detail="unavailable",
            provider="gemini",
            error_type="unavailable",
        )

    result = run_ollama_batch(
        [item],
        generate,
        run_dir / "results.jsonl",
        OllamaBatchConfig(
            model="gemini-flash",
            provider="gemini",
            provider_retries=0,
            skip_item_on_timeout=True,
        ),
        out_dir=run_dir,
    )
    assert result.infrastructure_failures == 1
    scores = json.loads((run_dir / "scores.jsonl").read_text(encoding="utf-8").strip())
    assert scores["infrastructure_failure"] is True
    assert scores["failure_stage"] == "provider_error"
    assert scores["provider_error_type"] == "unavailable"


def test_http_gemini_client_raises_provider_transient_on_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"n": 0}

    class FakeResponse:
        def read(self) -> bytes:
            return b'{"candidates":[{"content":{"parts":[{"text":"ok"}]}}]}'

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def fake_urlopen(_request, timeout=None):  # noqa: ANN001, ARG001
        calls["n"] += 1
        if calls["n"] == 1:
            raise urllib.error.HTTPError(
                "https://example.test",
                503,
                "UNAVAILABLE",
                hdrs=None,
                fp=io.BytesIO(b"high demand"),
            )
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = HttpGeminiClient(
        GeminiConfig(api_key="test-key", model="gemini-2.5-flash", max_tokens=128)
    )
    with pytest.raises(ProviderTransientError, match="provider_http_503"):
        client.generate("hello")


def test_build_generate_factory_ollama_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    generate = build_generate_factory(GenerateBackendConfig(provider="ollama"))(
        "qwen2.5-coder:7b",
        0.0,
    )
    assert callable(generate)


def test_require_gemini_api_key_not_retried(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GEMINI_API_KEY or GOOGLE_API_KEY"):
        build_generate_factory(
            GenerateBackendConfig(provider="gemini", provider_dry_run=False)
        )


def test_provider_retry_delay_exponential() -> None:
    with patch("fsmreasonbench.runners.item_watchdog.random.uniform", return_value=0.0):
        assert provider_retry_delay_seconds(0, 5.0) == 5.0
        assert provider_retry_delay_seconds(1, 5.0) == 15.0
        assert provider_retry_delay_seconds(2, 5.0) == 45.0
