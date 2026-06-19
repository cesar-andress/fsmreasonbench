"""F1 evaluation parser and scorer tests."""

import pytest

from fsmreasonbench.baselines.common import run_invalid_baseline
from fsmreasonbench.baselines.f1 import run_oracle_baseline
from fsmreasonbench.evaluator.models import FailureStage
from fsmreasonbench.evaluator.scorer import score_f1_item, score_item
from fsmreasonbench.generator.separation import generate_separation_item


def test_oracle_baseline_scores_fully_correct() -> None:
    item = generate_separation_item(12)
    record = score_f1_item(item, run_oracle_baseline(item))
    assert record.fully_correct is True
    assert record.failure_stage == FailureStage.CORRECT


def test_invalid_baseline_not_extractable() -> None:
    item = generate_separation_item(13)
    record = score_item(item, run_invalid_baseline(item))
    assert record.extractable is False
    assert record.failure_stage == FailureStage.NOT_EXTRACTABLE


def test_wrong_verdict_scores_verdict_wrong() -> None:
    item = generate_separation_item(14)
    submission = run_oracle_baseline(item)
    submission["verdict"] = True
    record = score_f1_item(item, submission)
    assert record.failure_stage == FailureStage.VERDICT_WRONG
