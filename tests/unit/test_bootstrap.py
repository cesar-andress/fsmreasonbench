"""Bootstrap confidence interval tests."""

from __future__ import annotations

import pytest

from fsmreasonbench.evaluator.bootstrap import bootstrap_capability_surface_cis
from fsmreasonbench.evaluator.models import FailureStage, ScoringRecord


def _record(
    *,
    extractable: bool = True,
    verdict_correct: bool | None = True,
    fully_correct: bool = False,
    failure_stage: FailureStage = FailureStage.CORRECT,
) -> ScoringRecord:
    return ScoringRecord(
        item_id="item",
        family="F1",
        extractable=extractable,
        verdict_correct=verdict_correct,
        certificate_valid=fully_correct,
        fully_correct=fully_correct,
        failure_stage=failure_stage,
    )


def test_bootstrap_cis_are_deterministic_with_fixed_seed() -> None:
    records = [
        _record(fully_correct=True),
        _record(fully_correct=False, verdict_correct=False, failure_stage=FailureStage.VERDICT_WRONG),
        _record(fully_correct=False, extractable=False, verdict_correct=None, failure_stage=FailureStage.NOT_EXTRACTABLE),
        _record(fully_correct=True),
    ]
    first = bootstrap_capability_surface_cis(records, n_resamples=1000, seed=17)
    second = bootstrap_capability_surface_cis(records, n_resamples=1000, seed=17)
    assert first == second


def test_bootstrap_cis_bracket_point_estimates() -> None:
    records = [
        _record(fully_correct=True),
        _record(fully_correct=False, verdict_correct=False, failure_stage=FailureStage.VERDICT_WRONG),
        _record(fully_correct=False),
        _record(fully_correct=True),
    ]
    cis = bootstrap_capability_surface_cis(records, n_resamples=500, seed=3)
    fully_correct_rate = 0.5
    verdict_accuracy = 2 / 3
    assert cis["fully_correct_rate_ci_low"] <= fully_correct_rate <= cis["fully_correct_rate_ci_high"]
    assert cis["verdict_accuracy_ci_low"] <= verdict_accuracy <= cis["verdict_accuracy_ci_high"]


def test_bootstrap_cis_empty_records() -> None:
    cis = bootstrap_capability_surface_cis([], n_resamples=1000, seed=0)
    assert cis == {
        "fully_correct_rate_ci_low": 0.0,
        "fully_correct_rate_ci_high": 0.0,
        "verdict_accuracy_ci_low": 0.0,
        "verdict_accuracy_ci_high": 0.0,
    }


def test_bootstrap_rejects_invalid_resample_count() -> None:
    with pytest.raises(ValueError, match="n_resamples"):
        bootstrap_capability_surface_cis([_record()], n_resamples=0, seed=0)
