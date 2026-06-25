"""Tests for F1 R2 attribution tools and prompts."""

from __future__ import annotations

import json
from pathlib import Path
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


def test_r2c_prompt_documents_certificate_builders() -> None:
    item = generate_separation_item(31)
    prompt = render_r2_attribution_tool_plan_prompt(item, R2AttributionMode.R2C)
    assert "solver.equivalence_certificate" in prompt
    assert "minimized_hash_A" in prompt


def test_ensure_f1_r2c_certificate_synthesis_supplements_equivalence_builder() -> None:
    from fsmreasonbench.generator.separation import SeparationGeneratorConfig
    from fsmreasonbench.runners.r2c_certificate_synthesis import (
        ensure_f1_r2c_certificate_synthesis,
    )
    from fsmreasonbench.tracks.audit import AuditLogBuilder
    from fsmreasonbench.tracks.models import TrackId
    from fsmreasonbench.verifier.separation import verify_f1_certificate

    item = generate_separation_item(
        37,
        SeparationGeneratorConfig(include_equivalent=True, equivalent_ratio=1.0, mode="random"),
    )
    assert item.fsm_b is not None
    audit = AuditLogBuilder(TrackId.R2)
    tool_outputs = [
        {
            "call_id": "1",
            "tool": "solver.check_separation",
            "status": "executed",
            "outputs": {
                "equivalent": True,
                "distinguishing_trace": None,
            },
        }
    ]
    synthesis = ensure_f1_r2c_certificate_synthesis(item, tool_outputs, audit)
    audit_log = audit.build()

    tool_names = [inv.tool_name for inv in audit_log.tool_invocations]
    assert "solver.equivalence_certificate" in tool_names
    assert audit_log.certificate_assembly
    assert synthesis.verdict is True
    assert synthesis.certificate["certificate_type"] == "equivalence_witness"
    assert synthesis.certificate["payload"]["minimized_hash_A"]
    assert synthesis.certificate["payload"]["minimized_hash_B"]
    verify_result = verify_f1_certificate(
        item.fsm_a,
        item.fsm_b,
        synthesis.certificate,
    )
    assert verify_result.valid is True


def test_r2c_smoke_equivalence_item_passes_with_check_separation_only_plan(tmp_path: Path) -> None:
    from fsmreasonbench.certificates.separation import build_equivalence_witness_certificate
    from fsmreasonbench.generator.separation import SeparationGeneratorConfig
    from fsmreasonbench.runners.ollama_batch import OllamaBatchConfig
    from fsmreasonbench.runners.r2_attribution_batch import run_r2_attribution_batch

    item = generate_separation_item(
        41,
        SeparationGeneratorConfig(include_equivalent=True, equivalent_ratio=1.0, mode="random"),
    )
    assert item.fsm_b is not None
    canonical = build_equivalence_witness_certificate(item.fsm_a, item.fsm_b)
    calls = 0

    def fake_generate(
        prompt: str,
        *,
        model: str,
        temperature: float,
        timeout: float,
    ) -> str:
        nonlocal calls
        _ = (prompt, model, temperature, timeout)
        calls += 1
        if calls == 1:
            return json.dumps(
                {
                    "phase": "tool_plan",
                    "tool_calls": [
                        {
                            "call_id": "1",
                            "tool": "solver.check_separation",
                            "inputs": {
                                "fsm_id_a": item.fsm_a.fsm_id,
                                "fsm_id_b": item.fsm_b.fsm_id,
                            },
                        }
                    ],
                }
            )
        return json.dumps(
            {
                "phase": "final_submission",
                "submission": {
                    "item_id": item.item_id,
                    "verdict": True,
                    "certificate": canonical,
                },
            }
        )

    out_dir = tmp_path / "r2c_smoke"
    result = run_r2_attribution_batch(
        [item],
        fake_generate,
        out_dir,
        OllamaBatchConfig(model="gpt-4.1", provider="openai", max_items=1, force_cell=True),
        R2AttributionMode.R2C,
    )
    assert calls == 2
    assert result.summary["certificate_valid_rate"] == 1.0
    assert result.summary["fully_correct_rate"] == 1.0
    transcript = json.loads((out_dir / "transcripts" / f"{item.item_id}.json").read_text())
    tool_names = [
        inv["tool_name"] for inv in transcript["audit_log"]["tool_invocations"]
    ]
    assert "solver.equivalence_certificate" in tool_names
    assert transcript["audit_log"]["certificate_assembly"]
