"""Local matrix runner hardening tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fsmreasonbench.generator.reachability import generate_reachability_item
from fsmreasonbench.generator.separation import SeparationGeneratorConfig, generate_separation_item
from fsmreasonbench.runners.cell_failure import (
    ERROR_JSON,
    classify_cell_error,
    is_cell_complete,
    is_cell_failed,
    read_cell_error,
    should_run_cell,
    write_cell_error,
)
from fsmreasonbench.runners.tool_executor import (
    C2_R2_ALLOWED_TOOLS,
    F1_R2_ALLOWED_TOOLS,
    allowed_r2_tools_for_family,
    execute_tool_plan,
)
from fsmreasonbench.runners.track_pilot_models import (
    TrackPilotModelsConfig,
    build_delegation_rows,
    render_track_pilot_report,
    run_track_pilot_models,
)
from fsmreasonbench.tracks.agents import run_r2_agent
from fsmreasonbench.tracks.audit import AuditLogBuilder
from fsmreasonbench.tracks.models import TrackId
from fsmreasonbench.tracks.solver_tools import SolverToolRegistry


def test_f1_equivalent_pair_r2_uses_equivalence_witness() -> None:
    item = generate_separation_item(
        201,
        SeparationGeneratorConfig(include_equivalent=True, equivalent_ratio=1.0, mode="random"),
    )
    assert item.answer_key["verdict"] is True
    result = run_r2_agent(item)
    assert result.scoring_record.fully_correct is True
    submission = json.loads(result.raw_response)
    assert submission["certificate"]["certificate_type"] == "equivalence_witness"
    assert submission["verdict"] is True


def test_f1_non_equivalent_pair_r2_uses_distinguishing_trace() -> None:
    item = generate_separation_item(
        202,
        SeparationGeneratorConfig(include_equivalent=False, min_distinguishing_trace_length=2),
    )
    assert item.answer_key["verdict"] is False
    result = run_r2_agent(item)
    assert result.scoring_record.fully_correct is True
    submission = json.loads(result.raw_response)
    assert submission["certificate"]["certificate_type"] == "distinguishing_trace"
    assert submission["verdict"] is False


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
    assert audit.build().tool_invocations == ()


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


def test_solver_registry_equivalent_guard() -> None:
    item = generate_separation_item(
        205,
        SeparationGeneratorConfig(include_equivalent=True, equivalent_ratio=1.0, mode="random"),
    )
    audit = AuditLogBuilder(TrackId.R2)
    solvers = SolverToolRegistry(audit=audit)
    with pytest.raises(ValueError, match="equivalence_certificate"):
        solvers.distinguishing_certificate(item.fsm_a, item.fsm_b)


def test_family_tool_registries_disjoint() -> None:
    assert allowed_r2_tools_for_family("C2") == C2_R2_ALLOWED_TOOLS
    assert allowed_r2_tools_for_family("F1") == F1_R2_ALLOWED_TOOLS
    assert C2_R2_ALLOWED_TOOLS.isdisjoint(F1_R2_ALLOWED_TOOLS)


def test_failed_cell_writes_error_json(tmp_path: Path) -> None:
    run_dir = tmp_path / "cell"
    write_cell_error(
        run_dir,
        error_type="timeout",
        error="timed out",
        model="llama3.1:8b",
        family="C2",
        track="R1",
        temperature=0.0,
        exc_type="RuntimeError",
    )
    assert is_cell_failed(run_dir)
    assert not is_cell_complete(run_dir)
    payload = read_cell_error(run_dir)
    assert payload is not None
    assert payload["error_type"] == "timeout"
    assert (run_dir / ERROR_JSON).exists()


def test_should_run_cell_retry_failed_only(tmp_path: Path) -> None:
    run_dir = tmp_path / "failed"
    write_cell_error(
        run_dir,
        error_type="timeout",
        error="timed out",
        model="m",
        family="C2",
        track="R1",
        temperature=0.0,
    )
    assert should_run_cell(
        run_dir,
        skip_completed=True,
        retry_failed=True,
        skip_failed=False,
        force=False,
    )
    assert not should_run_cell(
        run_dir,
        skip_completed=True,
        retry_failed=False,
        skip_failed=True,
        force=False,
    )


def test_report_separates_failed_cells_by_type() -> None:
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
            "track_rows": [],
            "delegation_rows": [],
            "temperature_delta_rows": [],
            "failed_cells": [
                {
                    "model": "m",
                    "family": "C2",
                    "track": "R1",
                    "temperature": 0.0,
                    "error": "timed out",
                    "error_type": "timeout",
                },
                {
                    "model": "m",
                    "family": "C2",
                    "track": "R2",
                    "temperature": 0.0,
                    "error": "cannot build distinguishing trace for equivalent DFAs",
                    "error_type": "tool_execution_error",
                },
            ],
        }
    )
    assert "#### Timeout" in report
    assert "#### Tool execution error" in report
    assert "do not interpret as zero improvement" in report


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
    assert "R1" in delegation[0]["missing_tracks"]


def test_classify_cell_error() -> None:
    assert classify_cell_error("ollama request failed: timed out") == "timeout"
    assert (
        classify_cell_error("internal error: cannot build distinguishing trace for equivalent DFAs")
        == "tool_execution_error"
    )


def test_run_track_pilot_records_cell_error_on_batch_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = generate_reachability_item(206)

    def boom(*_args, **_kwargs):
        raise RuntimeError("timed out")

    monkeypatch.setattr(
        "fsmreasonbench.runners.track_pilot_models.run_ollama_track_batch",
        boom,
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

    def factory(_model: str, _temp: float):
        return lambda *_a, **_k: "{}"

    monkeypatch.setattr(
        "fsmreasonbench.runners.track_pilot_models._load_family_items",
        lambda _cfg: {"C2": [item]},
    )

    result = run_track_pilot_models(config, factory)
    assert len(result.failed_cells) == 1
    run_dir = Path(result.failed_cells[0]["run_dir"])
    assert read_cell_error(run_dir) is not None
    assert read_cell_error(run_dir)["error_type"] == "timeout"
