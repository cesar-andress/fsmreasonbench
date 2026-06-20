"""Track-aware transcript recording."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fsmreasonbench.evaluator.models import SCORER_VERSION, ScoringRecord
from fsmreasonbench.evaluator.parser import parse_submission
from fsmreasonbench.evaluator.transcript import TRANSCRIPT_VERSION, utc_timestamp
from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.tracks.models import TrackRunResult, TRACKS_VERSION


@dataclass(frozen=True, slots=True)
class TrackTranscript:
    """Transcript extended with track metadata and audit log."""

    transcript_version: str
    tracks_version: str
    scorer_version: str
    timestamp: str
    track: str
    item: dict[str, Any]
    raw_response: Any
    parsed_submission: dict[str, Any] | None
    scoring_record: ScoringRecord
    audit_log: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "transcript_version": self.transcript_version,
            "tracks_version": self.tracks_version,
            "scorer_version": self.scorer_version,
            "timestamp": self.timestamp,
            "track": self.track,
            "item": self.item,
            "raw_response": self.raw_response,
            "parsed_submission": self.parsed_submission,
            "scoring_record": self.scoring_record.to_dict(),
            "audit_log": self.audit_log,
            "tool_invocation_count": len(self.audit_log.get("tool_invocations", [])),
        }


def record_track_transcript(
    item: BenchmarkItem,
    result: TrackRunResult,
    *,
    timestamp: str | None = None,
) -> TrackTranscript:
    parse_result = parse_submission(result.raw_response, item.family)
    parsed_dict = None
    if parse_result.extractable and parse_result.submission is not None:
        submission = parse_result.submission
        parsed_dict = {
            "item_id": submission.item_id,
            "verdict": submission.verdict,
            "certificate": submission.certificate,
        }

    return TrackTranscript(
        transcript_version=TRANSCRIPT_VERSION,
        tracks_version=TRACKS_VERSION,
        scorer_version=SCORER_VERSION,
        timestamp=timestamp or utc_timestamp(),
        track=result.track.value,
        item=item.to_full_dict(),
        raw_response=result.raw_response,
        parsed_submission=parsed_dict,
        scoring_record=result.scoring_record,
        audit_log=result.audit_log.to_dict(),
    )
