"""C2 R2 attribution ablation tools (verify-only and repair-only)."""

from __future__ import annotations

import json
from typing import Any

from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.runners.response_extract import (
    extract_submission_payload_with_json_repair,
)
from fsmreasonbench.tracks.audit import AuditLogBuilder
from fsmreasonbench.verifier.reachability import verify_reachability_certificate

C2_R2A_VERIFY_TOOL = "verifier.validate_c2_certificate"
C2_R2B_REPAIR_TOOL = "format.repair_c2_submission"

C2_R2A_ALLOWED_TOOLS = frozenset({C2_R2A_VERIFY_TOOL})
C2_R2B_ALLOWED_TOOLS = frozenset({C2_R2B_REPAIR_TOOL})

C2_R2C_ALLOWED_TOOLS = frozenset(
    {
        "solver.is_reachable",
        "solver.reachability_certificate",
    }
)


def execute_c2_attribution_tool(
    item: BenchmarkItem,
    call: dict[str, Any],
    *,
    allowed: frozenset[str],
    audit: AuditLogBuilder,
) -> dict[str, Any]:
    call_id = call["call_id"]
    tool = call["tool"]
    inputs = call["inputs"]
    if tool not in allowed:
        return {
            "call_id": call_id,
            "tool": tool,
            "status": "rejected",
            "error": f"tool {tool!r} not allowed in this ablation mode (allowed: {sorted(allowed)})",
        }
    if tool == C2_R2A_VERIFY_TOOL:
        return _execute_validate_c2_certificate(item, call_id, tool, inputs, audit=audit)
    if tool == C2_R2B_REPAIR_TOOL:
        return _execute_repair_c2_submission(call_id, tool, inputs, audit=audit)
    return {
        "call_id": call_id,
        "tool": tool,
        "status": "rejected",
        "error": f"unsupported C2 attribution tool {tool!r}",
    }


def execute_c2_attribution_tool_plan(
    item: BenchmarkItem,
    tool_calls: list[dict[str, Any]],
    *,
    allowed: frozenset[str],
    audit: AuditLogBuilder,
) -> list[dict[str, Any]]:
    from fsmreasonbench.runners.tool_executor import MAX_TOOL_CALLS_PER_ROUND

    if len(tool_calls) > MAX_TOOL_CALLS_PER_ROUND:
        raise ValueError(f"tool plan exceeds max calls ({MAX_TOOL_CALLS_PER_ROUND})")
    return [
        execute_c2_attribution_tool(item, call, allowed=allowed, audit=audit)
        for call in tool_calls
    ]


def _execute_validate_c2_certificate(
    item: BenchmarkItem,
    call_id: str,
    tool: str,
    inputs: dict[str, Any],
    *,
    audit: AuditLogBuilder,
) -> dict[str, Any]:
    target_state = item.question.get("target_state")
    if not isinstance(target_state, str):
        return {
            "call_id": call_id,
            "tool": tool,
            "status": "rejected",
            "error": "C2 item missing target_state",
        }
    certificate = inputs.get("certificate")
    if not isinstance(certificate, dict):
        return {
            "call_id": call_id,
            "tool": tool,
            "status": "rejected",
            "error": "inputs.certificate must be an object",
        }
    result = verify_reachability_certificate(item.fsm, target_state, certificate)
    audit.record_tool(
        tool,
        {
            "fsm_id": item.fsm.fsm_id,
            "target_state": target_state,
            "certificate": certificate,
        },
        {"valid": result.valid, "error_count": len(result.errors)},
        tool_version="1.0",
        provenance="verifier.reachability.verify_reachability_certificate",
    )
    return {
        "call_id": call_id,
        "tool": tool,
        "status": "executed",
        "outputs": {
            "valid": result.valid,
            "errors": list(result.errors),
        },
    }


def _execute_repair_c2_submission(
    call_id: str,
    tool: str,
    inputs: dict[str, Any],
    *,
    audit: AuditLogBuilder,
) -> dict[str, Any]:
    submission = inputs.get("submission")
    if not isinstance(submission, dict):
        return {
            "call_id": call_id,
            "tool": tool,
            "status": "rejected",
            "error": "inputs.submission must be an object",
        }
    original_certificate = submission.get("certificate")
    repaired = extract_submission_payload_with_json_repair(json.dumps(submission))
    if not isinstance(repaired, dict):
        return {
            "call_id": call_id,
            "tool": tool,
            "status": "rejected",
            "error": "submission could not be repaired as JSON object",
        }
    if _semantic_certificate_changed(original_certificate, repaired.get("certificate")):
        return {
            "call_id": call_id,
            "tool": tool,
            "status": "rejected",
            "error": "repair would alter semantic certificate content (forbidden)",
        }
    audit.record_tool(
        tool,
        {"submission": submission},
        {"repaired": True},
        tool_version="1.0",
        provenance="runners.response_extract.extract_submission_payload_with_json_repair",
    )
    return {
        "call_id": call_id,
        "tool": tool,
        "status": "executed",
        "outputs": {"submission": repaired},
    }


def _semantic_certificate_changed(before: Any, after: Any) -> bool:
    if before is None and after is None:
        return False
    return _normalize_certificate_for_compare(before) != _normalize_certificate_for_compare(after)


def _normalize_certificate_for_compare(certificate: Any) -> str | None:
    if certificate is None:
        return None
    if isinstance(certificate, str):
        parsed = extract_submission_payload_with_json_repair(
            json.dumps({"certificate": certificate})
        )
        if isinstance(parsed, dict):
            certificate = parsed.get("certificate")
    if not isinstance(certificate, dict):
        return json.dumps(certificate, sort_keys=True)
    return json.dumps(certificate, sort_keys=True)
