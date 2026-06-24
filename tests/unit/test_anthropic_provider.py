"""Anthropic provider backend tests (no paid API calls)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fsmreasonbench.generator.reachability import generate_reachability_item
from fsmreasonbench.runners.providers.anthropic import (
    build_anthropic_messages_request,
    extract_anthropic_response_text,
    require_anthropic_api_key,
    resolve_anthropic_model,
)
from fsmreasonbench.runners.providers.base import (
    GenerateBackendConfig,
    build_generate_factory,
    estimate_frontier_run,
    estimated_api_calls_per_item,
    validate_provider_tracks,
)
from fsmreasonbench.runners.track_pilot_models import (
    TrackPilotModelsConfig,
    run_track_pilot_models,
)


def test_require_anthropic_api_key_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        require_anthropic_api_key()


def test_resolve_anthropic_model_env_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-opus-4-1")
    assert resolve_anthropic_model("opus") == "claude-opus-4-1"
    assert resolve_anthropic_model("claude-opus-4-1") == "claude-opus-4-1"


def test_extract_anthropic_response_text_maps_to_plain_text() -> None:
    payload = {
        "content": [
            {"type": "text", "text": '{"item_id":"x","verdict":true}'},
        ]
    }
    text = extract_anthropic_response_text(payload)
    assert json.loads(text)["verdict"] is True


def test_validate_provider_tracks_allows_r1_r2_for_anthropic() -> None:
    validate_provider_tracks("anthropic", ("R0", "R1", "R2"))


def test_validate_provider_tracks_rejects_unknown_track_for_anthropic() -> None:
    with pytest.raises(ValueError, match="provider=anthropic supports tracks"):
        validate_provider_tracks("anthropic", ("R0", "R99"))


def test_estimated_api_calls_per_item_anthropic_r2() -> None:
    assert estimated_api_calls_per_item("anthropic", ("R0",)) == 1
    assert estimated_api_calls_per_item("anthropic", ("R2",)) == 2
    assert estimated_api_calls_per_item("anthropic", ("R0", "R2")) == 2


def test_estimate_frontier_run_anthropic_r2_doubles_api_calls() -> None:
    estimate = estimate_frontier_run(
        provider="anthropic",
        models=("claude-sonnet-4-5-20250929",),
        families=("C2",),
        tracks=("R2",),
        temperatures=(0.2,),
        max_items=10,
        max_cells=None,
        max_tokens=8192,
    )
    assert estimate["estimated_api_calls"] == 20


def test_provider_dry_run_writes_diagnostic_without_api_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    item = generate_reachability_item(42)
    items_path = tmp_path / "c2.jsonl"
    items_path.write_text(
        json.dumps(item.to_full_dict()) + "\n",
        encoding="utf-8",
    )

    out_dir = tmp_path / "frontier"
    config = TrackPilotModelsConfig(
        models=("claude-opus-4-1",),
        families=("C2",),
        tracks=("R0",),
        c2_items_path=items_path,
        f1_items_path=items_path,
        out_dir=out_dir,
        max_items=1,
        temperatures=(0.2,),
        provider="anthropic",
        provider_dry_run=True,
        skip_completed=False,
    )
    run_track_pilot_models(
        config,
        lambda _m, _t: (_ for _ in ()).throw(AssertionError("API must not be called")),
    )

    diagnostic = json.loads((out_dir / "provider_dry_run.json").read_text(encoding="utf-8"))
    assert diagnostic["provider"] == "anthropic"
    assert diagnostic["cells"][0]["track"] == "R0"
    assert diagnostic["cells"][0]["max_tokens"] == 8192
    assert diagnostic["cells"][0]["request"]["model"] == "claude-opus-4-1"


def test_build_generate_factory_anthropic_requires_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        build_generate_factory(
            GenerateBackendConfig(provider="anthropic", provider_dry_run=False)
        )


def test_build_anthropic_messages_request_shape() -> None:
    body = build_anthropic_messages_request(
        prompt="hello",
        model="claude-opus-4-1",
        max_tokens=1024,
        temperature=0.2,
    )
    assert body["model"] == "claude-opus-4-1"
    assert body["max_tokens"] == 1024
    assert body["messages"][0]["content"] == "hello"


def test_build_generate_factory_ollama_does_not_require_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    generate = build_generate_factory(GenerateBackendConfig(provider="ollama"))(
        "qwen2.5-coder:7b",
        0.0,
    )
    assert callable(generate)


def test_anthropic_provider_r2_track_batch_uses_two_phase_protocol(tmp_path: Path) -> None:
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

    out_dir = tmp_path / "anthropic_r2"
    result = run_ollama_track_batch(
        [item],
        fake_generate,
        tmp_path / "r2.jsonl",
        OllamaBatchConfig(model="claude-sonnet-4-5-20250929", provider="anthropic"),
        TrackId.R2,
        out_dir=out_dir,
    )
    assert result.summary["track"] == "R2"
    assert result.summary["provider"] == "anthropic"
    assert calls == 2
    assert result.summary["fully_correct_rate"] == 1.0
