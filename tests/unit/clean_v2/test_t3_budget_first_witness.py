"""Tests for T3 budget, silent witness_valid_first, and invisibility."""

from __future__ import annotations

import copy
import json

from fsmreasonbench.certificates.separation import build_bisimulation_witness_certificate
from fsmreasonbench.clean_v2.condition import ContractId, ToolPaletteId
from fsmreasonbench.clean_v2.confirmatory.constants import MAX_VERIFIER_CALLS
from fsmreasonbench.clean_v2.confirmatory.t3_budget import compute_witness_valid_first
from fsmreasonbench.clean_v2.tools import execute_clean_tool_plan
from fsmreasonbench.clean_v2.views import build_evaluatee_view
from fsmreasonbench.evaluator.jsonl import load_items_jsonl


def _eq_item(repo_root):
    items = load_items_jsonl(repo_root / "cohorts/v0.1-expanded-n100/f1-mixed-level3/items.jsonl")
    return next(item for item in items if item.answer_key["verdict"] is True)


def _bad_cert(item):
    return {
        "certificate_type": "bisimulation_witness",
        "version": "1.0",
        "fsm_ids": [item.fsm_a.fsm_id, item.fsm_b.fsm_id],
        "payload": {"equivalent": True, "pairs": []},
    }


def test_max_verifier_calls_is_three():
    assert MAX_VERIFIER_CALLS == 3


def test_verifier_budget_caps_at_three(repo_root):
    item = _eq_item(repo_root)
    evaluatee = build_evaluatee_view(item)
    gold = build_bisimulation_witness_certificate(item.fsm_a, item.fsm_b)
    bad = _bad_cert(item)
    calls = [
        {"call_id": str(i), "tool": "verifier.validate_certificate_coarse", "inputs": {"certificate": bad}}
        for i in range(1, 5)
    ]
    calls[2]["inputs"] = {"certificate": gold}
    results, audit = execute_clean_tool_plan(
        item,
        evaluatee,
        calls,
        palette=ToolPaletteId.T3_VERIFY,
        contract=ContractId.BISIMULATION,
        max_verifier_calls=3,
    )
    assert audit["verifier_call_count"] == 3
    assert audit["verifier_call_cap_reached"] is True
    assert results[3]["status"] == "rejected"
    assert results[3]["error"] == "max_verifier_calls_exhausted"
    assert len(audit["coarse_verifier_responses"]) == 4


def test_witness_valid_first_uses_first_complete_proposal(repo_root):
    item = _eq_item(repo_root)
    gold = build_bisimulation_witness_certificate(item.fsm_a, item.fsm_b)
    bad = _bad_cert(item)
    tool_calls = [
        {"call_id": "1", "tool": "verifier.validate_certificate_coarse", "inputs": {"certificate": bad}},
        {"call_id": "2", "tool": "verifier.validate_certificate_coarse", "inputs": {"certificate": gold}},
    ]
    audit = compute_witness_valid_first(
        item,
        contract=ContractId.BISIMULATION,
        tool_calls=tool_calls,
        final_certificate=gold,
    )
    assert audit["witness_valid_first"] is False
    assert audit["first_proposal_source"] == "tool_call"
    # Final may still be valid.
    from fsmreasonbench.clean_v2.confirmatory.t3_budget import silent_witness_valid

    assert silent_witness_valid(item, gold, contract=ContractId.BISIMULATION) is True


def test_witness_valid_first_computation_invisible_to_evaluatee(repo_root):
    """Silent first-proposal eval must not alter model-visible messages/tool state."""
    item = _eq_item(repo_root)
    evaluatee = build_evaluatee_view(item)
    gold = build_bisimulation_witness_certificate(item.fsm_a, item.fsm_b)
    bad = _bad_cert(item)
    tool_calls = [
        {"call_id": "1", "tool": "verifier.validate_certificate_coarse", "inputs": {"certificate": bad}},
    ]
    # Snapshot evaluatee and tool_calls before silent audit.
    evaluatee_before = copy.deepcopy(evaluatee.to_dict())
    calls_before = copy.deepcopy(tool_calls)
    results, tool_audit = execute_clean_tool_plan(
        item,
        evaluatee,
        tool_calls,
        palette=ToolPaletteId.T3_VERIFY,
        contract=ContractId.BISIMULATION,
    )
    outputs_before = copy.deepcopy(results)
    messages = [
        {"role": "user", "content": "plan"},
        {"role": "assistant", "content": "tools"},
        {"role": "user", "content": json.dumps(results)},
    ]
    messages_before = copy.deepcopy(messages)

    audit = compute_witness_valid_first(
        item,
        contract=ContractId.BISIMULATION,
        tool_calls=tool_calls,
        final_certificate=gold,
    )
    assert audit["witness_valid_first"] is False

    # Nothing model-visible changed.
    assert evaluatee.to_dict() == evaluatee_before
    assert tool_calls == calls_before
    assert results == outputs_before
    assert messages == messages_before
    # Silent audit fields must not appear in tool outputs.
    blob = json.dumps(results)
    assert "witness_valid_first" not in blob
    assert "_audit_first_certificate" not in blob
    # Coarse feedback still only status/code (no silent flag).
    assert set(results[0]["outputs"].keys()) == {"status", "code"}
