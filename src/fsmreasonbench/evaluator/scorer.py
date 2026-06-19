"""Family-aware benchmark scoring."""

from __future__ import annotations

from fsmreasonbench.evaluator.models import (
    FailureStage,
    ParsedSubmission,
    ScoringRecord,
)
from fsmreasonbench.evaluator.parser import parse_submission
from fsmreasonbench.evaluator.scorer_c2 import score_c2_item, score_c2_parsed
from fsmreasonbench.evaluator.scorer_f1 import score_f1_item, score_f1_parsed
from fsmreasonbench.items.assembly import BenchmarkItem


__all__ = [
    "score_item",
    "score_parsed_submission",
    "score_c2_item",
    "score_c2_parsed",
    "score_f1_item",
    "score_f1_parsed",
]


def score_item(item: BenchmarkItem, raw_response: object) -> ScoringRecord:
    """Score a raw model response against a benchmark item."""
    if item.family == "C2":
        return score_c2_item(item, raw_response)
    if item.family == "F1":
        return score_f1_item(item, raw_response)
    parse_result = parse_submission(raw_response, item.family)
    return ScoringRecord(
        item_id=item.item_id,
        family=item.family,
        extractable=False,
        verdict_correct=None,
        certificate_valid=None,
        fully_correct=False,
        failure_stage=FailureStage.NOT_EXTRACTABLE,
        parse_errors=parse_result.errors or (f"unsupported family: {item.family!r}",),
    )


def score_parsed_submission(item: BenchmarkItem, submission: ParsedSubmission) -> ScoringRecord:
    """Score an already parsed submission."""
    if item.family == "C2":
        return score_c2_parsed(item, submission)
    if item.family == "F1":
        return score_f1_parsed(item, submission)
    return ScoringRecord(
        item_id=item.item_id,
        family=item.family,
        extractable=False,
        verdict_correct=None,
        certificate_valid=None,
        fully_correct=False,
        failure_stage=FailureStage.NOT_EXTRACTABLE,
        parse_errors=(f"unsupported family: {item.family!r}",),
    )
