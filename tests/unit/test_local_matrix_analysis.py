"""Tests for local matrix follow-up analysis."""

from __future__ import annotations

from fsmreasonbench.evaluator.local_matrix_analysis import (
    classify_cell_safety,
    compute_delegation_table,
    cells_from_inventory,
    render_local_matrix_analysis_markdown,
)


def test_classify_cell_safety_thresholds() -> None:
    assert classify_cell_safety(status="completed", n=100, extractable=80, expected_n=100) == "safe"
    assert classify_cell_safety(status="completed", n=100, extractable=60, expected_n=100) == "marginal"
    assert classify_cell_safety(status="completed", n=100, extractable=40, expected_n=100) == "unsafe"
    assert classify_cell_safety(status="partial", n=50, extractable=40, expected_n=100) == "partial"


def test_compute_delegation_table() -> None:
    inventory = [
        {
            "model": "qwen2.5-coder:7b",
            "family": "F1",
            "track": "R0",
            "temperature": 0.2,
            "n": 20,
            "extractability_rate": 1.0,
            "verdict_accuracy": 0.5,
            "certificate_valid_rate": 0.1,
            "fully_correct_rate": 0.0,
            "failure_stage_counts": {"not_extractable": 0, "correct": 0, "verdict_wrong": 10, "certificate_invalid": 10},
            "extended_status": "completed",
        },
        {
            "model": "qwen2.5-coder:7b",
            "family": "F1",
            "track": "R2",
            "temperature": 0.2,
            "n": 20,
            "extractability_rate": 0.75,
            "verdict_accuracy": 1.0,
            "certificate_valid_rate": 0.5,
            "fully_correct_rate": 0.4,
            "failure_stage_counts": {"not_extractable": 5, "correct": 8, "verdict_wrong": 0, "certificate_invalid": 7},
            "extended_status": "completed",
        },
    ]
    cells = cells_from_inventory(inventory, temperature=0.2, expected_n=20)
    rows = compute_delegation_table(cells, temperature=0.2)
    assert len(rows) == 1
    row = rows[0]
    assert row["status"] == "ok"
    assert row["delta_fully_correct_rate"] == 0.4
    assert row["delta_certificate_valid_rate"] == 0.4
    assert row["delta_verdict_accuracy"] == 0.5


def test_render_analysis_includes_disclaimer() -> None:
    inventory = [
        {
            "model": "qwen2.5-coder:7b",
            "family": "C2",
            "track": "R0",
            "temperature": 0.2,
            "n": 20,
            "extractability_rate": 1.0,
            "verdict_accuracy": 0.2,
            "certificate_valid_rate": 0.0,
            "fully_correct_rate": 0.0,
            "failure_stage_counts": {"not_extractable": 0, "correct": 0, "verdict_wrong": 16, "certificate_invalid": 4},
            "extended_status": "completed",
        }
    ]
    cells = cells_from_inventory(inventory, temperature=0.2, expected_n=100)
    markdown = render_local_matrix_analysis_markdown(
        follow_root="runs/local_matrix_n100_t02_v1",
        follow_summary={"cell_inventory": inventory, "cell_status_counts": {"completed": 1, "missing": 23}, "max_items": 100, "cohort_ids": {"C2": "c2", "F1": "f1"}},
        follow_cells=cells,
        follow_delegation=compute_delegation_table(cells, temperature=0.2),
        pilot_summary=None,
        pilot_cells=None,
        pilot_delegation=None,
        extractability_audit_path="docs/extractability_audit_n100_t02.md",
        plots_dir="runs/local_matrix_n100_t02_v1/plots",
        report_path="runs/local_matrix_n100_t02_v1/report.md",
        temperature=0.2,
        expected_n=100,
    )
    assert "Not final benchmark scores" in markdown
    assert "Cohort cap" in markdown
    assert "## 2. Delegation gaps" in markdown
