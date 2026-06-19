"""C2 reachability scoring."""

from __future__ import annotations

from fsmreasonbench.evaluator.models import (
    FailureStage,
    ParseResult,
    ParsedSubmission,
    ScoringRecord,
)
from fsmreasonbench.evaluator.parser import parse_c2_response
from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.verifier.reachability import verify_reachability_certificate


def score_c2_item(item: BenchmarkItem, raw_response: object) -> ScoringRecord:
    """Score a raw model response against a C2 benchmark item."""
    parse_result = parse_c2_response(raw_response)
    if not parse_result.extractable or parse_result.submission is None:
        return ScoringRecord(
            item_id=item.item_id,
            family=item.family,
            extractable=False,
            verdict_correct=None,
            certificate_valid=None,
            fully_correct=False,
            failure_stage=FailureStage.NOT_EXTRACTABLE,
            parse_errors=parse_result.errors,
        )

    submission = parse_result.submission
    if submission.item_id != item.item_id:
        return ScoringRecord(
            item_id=item.item_id,
            family=item.family,
            extractable=False,
            verdict_correct=None,
            certificate_valid=None,
            fully_correct=False,
            failure_stage=FailureStage.NOT_EXTRACTABLE,
            parse_errors=(f"item_id mismatch: expected {item.item_id}, got {submission.item_id}",),
        )

    return _score_parsed_submission(item, submission, parse_errors=parse_result.errors)


def score_c2_parsed(item: BenchmarkItem, submission: ParsedSubmission) -> ScoringRecord:
    """Score an already parsed C2 submission."""
    if submission.item_id != item.item_id:
        return ScoringRecord(
            item_id=item.item_id,
            family=item.family,
            extractable=False,
            verdict_correct=None,
            certificate_valid=None,
            fully_correct=False,
            failure_stage=FailureStage.NOT_EXTRACTABLE,
            parse_errors=(f"item_id mismatch: expected {item.item_id}, got {submission.item_id}",),
        )
    return _score_parsed_submission(item, submission)


def _score_parsed_submission(
    item: BenchmarkItem,
    submission: ParsedSubmission,
    *,
    parse_errors: tuple[str, ...] = (),
) -> ScoringRecord:
    expected_verdict = item.answer_key["verdict"]
    verdict_correct = submission.verdict == expected_verdict

    target_state = item.question["target_state"]
    verify_result = verify_reachability_certificate(
        item.fsm,
        target_state,
        submission.certificate,
    )
    certificate_valid = verify_result.valid

    if parse_errors:
        return ScoringRecord(
            item_id=item.item_id,
            family=item.family,
            extractable=False,
            verdict_correct=None,
            certificate_valid=None,
            fully_correct=False,
            failure_stage=FailureStage.NOT_EXTRACTABLE,
            parse_errors=parse_errors,
        )

    if not verdict_correct:
        return ScoringRecord(
            item_id=item.item_id,
            family=item.family,
            extractable=True,
            verdict_correct=False,
            certificate_valid=certificate_valid,
            fully_correct=False,
            failure_stage=FailureStage.VERDICT_WRONG,
            certificate_errors=verify_result.errors,
        )

    if not certificate_valid:
        return ScoringRecord(
            item_id=item.item_id,
            family=item.family,
            extractable=True,
            verdict_correct=True,
            certificate_valid=False,
            fully_correct=False,
            failure_stage=FailureStage.CERTIFICATE_INVALID,
            certificate_errors=verify_result.errors,
        )

    return ScoringRecord(
        item_id=item.item_id,
        family=item.family,
        extractable=True,
        verdict_correct=True,
        certificate_valid=True,
        fully_correct=True,
        failure_stage=FailureStage.CORRECT,
    )
