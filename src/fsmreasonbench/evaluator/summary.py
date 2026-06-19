"""Aggregate scoring summaries for batch evaluation."""

from __future__ import annotations

from collections import Counter
from typing import Any

from fsmreasonbench.evaluator.models import FailureStage, ScoringRecord


def summarize_scoring_records(records: list[ScoringRecord]) -> dict[str, Any]:
    """Compute aggregate rates and failure-stage counts."""
    n = len(records)
    if n == 0:
        return {
            "n": 0,
            "extractability_rate": 0.0,
            "verdict_accuracy": 0.0,
            "certificate_valid_rate": 0.0,
            "fully_correct_rate": 0.0,
            "failure_stage_counts": {},
        }

    extractable_count = sum(1 for record in records if record.extractable)
    verdict_correct_count = sum(
        1 for record in records if record.verdict_correct is True
    )
    certificate_valid_count = sum(
        1 for record in records if record.certificate_valid is True
    )
    fully_correct_count = sum(1 for record in records if record.fully_correct)

    stage_counts = Counter(record.failure_stage.value for record in records)

    return {
        "n": n,
        "extractability_rate": extractable_count / n,
        "verdict_accuracy": (
            verdict_correct_count / extractable_count if extractable_count else 0.0
        ),
        "certificate_valid_rate": (
            certificate_valid_count / extractable_count if extractable_count else 0.0
        ),
        "fully_correct_rate": fully_correct_count / n,
        "failure_stage_counts": {
            stage.value: stage_counts.get(stage.value, 0)
            for stage in FailureStage
        },
    }
