"""Provider quota/rate-limit classification and retry handling tests."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
import urllib.error

from fsmreasonbench.generator.reachability import generate_reachability_item
from fsmreasonbench.runners.infrastructure_failure import summarize_provider_errors
from fsmreasonbench.runners.item_watchdog import (
    ItemInfrastructureError,
    ItemWatchdogConfig,
    call_generate_with_watchdog,
)
from fsmreasonbench.runners.ollama_batch import OllamaBatchConfig, run_ollama_batch
from fsmreasonbench.runners.provider_errors import (
    ProviderTransientError,
    classify_http_error,
    infer_429_error_type,
    parse_retry_after_seconds,
    resolve_provider_retry_delay_seconds,
)


def test_infer_429_error_type_quota_vs_rate_limit() -> None:
    assert infer_429_error_type('{"error":{"message":"Quota exceeded for metric"}}') == (
        "quota_exceeded"
    )
    assert infer_429_error_type("Rate limit exceeded") == "rate_limit"


def test_classify_http_error_429_sets_error_type_and_retry_after() -> None:
    exc = urllib.error.HTTPError(
        "https://example.test",
        429,
        "Too Many Requests",
        hdrs={"Retry-After": "12"},
        fp=io.BytesIO(b'{"error":{"message":"Quota exceeded"}}'),
    )
    err = classify_http_error(provider="gemini", exc=exc)
    assert isinstance(err, ProviderTransientError)
    assert err.http_status == 429
    assert err.error_type == "quota_exceeded"
    assert err.retry_after_seconds == 12.0


def test_classify_http_error_503_is_unavailable() -> None:
    exc = urllib.error.HTTPError(
        "https://example.test",
        503,
        "UNAVAILABLE",
        hdrs=None,
        fp=io.BytesIO(b"high demand"),
    )
    err = classify_http_error(provider="gemini", exc=exc)
    assert isinstance(err, ProviderTransientError)
    assert err.error_type == "unavailable"


def test_resolve_provider_retry_delay_honors_retry_after() -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            "fsmreasonbench.runners.item_watchdog.random.uniform",
            lambda _a, _b: 0.0,
        )
        delay = resolve_provider_retry_delay_seconds(
            0,
            5.0,
            retry_after_seconds=30.0,
        )
    assert delay == 30.0


def test_watchdog_429_retry_after_triggers_sleep_before_retry() -> None:
    calls = {"n": 0}

    def generate(*_args, **_kwargs) -> str:
        calls["n"] += 1
        if calls["n"] == 1:
            raise ProviderTransientError(
                http_status=429,
                detail="Quota exceeded",
                provider="gemini",
                error_type="quota_exceeded",
                retry_after_seconds=7.0,
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
            provider_retries=1,
            provider_retry_backoff_seconds=1.0,
            provider="gemini",
        ),
        sleep_fn=lambda seconds: sleeps.append(seconds),
    )
    assert "verdict" in text
    assert sleeps == [7.0]


def test_exhausted_429_recorded_as_provider_error_not_model_parse(
    tmp_path: Path,
) -> None:
    item = generate_reachability_item(3)

    def generate(*_args, **_kwargs) -> str:
        raise ProviderTransientError(
            http_status=429,
            detail="Quota exceeded",
            provider="gemini",
            error_type="quota_exceeded",
        )

    result = run_ollama_batch(
        [item],
        generate,
        tmp_path / "results.jsonl",
        OllamaBatchConfig(
            model="gemini-flash",
            provider="gemini",
            provider_retries=0,
            skip_item_on_timeout=True,
        ),
        out_dir=tmp_path / "cell",
    )
    assert result.infrastructure_failures == 1
    scores = json.loads((tmp_path / "cell" / "scores.jsonl").read_text(encoding="utf-8").strip())
    assert scores["infrastructure_failure"] is True
    assert scores["failure_stage"] == "provider_error"
    assert scores["provider_error_type"] == "quota_exceeded"
    assert scores["track_failure_class"] == "provider_error"
    assert "provider_http_429" in scores["parse_errors"][0]
    assert result.summary["provider_error_count"] == 1
    assert result.summary["provider_quota_error_count"] == 1
    assert result.summary["failure_stage_counts"]["not_extractable"] == 0
    assert result.summary["failure_stage_counts"]["provider_error"] == 1


def test_malformed_json_remains_not_extractable(tmp_path: Path) -> None:
    item = generate_reachability_item(5)

    def generate(*_args, **_kwargs) -> str:
        return "NOT VALID JSON"

    run_ollama_batch(
        [item],
        generate,
        tmp_path / "results.jsonl",
        OllamaBatchConfig(model="mock"),
        out_dir=tmp_path / "cell",
    )
    scores = json.loads((tmp_path / "cell" / "scores.jsonl").read_text(encoding="utf-8").strip())
    assert scores["failure_stage"] == "not_extractable"
    assert scores.get("infrastructure_failure") is not True


def test_summarize_provider_errors_counts() -> None:
    rows = [
        {"infrastructure_failure": True, "provider_error_type": "quota_exceeded"},
        {"infrastructure_failure": True, "provider_error_type": "unavailable"},
        {"infrastructure_failure": True, "provider_error_type": "rate_limit"},
        {"failure_stage": "not_extractable"},
    ]
    counts = summarize_provider_errors(rows)
    assert counts["provider_error_count"] == 3
    assert counts["provider_quota_error_count"] == 2


def test_parse_retry_after_seconds() -> None:
    assert parse_retry_after_seconds({"Retry-After": "8"}) == 8.0
    assert parse_retry_after_seconds(None) is None


def test_item_infrastructure_error_carries_provider_error_type() -> None:
    err = ItemInfrastructureError(
        "provider_http_429: quota",
        provider_error_type="quota_exceeded",
        http_status=429,
    )
    assert err.provider_error_type == "quota_exceeded"
    assert err.http_status == 429
