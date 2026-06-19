"""Failure inspection CLI and core logic tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fsmreasonbench.cli.inspect_failures import main as inspect_failures_main
from fsmreasonbench.evaluator.inspect_failures import (
    format_inspection_report,
    inspect_failures,
)
from fsmreasonbench.evaluator.jsonl import write_jsonl


def _write_fixture(tmp_path: Path) -> tuple[Path, Path]:
    scores_path = tmp_path / "scores.jsonl"
    results_path = tmp_path / "results.jsonl"

    write_jsonl(
        scores_path,
        [
            {
                "item_id": "item_not_extractable",
                "family": "C2",
                "extractable": False,
                "verdict_correct": None,
                "certificate_valid": None,
                "fully_correct": False,
                "failure_stage": "not_extractable",
                "parse_errors": ["missing verdict field"],
                "certificate_errors": [],
            },
            {
                "item_id": "item_verdict_wrong",
                "family": "C2",
                "extractable": True,
                "verdict_correct": False,
                "certificate_valid": True,
                "fully_correct": False,
                "failure_stage": "verdict_wrong",
                "parse_errors": [],
                "certificate_errors": [],
            },
            {
                "item_id": "item_certificate_invalid",
                "family": "C2",
                "extractable": True,
                "verdict_correct": True,
                "certificate_valid": False,
                "fully_correct": False,
                "failure_stage": "certificate_invalid",
                "parse_errors": [],
                "certificate_errors": ["trace does not reach target"],
            },
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
        [
            {
                "item_id": "item_not_extractable",
                "family": "C2",
                "raw_response_text": "Here is my answer without JSON.",
                "raw_response": "Here is my answer without JSON.",
            },
            {
                "item_id": "item_verdict_wrong",
                "family": "C2",
                "raw_response_text": '{"item_id":"item_verdict_wrong","verdict":false,"certificate":{"certificate_type":"trace_witness","payload":{}}}',
                "raw_response": {
                    "item_id": "item_verdict_wrong",
                    "verdict": False,
                    "certificate": {
                        "certificate_type": "trace_witness",
                        "payload": {},
                    },
                },
            },
            {
                "item_id": "item_certificate_invalid",
                "family": "C2",
                "raw_response_text": '{"item_id":"item_certificate_invalid","verdict":true,"certificate":{"certificate_type":"trace_witness","payload":{}}}',
                "raw_response": {
                    "item_id": "item_certificate_invalid",
                    "verdict": True,
                    "certificate": {
                        "certificate_type": "trace_witness",
                        "payload": {},
                    },
                },
            },
            {
                "item_id": "item_correct",
                "family": "C2",
                "raw_response_text": '{"item_id":"item_correct","verdict":true,"certificate":{"certificate_type":"trace_witness","payload":{}}}',
                "raw_response": {
                    "item_id": "item_correct",
                    "verdict": True,
                    "certificate": {
                        "certificate_type": "trace_witness",
                        "payload": {},
                    },
                },
            },
        ],
    )
    return scores_path, results_path


def test_inspect_failures_counts_rates_and_samples(tmp_path: Path) -> None:
    scores_path, results_path = _write_fixture(tmp_path)
    payload = inspect_failures(scores_path, results_path, limit=2)

    assert payload["n"] == 4
    assert payload["extractability_rate"] == 0.75
    assert payload["verdict_accuracy"] == pytest.approx(2 / 3)
    assert payload["certificate_valid_rate"] == pytest.approx(2 / 3)
    assert payload["fully_correct_rate"] == 0.25
    assert payload["failure_stage_counts"] == {
        "not_extractable": 1,
        "verdict_wrong": 1,
        "certificate_invalid": 1,
        "correct": 1,
    }
    assert payload["sample_item_ids_by_stage"]["verdict_wrong"] == ["item_verdict_wrong"]
    assert "correct" not in payload["samples_by_stage"]
    assert payload["samples_by_stage"]["not_extractable"][0]["family"] == "C2"
    assert payload["samples_by_stage"]["not_extractable"][0]["parsed_submission"] is None
    assert payload["samples_by_stage"]["verdict_wrong"][0]["verdict_correct"] is False
    assert payload["samples_by_stage"]["certificate_invalid"][0]["certificate_errors"] == [
        "trace does not reach target"
    ]
    assert "Here is my answer without JSON." in payload["samples_by_stage"]["not_extractable"][0][
        "raw_response_excerpt"
    ]


def test_format_inspection_report_includes_rates_and_stage_sections(tmp_path: Path) -> None:
    scores_path, results_path = _write_fixture(tmp_path)
    payload = inspect_failures(scores_path, results_path, limit=1)
    report = format_inspection_report(payload)

    assert "extractability_rate:" in report
    assert "verdict_accuracy:" in report
    assert "sample item_ids by failure_stage:" in report
    assert "--- not_extractable" in report
    assert "--- verdict_wrong" in report
    assert "--- certificate_invalid" in report
    assert "[item_id=item_verdict_wrong]" in report
    assert "family: C2" in report


def test_cli_json_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    scores_path, results_path = _write_fixture(tmp_path)
    assert (
        inspect_failures_main(
            [
                "--scores",
                str(scores_path),
                "--results",
                str(results_path),
                "--limit",
                "1",
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["n"] == 4
    assert "extractability_rate" in payload
    assert "sample_item_ids_by_stage" in payload
    assert "samples_by_stage" in payload


def test_cli_human_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    scores_path, results_path = _write_fixture(tmp_path)
    assert (
        inspect_failures_main(
            [
                "--scores",
                str(scores_path),
                "--results",
                str(results_path),
                "--limit",
                "1",
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert "Failure inspection (n=4)" in output
    assert "certificate_valid_rate:" in output
    assert "certificate_errors" in output
