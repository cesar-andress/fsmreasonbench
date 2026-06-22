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


def test_validate_provider_tracks_rejects_r1_r2_for_anthropic() -> None:
    with pytest.raises(ValueError, match="provider=anthropic does not implement"):
        validate_provider_tracks("anthropic", ("R0", "R1"))


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
