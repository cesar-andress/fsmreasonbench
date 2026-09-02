"""Tool isolation and T3 non-constructive feedback tests."""

from __future__ import annotations

import json

from fsmreasonbench.certificates.separation import build_bisimulation_witness_certificate
from fsmreasonbench.clean_v2.condition import ContractId, ToolPaletteId
from fsmreasonbench.clean_v2.tools import execute_clean_tool_plan
from fsmreasonbench.clean_v2.tools.palettes import (
    FORBIDDEN_CAUSAL_TOOLS,
    T2_COMPUTE_AVAILABLE,
    assert_palette_is_causal,
    tools_for_palette,
)
from fsmreasonbench.clean_v2.tools.verify_feedback import (
    coarse_validate_certificate,
    model_visible_feedback_is_safe,
)
from fsmreasonbench.clean_v2.views import build_evaluatee_view, collect_item_specific_gold_tokens
from fsmreasonbench.evaluator.jsonl import load_items_jsonl


def _eq_item(repo_root):
    items = load_items_jsonl(repo_root / "cohorts/v0.1-expanded-n100/f1-mixed-level3/items.jsonl")
    return next(item for item in items if item.answer_key["verdict"] is True)


def test_t2_omitted():
    assert T2_COMPUTE_AVAILABLE is False


def test_palettes_exclude_builders():
    for palette in ToolPaletteId:
        assert_palette_is_causal(palette)
        assert not (tools_for_palette(palette) & FORBIDDEN_CAUSAL_TOOLS)


def test_forbidden_tools_rejected(repo_root):
    item = _eq_item(repo_root)
    evaluatee = build_evaluatee_view(item)
    results = execute_clean_tool_plan(
        item,
        evaluatee,
        [
            {
                "call_id": "1",
                "tool": "solver.bisimulation_certificate",
                "inputs": {"fsm_id_a": item.fsm_a.fsm_id, "fsm_id_b": item.fsm_b.fsm_id},
            }
        ],
        palette=ToolPaletteId.T1_STEP,
        contract=ContractId.BISIMULATION,
    )
    assert results[0]["status"] == "rejected"


def test_t3_feedback_is_coarse_and_non_leaking(repo_root):
    item = _eq_item(repo_root)
    gold = build_bisimulation_witness_certificate(item.fsm_a, item.fsm_b)
    bad = {
        "certificate_type": "bisimulation_witness",
        "version": "1.0",
        "fsm_ids": [item.fsm_a.fsm_id, item.fsm_b.fsm_id],
        "payload": {
            "equivalent": True,
            "pairs": [{"state_a": item.fsm_a.initial_state, "state_b": "missing"}],
        },
    }
    ok = coarse_validate_certificate(item, gold, contract=ContractId.BISIMULATION)
    bad_out = coarse_validate_certificate(item, bad, contract=ContractId.BISIMULATION)
    assert ok == {"status": "accepted", "code": "accepted"}
    assert bad_out["status"] == "rejected"
    assert set(bad_out.keys()) == {"status", "code"}
    assert "pairs" not in json.dumps(bad_out)
    tokens = collect_item_specific_gold_tokens(item)
    assert model_visible_feedback_is_safe(ok, tokens)
    assert model_visible_feedback_is_safe(bad_out, tokens)


def test_t3_does_not_return_expected_relation_or_corrected_certificate(repo_root):
    item = _eq_item(repo_root)
    gold = build_bisimulation_witness_certificate(item.fsm_a, item.fsm_b)
    empty = {
        "certificate_type": "bisimulation_witness",
        "version": "1.0",
        "fsm_ids": [item.fsm_a.fsm_id, item.fsm_b.fsm_id],
        "payload": {"equivalent": True, "pairs": []},
    }
    out = coarse_validate_certificate(item, empty, contract=ContractId.BISIMULATION)
    blob = json.dumps(out)
    assert "state_a" not in blob
    assert str(gold["payload"]["pairs"][0]) not in blob
