"""Tests for TMLR empirical package export."""

from __future__ import annotations

from pathlib import Path

from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.evaluator.tmlr_empirical_package import (
    PACKAGE_DIR,
    build_table1,
    build_table1_frontier_comparison,
    build_table2,
    export_tmlr_empirical_package,
    write_certificate_complexity_figures,
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


def test_table1_frontier_comparison_has_gpt_rates():
    rows = {r["certificate_type"]: r for r in build_table1_frontier_comparison(find_repo_root())}
    assert rows["equivalence_witness"]["Claude_R1_cert"] == 0.0
    assert rows["equivalence_witness"]["GPT_R1_cert"] == 0.0
    assert rows["distinguishing_trace"]["GPT_R1_cert"] == 0.143
    assert rows["trace_witness"]["Claude_R1_cert"] == 1.0
    assert rows["unreachability_witness"]["Claude_R1_cert"] == 0.931


def test_write_certificate_complexity_figures_both(tmp_path):
    repo = find_repo_root()
    out_dir = tmp_path / "pkg"
    written = write_certificate_complexity_figures(
        repo,
        out_dir,
        model="both",
        paper_figures_dir=None,
    )
    assert (out_dir / "figures" / "figure1_complexity_vs_success.pdf").exists()
    assert (out_dir / "figures" / "figure_certificate_complexity_frontier_comparison.pdf").exists()
    assert "figures/figure_certificate_complexity_frontier_comparison.pdf" in written


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
