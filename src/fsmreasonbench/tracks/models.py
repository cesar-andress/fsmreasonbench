"""Track evaluation data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from fsmreasonbench.evaluator.models import ScoringRecord

TRACKS_VERSION = "1.0"


class TrackId(str, Enum):
    R0 = "R0"
    R1 = "R1"
    R2 = "R2"


@dataclass(frozen=True, slots=True)
class ScratchpadEntry:
    phase: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "message": self.message,
            "details": self.details,
        }


@dataclass(frozen=True, slots=True)
class ToolInvocation:
    sequence: int
    tool_name: str
    tool_version: str
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    provenance: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "tool_name": self.tool_name,
            "tool_version": self.tool_version,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "provenance": self.provenance,
        }


@dataclass(frozen=True, slots=True)
class AuditLog:
    track: TrackId
    track_version: str
    scratchpad: tuple[ScratchpadEntry, ...]
    tool_invocations: tuple[ToolInvocation, ...]
    certificate_assembly: tuple[ScratchpadEntry, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "track": self.track.value,
            "track_version": self.track_version,
            "scratchpad": [entry.to_dict() for entry in self.scratchpad],
            "tool_invocations": [inv.to_dict() for inv in self.tool_invocations],
            "certificate_assembly": [
                entry.to_dict() for entry in self.certificate_assembly
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuditLog:
        return cls(
            track=TrackId(data["track"]),
            track_version=data["track_version"],
            scratchpad=tuple(
                ScratchpadEntry(
                    phase=e["phase"],
                    message=e["message"],
                    details=e.get("details", {}),
                )
                for e in data.get("scratchpad", [])
            ),
            tool_invocations=tuple(
                ToolInvocation(
                    sequence=inv["sequence"],
                    tool_name=inv["tool_name"],
                    tool_version=inv["tool_version"],
                    inputs=inv["inputs"],
                    outputs=inv["outputs"],
                    provenance=inv["provenance"],
                )
                for inv in data.get("tool_invocations", [])
            ),
            certificate_assembly=tuple(
                ScratchpadEntry(
                    phase=e["phase"],
                    message=e["message"],
                    details=e.get("details", {}),
                )
                for e in data.get("certificate_assembly", [])
            ),
        )


@dataclass(frozen=True, slots=True)
class TrackRunResult:
    track: TrackId
    raw_response: str
    audit_log: AuditLog
    scoring_record: ScoringRecord

    def to_dict(self) -> dict[str, Any]:
        return {
            "track": self.track.value,
            "raw_response": self.raw_response,
            "audit_log": self.audit_log.to_dict(),
            "scoring_record": self.scoring_record.to_dict(),
            "tool_invocation_count": len(self.audit_log.tool_invocations),
        }


@dataclass(frozen=True, slots=True)
class TrackScoringRecord:
    """Scoring record with track metadata; backward compatible via nested scoring_record."""

    track: TrackId
    scoring_record: ScoringRecord
    audit_log: AuditLog

    def to_dict(self) -> dict[str, Any]:
        payload = self.scoring_record.to_dict()
        payload["track"] = self.track.value
        payload["tool_invocation_count"] = len(self.audit_log.tool_invocations)
        payload["audit_log"] = self.audit_log.to_dict()
        return payload
