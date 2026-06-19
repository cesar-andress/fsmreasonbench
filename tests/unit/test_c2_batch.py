"""C2 batch generation, baseline evaluation, and score summarization."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fsmreasonbench.cli.evaluate_baseline_batch import main as evaluate_batch_main
from fsmreasonbench.cli.generate_batch import main as generate_batch_main
from fsmreasonbench.cli.summarize_scores import main as summarize_main
from fsmreasonbench.evaluator.batch import evaluate_baseline_on_items, generate_c2_batch
from fsmreasonbench.evaluator.jsonl import load_items_jsonl, read_jsonl, write_jsonl
from fsmreasonbench.evaluator.summary import summarize_scoring_records


def test_batch_generation_deterministic_under_seed() -> None:
    first = generate_c2_batch(5, seed=1)
    second = generate_c2_batch(5, seed=1)
    assert [item.item_id for item in first] == [item.item_id for item in second]
    assert [item.to_full_dict() for item in first] == [
        item.to_full_dict() for item in second
    ]


def test_oracle_baseline_fully_correct_on_batch() -> None:
    items = generate_c2_batch(8, seed=7)
    records = evaluate_baseline_on_items("oracle", items)
    assert all(record.fully_correct for record in records)
    assert all(record.failure_stage.value == "correct" for record in records)


def test_invalid_baseline_zero_extractability() -> None:
    items = generate_c2_batch(6, seed=3)
    records = evaluate_baseline_on_items("invalid", items)
    assert all(not record.extractable for record in records)
    assert all(record.failure_stage.value == "not_extractable" for record in records)


def test_summarize_scores_returns_expected_counts() -> None:
    items = generate_c2_batch(4, seed=11)
    oracle_records = evaluate_baseline_on_items("oracle", items)
    invalid_records = evaluate_baseline_on_items("invalid", items)

    oracle_summary = summarize_scoring_records(oracle_records)
    assert oracle_summary["n"] == 4
    assert oracle_summary["extractability_rate"] == 1.0
    assert oracle_summary["fully_correct_rate"] == 1.0
    assert oracle_summary["failure_stage_counts"]["correct"] == 4

    invalid_summary = summarize_scoring_records(invalid_records)
    assert invalid_summary["n"] == 4
    assert invalid_summary["extractability_rate"] == 0.0
    assert invalid_summary["verdict_accuracy"] == 0.0
    assert invalid_summary["fully_correct_rate"] == 0.0
    assert invalid_summary["failure_stage_counts"]["not_extractable"] == 4


def test_batch_cli_pipeline(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    items_path = tmp_path / "items.jsonl"
    scores_path = tmp_path / "scores.jsonl"
    summary_path = tmp_path / "summary.json"

    assert generate_batch_main(["--n", "5", "--seed", "1", "--out", str(items_path)]) == 0
    loaded = load_items_jsonl(items_path)
    assert len(loaded) == 5

    assert (
        evaluate_batch_main(
            [
                "--baseline",
                "oracle",
                "--items",
                str(items_path),
                "--out",
                str(scores_path),
            ]
        )
        == 0
    )
    score_lines = read_jsonl(scores_path)
    assert len(score_lines) == 5
    assert all(line["fully_correct"] for line in score_lines)

    assert (
        summarize_main(
            ["--scores", str(scores_path), "--out", str(summary_path)]
        )
        == 0
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["n"] == 5
    assert summary["fully_correct_rate"] == 1.0
