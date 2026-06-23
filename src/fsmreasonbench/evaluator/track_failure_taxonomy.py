"""Track failure taxonomy for LLM evaluation runs."""

from __future__ import annotations

from typing import Any

TRACK_FAILURE_CLASSES: tuple[str, ...] = (
    "no_tool_plan",
    "invalid_tool_plan",
    "disallowed_tool",
    "tool_execution_error",
    "provider_error",
    "final_submission_not_extractable",
    "verdict_wrong",
    "certificate_invalid",
    "correct",
)


def _empty_counts() -> dict[str, int]:
    return {label: 0 for label in TRACK_FAILURE_CLASSES}


def classify_track_failure(
    *,
    track: str,
    scoring_record: dict[str, Any],
    tool_calls_requested: list[dict[str, Any]] | None = None,
    tool_outputs: list[dict[str, Any]] | None = None,
    tool_plan_valid: bool = True,
    tool_execution_error: str | None = None,
) -> str:
    """
    Assign a single primary failure class per item.

    Tool-phase classes apply only to R1/R2. R0 skips directly to submission outcomes.
    """
    if scoring_record.get("fully_correct"):
        return "correct"

    if scoring_record.get("infrastructure_failure"):
        return "provider_error"

    if track in {"R1", "R2"}:
        requested = tool_calls_requested or []
        outputs = tool_outputs or []

        if tool_execution_error:
            return "tool_execution_error"

        if not tool_plan_valid:
            return "invalid_tool_plan"

        if not requested:
            return "no_tool_plan"

        executed = [row for row in outputs if row.get("status") == "executed"]
        rejected = [row for row in outputs if row.get("status") == "rejected"]
        if requested and not executed and rejected:
            return "disallowed_tool"

    if not scoring_record.get("extractable"):
        return "final_submission_not_extractable"

    failure_stage = scoring_record.get("failure_stage")
    if failure_stage == "verdict_wrong":
        return "verdict_wrong"
    if failure_stage == "certificate_invalid":
        return "certificate_invalid"

    return "final_submission_not_extractable"


def aggregate_track_failure_counts(
    records: list[dict[str, Any]],
) -> dict[str, int]:
    counts = _empty_counts()
    for record in records:
        label = record.get("track_failure_class")
        if label not in counts:
            raise ValueError(f"unknown track_failure_class: {label!r}")
        counts[label] += 1
    return counts


def summarize_track_failure_taxonomy(
    item_records: list[dict[str, Any]],
) -> dict[str, Any]:
    counts = aggregate_track_failure_counts(item_records)
    n = len(item_records)
    rates = {
        f"{label}_rate": (counts[label] / n if n else 0.0)
        for label in TRACK_FAILURE_CLASSES
    }
    return {
        "track_failure_counts": counts,
        "track_failure_rates": rates,
    }
