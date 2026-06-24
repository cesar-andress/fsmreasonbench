"""Deterministic replay of track audit logs."""

from __future__ import annotations

from typing import Any

from fsmreasonbench.models.fsm import ExecutableFSM
from fsmreasonbench.tracks.audit import AuditLogBuilder
from fsmreasonbench.tracks.models import AuditLog, ToolInvocation, TrackId
from fsmreasonbench.tracks.solver_tools import SolverToolRegistry
from fsmreasonbench.tracks.step_simulator import StepSimulator


class ReplayMismatchError(ValueError):
    """Raised when replayed tool output differs from logged output."""


def replay_tool_invocation(
    invocation: ToolInvocation,
    *,
    fsm_by_id: dict[str, ExecutableFSM],
    audit: AuditLogBuilder,
) -> dict[str, Any]:
    """Re-execute one logged tool call and return fresh outputs."""
    if invocation.tool_name == "step":
        fsm_id = invocation.inputs["fsm_id"]
        fsm = fsm_by_id[fsm_id]
        simulator = StepSimulator(fsm, audit=audit)
        return simulator.step(invocation.inputs["state"], invocation.inputs["symbol"])

    solvers = SolverToolRegistry(audit=audit)
    if invocation.tool_name == "solver.is_reachable":
        fsm = fsm_by_id[invocation.inputs["fsm_id"]]
        reachable = solvers.is_reachable(fsm, invocation.inputs["target_state"])
        return {"reachable": reachable}

    if invocation.tool_name == "solver.reachability_certificate":
        fsm = fsm_by_id[invocation.inputs["fsm_id"]]
        certificate = solvers.reachability_certificate(
            fsm,
            invocation.inputs["target_state"],
        )
        return {
            "certificate_type": certificate["certificate_type"],
            "verdict_supported": certificate["verdict_supported"],
        }

    if invocation.tool_name == "solver.check_separation":
        fsm_a = fsm_by_id[invocation.inputs["fsm_id_a"]]
        fsm_b = fsm_by_id[invocation.inputs["fsm_id_b"]]
        return solvers.check_separation(fsm_a, fsm_b)

    if invocation.tool_name == "solver.equivalence_certificate":
        fsm_a = fsm_by_id[invocation.inputs["fsm_id_a"]]
        fsm_b = fsm_by_id[invocation.inputs["fsm_id_b"]]
        certificate = solvers.equivalence_certificate(fsm_a, fsm_b)
        return {
            "certificate_type": certificate["certificate_type"],
            "verdict_supported": certificate["verdict_supported"],
        }

    if invocation.tool_name == "solver.distinguishing_certificate":
        fsm_a = fsm_by_id[invocation.inputs["fsm_id_a"]]
        fsm_b = fsm_by_id[invocation.inputs["fsm_id_b"]]
        certificate = solvers.distinguishing_certificate(fsm_a, fsm_b)
        return {
            "certificate_type": certificate["certificate_type"],
            "verdict_supported": certificate["verdict_supported"],
        }

    if invocation.tool_name == "verifier.validate_c2_certificate":
        from fsmreasonbench.verifier.reachability import verify_reachability_certificate

        fsm = fsm_by_id[invocation.inputs["fsm_id"]]
        target_state = invocation.inputs["target_state"]
        certificate = invocation.inputs["certificate"]
        result = verify_reachability_certificate(fsm, target_state, certificate)
        return {"valid": result.valid, "error_count": len(result.errors)}

    if invocation.tool_name == "format.repair_c2_submission":
        from fsmreasonbench.runners.c2_attribution_tools import (
            _execute_repair_c2_submission,
        )

        replay = _execute_repair_c2_submission(
            "replay",
            invocation.tool_name,
            {"submission": invocation.inputs["submission"]},
            audit=audit,
        )
        if replay["status"] != "executed":
            raise ValueError(replay.get("error", "repair replay failed"))
        return {"repaired": True}

    if invocation.tool_name == "verifier.validate_f1_certificate":
        from fsmreasonbench.verifier.separation import verify_f1_certificate

        fsm_a = fsm_by_id[invocation.inputs["fsm_id_a"]]
        fsm_b = fsm_by_id[invocation.inputs["fsm_id_b"]]
        certificate = invocation.inputs["certificate"]
        result = verify_f1_certificate(fsm_a, fsm_b, certificate)
        return {"valid": result.valid, "error_count": len(result.errors)}

    if invocation.tool_name == "format.repair_f1_submission":
        from fsmreasonbench.runners.r2_attribution_tools import (
            _execute_repair_f1_submission,
        )

        replay = _execute_repair_f1_submission(
            "replay",
            invocation.tool_name,
            {"submission": invocation.inputs["submission"]},
            audit=audit,
        )
        if replay["status"] != "executed":
            raise ValueError(replay.get("error", "repair replay failed"))
        return {"repaired": True}

    raise ValueError(f"unsupported replay tool: {invocation.tool_name!r}")


def replay_audit_log(
    audit_log: AuditLog,
    *,
    fsm_by_id: dict[str, ExecutableFSM],
) -> None:
    """
    Replay all tool invocations and verify outputs match the log.

    Raises ReplayMismatchError on divergence.
    """
    replay_audit = AuditLogBuilder(audit_log.track)
    for invocation in audit_log.tool_invocations:
        replayed = replay_tool_invocation(
            invocation,
            fsm_by_id=fsm_by_id,
            audit=replay_audit,
        )
        if replayed != invocation.outputs:
            raise ReplayMismatchError(
                f"sequence={invocation.sequence} tool={invocation.tool_name!r}: "
                f"logged={invocation.outputs!r} replayed={replayed!r}"
            )

    if audit_log.track == TrackId.R0 and audit_log.tool_invocations:
        raise ReplayMismatchError("R0 audit log must not contain tool invocations")
