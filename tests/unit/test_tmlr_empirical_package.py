"""Tests for TMLR empirical package export."""

from __future__ import annotations

from pathlib import Path

from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.evaluator.tmlr_empirical_package import (
    PACKAGE_DIR,
    build_table1,
    build_table2,
    export_tmlr_empirical_package,
)


def test_table1_equivalence_witness_is_outlier():
    rows = {r["certificate_type"]: r for r in build_table1(find_repo_root())}
    assert rows["equivalence_witness"]["Claude_R1_cert"] == 0.0
    assert rows["trace_witness"]["Claude_R1_cert"] >= 0.9
    assert rows["unreachability_witness"]["Claude_R1_cert"] >= 0.9
    assert rows["distinguishing_trace"]["Claude_R1_cert"] > 0.9
    assert (
        rows["equivalence_witness"]["complexity_score"]
        > rows["distinguishing_trace"]["complexity_score"]
    )


def test_table2_eq_witness_zero_until_r2c():
    rows = {r["condition"]: r for r in build_table2(find_repo_root())}
    assert rows["R1"]["equivalence_witness_cert"] == 0.0
    assert rows["R2A verify-only"]["equivalence_witness_cert"] == 0.0
    assert rows["R2C generator-assisted"]["equivalence_witness_cert"] >= 0.98


def test_export_creates_package_artifacts(tmp_path):
    repo = find_repo_root()
    manifest = export_tmlr_empirical_package(repo)
    out = repo / PACKAGE_DIR
    assert (out / "README.md").exists()
    assert (out / "narrative_memo.md").exists()
    assert (out / "figures" / "figure1_complexity_vs_success.png").exists()
    assert (out / "tables" / "table1_certificate_complexity.tex").exists()
    assert manifest["package_version"] == "v1"
