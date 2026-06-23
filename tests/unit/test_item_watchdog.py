"""Per-item watchdog, heartbeat, and Ollama recovery tests (no real Ollama)."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from fsmreasonbench.generator.reachability import generate_reachability_item
from fsmreasonbench.runners.experiment_cells import (
    CELL_STATUS_JSON,
    completed_item_ids,
    detect_cell_status,
    is_stale_running,
    mark_cell_running,
    read_cell_status,
    update_cell_item_progress,
    format_cell_progress,
)
from fsmreasonbench.runners.experiment_status import format_experiment_status_report, scan_experiment_status
from fsmreasonbench.runners.item_watchdog import (
    ItemInfrastructureError,
    ItemWatchdogConfig,
    call_generate_with_watchdog,
    format_infrastructure_timeout_message,
)
from fsmreasonbench.runners.ollama_batch import OllamaBatchConfig, run_ollama_batch
from fsmreasonbench.runners.ollama_recovery import stop_ollama_model
from fsmreasonbench.runners.track_pilot_models import TrackPilotModelsConfig, run_track_pilot_models


def test_format_infrastructure_timeout_message() -> None:
    assert "infrastructure_timeout" in format_infrastructure_timeout_message(300.0)


def test_watchdog_marks_timeout_as_infrastructure_error() -> None:
    def slow_generate(*_args, **_kwargs) -> str:
        time.sleep(0.2)
        return "{}"

    config = ItemWatchdogConfig(
        item_timeout=0.05,
        skip_item_on_timeout=True,
    )
    with pytest.raises(ItemInfrastructureError, match="infrastructure_timeout"):
        call_generate_with_watchdog(
            slow_generate,
            prompt="hello",
            model="mock",
            temperature=0.0,
            timeout=0.05,
            config=config,
        )


def test_watchdog_retries_with_ollama_stop(tmp_path: Path) -> None:
    calls = {"generate": 0, "stop": 0}

    def flaky_generate(*_args, **_kwargs) -> str:
        calls["generate"] += 1
        if calls["generate"] == 1:
            raise TimeoutError("first attempt timed out")
        return '{"item_id":"x","verdict":true,"certificate":{}}'

    def fake_stop(model: str) -> None:
        calls["stop"] += 1
        assert model == "mock-model"

    config = ItemWatchdogConfig(
        item_timeout=1.0,
        ollama_retries=1,
        ollama_restart_on_timeout=True,
        skip_item_on_timeout=True,
        ollama_stop_delay_seconds=0.0,
        provider="ollama",
    )
    text = call_generate_with_watchdog(
        flaky_generate,
        prompt="hello",
        model="mock-model",
        temperature=0.0,
        timeout=1.0,
        config=config,
        stop_model_fn=fake_stop,
    )
    assert "verdict" in text
    assert calls["stop"] == 1
    assert calls["generate"] == 2


def test_run_ollama_batch_skips_timed_out_item_and_continues(tmp_path: Path) -> None:
    items = [generate_reachability_item(seed) for seed in (1, 2, 3)]
    run_dir = tmp_path / "cell"
    run_dir.mkdir()
    mark_cell_running(
        run_dir,
        model="mock",
        model_dir="mock",
        family="C2",
        track="R0",
        temperature=0.0,
        item_source="items.jsonl",
        config_hash="abc",
        max_items=3,
    )

    calls: list[str] = []

    def generate(prompt: str, *, model: str, temperature: float, timeout: float) -> str:
        _ = (prompt, model, temperature, timeout)
        item_id = items[len(calls)].item_id
        calls.append(item_id)
        if len(calls) == 2:
            raise TimeoutError("simulated hang")
        item = items[len(calls) - 1]
        submission = {
            "item_id": item.item_id,
            "verdict": item.answer_key["verdict"],
            "certificate": item.answer_key["certificate"],
        }
        return json.dumps(submission)

    result = run_ollama_batch(
        items,
        generate,
        run_dir / "results.jsonl",
        OllamaBatchConfig(
            model="mock",
            temperature=0.0,
            timeout=0.1,
            max_items=3,
            skip_item_on_timeout=True,
        ),
        out_dir=run_dir,
    )

    assert len(calls) == 3
    assert result.infrastructure_failures == 1
    assert len(completed_item_ids(run_dir)) == 3
    scores = (run_dir / "scores.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(scores) == 3
    infra_rows = [json.loads(line) for line in scores if "infrastructure_timeout" in line]
    assert len(infra_rows) == 1
    assert infra_rows[0]["failure_stage"] == "provider_error"
    assert infra_rows[0]["provider_error_type"] == "timeout"
    status = read_cell_status(run_dir)
    assert status is not None
    assert status["items_completed"] == 3
    assert status["last_item_id"] == items[2].item_id


def test_run_ollama_batch_resumes_without_rerunning_completed_items(tmp_path: Path) -> None:
    item = generate_reachability_item(9)
    run_dir = tmp_path / "cell"
    run_dir.mkdir()
    existing = {
        "item_id": item.item_id,
        "family": "C2",
        "extractable": True,
        "verdict_correct": True,
        "certificate_valid": True,
        "fully_correct": True,
        "failure_stage": "correct",
        "parse_errors": [],
        "certificate_errors": [],
        "track": "R0",
        "model": "mock",
        "tool_invocation_count": 0,
        "track_failure_class": "correct",
    }
    (run_dir / "scores.jsonl").write_text(json.dumps(existing) + "\n", encoding="utf-8")

    def generate(*_args, **_kwargs) -> str:
        raise AssertionError("completed item must not be rerun")

    run_ollama_batch(
        [item],
        generate,
        run_dir / "results.jsonl",
        OllamaBatchConfig(model="mock", max_items=1, resume_items=True),
        out_dir=run_dir,
    )


def test_heartbeat_updates_cell_status(tmp_path: Path) -> None:
    run_dir = tmp_path / "heartbeat"
    run_dir.mkdir()
    mark_cell_running(
        run_dir,
        model="mock",
        model_dir="mock",
        family="C2",
        track="R1",
        temperature=0.2,
        item_source="items.jsonl",
        config_hash="abc",
        max_items=100,
    )
    update_cell_item_progress(
        run_dir,
        items_completed=29,
        max_items=100,
        last_item_id="item-29",
    )
    status = read_cell_status(run_dir)
    assert status is not None
    assert status["items_completed"] == 29
    assert status["max_items"] == 100
    assert status["last_item_id"] == "item-29"
    assert format_cell_progress(run_dir) == "29/100"


def test_stale_running_uses_updated_at_not_only_mtime(tmp_path: Path) -> None:
    run_dir = tmp_path / "stale"
    run_dir.mkdir()
    (run_dir / CELL_STATUS_JSON).write_text(
        json.dumps(
            {
                "status": "running",
                "started_at": "2020-01-01T00:00:00+00:00",
                "updated_at": "2020-01-01T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    assert is_stale_running(run_dir, threshold_seconds=60.0)
    assert detect_cell_status(run_dir, stale_threshold_seconds=60.0) == "stale-running"


def test_experiment_status_shows_item_progress(tmp_path: Path) -> None:
    run_dir = tmp_path / "mistral-nemo_12b" / "C2" / "R1"
    run_dir.mkdir(parents=True)
    mark_cell_running(
        run_dir,
        model="mistral-nemo:12b",
        model_dir="mistral-nemo_12b",
        family="C2",
        track="R1",
        temperature=0.0,
        item_source="items.jsonl",
        config_hash="abc",
        max_items=100,
    )
    update_cell_item_progress(
        run_dir,
        items_completed=29,
        max_items=100,
        last_item_id="item-29",
    )
    result = scan_experiment_status(
        tmp_path,
        models=("mistral-nemo:12b",),
        families=("C2",),
        tracks=("R1",),
        temperatures=(0.0,),
    )
    report = format_experiment_status_report(result)
    assert "29/100" in report


def test_stop_ollama_model_invokes_runner() -> None:
    seen: list[str] = []

    def fake_stop(model: str) -> None:
        seen.append(model)

    stop_ollama_model("mistral-nemo:12b", delay_seconds=0.0, stop_runner=fake_stop)
    assert seen == ["mistral-nemo:12b"]


def test_skip_item_on_timeout_false_fails_cell(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = generate_reachability_item(42)

    def fail_batch(*_args, **_kwargs):
        raise TimeoutError("simulated item timeout")

    monkeypatch.setattr(
        "fsmreasonbench.runners.track_pilot_models._run_cell_batch",
        fail_batch,
    )
    monkeypatch.setattr(
        "fsmreasonbench.runners.track_pilot_models._load_family_items",
        lambda _cfg: {"C2": [item]},
    )
    monkeypatch.setattr("fsmreasonbench.runners.track_pilot_models.time.sleep", lambda _s: None)

    out_dir = tmp_path / "matrix"
    run_track_pilot_models(
        TrackPilotModelsConfig(
            models=("mock",),
            families=("C2",),
            tracks=("R0",),
            c2_items_path=".",
            f1_items_path=".",
            out_dir=out_dir,
            max_items=1,
            skip_item_on_timeout=False,
            skip_completed=False,
        ),
        lambda _m, _t: lambda *_a, **_k: "{}",
    )
    error_path = out_dir / "mock" / "C2" / "R0" / "error.json"
    assert error_path.exists()
