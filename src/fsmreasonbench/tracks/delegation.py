"""Delegation gap metrics between R2 and R0 track summaries."""

from __future__ import annotations

from typing import Any

DELEGATION_GAP_METRICS: tuple[str, ...] = (
    "verdict_accuracy",
    "certificate_valid_rate",
    "fully_correct_rate",
)


def compute_delegation_gap(
    r0_summary: dict[str, Any],
    r2_summary: dict[str, Any],
) -> dict[str, Any]:
    """
    Compute Δ_R2_R0 = metric(R2) − metric(R0) for primary track metrics.

    Both summaries must share the same ``family`` and ``n`` when present.
    """
    if r0_summary.get("family") != r2_summary.get("family"):
        raise ValueError("delegation gap requires matching family")
    if r0_summary.get("n") != r2_summary.get("n"):
        raise ValueError("delegation gap requires matching n")

    gaps: dict[str, float] = {}
    for metric in DELEGATION_GAP_METRICS:
        if metric not in r0_summary or metric not in r2_summary:
            raise ValueError(f"missing metric for delegation gap: {metric!r}")
        gaps[metric] = r2_summary[metric] - r0_summary[metric]

    return {
        "family": r0_summary.get("family"),
        "cohort_id": r0_summary.get("cohort_id"),
        "n": r0_summary.get("n"),
        "r0_track": r0_summary.get("track", "R0"),
        "r2_track": r2_summary.get("track", "R2"),
        "delegation_gap": gaps,
    }
