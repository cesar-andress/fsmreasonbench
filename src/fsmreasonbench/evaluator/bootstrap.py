"""Bootstrap confidence intervals for capability-surface metrics."""

from __future__ import annotations

import random
from typing import Any

from fsmreasonbench.evaluator.models import ScoringRecord

DEFAULT_BOOTSTRAP_RESAMPLES = 1000
DEFAULT_BOOTSTRAP_ALPHA = 0.05

BOOTSTRAP_CI_FIELDS: tuple[str, ...] = (
    "fully_correct_rate_ci_low",
    "fully_correct_rate_ci_high",
    "verdict_accuracy_ci_low",
    "verdict_accuracy_ci_high",
)


def bootstrap_capability_surface_cis(
    records: list[ScoringRecord],
    *,
    n_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    seed: int = 0,
    alpha: float = DEFAULT_BOOTSTRAP_ALPHA,
) -> dict[str, float]:
    """Compute percentile bootstrap CIs for key capability-surface rates."""
    if n_resamples < 1:
        raise ValueError("n_resamples must be >= 1")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be in (0, 1)")

    point_fully_correct = _fully_correct_rate(records)
    point_verdict_accuracy = _verdict_accuracy(records)
    if not records:
        return {
            "fully_correct_rate_ci_low": point_fully_correct,
            "fully_correct_rate_ci_high": point_fully_correct,
            "verdict_accuracy_ci_low": point_verdict_accuracy,
            "verdict_accuracy_ci_high": point_verdict_accuracy,
        }

    rng = random.Random(seed)
    fully_correct_samples: list[float] = []
    verdict_accuracy_samples: list[float] = []
    population = tuple(records)
    sample_size = len(population)

    for _ in range(n_resamples):
        sample = [population[rng.randrange(sample_size)] for _ in range(sample_size)]
        fully_correct_samples.append(_fully_correct_rate(sample))
        verdict_accuracy_samples.append(_verdict_accuracy(sample))

    low_q = alpha / 2.0
    high_q = 1.0 - alpha / 2.0
    return {
        "fully_correct_rate_ci_low": _percentile(fully_correct_samples, low_q),
        "fully_correct_rate_ci_high": _percentile(fully_correct_samples, high_q),
        "verdict_accuracy_ci_low": _percentile(verdict_accuracy_samples, low_q),
        "verdict_accuracy_ci_high": _percentile(verdict_accuracy_samples, high_q),
    }


def _fully_correct_rate(records: list[ScoringRecord]) -> float:
    if not records:
        return 0.0
    return sum(1 for record in records if record.fully_correct) / len(records)


def _verdict_accuracy(records: list[ScoringRecord]) -> float:
    extractable = [record for record in records if record.extractable]
    if not extractable:
        return 0.0
    verdict_correct = sum(1 for record in extractable if record.verdict_correct is True)
    return verdict_correct / len(extractable)


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = quantile * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight
