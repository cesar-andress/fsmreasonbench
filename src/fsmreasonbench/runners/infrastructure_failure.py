"""Shared scoring for runner/provider infrastructure failures."""

from __future__ import annotations

from typing import Any

from fsmreasonbench.evaluator.models import FailureStage, ScoringRecord
from fsmreasonbench.items.assembly import BenchmarkItem

PROVIDER_QUOTA_ERROR_TYPES = frozenset({"quota_exceeded", "rate_limit"})


def build_infrastructure_scoring_record(
    item: BenchmarkItem,
    *,
    error: str,
    provider_error_type: str,
) -> ScoringRecord:
    """Score a skipped item as provider/infrastructure failure, not model extraction."""
    return ScoringRecord(
        item_id=item.item_id,
        family=item.family,
        extractable=False,
        verdict_correct=None,
        certificate_valid=None,
        fully_correct=False,
        failure_stage=FailureStage.PROVIDER_ERROR,
        parse_errors=(error,),
    )


def enrich_infrastructure_scoring_dict(
    scoring_dict: dict[str, Any],
    *,
    provider_error_type: str,
    http_status: int | None = None,
) -> None:
    scoring_dict["infrastructure_failure"] = True
    scoring_dict["provider_error_type"] = provider_error_type
    if http_status is not None:
        scoring_dict["provider_http_status"] = http_status


def summarize_provider_errors(scoring_rows: list[dict[str, Any]]) -> dict[str, int]:
    provider_error_count = 0
    provider_quota_error_count = 0
    for row in scoring_rows:
        if not row.get("infrastructure_failure"):
            continue
        provider_error_count += 1
        error_type = row.get("provider_error_type")
        if error_type in PROVIDER_QUOTA_ERROR_TYPES:
            provider_quota_error_count += 1
    return {
        "provider_error_count": provider_error_count,
        "provider_quota_error_count": provider_quota_error_count,
    }
