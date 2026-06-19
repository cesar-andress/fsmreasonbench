"""Shared scoring logic for family scorers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fsmreasonbench.evaluator.models import FailureStage, ParsedSubmission, ScoringRecord
from fsmreasonbench.items.assembly import BenchmarkItem


def score_parsed_with_verifier(
    item: BenchmarkItem,
    submission: ParsedSubmission,
    *,
    expected_verdict: bool,
    verify: Callable[[BenchmarkItem, dict[str, Any]], tuple[bool, tuple[str, ...]]],
    parse_errors: tuple[str, ...] = (),
) -> ScoringRecord:
    verdict_correct = submission.verdict == expected_verdict
    certificate_valid, certificate_errors = verify(item, submission.certificate)

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
            certificate_errors=certificate_errors,
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
            certificate_errors=certificate_errors,
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
