"""Tests for track prompt hardening and failure taxonomy."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fsmreasonbench.evaluator.track_comparison import build_track_comparison
from fsmreasonbench.evaluator.track_failure_taxonomy import classify_track_failure
from fsmreasonbench.generator.reachability import generate_reachability_item
from fsmreasonbench.runners.ollama_batch import OllamaBatchConfig, run_ollama_batch
from fsmreasonbench.runners.track_prompt_schemas import (
    C2_TRACE_WITNESS_EXAMPLE,
    C2_UNREACHABILITY_WITNESS_EXAMPLE,
    F1_DISTINGUISHING_TRACE_EXAMPLE,
    F1_EQUIVALENCE_WITNESS_EXAMPLE,
    FINAL_SUBMISSION_ENVELOPE,
    INVALID_PAYLOAD_EXAMPLES,
)
from fsmreasonbench.runners.track_prompts import render_track_prompt
from fsmreasonbench.tracks.models import TrackId


@pytest.mark.parametrize(
    ("family", "generator"),
    [
        ("C2", lambda: generate_reachability_item(42)),
    ],
)
def test_phase2_prompt_contains_all_certificate_examples_for_c2(family, generator) -> None:
    item = generator()
    prompt = render_track_prompt(item, TrackId.R1, phase="tool_results", tool_results=[])
    assert "trace_witness" in prompt
    assert "unreachability_witness" in prompt
    assert C2_TRACE_WITNESS_EXAMPLE.strip() in prompt
    assert C2_UNREACHABILITY_WITNESS_EXAMPLE.strip() in prompt
    assert FINAL_SUBMISSION_ENVELOPE.strip() in prompt
    assert "reachable_states as string" in prompt
    assert INVALID_PAYLOAD_EXAMPLES.strip() in prompt
    assert "Pre-submit checklist" in prompt


def test_phase2_prompt_contains_f1_certificate_examples() -> None:
    from fsmreasonbench.generator.separation import (
        SeparationGeneratorConfig,
        generate_separation_item,
    )

    item = generate_separation_item(
        42,
        SeparationGeneratorConfig(min_distinguishing_trace_length=1),
    )
    prompt = render_track_prompt(item, TrackId.R2, phase="tool_results", tool_results=[])
    assert F1_DISTINGUISHING_TRACE_EXAMPLE.strip() in prompt
    assert F1_EQUIVALENCE_WITNESS_EXAMPLE.strip() in prompt
    assert "distinguishing_trace" in prompt
    assert "equivalence_witness" in prompt


def test_r0_prompt_unchanged_for_c2() -> None:
    item = generate_reachability_item(99)
    r0 = render_track_prompt(item, TrackId.R0)
    assert "tool_plan" not in r0
    assert "final_submission" not in r0
    assert "reachable" in r0.lower()


def test_classify_final_submission_not_extractable() -> None:
    label = classify_track_failure(
        track="R1",
        scoring_record={
            "fully_correct": False,
            "extractable": False,
            "failure_stage": "not_extractable",
        },
        tool_calls_requested=[{"call_id": "1", "tool": "step", "inputs": {}}],
        tool_outputs=[{"call_id": "1", "status": "executed", "outputs": {}}],
        tool_plan_valid=True,
    )
    assert label == "final_submission_not_extractable"


def test_compare_tracks_includes_failure_counts(tmp_path: Path) -> None:
    def write_run(track: str) -> Path:
        run_dir = tmp_path / track
        run_dir.mkdir(parents=True)
        summary = {
            "track": track,
            "model": "fake",
            "family": "C2",
            "n": 2,
            "extractability_rate": 0.5,
            "verdict_accuracy": 0.5,
            "certificate_valid_rate": 0.0,
            "fully_correct_rate": 0.0,
            "tool_invocation_rate": 0.0 if track == "R0" else 1.0,
            "average_tool_calls_per_item": 0.0 if track == "R0" else 1.0,
            "track_failure_counts": {
                "no_tool_plan": 0,
                "invalid_tool_plan": 0,
                "disallowed_tool": 0,
                "tool_execution_error": 0,
                "final_submission_not_extractable": 1 if track == "R1" else 0,
                "verdict_wrong": 1 if track == "R0" else 0,
                "certificate_invalid": 0,
                "correct": 0,
            },
        }
        (run_dir / "track_summary.json").write_text(json.dumps(summary), encoding="utf-8")
        return run_dir

    payload = build_track_comparison(
        r0_dir=write_run("R0"),
        r1_dir=write_run("R1"),
        r2_dir=write_run("R2"),
        cohort_id="test-cohort",
    )
    assert payload["track_rows"][1]["count_final_submission_not_extractable"] == 1
    assert payload["track_rows"][0]["count_verdict_wrong"] == 1


def test_r0_batch_still_scores_correctly(tmp_path: Path) -> None:
    item = generate_reachability_item(42)
    submission = {
        "item_id": item.item_id,
        "verdict": item.answer_key["verdict"],
        "certificate": item.answer_key["certificate"],
    }

    def fake_generate(prompt, *, model, temperature, timeout):
        return json.dumps(submission)

    result = run_ollama_batch(
        [item],
        fake_generate,
        tmp_path / "r0.jsonl",
        OllamaBatchConfig(model="fake"),
        out_dir=tmp_path / "run",
    )
    assert result.summary["fully_correct_rate"] == 1.0
    assert result.summary["track"] == "R0"
    assert result.summary["track_failure_counts"]["correct"] == 1
