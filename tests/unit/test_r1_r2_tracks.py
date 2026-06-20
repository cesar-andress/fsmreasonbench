"""Tests for R1/R2 evaluation tracks."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from fsmreasonbench.evaluator.io import load_item
from fsmreasonbench.evaluator.models import FailureStage, ScoringRecord
from fsmreasonbench.evaluator.r1_r2_report import (
    build_r1_r2_report,
    export_r1_r2_report,
)
from fsmreasonbench.evaluator.scorer import score_item
from fsmreasonbench.evaluator.track_guards import validate_track_audit_log
from fsmreasonbench.tracks.agents import run_r0_agent, run_r1_agent, run_r2_agent
from fsmreasonbench.tracks.delegation import compute_delegation_gap as track_delegation_gap
from fsmreasonbench.tracks.models import TrackId
from fsmreasonbench.tracks.replay import replay_audit_log
from fsmreasonbench.tracks.runner import run_track
from fsmreasonbench.tracks.transcript import record_track_transcript

ROOT = Path(__file__).resolve().parents[2]
C2_EXAMPLE = ROOT / "examples/item_C2_reachability_seed42.json"
F1_EXAMPLE = ROOT / "examples/item_F1_separation_seed42.json"


class _CertificateGuard(dict):
    def __getitem__(self, key: str):
        if key == "certificate":
            raise AssertionError("track agent must not read answer_key.certificate")
        return super().__getitem__(key)

    def get(self, key: str, default=None):
        if key == "certificate":
            raise AssertionError("track agent must not read answer_key.certificate")
        return super().get(key, default)


def _fsm_index(item):
    index = {item.fsm.fsm_id: item.fsm}
    if item.fsm_b is not None:
        index[item.fsm_b.fsm_id] = item.fsm_b
    return index


@pytest.mark.parametrize(
    ("example_path", "track"),
    [
        (C2_EXAMPLE, TrackId.R0),
        (C2_EXAMPLE, TrackId.R1),
        (C2_EXAMPLE, TrackId.R2),
        (F1_EXAMPLE, TrackId.R0),
        (F1_EXAMPLE, TrackId.R1),
        (F1_EXAMPLE, TrackId.R2),
    ],
)
def test_track_agents_score_through_public_path(example_path: Path, track: TrackId) -> None:
    item = load_item(example_path)
    guarded = replace(item, answer_key=_CertificateGuard(item.answer_key))
    result = run_track(guarded, track)
    validate_track_audit_log(result.audit_log)
    assert result.scoring_record.extractable is True
    assert result.scoring_record.fully_correct is True
    assert result.scoring_record.failure_stage == FailureStage.CORRECT
    replay_audit_log(result.audit_log, fsm_by_id=_fsm_index(item))


def test_r0_has_no_tool_invocations() -> None:
    item = load_item(C2_EXAMPLE)
    result = run_r0_agent(item)
    assert result.audit_log.tool_invocations == ()
    validate_track_audit_log(result.audit_log)


def test_r1_logs_only_step_tools() -> None:
    item = load_item(C2_EXAMPLE)
    result = run_r1_agent(item)
    assert result.audit_log.tool_invocations
    assert all(inv.tool_name == "step" for inv in result.audit_log.tool_invocations)
    validate_track_audit_log(result.audit_log)


def test_r2_logs_solver_tools_and_certificate_assembly() -> None:
    item = load_item(C2_EXAMPLE)
    result = run_r2_agent(item)
    assert result.audit_log.tool_invocations
    assert all(
        inv.tool_name.startswith("solver.")
        for inv in result.audit_log.tool_invocations
    )
    assert result.audit_log.certificate_assembly
    validate_track_audit_log(result.audit_log)


def test_r1_vs_r2_behavior_differs_in_audit_log() -> None:
    item = load_item(C2_EXAMPLE)
    r1 = run_r1_agent(item)
    r2 = run_r2_agent(item)
    r1_tools = {inv.tool_name for inv in r1.audit_log.tool_invocations}
    r2_tools = {inv.tool_name for inv in r2.audit_log.tool_invocations}
    assert r1_tools == {"step"}
    assert r2_tools.issubset(
        {
            "solver.is_reachable",
            "solver.reachability_certificate",
        }
    )
    assert r2.audit_log.certificate_assembly
    assert r1.audit_log.tool_invocations[0].provenance == "r1_step_simulator"
    assert r2.audit_log.tool_invocations[0].provenance.startswith("oracle.")


def test_track_transcript_backward_compatible_scoring_record() -> None:
    item = load_item(C2_EXAMPLE)
    result = run_r0_agent(item)
    transcript = record_track_transcript(item, result)
    payload = transcript.to_dict()
    legacy = ScoringRecord.from_dict(payload["scoring_record"])
    assert legacy.fully_correct is True
    assert payload["track"] == "R0"
    assert "audit_log" in payload


def test_scoring_record_without_track_metadata_still_parses() -> None:
    item = load_item(C2_EXAMPLE)
    raw = run_r0_agent(item).raw_response
    record = score_item(item, raw)
    restored = ScoringRecord.from_dict(record.to_dict())
    assert restored == record


def test_delegation_gap_calculation() -> None:
    r0 = {
        "family": "C2",
        "cohort_id": "test",
        "n": 10,
        "track": "R0",
        "verdict_accuracy": 0.8,
        "certificate_valid_rate": 0.7,
        "fully_correct_rate": 0.6,
    }
    r2 = {
        "family": "C2",
        "cohort_id": "test",
        "n": 10,
        "track": "R2",
        "verdict_accuracy": 0.9,
        "certificate_valid_rate": 0.85,
        "fully_correct_rate": 0.75,
    }
    gap = track_delegation_gap(r0, r2)
    assert gap["delegation_gap"]["verdict_accuracy"] == pytest.approx(0.1)
    assert gap["delegation_gap"]["fully_correct_rate"] == pytest.approx(0.15)


def test_delegation_gap_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="matching family"):
        track_delegation_gap({"family": "C2", "n": 1}, {"family": "F1", "n": 1})


def test_export_r1_r2_report_writes_outputs(tmp_path: Path) -> None:
    export_r1_r2_report(
        ROOT,
        out_json=tmp_path / "summary.json",
        out_csv=tmp_path / "summary.csv",
        out_md=tmp_path / "report.md",
    )
    assert (tmp_path / "summary.json").exists()
    payload = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert payload["delegation_gaps"]
    assert len(payload["track_rows"]) == 6
    assert "delegation gap" in (tmp_path / "report.md").read_text(encoding="utf-8").lower()


def test_build_r1_r2_report_reference_tracks_reach_full_correctness() -> None:
    payload = build_r1_r2_report(ROOT)
    for row in payload["track_rows"]:
        assert row["fully_correct_rate"] == 1.0
    for gap in payload["delegation_gaps"]:
        assert gap["delegation_gap"]["fully_correct_rate"] == 0.0
