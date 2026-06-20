"""Tests for the competent submitter baseline and ceiling report."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from fsmreasonbench.baselines.competent_submitter import (
    build_competent_submission,
    run_competent_submitter,
    serialize_competent_submission,
)
from fsmreasonbench.evaluator.competent_ceiling_report import (
    COMPETENT_CEILING_JSON_FIELDS,
    assert_competent_ceiling_complete,
    build_competent_ceiling_report,
    evaluate_competent_submitter_on_items,
    export_competent_ceiling_report,
    validate_competent_ceiling_row,
)
from fsmreasonbench.evaluator.io import load_item
from fsmreasonbench.evaluator.jsonl import load_items_jsonl
from fsmreasonbench.evaluator.models import FailureStage
from fsmreasonbench.evaluator.parser import parse_submission
from fsmreasonbench.evaluator.scorer import score_item
from fsmreasonbench.items.assembly import BenchmarkItem

ROOT = Path(__file__).resolve().parents[2]
C2_COHORT = ROOT / "cohorts/v0.1-exploratory/c2-reachability-level3/items.jsonl"
F1_COHORT = ROOT / "cohorts/v0.1-exploratory/f1-mixed-level3/items.jsonl"
C2_EXAMPLE = ROOT / "examples/item_C2_reachability_seed42.json"
F1_EXAMPLE = ROOT / "examples/item_F1_separation_seed42.json"
COMPETENT_SOURCE = (
    ROOT / "src/fsmreasonbench/baselines/competent_submitter.py"
)


class _CertificateGuard(dict):
    """Raise if gold certificate fields are accessed during submission construction."""

    def __getitem__(self, key: str):
        if key == "certificate":
            raise AssertionError("competent_submitter must not read answer_key.certificate")
        return super().__getitem__(key)

    def get(self, key: str, default=None):
        if key == "certificate":
            raise AssertionError("competent_submitter must not read answer_key.certificate")
        return super().get(key, default)


def _with_certificate_guard(item: BenchmarkItem) -> BenchmarkItem:
    guarded_key = _CertificateGuard(item.answer_key)
    return replace(item, answer_key=guarded_key)


def test_competent_submitter_does_not_import_oracle_modules() -> None:
    source = COMPETENT_SOURCE.read_text(encoding="utf-8")
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        assert "from fsmreasonbench.oracle" not in stripped
        assert "import fsmreasonbench.oracle" not in stripped


@pytest.mark.parametrize(
    ("example_path", "family"),
    [
        (C2_EXAMPLE, "C2"),
        (F1_EXAMPLE, "F1"),
    ],
)
def test_competent_submitter_never_reads_answer_key_certificate(
    example_path: Path,
    family: str,
) -> None:
    item = _with_certificate_guard(load_item(example_path))
    run = build_competent_submission(item)
    parsed = parse_submission(serialize_competent_submission(run), family)
    assert parsed.extractable is True
    assert parsed.submission is not None
    assert run.submission["item_id"] == item.item_id
    assert run.reasoning_log


def test_competent_submitter_uses_evaluator_facing_submission_objects() -> None:
    item = load_item(C2_EXAMPLE)
    run = run_competent_submitter(item)
    raw = serialize_competent_submission(run)
    parsed = parse_submission(raw, "C2")
    assert parsed.extractable is True
    assert parsed.submission is not None
    record = score_item(item, raw)
    assert record.extractable is True
    assert record.fully_correct is True
    assert record.failure_stage == FailureStage.CORRECT


@pytest.mark.parametrize("cohort_path", [C2_COHORT, F1_COHORT])
def test_competent_submitter_reaches_full_correctness_on_frozen_cohorts(
    cohort_path: Path,
) -> None:
    items = load_items_jsonl(cohort_path)
    records, logs = evaluate_competent_submitter_on_items(items)
    assert len(records) == len(items)
    assert len(logs) == len(items)
    assert all(record.fully_correct for record in records)
    assert all(record.certificate_valid is True for record in records)
    assert all(len(reasoning_log) >= 2 for _, reasoning_log in logs)


def test_competent_ceiling_report_schema_on_frozen_cohorts() -> None:
    payload = build_competent_ceiling_report(ROOT)
    assert len(payload["rows"]) == 6
    for row in payload["rows"]:
        validate_competent_ceiling_row(row)
        for field in COMPETENT_CEILING_JSON_FIELDS:
            assert field in row
    assert_competent_ceiling_complete(payload["rows"])


def test_competent_ceiling_export_writes_json_csv_md(tmp_path: Path) -> None:
    export_competent_ceiling_report(
        ROOT,
        out_json=tmp_path / "summary.json",
        out_csv=tmp_path / "summary.csv",
        out_md=tmp_path / "report.md",
    )
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "summary.csv").read_text(encoding="utf-8").startswith("cohort_id,")
    assert "competent submitter" in (tmp_path / "report.md").read_text(encoding="utf-8").lower()


def test_competent_ceiling_strict_detects_incomplete_rows() -> None:
    with pytest.raises(ValueError, match="competent ceiling completeness check failed"):
        assert_competent_ceiling_complete(
            [
                {
                    "cohort_id": "bad",
                    "system": "competent_submitter",
                    "extractability_rate": 1.0,
                    "verdict_accuracy": 1.0,
                    "certificate_valid_rate": 1.0,
                    "fully_correct_rate": 0.5,
                }
            ]
        )
