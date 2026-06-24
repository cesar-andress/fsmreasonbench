"""Tests for F1 Claude ablation stratified analysis."""

from __future__ import annotations

import json
from pathlib import Path

from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.evaluator.f1_claude_ablation_stratified_analysis import (
    analyze_f1_claude_ablation_stratified,
    exact_mcnemar_p_value,
    export_f1_claude_ablation_stratified_analysis,
)


def test_exact_mcnemar_symmetric() -> None:
    assert exact_mcnemar_p_value(0, 0) is None
    p = exact_mcnemar_p_value(3, 7)
    assert p is not None
    assert 0.0 < p <= 1.0


def test_stratified_analysis_runs_on_frozen_claude_runs() -> None:
    repo_root = find_repo_root()
    payload = analyze_f1_claude_ablation_stratified(repo_root)
    assert payload["item_id_alignment"]["reference_n"] == 100
    assert len(payload["tables"]["overall"]) == 6
    assert len(payload["item_level_records"]) == 100
    r1 = next(row for row in payload["tables"]["overall"] if row["Condition"] == "R1")
    assert r1["n"] == 100
    assert r1["cert"] == 0.46


def test_export_writes_requested_docs(tmp_path: Path) -> None:
    repo_root = find_repo_root()
    md = tmp_path / "report.md"
    js = tmp_path / "report.json"
    csv = tmp_path / "tables.csv"
    export_f1_claude_ablation_stratified_analysis(
        repo_root,
        markdown_path=md,
        json_path=js,
        csv_path=csv,
    )
    assert md.exists()
    assert js.exists()
    assert csv.exists()
    payload = json.loads(js.read_text(encoding="utf-8"))
    assert "tables" in payload
    assert "paired_comparisons" in payload["tables"]
