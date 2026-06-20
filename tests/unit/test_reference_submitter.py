"""Tests for the reference submitter baseline."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from fsmreasonbench.baselines.reference_submitter import (
    build_reference_submission,
    run_reference_submitter,
)
from fsmreasonbench.evaluator.io import load_item
from fsmreasonbench.evaluator.jsonl import load_items_jsonl
from fsmreasonbench.evaluator.models import FailureStage
from fsmreasonbench.evaluator.parser import parse_submission
from fsmreasonbench.evaluator.reference_submitter_report import (
    REFERENCE_SUBMITTER_JSON_FIELDS,
    assert_reference_submitter_complete,
    build_reference_submitter_report,
    evaluate_reference_submitter_on_items,
    export_reference_submitter_report,
    validate_reference_submitter_row,
)
from fsmreasonbench.evaluator.scorer import score_item
from fsmreasonbench.items.assembly import BenchmarkItem

ROOT = Path(__file__).resolve().parents[2]
C2_COHORT = ROOT / "cohorts/v0.1-exploratory/c2-reachability-level3/items.jsonl"
F1_COHORT = ROOT / "cohorts/v0.1-exploratory/f1-mixed-level3/items.jsonl"
C2_EXAMPLE = ROOT / "examples/item_C2_reachability_seed42.json"
F1_EXAMPLE = ROOT / "examples/item_F1_separation_seed42.json"


class _CertificateGuard(dict):
    """Raise if gold certificate fields are accessed during submission construction."""

    def __getitem__(self, key: str):
        if key == "certificate":
            raise AssertionError("reference_submitter must not read answer_key.certificate")
        return super().__getitem__(key)

    def get(self, key: str, default=None):
        if key == "certificate":
            raise AssertionError("reference_submitter must not read answer_key.certificate")
        return super().get(key, default)


def _with_certificate_guard(item: BenchmarkItem) -> BenchmarkItem:
    guarded_key = _CertificateGuard(item.answer_key)
    return replace(item, answer_key=guarded_key)


@pytest.mark.parametrize(
    ("example_path", "family"),
    [
        (C2_EXAMPLE, "C2"),
        (F1_EXAMPLE, "F1"),
    ],
)
def test_reference_submitter_never_reads_answer_key_certificate(
    example_path: Path,
    family: str,
) -> None:
    item = _with_certificate_guard(load_item(example_path))
    submission = build_reference_submission(item)
    parsed = parse_submission(run_reference_submitter(item), family)
    assert parsed.extractable is True
    assert parsed.submission is not None
    assert submission["item_id"] == item.item_id


def test_reference_submitter_uses_evaluator_facing_submission_objects() -> None:
    item = load_item(C2_EXAMPLE)
    raw = run_reference_submitter(item)
    parsed = parse_submission(raw, "C2")
    assert parsed.extractable is True
    assert parsed.submission is not None
    record = score_item(item, raw)
    assert record.extractable is True
    assert record.fully_correct is True
    assert record.failure_stage == FailureStage.CORRECT


@pytest.mark.parametrize("cohort_path", [C2_COHORT, F1_COHORT])
def test_reference_submitter_reaches_full_correctness_on_frozen_cohorts(
    cohort_path: Path,
) -> None:
    items = load_items_jsonl(cohort_path)
    records = evaluate_reference_submitter_on_items(items)
    assert len(records) == len(items)
    assert all(record.fully_correct for record in records)
    assert all(record.certificate_valid is True for record in records)


def test_reference_submitter_report_on_frozen_cohorts() -> None:
    payload = build_reference_submitter_report(ROOT)
    assert len(payload["rows"]) == 4
    for row in payload["rows"]:
        validate_reference_submitter_row(row)
        for field in REFERENCE_SUBMITTER_JSON_FIELDS:
            assert field in row
    assert_reference_submitter_complete(payload["rows"])


def test_reference_submitter_export_writes_json_csv_md(tmp_path: Path) -> None:
    export_reference_submitter_report(
        ROOT,
        out_json=tmp_path / "summary.json",
        out_csv=tmp_path / "summary.csv",
        out_md=tmp_path / "report.md",
    )
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "summary.csv").read_text(encoding="utf-8").startswith("cohort_id,")
    assert "reference submitter" in (tmp_path / "report.md").read_text(encoding="utf-8").lower()


def test_reference_submitter_strict_detects_incomplete_rows() -> None:
    with pytest.raises(ValueError, match="reference submitter completeness check failed"):
        assert_reference_submitter_complete(
            [
                {
                    "cohort_id": "bad",
                    "system": "reference_submitter",
                    "fully_correct_rate": 0.5,
                    "certificate_valid_rate": 0.5,
                }
            ]
        )
