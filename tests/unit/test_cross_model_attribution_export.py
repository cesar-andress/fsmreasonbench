"""Unit tests for cross-model attribution export (Experiment C)."""

from __future__ import annotations

from fsmreasonbench.evaluator.cross_model_attribution_export import (
    ATTRIBUTION_CONDITIONS,
    build_cross_model_attribution_report,
    render_cross_model_attribution_latex,
)


def test_cross_model_report_marks_pending_without_gpt_runs(tmp_path) -> None:
    report = build_cross_model_attribution_report(tmp_path)
    gpt = report["gpt"]["conditions"]
    for condition in ATTRIBUTION_CONDITIONS:
        assert gpt[condition]["status"] == "pending"
    paired = {row["condition"]: row for row in report["paired_comparisons"]}
    assert paired["R2A"]["status"] == "pending"


def test_cross_model_latex_renders_pending_cells(tmp_path) -> None:
    report = build_cross_model_attribution_report(tmp_path)
    latex = render_cross_model_attribution_latex(report)
    assert "extension-cross-model-attribution" in latex
    assert "R2A" in latex
    assert "pending" in latex
