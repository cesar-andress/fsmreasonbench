"""Capability-surface exploratory runner tests."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from fsmreasonbench.cli.run_capability_surface import main as capability_surface_main
from fsmreasonbench.evaluator.capability_surface import (
    CapabilitySurfaceConfig,
    run_capability_surface,
)


def test_capability_surface_produces_combined_summary(tmp_path: Path) -> None:
    payload = run_capability_surface(
        tmp_path / "surface",
        CapabilitySurfaceConfig(
            families=("C2", "F1"),
            n_per_level=3,
            seed=7,
            c2_levels=(1, 2),
            f1_levels=(1, 2),
        ),
    )
    assert len(payload["rows"]) == 2 * 2 * 3  # families × levels × baselines
    assert (tmp_path / "surface" / "combined_summary.json").exists()
    assert (tmp_path / "surface" / "combined_summary.csv").exists()


def test_oracle_fully_correct_for_all_rows(tmp_path: Path) -> None:
    payload = run_capability_surface(
        tmp_path / "oracle_check",
        CapabilitySurfaceConfig(
            families=("C2", "F1"),
            n_per_level=4,
            seed=3,
            c2_levels=(1,),
            f1_levels=(1,),
        ),
    )
    oracle_rows = [row for row in payload["rows"] if row["baseline"] == "oracle"]
    assert oracle_rows
    assert all(row["fully_correct_rate"] == 1.0 for row in oracle_rows)


def test_invalid_zero_extractability_for_all_rows(tmp_path: Path) -> None:
    payload = run_capability_surface(
        tmp_path / "invalid_check",
        CapabilitySurfaceConfig(
            families=("C2", "F1"),
            n_per_level=4,
            seed=5,
            c2_levels=(1,),
            f1_levels=(1,),
        ),
    )
    invalid_rows = [row for row in payload["rows"] if row["baseline"] == "invalid"]
    assert invalid_rows
    assert all(row["extractability_rate"] == 0.0 for row in invalid_rows)


def test_random_deterministic_under_seed(tmp_path: Path) -> None:
    config = CapabilitySurfaceConfig(
        families=("C2",),
        n_per_level=5,
        seed=11,
        baseline_seed=99,
        c2_levels=(1, 2),
        f1_levels=(),
    )
    first = run_capability_surface(tmp_path / "random_a", config)
    second = run_capability_surface(tmp_path / "random_b", config)
    random_first = [row for row in first["rows"] if row["baseline"] == "random"]
    random_second = [row for row in second["rows"] if row["baseline"] == "random"]
    assert random_first == random_second


def test_both_families_present_in_combined_summary(tmp_path: Path) -> None:
    payload = run_capability_surface(
        tmp_path / "both_families",
        CapabilitySurfaceConfig(
            families=("C2", "F1"),
            n_per_level=2,
            seed=1,
            c2_levels=(1,),
            f1_levels=(1,),
        ),
    )
    families = {row["family"] for row in payload["rows"]}
    assert families == {"C2", "F1"}


def test_combined_summary_csv_has_expected_columns(tmp_path: Path) -> None:
    run_capability_surface(
        tmp_path / "csv",
        CapabilitySurfaceConfig(
            families=("C2",),
            n_per_level=2,
            seed=2,
            c2_levels=(1,),
            f1_levels=(),
        ),
    )
    with (tmp_path / "csv" / "combined_summary.csv").open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        row = next(reader)
        assert row["family"] == "C2"
        assert row["baseline"] in {"oracle", "random", "invalid"}
        assert "failure_stage_counts" in row


def test_cli_produces_combined_summary(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out_dir = tmp_path / "cli_surface"
    assert (
        capability_surface_main(
            [
                "--families",
                "C2,F1",
                "--n-per-level",
                "2",
                "--seed",
                "1",
                "--out-dir",
                str(out_dir),
                "--skip-failed-levels",
            ]
        )
        == 0
    )
    payload = json.loads((out_dir / "combined_summary.json").read_text(encoding="utf-8"))
    assert payload["rows"]
    assert {row["family"] for row in payload["rows"]} == {"C2", "F1"}
    assert (out_dir / "combined_summary.csv").exists()


def test_explicit_failure_without_skip_failed_levels(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="failed to generate"):
        run_capability_surface(
            tmp_path / "fail",
            CapabilitySurfaceConfig(
                families=("F1",),
                n_per_level=10,
                seed=1,
                f1_levels=(4,),
                c2_levels=(),
            ),
        )
