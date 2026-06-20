"""Local model track-temperature matrix tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fsmreasonbench.evaluator.local_matrix_plots import plot_local_matrix
from fsmreasonbench.runners.track_pilot_models import (
    TrackPilotModelsConfig,
    build_delegation_rows,
    build_temperature_delta_rows,
    build_track_row,
    cell_dir,
    parse_temperatures,
    render_track_pilot_report,
    temperature_dir_name,
    write_track_pilot_csv,
)


def test_parse_temperatures() -> None:
    assert parse_temperatures("0,0.2,0.7") == (0.0, 0.2, 0.7)
    assert parse_temperatures("0") == (0.0,)
    with pytest.raises(ValueError):
        parse_temperatures("")


def test_temperature_dir_name() -> None:
    assert temperature_dir_name(0.0) == "temp_0"
    assert temperature_dir_name(0.2) == "temp_0.2"
    assert temperature_dir_name(0.7) == "temp_0.7"


def test_output_directory_layout_with_temperatures() -> None:
    root = Path("runs/local_matrix_v1")
    path = cell_dir(
        root,
        "qwen2.5-coder:7b",
        "C2",
        "R1",
        temperature=0.2,
        use_temperature_dirs=True,
    )
    assert path == root / "qwen2.5-coder_7b" / "C2" / "temp_0.2" / "R1"


def test_single_temperature_uses_legacy_layout() -> None:
    config = TrackPilotModelsConfig(
        models=("mock",),
        families=("C2",),
        tracks=("R0",),
        c2_items_path=".",
        f1_items_path=".",
        out_dir="runs/track_pilot_v1",
        temperatures=(0.0,),
    )
    assert config.use_temperature_dirs is False
    path = cell_dir(
        Path(config.out_dir),
        "mock",
        "C2",
        "R0",
        temperature=0.0,
        use_temperature_dirs=config.use_temperature_dirs,
    )
    assert path == Path("runs/track_pilot_v1/mock/C2/R0")


def _synthetic_rows() -> list[dict]:
    def row(model, family, track, temp, full, cert, verdict):
        return build_track_row(
            {
                "n": 20,
                "extractability_rate": 1.0,
                "verdict_accuracy": verdict,
                "certificate_valid_rate": cert,
                "fully_correct_rate": full,
                "tool_invocation_rate": 0.0 if track == "R0" else 1.0,
                "average_tool_calls_per_item": 0.0 if track == "R0" else 1.0,
                "failure_stage_counts": {},
                "track_failure_counts": {
                    "final_submission_not_extractable": 0,
                    "verdict_wrong": 0,
                    "certificate_invalid": 0,
                    "correct": int(full * 20),
                },
            },
            model=model,
            family=family,
            track=track,
            temperature=temp,
            cohort_id="test-cohort",
            run_dir=Path("."),
        )

    rows = []
    for temp, full_r2 in ((0.0, 0.1), (0.2, 0.2), (0.7, 0.05)):
        rows.extend(
            [
                row("mock-a", "C2", "R0", temp, 0.0, 0.0, 0.3),
                row("mock-a", "C2", "R1", temp, 0.05, 0.05, 0.5),
                row("mock-a", "C2", "R2", temp, full_r2, full_r2, 0.6),
                row("mock-a", "F1", "R0", temp, 0.0, 0.0, 0.4),
                row("mock-a", "F1", "R2", temp, 0.4, 0.5, 1.0),
            ]
        )
    return rows


def test_combined_summary_schema_fields() -> None:
    rows = _synthetic_rows()
    payload = {
        "experiment": "local_matrix",
        "models": ["mock-a"],
        "families": ["C2", "F1"],
        "tracks": ["R0", "R1", "R2"],
        "temperatures": [0.0, 0.2, 0.7],
        "max_items": 20,
        "timeout": 300.0,
        "cohort_ids": {"C2": "c2-test", "F1": "f1-test"},
        "track_rows": rows,
        "delegation_rows": build_delegation_rows(rows),
        "temperature_delta_rows": build_temperature_delta_rows(rows),
        "failed_cells": [],
    }
    row = payload["track_rows"][0]
    for field in (
        "model",
        "family",
        "track",
        "temperature",
        "n",
        "extractability_rate",
        "verdict_accuracy",
        "certificate_valid_rate",
        "fully_correct_rate",
        "tool_invocation_rate",
        "average_tool_calls_per_item",
        "failure_stage_counts",
        "track_failure_counts",
    ):
        assert field in row, field


def test_delegation_gaps_by_temperature() -> None:
    rows = _synthetic_rows()
    delegation = build_delegation_rows(rows)
    c2_t0 = next(
        row
        for row in delegation
        if row["family"] == "C2" and float(row["temperature"]) == 0.0
    )
    assert c2_t0["delta_R2_minus_R0_fully_correct_rate"] == pytest.approx(0.1)
    c2_t02 = next(
        row
        for row in delegation
        if row["family"] == "C2" and float(row["temperature"]) == 0.2
    )
    assert c2_t02["delta_R2_minus_R0_fully_correct_rate"] == pytest.approx(0.2)


def test_temperature_deltas() -> None:
    rows = _synthetic_rows()
    deltas = build_temperature_delta_rows(rows)
    c2_r2 = next(row for row in deltas if row["family"] == "C2" and row["track"] == "R2")
    assert c2_r2["delta_temp_0.2_minus_0.0_fully_correct_rate"] == pytest.approx(0.1)
    assert c2_r2["delta_temp_0.7_minus_0.0_fully_correct_rate"] == pytest.approx(-0.05)


def test_report_includes_research_questions() -> None:
    rows = _synthetic_rows()
    payload = {
        "experiment": "local_matrix",
        "models": ["mock-a"],
        "families": ["C2", "F1"],
        "tracks": ["R0", "R1", "R2"],
        "temperatures": [0.0, 0.2, 0.7],
        "max_items": 20,
        "timeout": 300.0,
        "cohort_ids": {"C2": "c2-test", "F1": "f1-test"},
        "track_rows": rows,
        "delegation_rows": build_delegation_rows(rows),
        "temperature_delta_rows": build_temperature_delta_rows(rows),
        "failed_cells": [],
    }
    report = render_track_pilot_report(payload)
    assert "## Matrix overview" in report
    assert "RQ-L1" in report
    assert "RQ-L2" in report
    assert "RQ-L3" in report
    assert "RQ-L4" in report
    assert "temperature sensitivity" in report.lower()
    assert "RTX 4090" in report
    assert "paid apis" in report.lower()


def test_write_csv_includes_temperature_sections(tmp_path: Path) -> None:
    rows = _synthetic_rows()
    delegation = build_delegation_rows(rows)
    deltas = build_temperature_delta_rows(rows)
    csv_path = tmp_path / "combined_summary.csv"
    write_track_pilot_csv(csv_path, rows, delegation, deltas)
    text = csv_path.read_text(encoding="utf-8")
    assert "temperature" in text
    assert "delta_temp_0.2_minus_0.0_fully_correct_rate" in text


def test_plot_local_matrix_writes_pngs(tmp_path: Path) -> None:
    rows = _synthetic_rows()
    payload = {
        "experiment": "local_matrix",
        "models": ["mock-a"],
        "families": ["C2", "F1"],
        "tracks": ["R0", "R1", "R2"],
        "temperatures": [0.0, 0.2, 0.7],
        "track_rows": rows,
        "delegation_rows": build_delegation_rows(rows),
    }
    summary_path = tmp_path / "combined_summary.json"
    summary_path.write_text(json.dumps(payload), encoding="utf-8")
    plot_dir = tmp_path / "plots"
    written = plot_local_matrix(summary_path, plot_dir)
    assert written
    assert all(path.suffix == ".png" for path in written)
    assert (plot_dir / "fully_correct_by_track.png").exists()


def test_plot_skips_gracefully_without_matplotlib(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = _synthetic_rows()
    payload = {
        "models": ["mock-a"],
        "families": ["C2"],
        "tracks": ["R0"],
        "temperatures": [0.0],
        "track_rows": rows,
        "delegation_rows": [],
    }
    summary_path = tmp_path / "combined_summary.json"
    summary_path.write_text(json.dumps(payload), encoding="utf-8")

    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "matplotlib.pyplot" or name.startswith("matplotlib"):
            raise ImportError("no matplotlib")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(RuntimeError, match="matplotlib"):
        plot_local_matrix(summary_path, tmp_path / "plots")
