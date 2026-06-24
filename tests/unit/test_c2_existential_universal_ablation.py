"""Unit tests for C2 existential-vs-universal ablation prompts and tools."""

from __future__ import annotations

import json

import pytest

from fsmreasonbench.cohort.c2_balanced_n100 import enrich_c2_item_metadata, generate_c2_balanced_items
from fsmreasonbench.evaluator.jsonl import load_items_jsonl
from fsmreasonbench.runners.c2_ablation_prompts import render_c2_oracle_verdict_certificate_prompt
from fsmreasonbench.runners.c2_attribution_tools import (
    C2_R2A_VERIFY_TOOL,
    execute_c2_attribution_tool,
)
from fsmreasonbench.tracks.audit import AuditLogBuilder
from fsmreasonbench.tracks.models import TrackId


def test_balanced_cohort_is_50_50():
    items = generate_c2_balanced_items(100)
    verdicts = [item.answer_key["verdict"] for item in items]
    assert len(items) == 100
    assert sum(verdicts) == 50
    cert_types = {item.answer_key["certificate"]["certificate_type"] for item in items}
    assert cert_types == {"trace_witness", "unreachability_witness"}


def test_oracle_prompt_includes_gold_verdict_and_schema():
    item = generate_c2_balanced_items(2)[0]
    prompt = render_c2_oracle_verdict_certificate_prompt(item)
    assert item.item_id in prompt
    assert "trace_witness" in prompt or "unreachability_witness" in prompt
    assert "No tools" in prompt


def test_r2a_validate_tool_accepts_gold_certificate():
    items = generate_c2_balanced_items(4)
    reachable = next(item for item in items if item.answer_key["verdict"])
    audit = AuditLogBuilder(TrackId.R2)
    certificate = reachable.answer_key["certificate"]
    result = execute_c2_attribution_tool(
        reachable,
        {
            "call_id": "1",
            "tool": C2_R2A_VERIFY_TOOL,
            "inputs": {"certificate": certificate},
        },
        allowed=frozenset({C2_R2A_VERIFY_TOOL}),
        audit=audit,
    )
    assert result["status"] == "executed"
    assert result["outputs"]["valid"] is True


def test_enriched_metadata_fields():
    item = enrich_c2_item_metadata(generate_c2_balanced_items(2)[0])
    core = item.difficulty["core"]
    assert "certificate_type" in core
    assert "reachable" in core
    assert "alphabet_size" in core
    assert "transition_count" in core
