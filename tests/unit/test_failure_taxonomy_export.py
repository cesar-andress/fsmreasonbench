"""Failure taxonomy LaTeX export tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from fsmreasonbench.cli.export_failure_taxonomy_table import main as export_main
from fsmreasonbench.evaluator.failure_taxonomy_export import (
    export_failure_taxonomy_latex,
    parse_failure_taxonomy_report_md,
    render_failure_taxonomy_latex_table,
    taxonomy_rows_for_latex,
)


_SAMPLE_REPORT = """\
# Sample

## Aggregated taxonomy (all runs)

| Category | Count | Share |
|----------|------:|------:|
| `acceptance_mismatch` | 88 | 63.8% |
| `replay_failure` | 50 | 36.2% |
| `wrong_trace_format` | 0 | 0.0% |
| `incomplete_reachability_set` | 0 | 0.0% |
| `equivalence_hash_mismatch` | 0 | 0.0% |
| `wrong_certificate_type` | 0 | 0.0% |
| `wrong_fsm_ids` | 0 | 0.0% |
| `malformed_certificate_payload` | 0 | 0.0% |
| `other` | 0 | 0.0% |

## Per-model breakdown
"""


def test_parse_failure_taxonomy_report_md() -> None:
    rows = parse_failure_taxonomy_report_md(_SAMPLE_REPORT)
    assert len(rows) == 9
    assert rows[0].category == "acceptance_mismatch"
    assert rows[0].count == 88
    assert rows[0].percentage == pytest.approx(63.8)


def test_taxonomy_rows_for_latex_inserts_missing_zero_categories() -> None:
    rows = taxonomy_rows_for_latex(
        parse_failure_taxonomy_report_md(_SAMPLE_REPORT)[:2]
    )
    assert [row.category for row in rows[:2]] == ["acceptance_mismatch", "replay_failure"]
    assert all(row.count == 0 for row in rows[2:])


def test_render_failure_taxonomy_latex_table_includes_all_categories() -> None:
    rows = parse_failure_taxonomy_report_md(_SAMPLE_REPORT)
    latex = render_failure_taxonomy_latex_table(rows)
    assert "\\label{tab:f1-mixed-failure-taxonomy}" in latex
    assert "Category & Count & Percentage" in latex
    assert "acceptance\\_mismatch" in latex
    assert "replay\\_failure" in latex
    assert "malformed\\_certificate\\_payload" in latex
    assert "88 & 63.8\\%" in latex
    assert "0 & 0.0\\%" in latex


def test_export_failure_taxonomy_latex_writes_file(tmp_path: Path) -> None:
    report = tmp_path / "report.md"
    report.write_text(_SAMPLE_REPORT, encoding="utf-8")
    out_tex = tmp_path / "taxonomy.tex"
    export_failure_taxonomy_latex(report, out_tex)
    content = out_tex.read_text(encoding="utf-8")
    assert "\\begin{table}[t]" in content
    assert "Exploratory distribution of certificate failure categories" in content


def test_export_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    report = tmp_path / "report.md"
    report.write_text(_SAMPLE_REPORT, encoding="utf-8")
    out_tex = tmp_path / "taxonomy.tex"
    assert (
        export_main(
            [
                "--report",
                str(report),
                "--out-tex",
                str(out_tex),
            ]
        )
        == 0
    )
    assert out_tex.is_file()
    assert "wrote" in capsys.readouterr().out
