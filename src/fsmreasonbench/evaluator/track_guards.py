"""Track-specific guard checks on audit logs."""

from __future__ import annotations

from fsmreasonbench.tracks.models import AuditLog, TrackId
from fsmreasonbench.tracks.solver_tools import REGISTERED_TOOL_NAMES
from fsmreasonbench.tracks.step_simulator import STEP_SIMULATOR_VERSION

R1_ALLOWED_TOOLS: frozenset[str] = frozenset({"step"})


def validate_track_audit_log(audit_log: AuditLog) -> None:
    """Raise ValueError when audit log violates track policy."""
    if audit_log.track == TrackId.R0:
        if audit_log.tool_invocations:
            raise ValueError("R0 audit log must not contain tool invocations")
        return

    if audit_log.track == TrackId.R1:
        for invocation in audit_log.tool_invocations:
            if invocation.tool_name not in R1_ALLOWED_TOOLS:
                raise ValueError(
                    f"R1 forbidden tool {invocation.tool_name!r}; "
                    f"allowed: {sorted(R1_ALLOWED_TOOLS)}"
                )
            if invocation.tool_version != STEP_SIMULATOR_VERSION:
                raise ValueError(
                    f"unexpected step simulator version: {invocation.tool_version!r}"
                )
        return

    if audit_log.track == TrackId.R2:
        for invocation in audit_log.tool_invocations:
            if invocation.tool_name not in REGISTERED_TOOL_NAMES:
                raise ValueError(
                    f"R2 unregistered tool {invocation.tool_name!r}; "
                    f"registered: {sorted(REGISTERED_TOOL_NAMES)}"
                )
        return

    raise ValueError(f"unknown track: {audit_log.track!r}")
