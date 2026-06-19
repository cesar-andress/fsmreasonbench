"""F1 batch generation and smoke runner tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fsmreasonbench.cli.generate_batch import main as generate_batch_main
from fsmreasonbench.cli.run_f1_smoke_baselines import main as f1_smoke_main
from fsmreasonbench.evaluator.batch import (
    evaluate_baseline_on_items,
    generate_f1_batch,
    run_f1_smoke_baselines,
)
from fsmreasonbench.evaluator.jsonl import load_items_jsonl, read_jsonl
from fsmreasonbench.generator.separation import SeparationGeneratorConfig


def test_f1_batch_generation_deterministic() -> None:
    config = SeparationGeneratorConfig(min_distinguishing_trace_length=2, max_retries=128)
    first = generate_f1_batch(5, seed=1, config=config)
    second = generate_f1_batch(5, seed=1, config=config)
    assert [item.item_id for item in first] == [item.item_id for item in second]


def test_f1_oracle_baseline_fully_correct_on_batch() -> None:
    config = SeparationGeneratorConfig(min_distinguishing_trace_length=2, max_retries=128)
    items = generate_f1_batch(6, seed=3, config=config)
    records = evaluate_baseline_on_items("oracle", items)
    assert all(record.fully_correct for record in records)


def test_f1_invalid_baseline_zero_extractability() -> None:
    config = SeparationGeneratorConfig(min_distinguishing_trace_length=2, max_retries=128)
    items = generate_f1_batch(4, seed=5, config=config)
    records = evaluate_baseline_on_items("invalid", items)
    assert all(not record.extractable for record in records)


def test_f1_smoke_runner_writes_combined_summary(tmp_path: Path) -> None:
    config = SeparationGeneratorConfig(min_distinguishing_trace_length=2, max_retries=128)
    combined = run_f1_smoke_baselines(8, seed=2, out_dir=tmp_path / "smoke", config=config)
    assert len(combined) == 3
    assert {row["baseline"] for row in combined} == {"oracle", "random", "invalid"}
    assert (tmp_path / "smoke" / "combined_summary.json").exists()
    assert (tmp_path / "smoke" / "f1_items.jsonl").exists()
    oracle = next(row for row in combined if row["baseline"] == "oracle")
    assert oracle["fully_correct_rate"] == 1.0


def test_f1_batch_cli_and_smoke_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    items_path = tmp_path / "f1_items.jsonl"
    assert (
        generate_batch_main(
            [
                "--family",
                "F1",
                "--n",
                "4",
                "--seed",
                "1",
                "--out",
                str(items_path),
                "--min-distinguishing-trace-length",
                "2",
            ]
        )
        == 0
    )
    assert len(load_items_jsonl(items_path)) == 4

    out_dir = tmp_path / "cli_smoke"
    assert (
        f1_smoke_main(
            [
                "--n",
                "4",
                "--seed",
                "1",
                "--out-dir",
                str(out_dir),
                "--min-distinguishing-trace-length",
                "2",
            ]
        )
        == 0
    )
    combined = json.loads((out_dir / "combined_summary.json").read_text(encoding="utf-8"))
    assert len(combined) == 3
    scores = read_jsonl(out_dir / "oracle_scores.jsonl")
    assert len(scores) == 4
    assert all(line["fully_correct"] for line in scores)
