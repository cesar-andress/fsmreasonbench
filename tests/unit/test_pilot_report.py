"""Pilot evaluation report generator tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from fsmreasonbench.cli.generate_pilot_report import main as generate_pilot_report_main
from fsmreasonbench.evaluator.jsonl import write_jsonl
from fsmreasonbench.evaluator.pilot_report import (
    build_pilot_report,
    render_pilot_report_markdown,
    write_pilot_report,
)


def _score_record(
    *,
    item_id: str,
    failure_stage: str,
    extractable: bool = True,
    verdict_correct: bool | None = True,
    certificate_valid: bool | None = True,
    fully_correct: bool = True,
    parse_errors: list[str] | None = None,
    certificate_errors: list[str] | None = None,
) -> dict[str, object]:
    return {
        "item_id": item_id,
        "family": "C2",
        "extractable": extractable,
        "verdict_correct": verdict_correct,
        "certificate_valid": certificate_valid,
        "fully_correct": fully_correct,
        "failure_stage": failure_stage,
        "parse_errors": parse_errors or [],
        "certificate_errors": certificate_errors or [],
    }


def _write_scores(path: Path) -> None:
    write_jsonl(
        path,
        [
            _score_record(
                item_id="item_ok",
                failure_stage="correct",
            ),
            _score_record(
                item_id="item_bad_verdict",
                failure_stage="verdict_wrong",
                verdict_correct=False,
                certificate_valid=True,
                fully_correct=False,
            ),
            _score_record(
                item_id="item_bad_cert_a",
                failure_stage="certificate_invalid",
                verdict_correct=True,
                certificate_valid=False,
                fully_correct=False,
                certificate_errors=["trace does not reach target"],
            ),
            _score_record(
                item_id="item_bad_cert_b",
                failure_stage="certificate_invalid",
                verdict_correct=True,
                certificate_valid=False,
                fully_correct=False,
                certificate_errors=[
                    "trace does not reach target",
                    "invalid transition",
                ],
            ),
            _score_record(
                item_id="item_unparsed",
                failure_stage="not_extractable",
                extractable=False,
                verdict_correct=None,
                certificate_valid=None,
                fully_correct=False,
                parse_errors=["missing verdict field"],
            ),
        ],
    )


def test_build_pilot_report_metrics_and_samples(tmp_path: Path) -> None:
    scores_path = tmp_path / "oracle_scores.jsonl"
    _write_scores(scores_path)

    summaries = build_pilot_report([scores_path], sample_limit=2, top_reason_limit=3)
    assert len(summaries) == 1
    summary = summaries[0]

    assert summary.label == "oracle_scores"
    assert summary.n == 5
    assert summary.extractability_rate == 0.8
    assert summary.fully_correct_rate == 0.2
    assert summary.failure_stage_counts["correct"] == 1
    assert summary.failure_stage_counts["certificate_invalid"] == 2
    assert summary.top_certificate_failure_reasons[0] == ("trace does not reach target", 2)
    assert "verdict_wrong" in summary.sample_failures_by_stage
    assert summary.sample_failures_by_stage["certificate_invalid"][0]["item_id"] == "item_bad_cert_a"


def test_render_pilot_report_markdown_contains_sections(tmp_path: Path) -> None:
    scores_path = tmp_path / "model_scores.jsonl"
    _write_scores(scores_path)
    markdown = render_pilot_report_markdown(build_pilot_report([scores_path]))

    assert "# FSMReasonBench Pilot Evaluation Report" in markdown
    assert "## model_scores" in markdown
    assert "| extractability_rate |" in markdown
    assert "### Top certificate failure reasons" in markdown
    assert "#### certificate_invalid" in markdown
    assert "`item_bad_verdict`" in markdown


def test_write_pilot_report_creates_markdown_file(tmp_path: Path) -> None:
    scores_path = tmp_path / "scores.jsonl"
    _write_scores(scores_path)
    out_path = tmp_path / "pilot_v0" / "report.md"

    destination = write_pilot_report([scores_path], out_path)
    assert destination == out_path
    assert out_path.exists()
    assert "Failure stage counts" in out_path.read_text(encoding="utf-8")


def test_cli_writes_default_style_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    scores_path = tmp_path / "scores.jsonl"
    out_path = tmp_path / "pilot_v0" / "report.md"
    _write_scores(scores_path)

    assert (
        generate_pilot_report_main(
            [
                "--scores",
                str(scores_path),
                "--out",
                str(out_path),
                "--sample-limit",
                "2",
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    assert "Wrote pilot report" in captured.out
    assert out_path.exists()
