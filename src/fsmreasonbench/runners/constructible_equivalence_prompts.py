"""Prompts for F1 constructible bisimulation equivalence witness (Experiment A1)."""

from __future__ import annotations

import json
from typing import Any

from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.runners.constructible_final_answer_contract import (
    R1_EXECUTOR_MAX_STEP_CALLS,
    R1_MAX_STEP_CALLS,
    STUDY_CONDITION_ID,
    WITNESS_CONTRACT,
    render_final_answer_contract_block,
)
from fsmreasonbench.runners.track_prompt_schemas import INVALID_PAYLOAD_EXAMPLES, SCHEMA_RULE
from fsmreasonbench.tracks.models import TrackId

__all__ = [
    "STUDY_CONDITION_ID",
    "WITNESS_CONTRACT",
    "R1_MAX_STEP_CALLS",
    "constructible_prompt_metadata",
    "render_constructible_tool_plan_prompt",
    "render_constructible_final_prompt",
]


def constructible_prompt_metadata(item: BenchmarkItem) -> dict[str, str]:
    return {
        "study_condition": STUDY_CONDITION_ID,
        "witness_contract": WITNESS_CONTRACT,
        "prompt_id": item.question.get("prompt_id", ""),
        "family": item.family,
    }


def render_constructible_tool_plan_prompt(item: BenchmarkItem, track: TrackId) -> str:
    evaluatee = json.dumps(item.to_evaluatee_dict(), indent=2, sort_keys=True)
    if track == TrackId.R1:
        tools_doc = (
            '- "step": inputs {"fsm_id": string, "state": string, "symbol": string}\n'
            "  Returns {success, next_state?, error?}. Use only this tool."
        )
        tool_phase = (
            "Explore both DFAs with step to discover matching states and transitions. "
            f"Prefer at most {R1_MAX_STEP_CALLS} step calls in phase 1; the executor "
            f"accepts up to {R1_EXECUTOR_MAX_STEP_CALLS} if needed. Phase 2 must emit "
            "the final JSON answer."
        )
    elif track == TrackId.R2:
        tools_doc = (
            '- "solver.check_separation": inputs {"fsm_id_a", "fsm_id_b"}\n'
            '- "solver.bisimulation_certificate": inputs {"fsm_id_a", "fsm_id_b"}\n'
            "  Returns a verifier-ready bisimulation_witness (state-pair relation)."
        )
        tool_phase = (
            "Use solver.check_separation if needed, then solver.bisimulation_certificate "
            "to obtain the canonical bisimulation witness."
        )
    else:
        raise ValueError(f"unsupported track for constructible equivalence study: {track}")

    return f"""Respond with a single JSON object only (no prose outside JSON).

## Study: constructible equivalence witness (no hash fields)

This item is from the F1 **equivalence subset** (verdict=true). Phase 2 must submit
`certificate_type="{WITNESS_CONTRACT}"` with explicit state pairs — never
`equivalence_witness`, never hash fields, never placeholder strings.

## Item (evaluatee-visible)

{evaluatee}

## Phase 1: tool_plan ONLY

{tool_phase}

Allowed tools:
{tools_doc}

Emit exactly:
{{"phase": "tool_plan", "tool_calls": [{{"call_id": "1", "tool": "...", "inputs": {{...}}}}]}}

Do NOT emit final_submission in phase 1.

{SCHEMA_RULE}
"""


def render_constructible_final_prompt(
    item: BenchmarkItem,
    track: TrackId,
    tool_outputs: list[dict[str, Any]],
    *,
    canonical_certificate: dict[str, Any] | None = None,
    canonical_verdict: bool | None = None,
) -> str:
    if item.fsm_b is None:
        raise ValueError("F1 constructible prompt requires fsm_b")

    outputs_block = json.dumps(tool_outputs, indent=2, sort_keys=True)
    contract_block = render_final_answer_contract_block(item)

    canonical_block = ""
    if canonical_certificate is not None and canonical_verdict is not None:
        canonical_block = f"""
## Canonical certificate from solver (R2C: copy verbatim into final submission)

verdict: {json.dumps(canonical_verdict)}
certificate:
{json.dumps(canonical_certificate, indent=2, sort_keys=True)}
"""

    return f"""Respond with a single JSON object only (no prose, no markdown fences, no commentary).

## Phase 2: final_submission ONLY

Tool outputs from phase 1:
{outputs_block}
{canonical_block}
{contract_block}

## Invalid payload examples (do NOT emit)

{INVALID_PAYLOAD_EXAMPLES}

{SCHEMA_RULE}
"""
