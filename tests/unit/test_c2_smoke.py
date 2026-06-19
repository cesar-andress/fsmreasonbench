"""C2 smoke baseline batch runner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fsmreasonbench.cli.run_c2_smoke_baselines import main as smoke_main
from fsmreasonbench.evaluator.batch import run_c2_smoke_baselines


def test_oracle_smoke_summary_fully_correct(tmp_path: Path) -> None:
    combined = run_c2_smoke_baselines(12, seed=1, out_dir=tmp_path / "oracle_smoke")
    oracle = next(row for row in combined if row["baseline"] == "oracle")
    assert oracle["fully_correct_rate"] == 1.0
    assert oracle["extractability_rate"] == 1.0


def test_invalid_smoke_summary_zero_extractability(tmp_path: Path) -> None:
    combined = run_c2_smoke_baselines(10, seed=2, out_dir=tmp_path / "invalid_smoke")
    invalid = next(row for row in combined if row["baseline"] == "invalid")
    assert invalid["extractability_rate"] == 0.0
    assert invalid["fully_correct_rate"] == 0.0


def test_random_smoke_summary_deterministic_under_seed(tmp_path: Path) -> None:
    first = run_c2_smoke_baselines(15, seed=3, out_dir=tmp_path / "run_a", baseline_seed=7)
    second = run_c2_smoke_baselines(15, seed=3, out_dir=tmp_path / "run_b", baseline_seed=7)
    random_first = next(row for row in first if row["baseline"] == "random")
    random_second = next(row for row in second if row["baseline"] == "random")
    assert random_first == random_second


def test_combined_summary_contains_all_baselines(tmp_path: Path) -> None:
    combined = run_c2_smoke_baselines(8, seed=4, out_dir=tmp_path / "smoke")
    assert {row["baseline"] for row in combined} == {"oracle", "random", "invalid"}

    on_disk = json.loads((tmp_path / "smoke" / "combined_summary.json").read_text(encoding="utf-8"))
    assert len(on_disk) == 3
    assert {row["baseline"] for row in on_disk} == {"oracle", "random", "invalid"}
    for baseline in ("oracle", "random", "invalid"):
        assert (tmp_path / "smoke" / f"{baseline}_scores.jsonl").exists()
        assert (tmp_path / "smoke" / f"{baseline}_summary.json").exists()
    assert (tmp_path / "smoke" / "c2_items.jsonl").exists()


def test_smoke_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out_dir = tmp_path / "cli_smoke"
    assert smoke_main(["--n", "6", "--seed", "1", "--out-dir", str(out_dir)]) == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["n"] == 6
    assert set(payload["baselines"]) == {"oracle", "random", "invalid"}
    assert (out_dir / "combined_summary.json").exists()
