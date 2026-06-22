"""Incremental, resumable experiment runner tests."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from fsmreasonbench.evaluator.jsonl import read_jsonl
from fsmreasonbench.generator.reachability import generate_reachability_item
from fsmreasonbench.runners.cell_failure import ERROR_JSON, write_cell_error
from fsmreasonbench.runners.experiment_cells import (
    CELL_STATUS_JSON,
    completed_item_ids,
    detect_cell_status,
    is_stale_running,
    mark_cell_running,
    prepare_cell_rerun,
    should_run_cell,
    write_cell_status,
)
from fsmreasonbench.runners.experiment_status import (
    format_experiment_status_report,
    scan_experiment_status,
)
from fsmreasonbench.runners.track_pilot_models import (
    TrackPilotModelsConfig,
    apply_incremental_safe,
    format_dry_run_report,
    run_track_pilot_models,
)


def _write_completed_cell(run_dir: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "n": 20,
        "extractability_rate": 1.0,
        "verdict_accuracy": 1.0,
        "certificate_valid_rate": 1.0,
        "fully_correct_rate": 1.0,
    }
    (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (run_dir / "scores.jsonl").write_text('{"item_id":"i1"}\n', encoding="utf-8")
    write_cell_status(run_dir, status="completed", model="m")


def test_completed_cell_skip(tmp_path: Path) -> None:
    run_dir = tmp_path / "done"
    _write_completed_cell(run_dir)
    assert not should_run_cell(
        run_dir,
        skip_completed=True,
        retry_failed=False,
        skip_failed=False,
        force_all=False,
        force_cell=False,
    )


def test_failed_cell_retry_only_with_flag(tmp_path: Path) -> None:
    run_dir = tmp_path / "failed"
    write_cell_error(
        run_dir,
        error_type="timeout",
        error_message="timed out",
        model="m",
        model_dir="m",
        family="C2",
        track="R1",
        temperature=0.0,
        out_dir=run_dir,
    )
    assert not should_run_cell(
        run_dir,
        skip_completed=True,
        retry_failed=False,
        skip_failed=False,
        force_all=False,
        force_cell=False,
    )
    assert should_run_cell(
        run_dir,
        skip_completed=True,
        retry_failed=True,
        skip_failed=False,
        force_all=False,
        force_cell=False,
    )


def test_missing_cell_runs_without_retry_flag(tmp_path: Path) -> None:
    run_dir = tmp_path / "missing"
    run_dir.mkdir()
    assert should_run_cell(
        run_dir,
        skip_completed=True,
        retry_failed=False,
        skip_failed=False,
        force_all=False,
        force_cell=False,
    )


def test_partial_item_level_resume(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_dir = tmp_path / "matrix" / "mock" / "C2" / "R0"
    run_dir.mkdir(parents=True)
    (run_dir / "scores.jsonl").write_text('{"item_id":"item-0"}\n', encoding="utf-8")
    items = [generate_reachability_item(i) for i in range(3)]
    for idx, item in enumerate(items):
        object.__setattr__(item, "item_id", f"item-{idx}")

    seen: list[str] = []

    def fake_batch(*, items, generate, run_dir, model, family, track, temperature, config, item_timeout):
        for item in items:
            if item.item_id in completed_item_ids(run_dir):
                continue
            seen.append(item.item_id)
            from fsmreasonbench.evaluator.jsonl import append_jsonl

            append_jsonl(run_dir / "scores.jsonl", {"item_id": item.item_id})
            append_jsonl(run_dir / "results.jsonl", {"item_id": item.item_id})
        summary = {
            "n": 3,
            "extractability_rate": 1.0,
            "verdict_accuracy": 1.0,
            "certificate_valid_rate": 1.0,
            "fully_correct_rate": 1.0,
            "tool_invocation_rate": 0.0,
            "average_tool_calls_per_item": 0.0,
        }
        (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
        (run_dir / "scores.jsonl").write_text(
            "\n".join(
                json.dumps({"item_id": f"item-{idx}"}) for idx in range(3)
            )
            + "\n",
            encoding="utf-8",
        )

    monkeypatch.setattr(
        "fsmreasonbench.runners.track_pilot_models._run_cell_batch",
        fake_batch,
    )
    monkeypatch.setattr(
        "fsmreasonbench.runners.track_pilot_models._load_family_items",
        lambda _cfg: {"C2": items},
    )

    config = TrackPilotModelsConfig(
        models=("mock",),
        families=("C2",),
        tracks=("R0",),
        c2_items_path=".",
        f1_items_path=".",
        out_dir=tmp_path / "matrix",
        temperatures=(0.0,),
        skip_completed=False,
        resume_items=True,
    )
    run_track_pilot_models(config, lambda _m, _t: lambda *_a, **_k: "{}")
    assert seen == ["item-1", "item-2"]


def test_stale_running_detection(tmp_path: Path) -> None:
    run_dir = tmp_path / "stale"
    run_dir.mkdir()
    status_path = run_dir / CELL_STATUS_JSON
    status_path.write_text(
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


def test_dry_run_output(tmp_path: Path) -> None:
    completed = tmp_path / "matrix" / "mock" / "C2" / "R0"
    _write_completed_cell(completed)
    config = TrackPilotModelsConfig(
        models=("mock",),
        families=("C2",),
        tracks=("R0",),
        c2_items_path=".",
        f1_items_path=".",
        out_dir=tmp_path / "matrix",
        temperatures=(0.0,),
        dry_run=True,
    )
    result = run_track_pilot_models(config, lambda _m, _t: lambda *_a, **_k: "{}")
    assert result.cell_status_counts["completed"] == 1


def test_experiment_status_output(tmp_path: Path) -> None:
    completed = tmp_path / "mock" / "C2" / "R0"
    _write_completed_cell(completed)
    missing = tmp_path / "mock" / "C2" / "R1"
    missing.mkdir(parents=True)
    result = scan_experiment_status(
        tmp_path,
        models=("mock",),
        families=("C2",),
        tracks=("R0", "R1"),
        temperatures=(0.0,),
    )
    report = format_experiment_status_report(result)
    assert "**Completed:** 1" in report
    assert "**Missing:** 1" in report
    assert "Suggested retry" in report


def test_incremental_safe_runs_all_pending_cells(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_batch(*, items, generate, run_dir, model, family, track, temperature, config, item_timeout):
        calls.append(f"{family}:{track}")
        summary = {
            "n": 1,
            "extractability_rate": 1.0,
            "verdict_accuracy": 1.0,
            "certificate_valid_rate": 1.0,
            "fully_correct_rate": 1.0,
            "tool_invocation_rate": 0.0,
            "average_tool_calls_per_item": 0.0,
        }
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
        (run_dir / "scores.jsonl").write_text('{"item_id":"x"}\n', encoding="utf-8")

    monkeypatch.setattr(
        "fsmreasonbench.runners.track_pilot_models._run_cell_batch",
        fake_batch,
    )
    monkeypatch.setattr(
        "fsmreasonbench.runners.track_pilot_models._load_family_items",
        lambda _cfg: {"C2": [generate_reachability_item(1)]},
    )
    monkeypatch.setattr("fsmreasonbench.runners.track_pilot_models.time.sleep", lambda _s: None)

    config = apply_incremental_safe(
        TrackPilotModelsConfig(
            models=("mock",),
            families=("C2",),
            tracks=("R0", "R1"),
            c2_items_path=".",
            f1_items_path=".",
            out_dir=tmp_path / "matrix",
            temperatures=(0.0,),
            incremental_safe=True,
            skip_completed=False,
        )
    )
    assert config.max_cells is None
    assert config.stop_after_failures == 1
    assert config.sleep_between_cells == 10.0
    assert config.resume_items is True
    run_track_pilot_models(config, lambda _m, _t: lambda *_a, **_k: "{}")
    assert calls == ["C2:R0", "C2:R1"]


def test_stop_after_failures_stops_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"n": 0}

    def fail_batch(*_args, **_kwargs):
        calls["n"] += 1
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "fsmreasonbench.runners.track_pilot_models._run_cell_batch",
        fail_batch,
    )
    monkeypatch.setattr(
        "fsmreasonbench.runners.track_pilot_models._load_family_items",
        lambda _cfg: {"C2": [generate_reachability_item(1)]},
    )
    monkeypatch.setattr("fsmreasonbench.runners.track_pilot_models.time.sleep", lambda _s: None)

    config = TrackPilotModelsConfig(
        models=("mock",),
        families=("C2",),
        tracks=("R0", "R1", "R2"),
        c2_items_path=".",
        f1_items_path=".",
        out_dir=tmp_path / "matrix",
        temperatures=(0.0,),
        skip_completed=False,
        stop_after_failures=2,
    )
    run_track_pilot_models(config, lambda _m, _t: lambda *_a, **_k: "{}")
    assert calls["n"] == 2


def test_report_reads_persisted_error_json_after_restart(tmp_path: Path) -> None:
    run_dir = tmp_path / "mock" / "C2" / "R1"
    write_cell_error(
        run_dir,
        error_type="timeout",
        error_message="timed out",
        model="mock",
        model_dir="mock",
        family="C2",
        track="R1",
        temperature=0.0,
        out_dir=run_dir,
    )
    write_cell_status(run_dir, status="failed", model="mock")

    config = TrackPilotModelsConfig(
        models=("mock",),
        families=("C2",),
        tracks=("R1",),
        c2_items_path=".",
        f1_items_path=".",
        out_dir=tmp_path,
        temperatures=(0.0,),
        report_only=True,
    )
    result = run_track_pilot_models(config, lambda _m, _t: lambda *_a, **_k: "{}")
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert result.cell_status_counts["failed"] == 1
    assert "timed out" in report
    assert (run_dir / ERROR_JSON).exists()


def test_prepare_cell_rerun_keeps_scores_when_resuming(tmp_path: Path) -> None:
    run_dir = tmp_path / "cell"
    run_dir.mkdir()
    (run_dir / "scores.jsonl").write_text('{"item_id":"a"}\n', encoding="utf-8")
    prepare_cell_rerun(run_dir, force_cell=False, resume_items=True)
    assert (run_dir / "scores.jsonl").exists()


def test_force_cell_wipes_partial_outputs(tmp_path: Path) -> None:
    run_dir = tmp_path / "cell"
    run_dir.mkdir()
    (run_dir / "scores.jsonl").write_text('{"item_id":"a"}\n', encoding="utf-8")
    prepare_cell_rerun(run_dir, force_cell=True, resume_items=True)
    assert not (run_dir / "scores.jsonl").exists()


def test_mark_cell_running_writes_status(tmp_path: Path) -> None:
    run_dir = tmp_path / "cell"
    run_dir.mkdir()
    mark_cell_running(
        run_dir,
        model="m",
        model_dir="m",
        family="C2",
        track="R0",
        temperature=0.0,
        item_source="/items.jsonl",
        config_hash="abc",
        max_items=20,
    )
    payload = json.loads((run_dir / CELL_STATUS_JSON).read_text(encoding="utf-8"))
    assert payload["status"] == "running"
    assert payload["config_hash"] == "abc"
