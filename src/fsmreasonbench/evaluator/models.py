"""Evaluation data models for C2 scoring and transcripts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FailureStage(str, Enum):
    NOT_EXTRACTABLE = "not_extractable"
    VERDICT_WRONG = "verdict_wrong"
    CERTIFICATE_INVALID = "certificate_invalid"
    CORRECT = "correct"


SCORER_VERSION = "0.2.0-dev"


@dataclass(frozen=True, slots=True)
class ParsedSubmission:
    """Extractable C2 submission."""

    item_id: str
    verdict: bool
    certificate: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ParseResult:
    """Outcome of answer parsing."""

    extractable: bool
    submission: ParsedSubmission | None = None
    errors: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class ScoringRecord:
    """Per-item scoring outcome."""

    item_id: str
    family: str
    extractable: bool
    verdict_correct: bool | None
    certificate_valid: bool | None
    fully_correct: bool
    failure_stage: FailureStage
    parse_errors: tuple[str, ...] = field(default_factory=tuple)
    certificate_errors: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "family": self.family,
            "extractable": self.extractable,
            "verdict_correct": self.verdict_correct,
            "certificate_valid": self.certificate_valid,
            "fully_correct": self.fully_correct,
            "failure_stage": self.failure_stage.value,
            "parse_errors": list(self.parse_errors),
            "certificate_errors": list(self.certificate_errors),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScoringRecord:
        return cls(
            item_id=data["item_id"],
            family=data["family"],
            extractable=data["extractable"],
            verdict_correct=data["verdict_correct"],
            certificate_valid=data["certificate_valid"],
            fully_correct=data["fully_correct"],
            failure_stage=FailureStage(data["failure_stage"]),
            parse_errors=tuple(data.get("parse_errors", [])),
            certificate_errors=tuple(data.get("certificate_errors", [])),
        )


@dataclass(frozen=True, slots=True)
class Transcript:
    """Recorded evaluation transcript for deterministic rescore."""

    transcript_version: str
    scorer_version: str
    timestamp: str
    item: dict[str, Any]
    raw_response: Any
    parsed_submission: dict[str, Any] | None
    scoring_record: ScoringRecord

    def to_dict(self) -> dict[str, Any]:
        return {
            "transcript_version": self.transcript_version,
            "scorer_version": self.scorer_version,
            "timestamp": self.timestamp,
            "item": self.item,
            "raw_response": self.raw_response,
            "parsed_submission": self.parsed_submission,
            "scoring_record": self.scoring_record.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Transcript:
        return cls(
            transcript_version=data["transcript_version"],
            scorer_version=data["scorer_version"],
            timestamp=data["timestamp"],
            item=data["item"],
            raw_response=data["raw_response"],
            parsed_submission=data.get("parsed_submission"),
            scoring_record=ScoringRecord.from_dict(data["scoring_record"]),
        )
