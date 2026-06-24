"""R2 attribution ablation tools (verify-only and repair-only)."""

from __future__ import annotations

import json
from typing import Any

from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.runners.response_extract import (
    extract_submission_payload_with_json_repair,
)
from fsmreasonbench.tracks.audit import AuditLogBuilder
from fsmreasonbench.verifier.separation import verify_f1_certificate

R2A_VERIFY_TOOL = "verifier.validate_f1_certificate"
R2B_REPAIR_TOOL = "format.repair_f1_submission"

F1_R2A_ALLOWED_TOOLS = frozenset({R2A_VERIFY_TOOL})
F1_R2B_ALLOWED_TOOLS = frozenset({R2B_REPAIR_TOOL})

F1_R2C_ALLOWED_TOOLS = frozenset(
    {
        "solver.check_separation",
        "solver.equivalence_certificate",
        "solver.distinguishing_certificate",
    }
)


def execute_r2_attribution_tool(
    item: BenchmarkItem,
    call: dict[str, Any],
    *,
    allowed: frozenset[str],
    audit: AuditLogBuilder,
) -> dict[str, Any]:
    """Execute a single R2 attribution tool call."""
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
    if tool == R2A_VERIFY_TOOL:
        return _execute_validate_f1_certificate(item, call_id, tool, inputs, audit=audit)
    if tool == R2B_REPAIR_TOOL:
        return _execute_repair_f1_submission(call_id, tool, inputs, audit=audit)
    return {
        "call_id": call_id,
        "tool": tool,
        "status": "rejected",
        "error": f"unsupported attribution tool {tool!r}",
    }


def execute_r2_attribution_tool_plan(
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
        execute_r2_attribution_tool(item, call, allowed=allowed, audit=audit)
        for call in tool_calls
    ]


def _execute_validate_f1_certificate(
    item: BenchmarkItem,
    call_id: str,
    tool: str,
    inputs: dict[str, Any],
    *,
    audit: AuditLogBuilder,
) -> dict[str, Any]:
    if item.fsm_b is None:
        return {
            "call_id": call_id,
            "tool": tool,
            "status": "rejected",
            "error": "F1 item missing fsm_b",
        }
    certificate = inputs.get("certificate")
    if not isinstance(certificate, dict):
        return {
            "call_id": call_id,
            "tool": tool,
            "status": "rejected",
            "error": "inputs.certificate must be an object",
        }
    result = verify_f1_certificate(item.fsm_a, item.fsm_b, certificate)
    outputs = {
        "valid": result.valid,
        "errors": list(result.errors),
    }
    audit.record_tool(
        tool,
        {
            "fsm_id_a": item.fsm_a.fsm_id,
            "fsm_id_b": item.fsm_b.fsm_id,
            "certificate": certificate,
        },
        {"valid": result.valid, "error_count": len(result.errors)},
        tool_version="1.0",
        provenance="verifier.separation.verify_f1_certificate",
    )
    return {
        "call_id": call_id,
        "tool": tool,
        "status": "executed",
        "outputs": outputs,
    }


def _execute_repair_f1_submission(
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
    """Return True if repair altered certificate semantics (not just wrappers)."""
    if before is None and after is None:
        return False
    normalized_before = _normalize_certificate_for_compare(before)
    normalized_after = _normalize_certificate_for_compare(after)
    return normalized_before != normalized_after


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
