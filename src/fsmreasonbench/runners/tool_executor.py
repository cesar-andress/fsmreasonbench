"""Execute LLM-requested track tool calls."""

from __future__ import annotations

from typing import Any

from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.tracks.audit import AuditLogBuilder
from fsmreasonbench.tracks.models import TrackId
from fsmreasonbench.tracks.solver_tools import REGISTERED_TOOL_NAMES, SolverToolRegistry
from fsmreasonbench.tracks.step_simulator import StepSimulator

R1_ALLOWED_TOOLS: frozenset[str] = frozenset({"step"})
MAX_TOOL_CALLS_PER_ROUND = 64


def _fsm_index(item: BenchmarkItem) -> dict[str, Any]:
    index = {item.fsm.fsm_id: item.fsm}
    if item.fsm_b is not None:
        index[item.fsm_b.fsm_id] = item.fsm_b
    return index


def execute_tool_plan(
    item: BenchmarkItem,
    track: TrackId,
    tool_calls: list[dict[str, Any]],
    audit: AuditLogBuilder,
) -> list[dict[str, Any]]:
    """Execute or reject tool calls; return per-call results for phase-2 prompt."""
    if len(tool_calls) > MAX_TOOL_CALLS_PER_ROUND:
        raise ValueError(f"tool plan exceeds max calls ({MAX_TOOL_CALLS_PER_ROUND})")

    allowed = R1_ALLOWED_TOOLS if track == TrackId.R1 else REGISTERED_TOOL_NAMES
    fsm_by_id = _fsm_index(item)
    results: list[dict[str, Any]] = []

    if track == TrackId.R1:
        simulators = {fsm_id: StepSimulator(fsm, audit=audit) for fsm_id, fsm in fsm_by_id.items()}
        for call in tool_calls:
            results.append(_execute_r1_call(call, allowed, simulators))
        return results

    if track == TrackId.R2:
        solvers = SolverToolRegistry(audit=audit)
        for call in tool_calls:
            results.append(_execute_r2_call(call, allowed, item, fsm_by_id, solvers))
        return results

    raise ValueError(f"track {track.value} does not support tool execution")


def _execute_r1_call(
    call: dict[str, Any],
    allowed: frozenset[str],
    simulators: dict[str, StepSimulator],
) -> dict[str, Any]:
    call_id = call["call_id"]
    tool = call["tool"]
    inputs = call["inputs"]
    if tool not in allowed:
        return {
            "call_id": call_id,
            "tool": tool,
            "status": "rejected",
            "error": f"tool {tool!r} not allowed on R1",
        }
    fsm_id = inputs.get("fsm_id")
    state = inputs.get("state")
    symbol = inputs.get("symbol")
    if not isinstance(fsm_id, str) or fsm_id not in simulators:
        return {
            "call_id": call_id,
            "tool": tool,
            "status": "rejected",
            "error": f"unknown fsm_id {fsm_id!r}",
        }
    if not isinstance(state, str) or not isinstance(symbol, str):
        return {
            "call_id": call_id,
            "tool": tool,
            "status": "rejected",
            "error": "state and symbol must be strings",
        }
    outputs = simulators[fsm_id].step(state, symbol)
    return {
        "call_id": call_id,
        "tool": tool,
        "status": "executed",
        "outputs": outputs,
    }


def _execute_r2_call(
    call: dict[str, Any],
    allowed: frozenset[str],
    item: BenchmarkItem,
    fsm_by_id: dict[str, Any],
    solvers: SolverToolRegistry,
) -> dict[str, Any]:
    call_id = call["call_id"]
    tool = call["tool"]
    inputs = call["inputs"]
    if tool not in allowed:
        return {
            "call_id": call_id,
            "tool": tool,
            "status": "rejected",
            "error": f"tool {tool!r} not registered for R2",
        }

    try:
        if tool == "solver.is_reachable":
            fsm = fsm_by_id[inputs["fsm_id"]]
            outputs = {"reachable": solvers.is_reachable(fsm, inputs["target_state"])}
        elif tool == "solver.reachability_certificate":
            fsm = fsm_by_id[inputs["fsm_id"]]
            certificate = solvers.reachability_certificate(fsm, inputs["target_state"])
            outputs = {
                "certificate_type": certificate["certificate_type"],
                "verdict_supported": certificate["verdict_supported"],
                "certificate": certificate,
            }
        elif tool == "solver.check_separation":
            fsm_a = fsm_by_id[inputs["fsm_id_a"]]
            fsm_b = fsm_by_id[inputs["fsm_id_b"]]
            outputs = solvers.check_separation(fsm_a, fsm_b)
        elif tool == "solver.equivalence_certificate":
            fsm_a = fsm_by_id[inputs["fsm_id_a"]]
            fsm_b = fsm_by_id[inputs["fsm_id_b"]]
            certificate = solvers.equivalence_certificate(fsm_a, fsm_b)
            outputs = {
                "certificate_type": certificate["certificate_type"],
                "certificate": certificate,
            }
        elif tool == "solver.distinguishing_certificate":
            fsm_a = fsm_by_id[inputs["fsm_id_a"]]
            fsm_b = fsm_by_id[inputs["fsm_id_b"]]
            certificate = solvers.distinguishing_certificate(fsm_a, fsm_b)
            outputs = {
                "certificate_type": certificate["certificate_type"],
                "certificate": certificate,
            }
        else:
            return {
                "call_id": call_id,
                "tool": tool,
                "status": "rejected",
                "error": f"unsupported registered tool {tool!r}",
            }
    except KeyError as exc:
        return {
            "call_id": call_id,
            "tool": tool,
            "status": "rejected",
            "error": f"missing or invalid input field: {exc}",
        }
    except (TypeError, ValueError) as exc:
        return {
            "call_id": call_id,
            "tool": tool,
            "status": "rejected",
            "error": str(exc),
        }

    return {
        "call_id": call_id,
        "tool": tool,
        "status": "executed",
        "outputs": outputs,
    }
