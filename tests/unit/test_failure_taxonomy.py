"""Failure taxonomy analysis tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fsmreasonbench.cli.failure_taxonomy import main as failure_taxonomy_main
from fsmreasonbench.cli.failure_taxonomy_batch import main as failure_taxonomy_batch_main
from fsmreasonbench.evaluator.failure_taxonomy import (
    TAXONOMY_CATEGORIES,
    analyze_failure_taxonomy,
    analyze_failure_taxonomy_batch,
    classify_certificate_errors,
    discover_scored_run_pairs,
    format_failure_taxonomy_report,
)
from fsmreasonbench.evaluator.jsonl import write_jsonl


def _certificate_invalid_record(
    item_id: str,
    *,
    family: str,
    certificate_errors: list[str],
) -> dict[str, object]:
    return {
        "item_id": item_id,
        "family": family,
        "extractable": True,
        "verdict_correct": True,
        "certificate_valid": False,
        "fully_correct": False,
        "failure_stage": "certificate_invalid",
        "parse_errors": [],
        "certificate_errors": certificate_errors,
    }


def _write_taxonomy_fixture(tmp_path: Path) -> tuple[Path, Path]:
    scores_path = tmp_path / "scores.jsonl"
    results_path = tmp_path / "results.jsonl"

    write_jsonl(
        scores_path,
        [
            _certificate_invalid_record(
                "c2_wrong_trace_format",
                family="C2",
                certificate_errors=["trace and state_sequence must be arrays"],
            ),
            _certificate_invalid_record(
                "c2_replay_failure",
                family="C2",
                certificate_errors=["simulation failed: invalid transition"],
            ),
            _certificate_invalid_record(
                "c2_incomplete_reachability",
                family="C2",
                certificate_errors=["missing reachable states: ['q1']"],
            ),
            _certificate_invalid_record(
                "f1_acceptance_mismatch",
                family="F1",
                certificate_errors=["acceptance.A mismatch: replay=True, declared=False"],
            ),
            _certificate_invalid_record(
                "f1_equivalence_hash_mismatch",
                family="F1",
                certificate_errors=["minimized_hash_A mismatch"],
            ),
            _certificate_invalid_record(
                "f1_wrong_certificate_type",
                family="F1",
                certificate_errors=["unsupported certificate_type: 'bogus'"],
            ),
            _certificate_invalid_record(
                "f1_wrong_fsm_ids",
                family="F1",
                certificate_errors=["fsm_ids mismatch: expected ['A', 'B'], got ['X', 'Y']"],
            ),
            _certificate_invalid_record(
                "f1_malformed_payload",
                family="F1",
                certificate_errors=["payload.acceptance.A must be boolean"],
            ),
            _certificate_invalid_record(
                "f1_other",
                family="F1",
                certificate_errors=["trace does not reach target"],
            ),
            {
                "item_id": "item_correct",
                "family": "C2",
                "extractable": True,
                "verdict_correct": True,
                "certificate_valid": True,
                "fully_correct": True,
                "failure_stage": "correct",
                "parse_errors": [],
                "certificate_errors": [],
            },
        ],
    )
    write_jsonl(
        results_path,
        [{"item_id": f"item_{index}", "family": "C2"} for index in range(10)],
    )
    return scores_path, results_path


@pytest.mark.parametrize(
    ("errors", "expected"),
    [
        (("unsupported certificate_type: 'x'",), "wrong_certificate_type"),
        (("fsm_ids mismatch: expected ['A', 'B']",), "wrong_fsm_ids"),
        (("minimized_hash_A mismatch",), "equivalence_hash_mismatch"),
        (("missing reachable states: ['q1']",), "incomplete_reachability_set"),
        (("acceptance.B mismatch: replay=False, declared=True",), "acceptance_mismatch"),
        (("trace must distinguish A and B (acceptance values equal)",), "acceptance_mismatch"),
        (("simulation failed: boom",), "replay_failure"),
        (("state_sequence does not match replay: expected ('q0',), got ('q1',)",), "replay_failure"),
        (("trace and state_sequence must be arrays",), "wrong_trace_format"),
        (("payload.acceptance.A must be boolean",), "malformed_certificate_payload"),
        (("trace does not reach target",), "other"),
        ((), "other"),
    ],
)
def test_classify_certificate_errors(errors: tuple[str, ...], expected: str) -> None:
    assert classify_certificate_errors(errors) == expected


def test_analyze_failure_taxonomy_counts_groups_and_samples(tmp_path: Path) -> None:
    scores_path, results_path = _write_taxonomy_fixture(tmp_path)
    payload = analyze_failure_taxonomy(scores_path, results_path, sample_limit=2)

    assert payload["n"] == 10
    assert payload["certificate_invalid_count"] == 9
    assert set(payload["overall"]["taxonomy"]) == set(TAXONOMY_CATEGORIES)

    overall = payload["overall"]["taxonomy"]
    assert overall["wrong_trace_format"]["count"] == 1
    assert overall["wrong_trace_format"]["percentage"] == pytest.approx(1 / 9)
    assert overall["wrong_trace_format"]["sample_item_ids"] == ["c2_wrong_trace_format"]
    assert overall["other"]["count"] == 1
    assert overall["other"]["sample_item_ids"] == ["f1_other"]

    groups = {group["family"]: group for group in payload["groups"]}
    assert set(groups) == {"C2", "F1"}
    assert groups["C2"]["n"] == 3
    assert groups["F1"]["n"] == 6
    assert groups["C2"]["failure_stage"] == "certificate_invalid"
    assert groups["F1"]["taxonomy"]["acceptance_mismatch"]["count"] == 1

    summary = payload["failure_stage_summary_by_family"]
    assert summary["C2"]["certificate_invalid"] == 3
    assert summary["C2"]["correct"] == 1
    assert summary["F1"]["certificate_invalid"] == 6


def test_format_failure_taxonomy_report_lists_nonzero_categories(tmp_path: Path) -> None:
    scores_path, results_path = _write_taxonomy_fixture(tmp_path)
    payload = analyze_failure_taxonomy(scores_path, results_path, sample_limit=1)
    report = format_failure_taxonomy_report(payload)

    assert "Failure taxonomy (n=10, certificate_invalid=9)" in report
    assert "wrong_trace_format:" in report
    assert "sample=['c2_wrong_trace_format']" in report


def test_discover_scored_run_pairs_and_batch_aggregate(tmp_path: Path) -> None:
    run_a = tmp_path / "capability_surface_models_f1_mixed" / "F1" / "level_1" / "model_a"
    run_b = tmp_path / "capability_surface_models_f1_mixed" / "F1" / "level_2" / "model_b"
    for run_dir in (run_a, run_b):
        run_dir.mkdir(parents=True)
        write_jsonl(
            run_dir / "scores.jsonl",
            [
                _certificate_invalid_record(
                    f"{run_dir.name}_replay",
                    family="F1",
                    certificate_errors=["trace replay failed: boom"],
                )
            ],
        )
        write_jsonl(run_dir / "results.jsonl", [{"item_id": "x", "family": "F1"}])

    root = tmp_path / "capability_surface_models_f1_mixed"
    pairs = discover_scored_run_pairs(root)
    assert len(pairs) == 2

    payload = analyze_failure_taxonomy_batch(root, sample_limit=3)
    assert payload["run_count"] == 2
    assert payload["aggregate"]["certificate_invalid_count"] == 2
    assert payload["aggregate"]["overall"]["taxonomy"]["replay_failure"]["count"] == 2
    assert len(payload["runs"]) == 2


def test_failure_taxonomy_cli_writes_json(tmp_path: Path) -> None:
    scores_path, results_path = _write_taxonomy_fixture(tmp_path)
    out_path = tmp_path / "taxonomy.json"
    assert (
        failure_taxonomy_main(
            [
                "--scores",
                str(scores_path),
                "--results",
                str(results_path),
                "--out",
                str(out_path),
                "--limit",
                "2",
            ]
        )
        == 0
    )
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["certificate_invalid_count"] == 9


def test_failure_taxonomy_batch_cli_writes_json(tmp_path: Path) -> None:
    run_dir = tmp_path / "root" / "F1" / "level_1" / "model_a"
    run_dir.mkdir(parents=True)
    write_jsonl(
        run_dir / "scores.jsonl",
        [
            _certificate_invalid_record(
                "item_replay",
                family="F1",
                certificate_errors=["simulation failed: boom"],
            )
        ],
    )
    write_jsonl(run_dir / "results.jsonl", [{"item_id": "item_replay", "family": "F1"}])

    out_path = tmp_path / "batch_taxonomy.json"
    assert (
        failure_taxonomy_batch_main(
            [
                "--root",
                str(tmp_path / "root"),
                "--out",
                str(out_path),
            ]
        )
        == 0
    )
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["run_count"] == 1
    assert payload["aggregate"]["overall"]["taxonomy"]["replay_failure"]["count"] == 1
