"""Extractability denominator audit tests."""

from __future__ import annotations

import json
from pathlib import Path

from fsmreasonbench.evaluator.extractability_audit import (
    audit_cell_scores,
    audit_matrix_scores,
    render_extractability_audit_markdown,
)
from fsmreasonbench.evaluator.models import FailureStage, ScoringRecord


def _write_cell(
    run_dir: Path,
    records: list[ScoringRecord],
    *,
    family: str = "C2",
    temp: str = "0",
    track: str = "R0",
) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    rows = [record.to_dict() for record in records]
    (run_dir / "scores.jsonl").write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_verdict_and_certificate_share_extractable_denominator(tmp_path: Path) -> None:
    root = tmp_path / "matrix"
    cell = root / "mock" / "C2" / "temp_0" / "R1"
    _write_cell(
        cell,
        [
            ScoringRecord(
                item_id="a",
                family="C2",
                extractable=True,
                verdict_correct=True,
                certificate_valid=True,
                fully_correct=True,
                failure_stage=FailureStage.CORRECT,
            ),
            ScoringRecord(
                item_id="b",
                family="C2",
                extractable=True,
                verdict_correct=False,
                certificate_valid=True,
                fully_correct=False,
                failure_stage=FailureStage.VERDICT_WRONG,
            ),
            ScoringRecord(
                item_id="c",
                family="C2",
                extractable=False,
                verdict_correct=None,
                certificate_valid=None,
                fully_correct=False,
                failure_stage=FailureStage.NOT_EXTRACTABLE,
            ),
        ],
    )
    audit = audit_cell_scores(cell / "scores.jsonl", root=root)
    assert audit is not None
    assert audit.total_items == 3
    assert audit.extractable_items == 2
    assert audit.non_extractable_items == 1
    assert audit.verdict_denominator == 2
    assert audit.certificate_denominator == 2
    assert audit.verdict_accuracy == 0.5
    assert audit.certificate_valid_rate == 1.0
    assert audit.denominators_match is True


def test_render_extractability_audit_markdown(tmp_path: Path) -> None:
    root = tmp_path / "matrix"
    cell = root / "mock" / "F1" / "temp_0.2" / "R2"
    _write_cell(cell, [], family="F1", temp="0.2", track="R2")
    audits = audit_matrix_scores(root)
    report = render_extractability_audit_markdown(audits, root=root)
    assert "share the same denominator" in report
    assert "F1" in report
