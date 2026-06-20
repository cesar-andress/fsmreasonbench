"""Tests for oracle ceiling reporting utilities."""

from __future__ import annotations

from pathlib import Path

import pytest

from fsmreasonbench.evaluator.oracle_ceiling_report import (
    ORACLE_CEILING_JSON_FIELDS,
    assert_oracle_ceiling_complete,
    build_oracle_ceiling_report,
    export_oracle_ceiling_report,
    validate_oracle_ceiling_row,
    write_oracle_ceiling_csv,
)
from fsmreasonbench.evaluator.io import load_json
from fsmreasonbench.generator.reachability import ReachabilityGeneratorConfig
from fsmreasonbench.evaluator.batch import generate_c2_batch
from fsmreasonbench.evaluator.jsonl import write_jsonl


def test_oracle_ceiling_report_schema_fields(tmp_path: Path) -> None:
    items = generate_c2_batch(3, seed=1, config=ReachabilityGeneratorConfig(state_count=4))
    items_path = tmp_path / "items.jsonl"
    write_jsonl(items_path, (item.to_full_dict() for item in items))
    payload = build_oracle_ceiling_report(
        tmp_path,
        batches=(
            {
                "source_name": "tmp/items.jsonl",
                "items_path": str(items_path.relative_to(tmp_path)),
            },
        ),
    )
    row = payload["rows"][0]
    validate_oracle_ceiling_row(row)
    for field in ORACLE_CEILING_JSON_FIELDS:
        assert field in row
    assert row["fully_correct_rate"] == 1.0


def test_oracle_ceiling_strict_detects_non_one_rows() -> None:
    with pytest.raises(ValueError, match="oracle ceiling check failed"):
        assert_oracle_ceiling_complete(
            [
                {
                    "source_name": "bad",
                    "fully_correct_rate": 0.5,
                    "certificate_valid_rate": 0.5,
                }
            ]
        )


def test_oracle_ceiling_export_writes_json_csv_md(tmp_path: Path) -> None:
    items = generate_c2_batch(2, seed=2, config=ReachabilityGeneratorConfig(state_count=4))
    items_path = tmp_path / "items.jsonl"
    write_jsonl(items_path, (item.to_full_dict() for item in items))
    out_json = tmp_path / "oracle.json"
    out_csv = tmp_path / "oracle.csv"
    out_md = tmp_path / "oracle.md"
    export_oracle_ceiling_report(
        tmp_path,
        out_json=out_json,
        out_csv=out_csv,
        out_md=out_md,
        batches=(
            {
                "source_name": "tmp/items.jsonl",
                "items_path": str(items_path.relative_to(tmp_path)),
            },
        ),
    )
    payload = load_json(out_json)
    assert payload["rows"][0]["fully_correct_rate"] == 1.0
    assert out_csv.read_text(encoding="utf-8").startswith("source_name,")
    assert "oracle/symbolic ceiling" in out_md.read_text(encoding="utf-8").lower()


def test_oracle_ceiling_csv_contains_required_fields(tmp_path: Path) -> None:
    rows = [
        {
            "source_name": "x/items.jsonl",
            "family": "C2",
            "difficulty_level": 1,
            "cohort_id": None,
            "n": 20,
            "extractability_rate": 1.0,
            "verdict_accuracy": 1.0,
            "certificate_valid_rate": 1.0,
            "fully_correct_rate": 1.0,
        }
    ]
    csv_path = tmp_path / "oracle.csv"
    write_oracle_ceiling_csv(csv_path, rows)
    header = csv_path.read_text(encoding="utf-8").splitlines()[0]
    for field in ORACLE_CEILING_JSON_FIELDS:
        assert field in header
