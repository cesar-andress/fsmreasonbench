"""Transcript recording and deterministic rescore."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fsmreasonbench.evaluator.models import SCORER_VERSION, ScoringRecord, Transcript
from fsmreasonbench.evaluator.parser import parse_submission
from fsmreasonbench.evaluator.scorer import score_item, score_parsed_submission
from fsmreasonbench.items.assembly import BenchmarkItem

TRANSCRIPT_VERSION = "1.0"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def record_transcript(
    item: BenchmarkItem,
    raw_response: Any,
    *,
    timestamp: str | None = None,
) -> Transcript:
    """Parse, score, and record a full evaluation transcript."""
    parse_result = parse_submission(raw_response, item.family)
    scoring = score_item(item, raw_response)
    parsed_dict = None
    if parse_result.extractable and parse_result.submission is not None:
        submission = parse_result.submission
        parsed_dict = {
            "item_id": submission.item_id,
            "verdict": submission.verdict,
            "certificate": submission.certificate,
        }

    return Transcript(
        transcript_version=TRANSCRIPT_VERSION,
        scorer_version=SCORER_VERSION,
        timestamp=timestamp or utc_timestamp(),
        item=item.to_full_dict(),
        raw_response=raw_response,
        parsed_submission=parsed_dict,
        scoring_record=scoring,
    )


def rescore_transcript(transcript: Transcript) -> ScoringRecord:
    """
    Deterministically recompute scoring from a saved transcript.

    Uses parsed_submission when present; otherwise reparses raw_response.
    """
    item = _item_from_transcript(transcript)
    if transcript.parsed_submission is not None:
        from fsmreasonbench.evaluator.models import ParsedSubmission

        submission = ParsedSubmission(
            item_id=transcript.parsed_submission["item_id"],
            verdict=transcript.parsed_submission["verdict"],
            certificate=transcript.parsed_submission["certificate"],
        )
        return score_parsed_submission(item, submission)
    return score_item(item, transcript.raw_response)


def _item_from_transcript(transcript: Transcript) -> BenchmarkItem:
    from fsmreasonbench.evaluator.io import item_from_dict

    return item_from_dict(transcript.item)
