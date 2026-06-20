"""F2 composition scoring."""

from __future__ import annotations

from typing import Any

from fsmreasonbench.evaluator.f2_parser import parse_f2_response
from fsmreasonbench.evaluator.models import FailureStage, ParsedSubmission, ScoringRecord
from fsmreasonbench.evaluator.scoring_common import score_parsed_with_verifier
from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.verifier.composition import verify_f2_certificate


def score_f2_item(item: BenchmarkItem, raw_response: object) -> ScoringRecord:
    parse_result = parse_f2_response(raw_response)
    if not parse_result.extractable or parse_result.submission is None:
        return _not_extractable(item, parse_result.errors)
    submission = parse_result.submission
    if submission.item_id != item.item_id:
        return _item_id_mismatch(item, submission.item_id)
    return _score_parsed_submission(item, submission, parse_errors=parse_result.errors)


def score_f2_parsed(item: BenchmarkItem, submission: ParsedSubmission) -> ScoringRecord:
    if submission.item_id != item.item_id:
        return _item_id_mismatch(item, submission.item_id)
    return _score_parsed_submission(item, submission)


def _score_parsed_submission(
    item: BenchmarkItem,
    submission: ParsedSubmission,
    *,
    parse_errors: tuple[str, ...] = (),
) -> ScoringRecord:
    if item.fsm_b is None:
        return ScoringRecord(
            item_id=item.item_id,
            family=item.family,
            extractable=False,
            verdict_correct=None,
            certificate_valid=None,
            fully_correct=False,
            failure_stage=FailureStage.NOT_EXTRACTABLE,
            parse_errors=("F2 item missing fsm_b",),
        )

    def verify(_item: BenchmarkItem, certificate: dict[str, Any]) -> tuple[bool, tuple[str, ...]]:
        result = verify_f2_certificate(
            _item.fsm_a,
            _item.fsm_b,
            _item.question,
            certificate,
        )
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
