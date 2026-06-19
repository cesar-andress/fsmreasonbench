"""C2 reference baselines: oracle ceiling, random, invalid."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fsmreasonbench.baselines.c2 import (
    run_invalid_baseline,
    run_oracle_baseline,
    run_random_baseline,
)
from fsmreasonbench.cli.run_baseline import main as run_baseline_main
from fsmreasonbench.evaluator.io import load_item
from fsmreasonbench.evaluator.models import FailureStage
from fsmreasonbench.evaluator.parser import parse_c2_response
from fsmreasonbench.evaluator.scorer import score_c2_item

ROOT = Path(__file__).resolve().parents[2]
POSITIVE_ITEM = ROOT / "examples/item_C2_reachability_seed42.json"


def _load_positive_item():
    return load_item(POSITIVE_ITEM)


def test_oracle_baseline_scores_fully_correct() -> None:
    item = _load_positive_item()
    raw = run_oracle_baseline(item)
    record = score_c2_item(item, raw)
    assert record.fully_correct is True
    assert record.failure_stage == FailureStage.CORRECT


def test_invalid_baseline_not_extractable() -> None:
    item = _load_positive_item()
    raw = run_invalid_baseline(item)
    record = score_c2_item(item, raw)
    assert record.extractable is False
    assert record.failure_stage == FailureStage.NOT_EXTRACTABLE


def test_random_baseline_deterministic_under_seed() -> None:
    item = _load_positive_item()
    first = run_random_baseline(item, seed=123)
    second = run_random_baseline(item, seed=123)
    assert first == second


def test_random_baseline_produces_parseable_output() -> None:
    item = _load_positive_item()
    raw = run_random_baseline(item, seed=7)
    result = parse_c2_response(raw)
    assert result.extractable is True
    assert result.submission is not None
    assert result.submission.item_id == item.item_id


@pytest.mark.parametrize("baseline", ["oracle", "random", "invalid"])
def test_baseline_cli_runs(baseline: str, capsys: pytest.CaptureFixture[str]) -> None:
    argv = [
        "--baseline",
        baseline,
        "--item",
        str(POSITIVE_ITEM),
    ]
    if baseline == "random":
        argv.extend(["--seed", "123"])
    assert run_baseline_main(argv) == 0
    captured = capsys.readouterr()
    if baseline == "invalid":
        assert "NOT VALID JSON" in captured.out
    else:
        payload = json.loads(captured.out)
        assert payload["item_id"] == _load_positive_item().item_id


def test_baseline_cli_score_oracle(capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        run_baseline_main(
            [
                "--baseline",
                "oracle",
                "--item",
                str(POSITIVE_ITEM),
                "--score",
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    scoring = json.loads(captured.err)
    assert scoring["fully_correct"] is True
    assert scoring["failure_stage"] == "correct"
