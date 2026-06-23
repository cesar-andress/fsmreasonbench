"""Gemini provider backend tests (no paid API calls)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fsmreasonbench.generator.reachability import generate_reachability_item
from fsmreasonbench.runners.providers.base import (
    GenerateBackendConfig,
    build_generate_factory,
    estimate_frontier_run,
    validate_provider_tracks,
)
from fsmreasonbench.runners.providers.gemini import (
    build_gemini_generate_content_request,
    extract_gemini_response_text,
    require_gemini_api_key,
    resolve_gemini_model,
)
from fsmreasonbench.runners.track_pilot_models import (
    TrackPilotModelsConfig,
    run_track_pilot_models,
)


def test_require_gemini_api_key_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GEMINI_API_KEY or GOOGLE_API_KEY"):
        require_gemini_api_key()


def test_require_gemini_api_key_prefers_gemini_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "google-key")
    assert require_gemini_api_key() == "gemini-key"


def test_require_gemini_api_key_falls_back_to_google(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "google-key")
    assert require_gemini_api_key() == "google-key"


def test_resolve_gemini_model_aliases_and_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash-preview")
    assert resolve_gemini_model("gemini-flash") == "gemini-2.5-flash-preview"
    assert resolve_gemini_model("flash") == "gemini-2.5-flash-preview"
    assert resolve_gemini_model("gemini-2.0-flash") == "gemini-2.0-flash"


def test_extract_gemini_response_text_maps_to_plain_text() -> None:
    payload = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": '{"item_id":"x","verdict":true}'}],
                }
            }
        ]
    }
    text = extract_gemini_response_text(payload)
    assert json.loads(text)["verdict"] is True


def test_validate_provider_tracks_rejects_r1_r2_for_gemini() -> None:
    with pytest.raises(
        ValueError,
        match="Gemini provider currently supports R0 only; tool tracks are not implemented.",
    ):
        validate_provider_tracks("gemini", ("R0", "R1"))


def test_build_gemini_generate_content_request_shape() -> None:
    body = build_gemini_generate_content_request(
        prompt="hello",
        max_tokens=1024,
        temperature=0.2,
    )
    assert body["contents"][0]["parts"][0]["text"] == "hello"
    assert body["generationConfig"]["maxOutputTokens"] == 1024
    assert body["generationConfig"]["temperature"] == 0.2
    assert body["generationConfig"]["responseMimeType"] == "application/json"


def test_provider_dry_run_writes_diagnostic_without_api_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    item = generate_reachability_item(42)
    items_path = tmp_path / "c2.jsonl"
    items_path.write_text(
        json.dumps(item.to_full_dict()) + "\n",
        encoding="utf-8",
    )

    out_dir = tmp_path / "frontier"
    config = TrackPilotModelsConfig(
        models=("gemini-flash",),
        families=("C2",),
        tracks=("R0",),
        c2_items_path=items_path,
        f1_items_path=items_path,
        out_dir=out_dir,
        max_items=1,
        temperatures=(0.2,),
        provider="gemini",
        provider_dry_run=True,
        skip_completed=False,
    )
    run_track_pilot_models(
        config,
        lambda _m, _t: (_ for _ in ()).throw(AssertionError("API must not be called")),
    )

    diagnostic = json.loads((out_dir / "provider_dry_run.json").read_text(encoding="utf-8"))
    assert diagnostic["provider"] == "gemini"
    assert diagnostic["cells"][0]["track"] == "R0"
    assert diagnostic["cells"][0]["max_tokens"] == 8192
    request = diagnostic["cells"][0]["request"]
    assert "generateContent" in request["endpoint"]
    assert request["body"]["generationConfig"]["maxOutputTokens"] == 8192
    assert (
        request["body"]["generationConfig"]["responseMimeType"] == "application/json"
    )
    assert "Return ONLY one JSON object" in diagnostic["cells"][0]["request"]["body"][
        "contents"
    ][0]["parts"][0]["text"]


def test_build_generate_factory_gemini_requires_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GEMINI_API_KEY or GOOGLE_API_KEY"):
        build_generate_factory(
            GenerateBackendConfig(provider="gemini", provider_dry_run=False)
        )


def test_estimate_only_works_without_api_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    item = generate_reachability_item(7)
    items_path = tmp_path / "items.jsonl"
    items_path.write_text(
        json.dumps(item.to_full_dict()) + "\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "estimate"
    config = TrackPilotModelsConfig(
        models=("gemini-flash",),
        families=("C2",),
        tracks=("R0",),
        c2_items_path=items_path,
        f1_items_path=items_path,
        out_dir=out_dir,
        max_items=30,
        temperatures=(0.2,),
        provider="gemini",
        estimate_only=True,
        skip_completed=False,
    )
    run_track_pilot_models(
        config,
        lambda _m, _t: (_ for _ in ()).throw(AssertionError("API must not be called")),
    )
    estimate = json.loads((out_dir / "frontier_estimate.json").read_text(encoding="utf-8"))
    assert estimate["provider"] == "gemini"
    assert estimate["executable_cells"] == 1
    assert estimate["estimated_items_scored"] == 30
    assert estimate["estimated_api_calls"] == 30
    assert "Google Gemini pricing" in estimate["note"]


def test_estimate_frontier_run_cell_counts() -> None:
    estimate = estimate_frontier_run(
        provider="gemini",
        models=("gemini-flash",),
        families=("C2", "F1"),
        tracks=("R0",),
        temperatures=(0.2, 0.7),
        max_items=10,
        max_cells=None,
        max_tokens=8192,
    )
    assert estimate["planned_cells"] == 4
    assert estimate["estimated_api_calls"] == 40


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
