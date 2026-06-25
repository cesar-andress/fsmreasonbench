"""Offline export tests for TOSEM manuscript tables."""

from __future__ import annotations

import json
from pathlib import Path

from fsmreasonbench.evaluator.tosem_empirical_package import export_tosem_empirical_package


def test_export_tosem_empirical_package_writes_gpt_tables(tmp_path, monkeypatch):
    repo_root = Path(__file__).resolve().parents[2]
    paper_tables = tmp_path / "paper_tables"
    manifest = export_tosem_empirical_package(
        repo_root,
        paper_tables_dir=paper_tables,
        paper_figures_dir=tmp_path / "figures",
    )

    assert (paper_tables / "gpt_tools_n100_summary.tex").is_file()
    assert (paper_tables / "f1_gpt_ablations.tex").is_file()
    assert (paper_tables / "frontier_tools_comparison_n100.tex").is_file()
    assert (paper_tables / "knowing_showing_gap_n100.tex").is_file()
    assert (paper_tables / "results_paired_mcnemar.tex").is_file()
    assert (paper_tables / "local_matrix_n100_summary.tex").is_file()
    assert "[0." in (paper_tables / "local_matrix_n100_summary.tex").read_text(encoding="utf-8")

    gpt_json = json.loads(
        (repo_root / "docs/f1_gpt_ablation_stratified_analysis.json").read_text(encoding="utf-8")
    )
    r2c = next(row for row in gpt_json["rows"] if row["condition"] == "R2C")
    assert r2c["overall_full"] == 1.0

    uncertainty = json.loads(
        (repo_root / "docs/frontier_gpt_tools_n100_v1_uncertainty.json").read_text(encoding="utf-8")
    )
    assert uncertainty["paired_track_comparisons"]

    assert manifest["gpt_frontier_export"]["cells_exported"] == 4

    gap_figure = manifest["paper_figures"].get("figure_verdict_witness_gap_comparison.pdf")
    assert gap_figure is not None
    assert Path(gap_figure).is_file()
