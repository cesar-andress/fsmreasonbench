"""Tool execution for clean_v2 causal palettes."""

from __future__ import annotations

from typing import Any

from fsmreasonbench.clean_v2.condition import ContractId, ToolPaletteId
from fsmreasonbench.clean_v2.confirmatory.constants import MAX_VERIFIER_CALLS
from fsmreasonbench.clean_v2.tools.palettes import FORBIDDEN_CAUSAL_TOOLS, tools_for_palette
from fsmreasonbench.clean_v2.tools.verify_feedback import coarse_validate_certificate
from fsmreasonbench.clean_v2.views import EvaluateeView
from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.models.fsm import ExecutableFSM
from fsmreasonbench.tracks.step_simulator import StepSimulator

VERIFIER_TOOL = "verifier.validate_certificate_coarse"


def _fsm_index(item: BenchmarkItem) -> dict[str, ExecutableFSM]:
    index = {item.fsm_a.fsm_id: item.fsm_a}
    if item.fsm_b is not None:
        index[item.fsm_b.fsm_id] = item.fsm_b
    return index


def execute_clean_tool_plan(
    item: BenchmarkItem,
    evaluatee: EvaluateeView,
    tool_calls: list[dict[str, Any]],
    *,
    palette: ToolPaletteId,
    contract: ContractId,
    tool_call_budget: int = 64,
    max_verifier_calls: int = MAX_VERIFIER_CALLS,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Execute model-requested tools under a causal palette (no builders).

    Returns (results, tool_audit). Verifier calls are capped at max_verifier_calls=3.
    """
    del evaluatee  # evaluatee is the only FSM surface used for ids; FSMs come from item.
    allowed = tools_for_palette(palette)
    if len(tool_calls) > tool_call_budget:
        raise ValueError(f"tool plan exceeds budget ({tool_call_budget})")
    fsm_by_id = _fsm_index(item)
    # StepSimulator requires AuditLogBuilder — use a lightweight shim.
    from fsmreasonbench.tracks.audit import AuditLogBuilder
    from fsmreasonbench.tracks.models import TrackId

    audit_log = AuditLogBuilder(TrackId.R1)
    simulators = {fsm_id: StepSimulator(fsm, audit=audit_log) for fsm_id, fsm in fsm_by_id.items()}

    results: list[dict[str, Any]] = []
    coarse_log: list[dict[str, Any]] = []
    verifier_call_count = 0
    cap_reached = False
    proposal_order = 0

    for call in tool_calls:
        call_id = str(call.get("call_id", len(results) + 1))
        tool = call.get("tool")
        inputs = call.get("inputs")
        if not isinstance(tool, str) or not isinstance(inputs, dict):
            results.append(
                {
                    "call_id": call_id,
                    "tool": tool,
                    "status": "rejected",
                    "error": "invalid tool call shape",
                }
            )
            continue
        if tool in FORBIDDEN_CAUSAL_TOOLS:
            results.append(
                {
                    "call_id": call_id,
                    "tool": tool,
                    "status": "rejected",
                    "error": "tool forbidden on clean_v2 causal palettes",
                }
            )
            continue
        if tool not in allowed:
            results.append(
                {
                    "call_id": call_id,
                    "tool": tool,
                    "status": "rejected",
                    "error": f"tool not allowed in palette {palette.value}",
                }
            )
            continue
        if tool == "step":
            fsm_id = inputs.get("fsm_id")
            state = inputs.get("state")
            symbol = inputs.get("symbol")
            if fsm_id not in simulators:
                results.append(
                    {
                        "call_id": call_id,
                        "tool": tool,
                        "status": "rejected",
                        "error": "unknown fsm_id",
                    }
                )
                continue
            outputs = simulators[fsm_id].step(str(state), str(symbol))
            results.append(
                {
                    "call_id": call_id,
                    "tool": tool,
                    "status": "executed",
                    "outputs": outputs,
                }
            )
            continue
        if tool == VERIFIER_TOOL:
            proposal_order += 1
            if verifier_call_count >= max_verifier_calls:
                cap_reached = True
                results.append(
                    {
                        "call_id": call_id,
                        "tool": tool,
                        "status": "rejected",
                        "error": "max_verifier_calls_exhausted",
                        "proposal_order": proposal_order,
                    }
                )
                coarse_log.append(
                    {
                        "proposal_order": proposal_order,
                        "call_id": call_id,
                        "status": "rejected",
                        "code": "max_verifier_calls_exhausted",
                        "counted_toward_budget": False,
                    }
                )
                continue
            certificate = inputs.get("certificate")
            if not isinstance(certificate, dict):
                results.append(
                    {
                        "call_id": call_id,
                        "tool": tool,
                        "status": "rejected",
                        "error": "certificate must be an object",
                        "proposal_order": proposal_order,
                    }
                )
                continue
            coarse = coarse_validate_certificate(item, certificate, contract=contract)
            verifier_call_count += 1
            if verifier_call_count >= max_verifier_calls:
                cap_reached = True
            results.append(
                {
                    "call_id": call_id,
                    "tool": tool,
                    "status": "executed",
                    "outputs": coarse,
                    "proposal_order": proposal_order,
                    "verifier_call_index": verifier_call_count,
                }
            )
            coarse_log.append(
                {
                    "proposal_order": proposal_order,
                    "call_id": call_id,
                    "status": coarse.get("status"),
                    "code": coarse.get("code"),
                    "counted_toward_budget": True,
                    "verifier_call_index": verifier_call_count,
                }
            )
            continue
        results.append(
            {
                "call_id": call_id,
                "tool": tool,
                "status": "rejected",
                "error": "unsupported tool",
            }
        )
    tool_audit = {
        "max_verifier_calls": max_verifier_calls,
        "verifier_call_count": verifier_call_count,
        "verifier_call_cap_reached": cap_reached,
        "coarse_verifier_responses": coarse_log,
    }
    return results, tool_audit

