"""Audit log builder for track evaluation."""

from __future__ import annotations

from typing import Any

from fsmreasonbench.tracks.models import (
    AuditLog,
    ScratchpadEntry,
    ToolInvocation,
    TrackId,
    TRACKS_VERSION,
)


class AuditLogBuilder:
    """Collect scratchpad entries and tool invocations during a track run."""

    def __init__(self, track: TrackId) -> None:
        self._track = track
        self._scratchpad: list[ScratchpadEntry] = []
        self._tool_invocations: list[ToolInvocation] = []
        self._certificate_assembly: list[ScratchpadEntry] = []
        self._sequence = 0

    def scratchpad(
        self,
        phase: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self._scratchpad.append(
            ScratchpadEntry(phase=phase, message=message, details=details or {})
        )

    def certificate_step(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self._certificate_assembly.append(
            ScratchpadEntry(
                phase="certificate_assembly",
                message=message,
                details=details or {},
            )
        )

    def record_tool(
        self,
        tool_name: str,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        *,
        tool_version: str = "1.0",
        provenance: str = "tracks",
    ) -> ToolInvocation:
        self._sequence += 1
        invocation = ToolInvocation(
            sequence=self._sequence,
            tool_name=tool_name,
            tool_version=tool_version,
            inputs=inputs,
            outputs=outputs,
            provenance=provenance,
        )
        self._tool_invocations.append(invocation)
        return invocation

    def build(self) -> AuditLog:
        return AuditLog(
            track=self._track,
            track_version=TRACKS_VERSION,
            scratchpad=tuple(self._scratchpad),
            tool_invocations=tuple(self._tool_invocations),
            certificate_assembly=tuple(self._certificate_assembly),
        )
