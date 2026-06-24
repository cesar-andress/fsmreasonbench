"""Anthropic provider HTTP error classification tests."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
import urllib.error

from fsmreasonbench.generator.reachability import generate_reachability_item
from fsmreasonbench.runners.infrastructure_failure import (
    reclassify_provider_error_scoring_row,
    summarize_provider_errors,
)
from fsmreasonbench.runners.item_watchdog import (
    ItemInfrastructureError,
    ItemWatchdogConfig,
    call_generate_with_watchdog,
)
from fsmreasonbench.runners.ollama_batch import OllamaBatchConfig
from fsmreasonbench.runners.ollama_track_batch import run_ollama_track_batch
from fsmreasonbench.runners.provider_errors import (
    ProviderTransientError,
    classify_http_error,
    infer_provider_error_from_message,
    infer_provider_error_type,
)
from fsmreasonbench.tracks.models import TrackId


def test_classify_http_error_anthropic_429_rate_limit() -> None:
    body = json.dumps(
        {
            "type": "error",
            "error": {
                "type": "rate_limit_error",
                "message": "This request would exceed your organization's rate limit",
            },
        }
    )
    exc = urllib.error.HTTPError(
        "https://api.anthropic.com/v1/messages",
        429,
        "Too Many Requests",
        hdrs={"Retry-After": "5"},
        fp=io.BytesIO(body.encode("utf-8")),
    )
    err = classify_http_error(provider="anthropic", exc=exc)
    assert isinstance(err, ProviderTransientError)
    assert err.error_type == "rate_limit"
    assert err.http_status == 429


def test_classify_http_error_anthropic_400_insufficient_credit() -> None:
    body = json.dumps(
        {
            "type": "error",
            "error": {
                "type": "invalid_request_error",
                "message": "Your credit balance is too low to access the Anthropic API.",
            },
        }
    )
    exc = urllib.error.HTTPError(
        "https://api.anthropic.com/v1/messages",
        400,
        "Bad Request",
        hdrs=None,
        fp=io.BytesIO(body.encode("utf-8")),
    )
    err = classify_http_error(provider="anthropic", exc=exc)
    assert isinstance(err, ProviderTransientError)
    assert err.error_type == "insufficient_credit"
    assert err.http_status == 400


def test_infer_provider_error_from_runtime_message_anthropic_400() -> None:
    message = (
        'anthropic request failed with HTTP 400: {"type":"error","error":{"type":'
        '"invalid_request_error","message":"Your credit balance is too low to access '
        'the Anthropic API."}}'
    )
    classification = infer_provider_error_from_message(message)
    assert classification is not None
    assert classification.provider_error_type == "insufficient_credit"
    assert classification.http_status == 400


def test_watchdog_anthropic_400_insufficient_credit_is_provider_error() -> None:
    body = json.dumps(
        {
            "type": "error",
            "error": {
                "type": "invalid_request_error",
                "message": "Your credit balance is too low to access the Anthropic API.",
            },
        }
    )

    def generate(*_args, **_kwargs) -> str:
        raise RuntimeError(f"anthropic request failed with HTTP 400: {body}")

    with pytest.raises(ItemInfrastructureError) as exc_info:
        call_generate_with_watchdog(
            generate,
            prompt="hello",
            model="claude-sonnet-4-5-20250929",
            temperature=0.0,
            timeout=30.0,
            config=ItemWatchdogConfig(
                item_timeout=30.0,
                provider_retries=0,
                provider="anthropic",
            ),
        )
    assert exc_info.value.provider_error_type == "insufficient_credit"
    assert exc_info.value.http_status == 400


def test_r2_anthropic_429_rate_limit_recorded_as_provider_error(tmp_path: Path) -> None:
    item = generate_reachability_item(7)
    body = json.dumps(
        {
            "type": "error",
            "error": {
                "type": "rate_limit_error",
                "message": "rate limit exceeded",
            },
        }
    )

    def generate(*_args, **_kwargs) -> str:
        raise RuntimeError(f"anthropic request failed with HTTP 429: {body}")

    result = run_ollama_track_batch(
        [item],
        generate,
        tmp_path / "r2.jsonl",
        OllamaBatchConfig(
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            provider_retries=0,
        ),
        TrackId.R2,
        out_dir=tmp_path / "cell",
    )
    assert result.infrastructure_failures == 1
    scores = json.loads((tmp_path / "cell" / "scores.jsonl").read_text(encoding="utf-8").strip())
    assert scores["failure_stage"] == "provider_error"
    assert scores["infrastructure_failure"] is True
    assert scores["provider_error_type"] == "rate_limit"
    assert scores["track_failure_class"] == "provider_error"
    assert result.summary["failure_stage_counts"]["not_extractable"] == 0
    assert result.summary["failure_stage_counts"]["provider_error"] == 1


def test_genuine_parse_error_remains_not_extractable() -> None:
    row = {
        "failure_stage": "not_extractable",
        "parse_errors": ("fsm_ids must be an array of length 2",),
    }
    assert reclassify_provider_error_scoring_row(row) is False
    assert row["failure_stage"] == "not_extractable"


def test_reclassify_misclassified_anthropic_runtime_message() -> None:
    row = {
        "failure_stage": "not_extractable",
        "parse_errors": (
            'anthropic request failed with HTTP 400: {"type":"error","error":{"type":"invalid_request_error","message":"Your credit balance is too low to access the Anthropic API."}}',
        ),
    }
    assert reclassify_provider_error_scoring_row(row) is True
    assert row["failure_stage"] == "provider_error"
    assert row["provider_error_type"] == "insufficient_credit"
    assert row["infrastructure_failure"] is True


def test_summarize_provider_errors_tracks_rate_limit_and_insufficient_credit() -> None:
    rows = [
        {"infrastructure_failure": True, "provider_error_type": "rate_limit"},
        {"infrastructure_failure": True, "provider_error_type": "insufficient_credit"},
        {"failure_stage": "not_extractable"},
    ]
    counts = summarize_provider_errors(rows)
    assert counts["provider_error_count"] == 2
    assert counts["provider_rate_limit_count"] == 1
    assert counts["provider_insufficient_credit_count"] == 1
    assert counts["provider_quota_error_count"] == 2


def test_infer_provider_error_type_anthropic_json_rate_limit() -> None:
    detail = json.dumps({"error": {"type": "rate_limit_error", "message": "slow down"}})
    assert infer_provider_error_type(429, detail) == "rate_limit"
