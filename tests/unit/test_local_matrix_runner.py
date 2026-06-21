"""Local matrix runner hardening tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fsmreasonbench.generator.reachability import generate_reachability_item
from fsmreasonbench.generator.separation import SeparationGeneratorConfig, generate_separation_item
from fsmreasonbench.runners.cell_failure import (
    ERROR_JSON,
    ERROR_PREVIOUS_JSON,
    classify_cell,
    classify_cell_error,
    is_cell_complete,
    is_cell_failed,
    prepare_cell_rerun,
    read_cell_error,
    should_run_cell,
    write_cell_error,
)
from fsmreasonbench.runners.tool_executor import execute_tool_plan
from fsmreasonbench.runners.track_pilot_models import (
    TrackPilotModelsConfig,
    build_delegation_rows,
    finalize_matrix_run,
    render_track_pilot_report,
    run_track_pilot_models,
    scan_matrix_inventory,
)
from fsmreasonbench.tracks.agents import run_r2_agent
from fsmreasonbench.tracks.audit import AuditLogBuilder
from fsmreasonbench.tracks.models import TrackId


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
    (run_dir / "scores.jsonl").write_text("{}\n", encoding="utf-8")


def test_f1_equivalent_pair_r2_uses_equivalence_witness() -> None:
    item = generate_separation_item(
        201,
        SeparationGeneratorConfig(include_equivalent=True, equivalent_ratio=1.0, mode="random"),
    )
    result = run_r2_agent(item)
    submission = json.loads(result.raw_response)
    assert submission["certificate"]["certificate_type"] == "equivalence_witness"
    assert result.scoring_record.fully_correct is True


def test_f1_non_equivalent_pair_r2_uses_distinguishing_trace() -> None:
    item = generate_separation_item(
        202,
        SeparationGeneratorConfig(include_equivalent=False, min_distinguishing_trace_length=2),
    )
    result = run_r2_agent(item)
    submission = json.loads(result.raw_response)
    assert submission["certificate"]["certificate_type"] == "distinguishing_trace"
    assert result.scoring_record.fully_correct is True


def test_c2_r2_cannot_access_f1_tools() -> None:
    item = generate_reachability_item(203)
    audit = AuditLogBuilder(TrackId.R2)
    results = execute_tool_plan(
        item,
        TrackId.R2,
        [
            {
                "call_id": "1",
                "tool": "solver.distinguishing_certificate",
                "inputs": {
                    "fsm_id_a": item.fsm.fsm_id,
                    "fsm_id_b": item.fsm.fsm_id,
                },
            }
        ],
        audit,
    )
    assert results[0]["status"] == "rejected"
    assert "not allowed for family 'C2'" in results[0]["error"]


def test_f1_r2_distinguishing_on_equivalent_pair_rejected_not_fatal() -> None:
    item = generate_separation_item(
        204,
        SeparationGeneratorConfig(include_equivalent=True, equivalent_ratio=1.0, mode="random"),
    )
    audit = AuditLogBuilder(TrackId.R2)
    results = execute_tool_plan(
        item,
        TrackId.R2,
        [
            {
                "call_id": "1",
                "tool": "solver.distinguishing_certificate",
                "inputs": {
                    "fsm_id_a": item.fsm_a.fsm_id,
                    "fsm_id_b": item.fsm_b.fsm_id,
                },
            }
        ],
        audit,
    )
    assert results[0]["status"] == "rejected"
    assert "equivalence_certificate" in results[0]["error"]


def test_cell_classification_completed_failed_missing_partial(tmp_path: Path) -> None:
    completed = tmp_path / "completed"
    _write_completed_cell(completed)
    assert classify_cell(completed) == "completed"
    assert is_cell_complete(completed)

    failed = tmp_path / "failed"
    write_cell_error(
        failed,
        error_type="timeout",
        error_message="timed out",
        model="m",
        model_dir="m",
        family="C2",
        track="R1",
        temperature=0.0,
        out_dir=failed,
    )
    assert classify_cell(failed) == "failed"
    assert is_cell_failed(failed)
    assert not is_cell_complete(failed)

    missing = tmp_path / "missing"
    missing.mkdir()
    assert classify_cell(missing) == "missing"

    partial = tmp_path / "partial"
    partial.mkdir()
    (partial / "results.jsonl").write_text("{}\n", encoding="utf-8")
    assert classify_cell(partial) == "partial"


def test_error_json_full_schema(tmp_path: Path) -> None:
    run_dir = tmp_path / "cell"
    write_cell_error(
        run_dir,
        error_type="timeout",
        error_message="ollama request failed: timed out",
        model="llama3.1:8b",
        model_dir="llama3.1_8b",
        family="C2",
        track="R1",
        temperature=0.0,
        out_dir=run_dir,
        started_at="2026-06-20T00:00:00+00:00",
        ended_at="2026-06-20T00:10:00+00:00",
        partial_outputs_present=False,
        retryable=True,
        exc_type="RuntimeError",
        tb="Traceback...\n",
    )
    payload = read_cell_error(run_dir)
    assert payload is not None
    for key in (
        "model",
        "model_dir",
        "family",
        "track",
        "temperature",
        "out_dir",
        "error_type",
        "error_message",
        "traceback",
        "started_at",
        "ended_at",
        "partial_outputs_present",
        "retryable",
    ):
        assert key in payload


def test_prepare_cell_rerun_archives_previous_error(tmp_path: Path) -> None:
    run_dir = tmp_path / "cell"
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
    prepare_cell_rerun(run_dir)
    assert not (run_dir / ERROR_JSON).exists()
    assert (run_dir / ERROR_PREVIOUS_JSON).exists()


def test_retry_failed_includes_missing_and_partial(tmp_path: Path) -> None:
    completed = tmp_path / "done"
    _write_completed_cell(completed)
    missing = tmp_path / "missing"
    missing.mkdir()
    partial = tmp_path / "partial"
    partial.mkdir()
    (partial / "scores.jsonl").write_text("{}\n", encoding="utf-8")

    assert not should_run_cell(
        completed,
        skip_completed=True,
        retry_failed=True,
        skip_failed=False,
        force=False,
    )
    assert should_run_cell(
        missing,
        skip_completed=True,
        retry_failed=True,
        skip_failed=False,
        force=False,
    )
    assert should_run_cell(
        partial,
        skip_completed=True,
        retry_failed=True,
        skip_failed=False,
        force=False,
    )


def test_skip_failed_skips_error_json_cells(tmp_path: Path) -> None:
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
        skip_failed=True,
        force=False,
    )


def test_timeout_writes_error_json_on_batch_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = generate_reachability_item(206)

    def boom(*_args, **_kwargs):
        raise RuntimeError("ollama request failed: timed out")

    monkeypatch.setattr(
        "fsmreasonbench.runners.track_pilot_models.run_ollama_track_batch",
        boom,
    )
    monkeypatch.setattr(
        "fsmreasonbench.runners.track_pilot_models._load_family_items",
        lambda _cfg: {"C2": [item]},
    )

    config = TrackPilotModelsConfig(
        models=("mock",),
        families=("C2",),
        tracks=("R1",),
        c2_items_path=".",
        f1_items_path=".",
        out_dir=tmp_path / "matrix",
        temperatures=(0.0,),
        skip_completed=False,
    )
    result = run_track_pilot_models(config, lambda _m, _t: lambda *_a, **_k: "{}")
    assert result.cell_status_counts["failed"] == 1
    run_dir = Path(result.failed_cells[0]["run_dir"])
    payload = read_cell_error(run_dir)
    assert payload is not None
    assert payload["error_type"] == "timeout"
    assert payload["traceback"]


def test_internal_error_writes_error_json_with_root_cause(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = generate_reachability_item(207)

    def boom(*_args, **_kwargs):
        raise RuntimeError("internal error: cannot build distinguishing trace for equivalent DFAs")

    monkeypatch.setattr(
        "fsmreasonbench.runners.track_pilot_models.run_ollama_track_batch",
        boom,
    )
    monkeypatch.setattr(
        "fsmreasonbench.runners.track_pilot_models._load_family_items",
        lambda _cfg: {"C2": [item]},
    )

    config = TrackPilotModelsConfig(
        models=("mock",),
        families=("C2",),
        tracks=("R2",),
        c2_items_path=".",
        f1_items_path=".",
        out_dir=tmp_path / "matrix",
        temperatures=(0.0,),
        skip_completed=False,
    )
    result = run_track_pilot_models(config, lambda _m, _t: lambda *_a, **_k: "{}")
    payload = read_cell_error(Path(result.failed_cells[0]["run_dir"]))
    assert payload is not None
    assert payload["error_type"] == "tool_execution_error"
    assert payload["root_cause"]


def test_report_regenerated_from_persisted_error_json(tmp_path: Path) -> None:
    root = tmp_path / "matrix"
    run_dir = root / "llama3.1_8b" / "C2" / "R2"
    write_cell_error(
        run_dir,
        error_type="tool_execution_error",
        error_message="internal error: cannot build distinguishing trace for equivalent DFAs",
        model="llama3.1:8b",
        model_dir="llama3.1_8b",
        family="C2",
        track="R2",
        temperature=0.0,
        out_dir=run_dir,
        root_cause="model_requested_wrong_tool",
    )
    _write_completed_cell(root / "qwen2.5-coder_7b" / "C2" / "R0")

    config = TrackPilotModelsConfig(
        models=("qwen2.5-coder:7b", "llama3.1:8b"),
        families=("C2",),
        tracks=("R0", "R2"),
        c2_items_path=".",
        f1_items_path=".",
        out_dir=root,
        temperatures=(0.0,),
        report_only=True,
    )
    inventory = scan_matrix_inventory(root, config)
    result = finalize_matrix_run(root, config, inventory, cohort_ids={"C2": "test"})
    assert result.cell_status_counts["completed"] == 1
    assert result.cell_status_counts["failed"] == 1
    report = (root / "report.md").read_text(encoding="utf-8")
    assert "Cell status" in report
    assert "Incomplete cells" in report
    assert "llama3.1:8b" in report


def test_report_includes_status_counts_and_incomplete_table() -> None:
    report = render_track_pilot_report(
        {
            "experiment": "local_matrix",
            "models": ["m"],
            "families": ["C2"],
            "tracks": ["R2"],
            "temperatures": [0.0],
            "max_items": 20,
            "timeout": 120.0,
            "cohort_ids": {"C2": "c"},
            "cell_status_counts": {
                "completed": 58,
                "failed": 3,
                "missing": 10,
                "partial": 1,
            },
            "track_rows": [],
            "delegation_rows": [],
            "temperature_delta_rows": [],
            "incomplete_cells": [
                {
                    "model": "m",
                    "family": "C2",
                    "track": "R1",
                    "temperature": 0.0,
                    "cell_status": "missing",
                    "error_type": "unknown",
                    "error_message": "cell never completed",
                }
            ],
            "failed_cells": [],
        }
    )
    assert "**Completed:** 58" in report
    assert "**Missing:** 10" in report
    assert "Incomplete cells" in report


def test_delegation_rows_mark_incomplete_when_track_missing() -> None:
    rows = [
        {
            "model": "m",
            "family": "C2",
            "track": "R0",
            "temperature": 0.0,
            "cohort_id": "c",
            "n": 20,
            "status": "completed",
            "extractability_rate": 1.0,
            "verdict_accuracy": 0.5,
            "certificate_valid_rate": 0.0,
            "fully_correct_rate": 0.0,
        }
    ]
    delegation = build_delegation_rows(rows)
    assert delegation[0]["delegation_incomplete"] is True
