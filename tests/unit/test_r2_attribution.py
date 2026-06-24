"""Tests for F1 R2 attribution tools and prompts."""

from __future__ import annotations

import json
from unittest.mock import patch

from fsmreasonbench.generator.separation import generate_separation_item
from fsmreasonbench.runners.r2_attribution_prompts import (
    MODE_CONDITION_IDS,
    R2AttributionMode,
    render_r2_attribution_final_prompt,
    render_r2_attribution_tool_plan_prompt,
)
from fsmreasonbench.runners.r2_attribution_tools import (
    F1_R2A_ALLOWED_TOOLS,
    F1_R2B_ALLOWED_TOOLS,
    R2A_VERIFY_TOOL,
    R2B_REPAIR_TOOL,
    execute_r2_attribution_tool,
)
from fsmreasonbench.tracks.audit import AuditLogBuilder
from fsmreasonbench.tracks.models import TrackId


def test_r2a_prompt_forbids_solver_generators() -> None:
    item = generate_separation_item(11)
    prompt = render_r2_attribution_tool_plan_prompt(item, R2AttributionMode.R2A)
    assert R2A_VERIFY_TOOL in prompt
    assert "solver.equivalence_certificate" in prompt
    assert "Forbidden" in prompt
    assert MODE_CONDITION_IDS[R2AttributionMode.R2A] in prompt or "R2A" in prompt


def test_r2b_prompt_allows_repair_only() -> None:
    item = generate_separation_item(13)
    prompt = render_r2_attribution_tool_plan_prompt(item, R2AttributionMode.R2B)
    assert R2B_REPAIR_TOOL in prompt
    assert "formatting" in prompt.lower()


def test_r2a_rejects_disallowed_tool() -> None:
    item = generate_separation_item(17)
    audit = AuditLogBuilder(TrackId.R2)
    result = execute_r2_attribution_tool(
        item,
        {
            "call_id": "1",
            "tool": "solver.equivalence_certificate",
            "inputs": {},
        },
        allowed=F1_R2A_ALLOWED_TOOLS,
        audit=audit,
    )
    assert result["status"] == "rejected"
    assert "not allowed" in result["error"]


def test_r2b_repair_rejects_semantic_change() -> None:
    item = generate_separation_item(19)
    audit = AuditLogBuilder(TrackId.R2)
    submission = {
        "item_id": item.item_id,
        "verdict": True,
        "certificate": {
            "type": "equivalence_witness",
            "minimized_state_hashes": ["aaa"],
        },
    }
    tampered = {
        **submission,
        "certificate": {
            "type": "equivalence_witness",
            "minimized_state_hashes": ["bbb"],
        },
    }
    with patch(
        "fsmreasonbench.runners.r2_attribution_tools.extract_submission_payload_with_json_repair",
        return_value=tampered,
    ):
        result = execute_r2_attribution_tool(
            item,
            {
                "call_id": "1",
                "tool": R2B_REPAIR_TOOL,
                "inputs": {"submission": submission},
            },
            allowed=F1_R2B_ALLOWED_TOOLS,
            audit=audit,
        )
    assert result["status"] == "rejected"
    assert "semantic" in result["error"].lower()


def test_r2b_repair_allows_formatting_only() -> None:
    item = generate_separation_item(23)
    audit = AuditLogBuilder(TrackId.R2)
    cert = {
        "type": "equivalence_witness",
        "minimized_state_hashes": ["deadbeef"],
        "bijection": [],
    }
    submission = {
        "item_id": item.item_id,
        "verdict": True,
        "certificate": json.dumps(cert),
    }
    result = execute_r2_attribution_tool(
        item,
        {
            "call_id": "1",
            "tool": R2B_REPAIR_TOOL,
            "inputs": {"submission": submission},
        },
        allowed=F1_R2B_ALLOWED_TOOLS,
        audit=audit,
    )
    assert result["status"] == "executed"
    repaired = result["outputs"]["submission"]
    assert isinstance(repaired["certificate"], dict)


def test_final_prompt_includes_tool_results() -> None:
    item = generate_separation_item(29)
    tool_results = [{"call_id": "1", "status": "executed", "outputs": {"valid": False}}]
    prompt = render_r2_attribution_final_prompt(item, R2AttributionMode.R2A, tool_results)
    assert item.item_id in prompt
    assert "valid" in prompt.lower()
