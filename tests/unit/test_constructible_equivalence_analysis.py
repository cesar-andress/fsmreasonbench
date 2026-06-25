"""Tests for Experiment A1 constructible-equivalence statistical export."""

from __future__ import annotations

from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.evaluator.constructible_equivalence_analysis import (
    build_a1_paired_comparisons,
    build_constructible_equivalence_analysis,
    render_constructible_equivalence_statistics_latex,
)


def test_a1_paired_comparisons_cover_required_groups() -> None:
    repo = find_repo_root()
    report = build_constructible_equivalence_analysis(repo)
    comparisons = report["paired_comparisons"]
    groups = {row["group"] for row in comparisons}
    assert groups == {"A_contract_r1", "B_contract_r2c", "C_cross_model"}
    assert len([row for row in comparisons if row["group"] == "A_contract_r1"]) == 2
    assert len([row for row in comparisons if row["group"] == "B_contract_r2c"]) == 2
    assert len([row for row in comparisons if row["group"] == "C_cross_model"]) == 4


def test_a1_claude_hash_r1_vs_bisim_r1_rates_and_mcnemar() -> None:
    repo = find_repo_root()
    comparisons = build_a1_paired_comparisons(
        repo,
        __import__(
            "fsmreasonbench.evaluator.f1_claude_ablation_stratified_analysis",
            fromlist=["load_item_metadata"],
        ).load_item_metadata(repo / "cohorts/v0.1-expanded-n100/f1-mixed-level3/items.jsonl"),
    )
    row = next(item for item in comparisons if item["comparison_id"] == "claude_hash_r1_vs_bisim_r1")
    assert row["paired_items"] == 51
    assert row["agreement_table"]["second_only_valid"] == 18
    assert row["cert_diff_first_minus_second"]["point_diff"] == -0.3529
    assert row["mcnemar_p_value"] is not None
    assert row["mcnemar_p_value"] < 0.05


def test_statistics_latex_contains_bootstrap_and_mcnemar() -> None:
    repo = find_repo_root()
    report = build_constructible_equivalence_analysis(repo)
    latex = render_constructible_equivalence_statistics_latex(report)
    assert "tab:extension-constructible-equivalence-stats" in latex
    assert "0.353 [0.235, 0.490]" in latex
    assert "hash R1 vs bisim R1" in latex
    assert "$\\ll 0.05$" in latex
