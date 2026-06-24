"""Tests for local matrix F1 subtype-stratified analysis."""

from __future__ import annotations

import json
from pathlib import Path

from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.evaluator.f1_local_matrix_subtype_stratified_analysis import (
    analyze_f1_local_matrix_subtype_stratified,
    export_f1_local_matrix_subtype_stratified_analysis,
)


def test_local_matrix_subtype_analysis_discovers_twelve_f1_cells() -> None:
    repo_root = find_repo_root()
    payload = analyze_f1_local_matrix_subtype_stratified(repo_root)
    assert payload["cells_discovered"] == 12
    assert len(payload["models"]) == 4
    assert all(row["perfect_cohort_alignment"] for row in payload["item_id_alignment"])


def test_export_writes_requested_docs(tmp_path: Path) -> None:
    repo_root = find_repo_root()
    payload = export_f1_local_matrix_subtype_stratified_analysis(
        repo_root,
        markdown_path=tmp_path / "report.md",
        json_path=tmp_path / "report.json",
        csv_path=tmp_path / "tables.csv",
    )
    assert (tmp_path / "report.md").exists()
    assert (tmp_path / "report.json").exists()
    assert (tmp_path / "tables.csv").exists()
    assert "gap_decomposition" in payload["tables"]
    saved = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert saved["cells_discovered"] == 12
