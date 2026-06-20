"""Tests for track-aware Ollama batch evaluation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fsmreasonbench.cli.summarize_scores import main as summarize_scores_main
from fsmreasonbench.evaluator.jsonl import read_jsonl
from fsmreasonbench.evaluator.track_comparison import build_track_comparison, export_track_comparison
from fsmreasonbench.generator.reachability import generate_reachability_item
from fsmreasonbench.runners.ollama_batch import OllamaBatchConfig, run_ollama_batch
from fsmreasonbench.runners.ollama_track_batch import run_ollama_track_batch
from fsmreasonbench.runners.tool_executor import execute_tool_plan
from fsmreasonbench.tracks.audit import AuditLogBuilder
from fsmreasonbench.tracks.models import TrackId
from fsmreasonbench.tracks.replay import replay_audit_log


def _fsm_index(item):
    index = {item.fsm.fsm_id: item.fsm}
    if item.fsm_b is not None:
        index[item.fsm_b.fsm_id] = item.fsm_b
    return index


class FakeTrackModel:
    """Deterministic fake LLM client for track protocol tests."""

    def __init__(self, track: TrackId, item) -> None:
        self.track = track
        self.item = item
        self.calls = 0

    def generate(
        self,
        prompt: str,
        *,
        model: str,
        temperature: float,
        timeout: float,
    ) -> str:
        _ = (model, temperature, timeout)
        self.calls += 1
        if self.track == TrackId.R0:
            return json.dumps(
                {
                    "item_id": self.item.item_id,
                    "verdict": self.item.answer_key["verdict"],
                    "certificate": self.item.answer_key["certificate"],
                }
            )

        if self.calls == 1:
            if self.track == TrackId.R1:
                return json.dumps(
                    {
                        "phase": "tool_plan",
                        "tool_calls": [
                            {
                                "call_id": "1",
                                "tool": "step",
                                "inputs": {
                                    "fsm_id": self.item.fsm.fsm_id,
                                    "state": self.item.fsm.initial_state,
                                    "symbol": self.item.fsm.input_alphabet[0],
                                },
                            }
                        ],
                    }
                )
            return json.dumps(
                {
                    "phase": "tool_plan",
                    "tool_calls": [
                        {
                            "call_id": "1",
                            "tool": "solver.reachability_certificate",
                            "inputs": {
                                "fsm_id": self.item.fsm.fsm_id,
                                "target_state": self.item.question["target_state"],
                            },
                        }
                    ],
                }
            )

        return json.dumps(
            {
                "phase": "final_submission",
                "submission": {
                    "item_id": self.item.item_id,
                    "verdict": self.item.answer_key["verdict"],
                    "certificate": self.item.answer_key["certificate"],
                },
            }
        )


class FakeInvalidToolModel(FakeTrackModel):
    def generate(self, prompt, *, model, temperature, timeout) -> str:
        _ = (prompt, model, temperature, timeout)
        self.calls += 1
        if self.calls == 1:
            return json.dumps(
                {
                    "phase": "tool_plan",
                    "tool_calls": [
                        {
                            "call_id": "1",
                            "tool": "solver.is_reachable",
                            "inputs": {},
                        }
                    ],
                }
            )
        return json.dumps(
            {
                "phase": "final_submission",
                "submission": {
                    "item_id": self.item.item_id,
                    "verdict": False,
                    "certificate": {"certificate_type": "trace_witness", "payload": {}},
                },
            }
        )


def test_r0_ollama_batch_unchanged(tmp_path: Path) -> None:
    item = generate_reachability_item(42)
    model = FakeTrackModel(TrackId.R0, item)
    out_dir = tmp_path / "r0"
    result = run_ollama_batch(
        [item],
        model.generate,
        tmp_path / "r0.jsonl",
        OllamaBatchConfig(model="fake"),
        out_dir=out_dir,
    )
    assert model.calls == 1
    assert result.summary["fully_correct_rate"] == 1.0
    assert result.summary.get("track", "R0") == "R0"


def test_r1_executes_step_tools(tmp_path: Path) -> None:
    item = generate_reachability_item(42)
    model = FakeTrackModel(TrackId.R1, item)
    out_dir = tmp_path / "r1"
    result = run_ollama_track_batch(
        [item],
        model.generate,
        tmp_path / "r1.jsonl",
        OllamaBatchConfig(model="fake"),
        TrackId.R1,
        out_dir=out_dir,
    )
    assert model.calls == 2
    assert result.summary["track"] == "R1"
    assert result.summary["average_tool_calls_per_item"] >= 1.0
    transcript = json.loads(
        (out_dir / "transcripts" / f"{item.item_id}.json").read_text(encoding="utf-8")
    )
    assert transcript["tool_calls_requested"]
    assert transcript["audit_log"]["tool_invocations"]
    replay_audit_log(
        __import__(
            "fsmreasonbench.tracks.models", fromlist=["AuditLog"]
        ).AuditLog.from_dict(transcript["audit_log"]),
        fsm_by_id=_fsm_index(item),
    )


def test_r2_executes_solver_tools(tmp_path: Path) -> None:
    item = generate_reachability_item(43)
    model = FakeTrackModel(TrackId.R2, item)
    out_dir = tmp_path / "r2"
    result = run_ollama_track_batch(
        [item],
        model.generate,
        tmp_path / "r2.jsonl",
        OllamaBatchConfig(model="fake"),
        TrackId.R2,
        out_dir=out_dir,
    )
    assert model.calls == 2
    transcript = json.loads(
        (out_dir / "transcripts" / f"{item.item_id}.json").read_text(encoding="utf-8")
    )
    tools = {inv["tool_name"] for inv in transcript["audit_log"]["tool_invocations"]}
    assert "solver.reachability_certificate" in tools


def test_invalid_r1_tool_rejected(tmp_path: Path) -> None:
    item = generate_reachability_item(44)
    audit = AuditLogBuilder(TrackId.R1)
    results = execute_tool_plan(
        item,
        TrackId.R1,
        [{"call_id": "1", "tool": "solver.is_reachable", "inputs": {}}],
        audit,
    )
    assert results[0]["status"] == "rejected"
    assert audit.build().tool_invocations == ()


def test_r1_invalid_model_tool_plan_still_scores(tmp_path: Path) -> None:
    item = generate_reachability_item(45)
    model = FakeInvalidToolModel(TrackId.R1, item)
    out_dir = tmp_path / "r1_bad"
    run_ollama_track_batch(
        [item],
        model.generate,
        tmp_path / "bad.jsonl",
        OllamaBatchConfig(model="fake"),
        TrackId.R1,
        out_dir=out_dir,
    )
    scores = read_jsonl(out_dir / "scores.jsonl")
    assert scores[0]["track"] == "R1"
    assert scores[0]["tool_invocation_count"] == 0


def test_scores_jsonl_compatible_with_summarize_scores(tmp_path: Path, capsys) -> None:
    item = generate_reachability_item(46)
    model = FakeTrackModel(TrackId.R1, item)
    out_dir = tmp_path / "sum"
    run_ollama_track_batch(
        [item],
        model.generate,
        tmp_path / "sum.jsonl",
        OllamaBatchConfig(model="fake"),
        TrackId.R1,
        out_dir=out_dir,
    )
    assert (
        summarize_scores_main(["--scores", str(out_dir / "scores.jsonl")]) == 0
    )
    assert "fully_correct_rate" in capsys.readouterr().out


def test_compare_tracks_delegation_gaps(tmp_path: Path) -> None:
    item = generate_reachability_item(47)

    def write_run(track: TrackId, rate: float) -> Path:
        run_dir = tmp_path / track.value
        run_dir.mkdir(parents=True)
        summary = {
            "track": track.value,
            "model": "fake",
            "family": "C2",
            "n": 1,
            "extractability_rate": 1.0,
            "verdict_accuracy": rate,
            "certificate_valid_rate": rate,
            "fully_correct_rate": rate,
            "tool_invocation_rate": 0.0 if track == TrackId.R0 else 1.0,
            "average_tool_calls_per_item": 0.0 if track == TrackId.R0 else 2.0,
            "track_failure_counts": {
                label: (1 if label == "correct" and rate == 1.0 else 0)
                for label in (
                    "no_tool_plan",
                    "invalid_tool_plan",
                    "disallowed_tool",
                    "tool_execution_error",
                    "final_submission_not_extractable",
                    "verdict_wrong",
                    "certificate_invalid",
                    "correct",
                )
            },
        }
        (run_dir / "track_summary.json").write_text(
            json.dumps(summary), encoding="utf-8"
        )
        return run_dir

    r0 = write_run(TrackId.R0, 0.5)
    r1 = write_run(TrackId.R1, 0.7)
    r2 = write_run(TrackId.R2, 1.0)
    payload = build_track_comparison(r0_dir=r0, r1_dir=r1, r2_dir=r2)
    assert payload["delegation_gaps"]["R1_minus_R0"]["delegation_gap"]["fully_correct_rate"] == pytest.approx(
        0.2
    )
    assert payload["delegation_gaps"]["R2_minus_R0"]["delegation_gap"]["fully_correct_rate"] == pytest.approx(
        0.5
    )

    export_track_comparison(
        r0_dir=r0,
        r1_dir=r1,
        r2_dir=r2,
        out_json=tmp_path / "cmp.json",
        out_csv=tmp_path / "cmp.csv",
        out_md=tmp_path / "cmp.md",
    )
    assert (tmp_path / "cmp.md").exists()
