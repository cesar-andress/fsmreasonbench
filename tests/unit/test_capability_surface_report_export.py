"""Tests for capability-surface report export utilities."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from fsmreasonbench.cli.export_capability_surface_report import main as export_cli_main
from fsmreasonbench.evaluator.capability_surface_report_export import (
    aggregate_by_family,
    aggregate_by_family_model,
    analyze_completeness,
    export_capability_surface_report,
    load_combined_summary,
    render_capability_surface_latex_table,
    render_capability_surface_report_markdown,
)


def _synthetic_payload(*, include_missing: bool = True) -> dict:
    rows = [
        {
            "family": "C2",
            "difficulty_level": 1,
            "model": "mock-a",
            "extractability_rate": 1.0,
            "verdict_accuracy": 0.9,
            "certificate_valid_rate": 0.7,
            "fully_correct_rate": 0.7,
        },
        {
            "family": "C2",
            "difficulty_level": 2,
            "model": "mock-a",
            "extractability_rate": 1.0,
            "verdict_accuracy": 0.8,
            "certificate_valid_rate": 0.5,
            "fully_correct_rate": 0.5,
        },
        {
            "family": "C2",
            "difficulty_level": 1,
            "model": "mock-b",
            "extractability_rate": 1.0,
            "verdict_accuracy": 0.85,
            "certificate_valid_rate": 0.6,
            "fully_correct_rate": 0.6,
        },
        {
            "family": "F1",
            "difficulty_level": 1,
            "model": "mock-a",
            "extractability_rate": 1.0,
            "verdict_accuracy": 1.0,
            "certificate_valid_rate": 0.2,
            "fully_correct_rate": 0.2,
        },
        {
            "family": "F1",
            "difficulty_level": 2,
            "model": "mock-a",
            "extractability_rate": 1.0,
            "verdict_accuracy": 1.0,
            "certificate_valid_rate": 0.1,
            "fully_correct_rate": 0.1,
        },
    ]
    models = ["mock-a", "mock-b"]
    if not include_missing:
        rows.extend(
            [
                {
                    "family": "C2",
                    "difficulty_level": 2,
                    "model": "mock-b",
                    "extractability_rate": 1.0,
                    "verdict_accuracy": 0.75,
                    "certificate_valid_rate": 0.45,
                    "fully_correct_rate": 0.45,
                },
                {
                    "family": "F1",
                    "difficulty_level": 1,
                    "model": "mock-b",
                    "extractability_rate": 1.0,
                    "verdict_accuracy": 1.0,
                    "certificate_valid_rate": 0.15,
                    "fully_correct_rate": 0.15,
                },
                {
                    "family": "F1",
                    "difficulty_level": 2,
                    "model": "mock-b",
                    "extractability_rate": 1.0,
                    "verdict_accuracy": 1.0,
                    "certificate_valid_rate": 0.05,
                    "fully_correct_rate": 0.05,
                },
            ]
        )
    return {
        "families": ["C2", "F1"],
        "models": models,
        "n_per_level": 10,
        "seed": 1,
        "temperature": 0.0,
        "rows": rows,
    }


def test_load_combined_summary_json(tmp_path: Path) -> None:
    summary_path = tmp_path / "combined_summary.json"
    summary_path.write_text(json.dumps(_synthetic_payload()), encoding="utf-8")
    summary = load_combined_summary(summary_path)
    assert len(summary.rows) == 5
    assert summary.families == ("C2", "F1")
    assert summary.models == ("mock-a", "mock-b")


def test_load_combined_summary_csv(tmp_path: Path) -> None:
    summary_path = tmp_path / "combined_summary.csv"
    summary_path.write_text(
        "family,difficulty_level,model,extractability_rate,verdict_accuracy,"
        "certificate_valid_rate,fully_correct_rate\n"
        "C2,1,mock-a,1.0,0.9,0.7,0.7\n",
        encoding="utf-8",
    )
    summary = load_combined_summary(summary_path)
    assert len(summary.rows) == 1
    assert summary.rows[0]["family"] == "C2"


def test_analyze_completeness_reports_missing_cells(tmp_path: Path) -> None:
    summary_path = tmp_path / "combined_summary.json"
    summary_path.write_text(json.dumps(_synthetic_payload()), encoding="utf-8")
    summary = load_combined_summary(summary_path)
    completeness = analyze_completeness(summary)
    assert completeness.present_cells == 5
    assert completeness.missing_count == 3
    assert ("C2", 2, "mock-b") in completeness.missing_cells


def test_aggregate_by_family_model_means(tmp_path: Path) -> None:
    summary_path = tmp_path / "combined_summary.json"
    summary_path.write_text(json.dumps(_synthetic_payload()), encoding="utf-8")
    summary = load_combined_summary(summary_path)
    aggregates = aggregate_by_family_model(summary)
    mock_a_c2 = next(
        agg for agg in aggregates if agg.family == "C2" and agg.model == "mock-a"
    )
    assert mock_a_c2.n_levels == 2
    assert mock_a_c2.extractability_rate == pytest.approx(1.0)
    assert mock_a_c2.fully_correct_rate == pytest.approx(0.6)


def test_aggregate_by_family(tmp_path: Path) -> None:
    summary_path = tmp_path / "combined_summary.json"
    summary_path.write_text(json.dumps(_synthetic_payload()), encoding="utf-8")
    summary = load_combined_summary(summary_path)
    aggregates = aggregate_by_family(summary)
    f1 = next(agg for agg in aggregates if agg.family == "F1")
    assert f1.n_rows == 2
    assert f1.verdict_accuracy == pytest.approx(1.0)
    assert f1.fully_correct_rate == pytest.approx(0.15)


def test_render_markdown_includes_family_sections(tmp_path: Path) -> None:
    summary_path = tmp_path / "combined_summary.json"
    summary_path.write_text(json.dumps(_synthetic_payload()), encoding="utf-8")
    summary = load_combined_summary(summary_path)
    markdown = render_capability_surface_report_markdown(summary)
    assert "## Family averages" in markdown
    assert "## C2 — model comparison" in markdown
    assert "## F1 — model comparison" in markdown
    assert "## Missing cells" in markdown
    assert "verdict-overstatement" in markdown


def test_render_latex_table(tmp_path: Path) -> None:
    summary_path = tmp_path / "combined_summary.json"
    summary_path.write_text(json.dumps(_synthetic_payload()), encoding="utf-8")
    summary = load_combined_summary(summary_path)
    family_model = aggregate_by_family_model(summary)
    latex = render_capability_surface_latex_table(family_model)
    assert "\\begin{table}[t]" in latex
    assert "Extract." in latex
    assert "mock-a" in latex or "mock\\_a" in latex


def test_export_writes_all_outputs(tmp_path: Path) -> None:
    summary_path = tmp_path / "combined_summary.json"
    summary_path.write_text(json.dumps(_synthetic_payload()), encoding="utf-8")
    md_path = tmp_path / "report.md"
    tex_path = tmp_path / "table.tex"
    csv_path = tmp_path / "aggregated.csv"

    written = export_capability_surface_report(
        summary_path,
        out_md=md_path,
        out_tex=tex_path,
        out_csv=csv_path,
    )
    assert written["markdown"] == md_path
    assert md_path.exists()
    assert tex_path.exists()
    assert csv_path.exists()

    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows
    assert {"family", "model", "fully_correct_rate"} <= set(rows[0].keys())


def test_export_incomplete_summary_without_strict(tmp_path: Path) -> None:
    summary_path = tmp_path / "combined_summary.json"
    summary_path.write_text(json.dumps(_synthetic_payload()), encoding="utf-8")
    export_capability_surface_report(
        summary_path,
        out_md=tmp_path / "report.md",
    )


def test_export_strict_fails_on_missing_cells(tmp_path: Path) -> None:
    summary_path = tmp_path / "combined_summary.json"
    summary_path.write_text(json.dumps(_synthetic_payload()), encoding="utf-8")
    with pytest.raises(ValueError, match="incomplete summary"):
        export_capability_surface_report(
            summary_path,
            out_md=tmp_path / "report.md",
            strict=True,
        )


def test_export_strict_passes_when_complete(tmp_path: Path) -> None:
    summary_path = tmp_path / "combined_summary.json"
    summary_path.write_text(
        json.dumps(_synthetic_payload(include_missing=False)),
        encoding="utf-8",
    )
    export_capability_surface_report(
        summary_path,
        out_md=tmp_path / "report.md",
        strict=True,
    )


def test_cli_export(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    summary_path = tmp_path / "combined_summary.json"
    summary_path.write_text(json.dumps(_synthetic_payload()), encoding="utf-8")
    md_path = tmp_path / "report.md"
    tex_path = tmp_path / "table.tex"

    rc = export_cli_main(
        [
            "--summary",
            str(summary_path),
            "--out-md",
            str(md_path),
            "--out-tex",
            str(tex_path),
        ]
    )
    assert rc == 0
    assert md_path.exists()
    assert tex_path.exists()
    captured = capsys.readouterr()
    assert "Wrote markdown" in captured.out


def test_cli_strict_returns_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    summary_path = tmp_path / "combined_summary.json"
    summary_path.write_text(json.dumps(_synthetic_payload()), encoding="utf-8")

    rc = export_cli_main(
        [
            "--summary",
            str(summary_path),
            "--out-md",
            str(tmp_path / "report.md"),
            "--strict",
        ]
    )
    assert rc == 2
    assert "incomplete summary" in capsys.readouterr().err


def test_example_synthetic_summary_loads() -> None:
    example = Path("examples/capability_surface_summary_synthetic.json")
    summary = load_combined_summary(example)
    assert summary.families == ("C2", "F1")
    assert len(summary.rows) == 5
