"""Shared scoring for runner/provider infrastructure failures."""

from __future__ import annotations

from typing import Any

from fsmreasonbench.evaluator.models import FailureStage, ScoringRecord
from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.runners.provider_errors import infer_provider_error_from_message

PROVIDER_QUOTA_ERROR_TYPES = frozenset({"quota_exceeded", "rate_limit", "insufficient_credit"})


def reclassify_provider_error_scoring_row(row: dict[str, Any]) -> bool:
    """Rewrite a misclassified not_extractable row when parse_errors are provider/API failures."""
    if row.get("infrastructure_failure"):
        return False
    if row.get("failure_stage") != "not_extractable":
        return False
    parse_errors = row.get("parse_errors") or ()
    if not parse_errors:
        return False
    message = str(parse_errors[0])
    classification = infer_provider_error_from_message(message)
    if classification is None:
        return False
    row["failure_stage"] = "provider_error"
    row["extractable"] = False
    row["verdict_correct"] = None
    row["certificate_valid"] = None
    row["fully_correct"] = False
    row["infrastructure_failure"] = True
    row["provider_error_type"] = classification.provider_error_type
    if classification.http_status is not None:
        row["provider_http_status"] = classification.http_status
    row["track_failure_class"] = "provider_error"
    return True


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
    provider_rate_limit_count = 0
    provider_insufficient_credit_count = 0
    for row in scoring_rows:
        if not row.get("infrastructure_failure"):
            continue
        provider_error_count += 1
        error_type = row.get("provider_error_type")
        if error_type == "rate_limit":
            provider_rate_limit_count += 1
        elif error_type == "insufficient_credit":
            provider_insufficient_credit_count += 1
        if error_type in PROVIDER_QUOTA_ERROR_TYPES:
            provider_quota_error_count += 1
    return {
        "provider_error_count": provider_error_count,
        "provider_quota_error_count": provider_quota_error_count,
        "provider_rate_limit_count": provider_rate_limit_count,
        "provider_insufficient_credit_count": provider_insufficient_credit_count,
    }
