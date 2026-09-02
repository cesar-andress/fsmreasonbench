"""T3 verifier budget and silent first-proposal witness audit."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from fsmreasonbench.clean_v2.condition import ContractId
from fsmreasonbench.clean_v2.confirmatory.constants import MAX_VERIFIER_CALLS
from fsmreasonbench.clean_v2.contracts import verify_certificate_for_contract
from fsmreasonbench.clean_v2.tools.verify_feedback import coarse_validate_certificate
from fsmreasonbench.items.assembly import BenchmarkItem

VERIFIER_TOOL = "verifier.validate_certificate_coarse"


def is_complete_certificate_proposal(obj: Any) -> bool:
    """A complete witness proposal is a dict with certificate_type and payload object."""
    if not isinstance(obj, dict):
        return False
    if not isinstance(obj.get("certificate_type"), str) or not obj["certificate_type"]:
        return False
    if not isinstance(obj.get("payload"), dict):
        return False
    return True


def silent_witness_valid(
    item: BenchmarkItem,
    certificate: dict[str, Any],
    *,
    contract: ContractId,
) -> bool:
    """
    Evaluator-only validity check.

    Must never write into model-visible messages, tool outputs, or tool state.
    """
    if item.fsm_b is None:
        return False
    # Deep-copy so accidental mutation cannot leak into model state.
    cert = deepcopy(certificate)
    result = verify_certificate_for_contract(item.fsm_a, item.fsm_b, cert, contract=contract)
    return bool(result.valid)


def extract_ordered_complete_proposals(
    tool_calls: list[dict[str, Any]],
    final_certificate: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Ordered complete witness proposals (tool inputs first, then final submission)."""
    proposals: list[dict[str, Any]] = []
    for idx, call in enumerate(tool_calls):
        if call.get("tool") != VERIFIER_TOOL:
            continue
        inputs = call.get("inputs")
        if not isinstance(inputs, dict):
            continue
        cert = inputs.get("certificate")
        if is_complete_certificate_proposal(cert):
            proposals.append(
                {
                    "order": len(proposals) + 1,
                    "source": "tool_call",
                    "tool_call_index": idx,
                    "call_id": call.get("call_id"),
                    "certificate": deepcopy(cert),
                }
            )
    if is_complete_certificate_proposal(final_certificate):
        proposals.append(
            {
                "order": len(proposals) + 1,
                "source": "final_submission",
                "tool_call_index": None,
                "call_id": None,
                "certificate": deepcopy(final_certificate),
            }
        )
    return proposals


def compute_witness_valid_first(
    item: BenchmarkItem,
    *,
    contract: ContractId,
    tool_calls: list[dict[str, Any]],
    final_certificate: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Compute witness_valid_first without altering evaluatee-visible state.

    Returns evaluator-only audit fields. Callers must not inject these into
    model context.
    """
    proposals = extract_ordered_complete_proposals(tool_calls, final_certificate)
    if not proposals:
        return {
            "witness_valid_first": None,
            "first_proposal_present": False,
            "first_proposal_source": None,
            "first_proposal_order": None,
            "proposal_count": 0,
            "proposals_meta": [],
        }
    first = proposals[0]
    valid = silent_witness_valid(item, first["certificate"], contract=contract)
    # Do not attach certificates to returned meta for exports that might leak;
    # store only structural pointers.
    meta = [
        {
            "order": p["order"],
            "source": p["source"],
            "tool_call_index": p["tool_call_index"],
            "call_id": p["call_id"],
        }
        for p in proposals
    ]
    return {
        "witness_valid_first": valid,
        "first_proposal_present": True,
        "first_proposal_source": first["source"],
        "first_proposal_order": first["order"],
        "proposal_count": len(proposals),
        "proposals_meta": meta,
        # Full first/final certs kept for offline audit only when requested.
        "_audit_first_certificate": first["certificate"],
        "_audit_final_certificate": deepcopy(final_certificate) if final_certificate else None,
    }


def apply_verifier_call_budget(
    item: BenchmarkItem,
    tool_calls: list[dict[str, Any]],
    *,
    contract: ContractId,
    max_verifier_calls: int = MAX_VERIFIER_CALLS,
    execute_coarse: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Execute verifier calls with a hard cap; record coarse responses and budget.

    Non-verifier tools are left for the main executor; this helper only
    processes verifier calls when used standalone in tests. Production path
    uses execute_clean_tool_plan with max_verifier_calls.
    """
    del execute_coarse  # always execute coarse for accepted calls under budget
    outputs: list[dict[str, Any]] = []
    coarse_log: list[dict[str, Any]] = []
    verifier_call_count = 0
    cap_reached = False
    for order, call in enumerate(tool_calls, start=1):
        call_id = str(call.get("call_id", order))
        tool = call.get("tool")
        inputs = call.get("inputs") if isinstance(call.get("inputs"), dict) else {}
        if tool != VERIFIER_TOOL:
            continue
        if verifier_call_count >= max_verifier_calls:
            cap_reached = True
            outputs.append(
                {
                    "call_id": call_id,
                    "tool": tool,
                    "status": "rejected",
                    "error": "max_verifier_calls_exhausted",
                    "proposal_order": order,
                }
            )
            coarse_log.append(
                {
                    "proposal_order": order,
                    "call_id": call_id,
                    "status": "rejected",
                    "code": "max_verifier_calls_exhausted",
                    "counted_toward_budget": False,
                }
            )
            continue
        certificate = inputs.get("certificate")
        if not isinstance(certificate, dict):
            outputs.append(
                {
                    "call_id": call_id,
                    "tool": tool,
                    "status": "rejected",
                    "error": "certificate must be an object",
                    "proposal_order": order,
                }
            )
            continue
        coarse = coarse_validate_certificate(item, certificate, contract=contract)
        verifier_call_count += 1
        if verifier_call_count >= max_verifier_calls:
            cap_reached = True
        row = {
            "call_id": call_id,
            "tool": tool,
            "status": "executed",
            "outputs": coarse,
            "proposal_order": order,
            "verifier_call_index": verifier_call_count,
        }
        outputs.append(row)
        coarse_log.append(
            {
                "proposal_order": order,
                "call_id": call_id,
                "status": coarse.get("status"),
                "code": coarse.get("code"),
                "counted_toward_budget": True,
                "verifier_call_index": verifier_call_count,
            }
        )
    audit = {
        "max_verifier_calls": max_verifier_calls,
        "verifier_call_count": verifier_call_count,
        "verifier_call_cap_reached": cap_reached,
        "coarse_verifier_responses": coarse_log,
    }
    return outputs, audit


def strip_silent_audit_for_model_export(audit: dict[str, Any]) -> dict[str, Any]:
    """Remove private certificate bodies before any model-adjacent export."""
    return {k: v for k, v in audit.items() if not str(k).startswith("_audit_")}
