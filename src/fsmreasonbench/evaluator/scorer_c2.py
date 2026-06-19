"""C2 reachability scoring."""

from __future__ import annotations

from fsmreasonbench.evaluator.models import (
    FailureStage,
    ParsedSubmission,
    ScoringRecord,
)
from fsmreasonbench.evaluator.parser import parse_c2_response
from fsmreasonbench.evaluator.scoring_common import score_parsed_with_verifier
from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.verifier.reachability import verify_reachability_certificate


def score_c2_item(item: BenchmarkItem, raw_response: object) -> ScoringRecord:
    """Score a raw model response against a C2 benchmark item."""
    parse_result = parse_c2_response(raw_response)
    if not parse_result.extractable or parse_result.submission is None:
        return _not_extractable(item, parse_result.errors)

    submission = parse_result.submission
    if submission.item_id != item.item_id:
        return _item_id_mismatch(item, submission.item_id)

    return _score_parsed_submission(item, submission, parse_errors=parse_result.errors)


def score_c2_parsed(item: BenchmarkItem, submission: ParsedSubmission) -> ScoringRecord:
    """Score an already parsed C2 submission."""
    if submission.item_id != item.item_id:
        return _item_id_mismatch(item, submission.item_id)
    return _score_parsed_submission(item, submission)


def _score_parsed_submission(
    item: BenchmarkItem,
    submission: ParsedSubmission,
    *,
    parse_errors: tuple[str, ...] = (),
) -> ScoringRecord:
    target_state = item.question["target_state"]

    def verify(_item: BenchmarkItem, certificate: dict) -> tuple[bool, tuple[str, ...]]:
        result = verify_reachability_certificate(_item.fsm, target_state, certificate)
        return result.valid, result.errors

    return score_parsed_with_verifier(
        item,
        submission,
        expected_verdict=item.answer_key["verdict"],
        verify=verify,
        parse_errors=parse_errors,
    )


def _not_extractable(item: BenchmarkItem, errors: tuple[str, ...]) -> ScoringRecord:
    return ScoringRecord(
        item_id=item.item_id,
        family=item.family,
        extractable=False,
        verdict_correct=None,
        certificate_valid=None,
        fully_correct=False,
        failure_stage=FailureStage.NOT_EXTRACTABLE,
        parse_errors=errors,
    )


def _item_id_mismatch(item: BenchmarkItem, got: str) -> ScoringRecord:
    return ScoringRecord(
        item_id=item.item_id,
        family=item.family,
        extractable=False,
        verdict_correct=None,
        certificate_valid=None,
        fully_correct=False,
        failure_stage=FailureStage.NOT_EXTRACTABLE,
        parse_errors=(f"item_id mismatch: expected {item.item_id}, got {got}",),
    )
