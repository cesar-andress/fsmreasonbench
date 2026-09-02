"""Common-denominator metrics for clean_v2 (n_attempted)."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable


PRIMARY_RATE_KEYS = (
    "extractable",
    "verdict_correct",
    "witness_valid",
    "fully_correct",
)


def summarize_attempt_records(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate primary rates over n_attempted with explicit numerators."""
    rows = list(records)
    n_attempted = len(rows)
    extractable_n = sum(1 for row in rows if row.get("extractable") is True)
    verdict_n = sum(1 for row in rows if row.get("verdict_correct") is True)
    witness_n = sum(1 for row in rows if row.get("witness_valid") is True)
    full_n = sum(1 for row in rows if row.get("fully_correct") is True)

    first_failure = Counter(str(row.get("first_failure", "unknown")) for row in rows)

    verdict_correct_rows = [row for row in rows if row.get("verdict_correct") is True]
    extractable_rows = [row for row in rows if row.get("extractable") is True]
    witness_given_verdict_n = sum(
        1 for row in verdict_correct_rows if row.get("witness_valid") is True
    )
    witness_given_extract_n = sum(
        1 for row in extractable_rows if row.get("witness_valid") is True
    )

    def rate(successes: int, denom: int) -> float | None:
        if denom == 0:
            return None
        return successes / denom

    return {
        "metrics_version": "clean_v2.metrics.v1",
        "n_attempted": n_attempted,
        "extractable": {
            "numerator": extractable_n,
            "denominator": n_attempted,
            "rate": rate(extractable_n, n_attempted),
        },
        "verdict_correct": {
            "numerator": verdict_n,
            "denominator": n_attempted,
            "rate": rate(verdict_n, n_attempted),
        },
        "witness_valid": {
            "numerator": witness_n,
            "denominator": n_attempted,
            "rate": rate(witness_n, n_attempted),
        },
        "fully_correct": {
            "numerator": full_n,
            "denominator": n_attempted,
            "rate": rate(full_n, n_attempted),
        },
        "first_failure_counts": dict(first_failure),
        "conditional": {
            "witness_valid_given_verdict_correct": {
                "numerator": witness_given_verdict_n,
                "denominator": len(verdict_correct_rows),
                "rate": rate(witness_given_verdict_n, len(verdict_correct_rows)),
            },
            "witness_valid_given_extractable": {
                "numerator": witness_given_extract_n,
                "denominator": len(extractable_rows),
                "rate": rate(witness_given_extract_n, len(extractable_rows)),
            },
        },
        "deprecated_mixed_gap": {
            "status": "deprecated",
            "message": (
                "clean_v2 does not export Verdict-Full mixed-denominator gap; "
                "use per-item decomposition counts instead"
            ),
        },
        "decomposition_counts": {
            "verdict_true_witness_false": sum(
                1
                for row in rows
                if row.get("verdict_correct") is True and row.get("witness_valid") is not True
            ),
            "verdict_false": sum(1 for row in rows if row.get("verdict_correct") is False),
            "not_extractable": sum(1 for row in rows if row.get("extractable") is not True),
            "fully_correct": full_n,
        },
    }
