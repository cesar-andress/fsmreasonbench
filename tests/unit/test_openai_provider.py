"""OpenAI provider backend tests (no paid API calls)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from fsmreasonbench.generator.reachability import generate_reachability_item
from fsmreasonbench.runners.providers.base import (
    GenerateBackendConfig,
    build_generate_factory,
    estimate_frontier_run,
    estimated_api_calls_per_item,
    resolve_provider_model,
    validate_provider_tracks,
)
from fsmreasonbench.runners.providers.openai import (
    OPENAI_API_KIND,
    OPENAI_CHAT_COMPLETIONS_URL,
    build_openai_chat_completions_request,
    extract_openai_response_text,
    openai_output_limit_param,
    require_openai_api_key,
    resolve_openai_model,
    run_openai_smoke_test,
)
from fsmreasonbench.runners.track_pilot_models import (
    TrackPilotModelsConfig,
    run_track_pilot_models,
)


def test_require_openai_api_key_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        require_openai_api_key()


def test_resolve_openai_model_env_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4.1")
    assert resolve_openai_model("gpt") == "gpt-4.1"
    assert resolve_openai_model("gpt-4.1") == "gpt-4.1"


def test_resolve_openai_model_prefers_gpt5_without_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    assert resolve_openai_model("default") == "gpt-5"


def test_openai_output_limit_param_gpt5_uses_max_completion_tokens() -> None:
    assert openai_output_limit_param("gpt-5") == "max_completion_tokens"
    assert openai_output_limit_param("gpt-4.1") == "max_tokens"


def test_build_openai_chat_completions_request_gpt5_shape() -> None:
    body = build_openai_chat_completions_request(
        prompt="hello",
        model="gpt-5",
        max_tokens=1024,
        temperature=0.2,
    )
    assert body["model"] == "gpt-5"
    assert body["max_completion_tokens"] == 1024
    assert "max_tokens" not in body
    assert "temperature" not in body


def test_openai_temperature_policy_gpt5_omits_custom_temperature() -> None:
    from fsmreasonbench.runners.providers.openai import openai_temperature_policy

    request_temp, effective, warning = openai_temperature_policy("gpt-5", 0.2)
    assert request_temp is None
    assert effective == 1.0
    assert warning is not None
    assert "gpt-4.1" in warning


def test_openai_temperature_policy_gpt41_passes_through() -> None:
    from fsmreasonbench.runners.providers.openai import openai_temperature_policy

    request_temp, effective, warning = openai_temperature_policy("gpt-4.1", 0.2)
    assert request_temp == 0.2
    assert effective == 0.2
    assert warning is None


def test_build_openai_chat_completions_request_gpt41_shape() -> None:
    body = build_openai_chat_completions_request(
        prompt="hello",
        model="gpt-4.1",
        max_tokens=1024,
        temperature=0.2,
    )
    assert body["model"] == "gpt-4.1"
    assert body["max_tokens"] == 1024
    assert "max_completion_tokens" not in body


def test_extract_openai_response_text_maps_to_plain_text() -> None:
    payload = {
        "id": "chatcmpl-test",
        "choices": [
            {
                "message": {"role": "assistant", "content": '{"item_id":"x","verdict":true}'},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
    }
    text = extract_openai_response_text(payload)
    assert json.loads(text)["verdict"] is True


def test_validate_provider_tracks_allows_r1_r2_for_openai() -> None:
    validate_provider_tracks("openai", ("R0", "R1", "R2"))


def test_estimated_api_calls_per_item_openai_r2() -> None:
    assert estimated_api_calls_per_item("openai", ("R0",)) == 1
    assert estimated_api_calls_per_item("openai", ("R2",)) == 2


def test_resolve_provider_model_openai_alias() -> None:
    assert resolve_provider_model("openai", "gpt") in {"gpt-5", "gpt-4.1"}


def test_provider_dry_run_writes_diagnostic_without_api_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    item = generate_reachability_item(42)
    items_path = tmp_path / "c2.jsonl"
    items_path.write_text(
        json.dumps(item.to_full_dict()) + "\n",
        encoding="utf-8",
    )

    out_dir = tmp_path / "frontier"
    config = TrackPilotModelsConfig(
        models=("gpt-4.1",),
        model_args=("gpt",),
        families=("C2",),
        tracks=("R0",),
        c2_items_path=items_path,
        f1_items_path=items_path,
        out_dir=out_dir,
        max_items=1,
        temperatures=(0.2,),
        provider="openai",
        provider_dry_run=True,
        skip_completed=False,
    )
    run_track_pilot_models(
        config,
        lambda _m, _t: (_ for _ in ()).throw(AssertionError("API must not be called")),
    )

    diagnostic = json.loads((out_dir / "provider_dry_run.json").read_text(encoding="utf-8"))
    assert diagnostic["provider"] == "openai"
    assert diagnostic["cells"][0]["request"]["model"] == "gpt-4.1"
    assert "max_tokens" in diagnostic["cells"][0]["request"]


def test_build_generate_factory_openai_requires_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        build_generate_factory(GenerateBackendConfig(provider="openai", provider_dry_run=False))


def test_run_openai_smoke_test_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def fake_post(**kwargs):
        assert kwargs["model"] == "gpt-5"
        from fsmreasonbench.runners.providers.openai import OpenAICompletionResult

        return OpenAICompletionResult(
            text='{"smoke":"ok"}',
            response_id="chatcmpl-smoke",
            finish_reason="stop",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            request_payload=build_openai_chat_completions_request(
                prompt=kwargs["prompt"],
                model=kwargs["model"],
                max_tokens=kwargs["max_tokens"],
                temperature=kwargs["temperature"],
            ),
            endpoint=OPENAI_CHAT_COMPLETIONS_URL,
        )

    with patch(
        "fsmreasonbench.runners.providers.openai.post_openai_chat_completion",
        side_effect=fake_post,
    ):
        payload = run_openai_smoke_test(model="gpt-5")

    assert payload["api_kind"] == OPENAI_API_KIND
    assert payload["endpoint"] == OPENAI_CHAT_COMPLETIONS_URL
    assert payload["resolved_model"] == "gpt-5"
    assert payload["response_id"] == "chatcmpl-smoke"
    assert payload["finish_reason"] == "stop"
    assert payload["usage"]["total_tokens"] == 15
    assert "max_completion_tokens" in payload["request_payload"]


def test_openai_provider_r2_track_batch_uses_two_phase_protocol(tmp_path: Path) -> None:
    from fsmreasonbench.runners.ollama_batch import OllamaBatchConfig
    from fsmreasonbench.runners.ollama_track_batch import run_ollama_track_batch
    from fsmreasonbench.tracks.models import TrackId

    item = generate_reachability_item(44)
    calls = 0

    def fake_generate(
        prompt: str,
        *,
        model: str,
        temperature: float,
        timeout: float,
    ) -> str:
        nonlocal calls
        _ = (prompt, model, temperature, timeout)
        calls += 1
        if calls == 1:
            return json.dumps(
                {
                    "phase": "tool_plan",
                    "tool_calls": [
                        {
                            "call_id": "1",
                            "tool": "solver.reachability_certificate",
                            "inputs": {
                                "fsm_id": item.fsm.fsm_id,
                                "target_state": item.question["target_state"],
                            },
                        }
                    ],
                }
            )
        return json.dumps(
            {
                "phase": "final_submission",
                "submission": {
                    "item_id": item.item_id,
                    "verdict": item.answer_key["verdict"],
                    "certificate": item.answer_key["certificate"],
                },
            }
        )

    out_dir = tmp_path / "openai_r2"
    result = run_ollama_track_batch(
        [item],
        fake_generate,
        tmp_path / "r2.jsonl",
        OllamaBatchConfig(model="gpt-4.1", provider="openai"),
        TrackId.R2,
        out_dir=out_dir,
    )
    assert result.summary["track"] == "R2"
    assert result.summary["provider"] == "openai"
    assert result.summary["model"] == "gpt-4.1"
    assert calls == 2
    assert result.summary["fully_correct_rate"] == 1.0
