"""Capability surface figure export tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from fsmreasonbench.cli.export_capability_surface_figures import main as export_figures_main
from fsmreasonbench.evaluator.capability_surface_figure_export import (
    export_capability_surface_figure,
    infer_report_path,
    parse_level_metrics_from_report_text,
)

_SAMPLE_REPORT = """\
# Report

### C2 — by difficulty level

| Model | Level | Extractability | Verdict | Certificate | Fully correct |
|-------|------:|---------------:|--------:|------------:|--------------:|
| `gemma2:9b` | 1 | 1.000 | 0.850 | 0.100 | 0.100 |
| `gemma2:9b` | 2 | 1.000 | 0.550 | 0.050 | 0.050 |
| `llama3.1:8b` | 1 | 1.000 | 0.900 | 0.100 | 0.100 |
| `llama3.1:8b` | 2 | 1.000 | 0.450 | 0.200 | 0.200 |
"""


def test_infer_report_path() -> None:
    path = infer_report_path(Path("docs/capability_surface_summary.csv"))
    assert path.name == "capability_surface_report.md"


def test_parse_level_metrics_from_report_md() -> None:
    rows = parse_level_metrics_from_report_text(_SAMPLE_REPORT, family="C2")
    assert len(rows) == 4
    assert rows[0].model == "gemma2:9b"
    assert rows[0].difficulty_level == 1
    assert rows[0].fully_correct_rate == pytest.approx(0.1)


def test_export_capability_surface_figure_writes_pdf(tmp_path: Path) -> None:
    report = tmp_path / "capability_surface_report.md"
    report.write_text(_SAMPLE_REPORT, encoding="utf-8")
    summary = tmp_path / "capability_surface_summary.csv"
    summary.write_text(
        "family,model,n_levels,missing_level_count,extractability_rate,"
        "verdict_accuracy,certificate_valid_rate,fully_correct_rate\n"
        "C2,gemma2:9b,2,0,1.0,0.7,0.075,0.075\n"
        "C2,llama3.1:8b,2,0,1.0,0.675,0.150,0.150\n",
        encoding="utf-8",
    )
    out_pdf = tmp_path / "c2_capability_surface.pdf"
    export_capability_surface_figure(
        summary,
        out_pdf,
        family="C2",
        report_md=report,
        title="Test C2",
    )
    assert out_pdf.is_file()
    assert out_pdf.read_bytes()[:4] == b"%PDF"


def test_export_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    report = tmp_path / "capability_surface_report.md"
    report.write_text(_SAMPLE_REPORT, encoding="utf-8")
    summary = tmp_path / "capability_surface_summary.csv"
    summary.write_text(
        "family,model,n_levels,missing_level_count,extractability_rate,"
        "verdict_accuracy,certificate_valid_rate,fully_correct_rate\n"
        "C2,gemma2:9b,2,0,1.0,0.7,0.075,0.075\n"
        "C2,llama3.1:8b,2,0,1.0,0.675,0.150,0.150\n",
        encoding="utf-8",
    )
    out_pdf = tmp_path / "c2.pdf"
    assert (
        export_figures_main(
            [
                "--summary-csv",
                str(summary),
                "--report-md",
                str(report),
                "--family",
                "C2",
                "--out",
                str(out_pdf),
            ]
        )
        == 0
    )
    assert out_pdf.is_file()
    assert "wrote" in capsys.readouterr().out
