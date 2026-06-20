"""Tests for bootstrap rate CI reporting utilities."""

from __future__ import annotations

from pathlib import Path

import pytest

from fsmreasonbench.evaluator.models import FailureStage, ScoringRecord
from fsmreasonbench.evaluator.rate_ci_report import (
    RATE_CI_JSON_FIELDS,
    bootstrap_rate_cis,
    build_rate_ci_row,
    export_rate_ci_report,
    summarize_rates_with_bootstrap,
    validate_rate_ci_row,
    write_rate_ci_csv,
)


def _record(
    *,
    extractable: bool = True,
    verdict_correct: bool | None = True,
    certificate_valid: bool | None = False,
    fully_correct: bool = False,
    failure_stage: FailureStage = FailureStage.CERTIFICATE_INVALID,
) -> ScoringRecord:
    return ScoringRecord(
        item_id="item",
        family="F1",
        extractable=extractable,
        verdict_correct=verdict_correct,
        certificate_valid=certificate_valid,
        fully_correct=fully_correct,
        failure_stage=failure_stage,
    )


def test_bootstrap_rate_cis_are_deterministic_with_fixed_seed() -> None:
    records = [
        _record(certificate_valid=True, fully_correct=True, failure_stage=FailureStage.CORRECT),
        _record(),
        _record(
            verdict_correct=False,
            failure_stage=FailureStage.VERDICT_WRONG,
        ),
        _record(certificate_valid=True, fully_correct=True, failure_stage=FailureStage.CORRECT),
    ]
    first = bootstrap_rate_cis(records, n_resamples=1000, seed=4242)
    second = bootstrap_rate_cis(records, n_resamples=1000, seed=4242)
    assert first == second


def test_bootstrap_rate_cis_bracket_point_estimates() -> None:
    records = [
        _record(certificate_valid=True, fully_correct=True, failure_stage=FailureStage.CORRECT),
        _record(),
        _record(
            verdict_correct=False,
            failure_stage=FailureStage.VERDICT_WRONG,
        ),
    ]
    summary = summarize_rates_with_bootstrap(records, n_resamples=500, seed=4242)
    assert (
        summary["verdict_accuracy_ci_low"]
        <= summary["verdict_accuracy"]
        <= summary["verdict_accuracy_ci_high"]
    )
    assert (
        summary["certificate_valid_rate_ci_low"]
        <= summary["certificate_valid_rate"]
        <= summary["certificate_valid_rate_ci_high"]
    )
    assert (
        summary["fully_correct_rate_ci_low"]
        <= summary["fully_correct_rate"]
        <= summary["fully_correct_rate_ci_high"]
    )


def test_rate_ci_row_schema_and_csv_fields(tmp_path: Path) -> None:
    scores_path = tmp_path / "scores.jsonl"
    scores_path.write_text(
        "\n".join(
            [
                '{"item_id":"a","family":"F1","extractable":true,'
                '"verdict_correct":true,"certificate_valid":true,'
                '"fully_correct":true,"failure_stage":"correct","parse_errors":[],'
                '"certificate_errors":[]}',
                '{"item_id":"b","family":"F1","extractable":true,'
                '"verdict_correct":true,"certificate_valid":false,'
                '"fully_correct":false,"failure_stage":"certificate_invalid",'
                '"parse_errors":[],"certificate_errors":["x"]}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    row = build_rate_ci_row(
        "capability_surface_models/F1/min_distinguishing_trace_length_1/qwen2.5-coder_7b/scores.jsonl",
        scores_path,
        n_resamples=200,
        seed=4242,
    )
    validate_rate_ci_row(row)
    for field in RATE_CI_JSON_FIELDS:
        assert field in row
    assert row["model"] == "qwen2.5-coder:7b"
    assert row["difficulty_level"] == 1

    csv_path = tmp_path / "rate_ci.csv"
    write_rate_ci_csv(csv_path, [row])
    header = csv_path.read_text(encoding="utf-8").splitlines()[0]
    for field in RATE_CI_JSON_FIELDS:
        assert field in header


def test_rate_ci_export_from_pilot_tree(tmp_path: Path) -> None:
    pilot_root = tmp_path / "runs" / "pilot_v1"
    scores_path = pilot_root / "gemma2_9b" / "C2" / "scores.jsonl"
    scores_path.parent.mkdir(parents=True)
    scores_path.write_text(
        '{"item_id":"a","family":"C2","extractable":true,'
        '"verdict_correct":true,"certificate_valid":false,'
        '"fully_correct":false,"failure_stage":"certificate_invalid",'
        '"parse_errors":[],"certificate_errors":["x"]}\n',
        encoding="utf-8",
    )
    out_json = tmp_path / "rate_ci.json"
    export_rate_ci_report(
        [pilot_root],
        out_json=out_json,
        out_csv=tmp_path / "rate_ci.csv",
        out_md=tmp_path / "rate_ci.md",
        n_resamples=100,
        seed=4242,
    )
    payload = out_json.read_text(encoding="utf-8")
    assert "verdict_accuracy_ci_low" in payload
    assert payload.count("gemma2:9b") >= 1


def test_bootstrap_rate_cis_rejects_invalid_resample_count() -> None:
    with pytest.raises(ValueError, match="n_resamples"):
        bootstrap_rate_cis([_record()], n_resamples=0, seed=4242)
