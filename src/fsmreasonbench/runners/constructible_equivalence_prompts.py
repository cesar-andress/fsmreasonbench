"""Prompts for F1 constructible bisimulation equivalence witness (Experiment A1)."""

from __future__ import annotations

import json
from typing import Any

from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.runners.track_prompt_schemas import (
    FINAL_SUBMISSION_CHECKLIST,
    FINAL_SUBMISSION_ENVELOPE,
    INVALID_PAYLOAD_EXAMPLES,
    SCHEMA_RULE,
)
from fsmreasonbench.tracks.models import TrackId

STUDY_CONDITION_ID = "F1-constructible-equivalence-v1"
WITNESS_CONTRACT = "bisimulation_witness"

F1_BISIMULATION_WITNESS_EXAMPLE = """{
  "certificate_type": "bisimulation_witness",
  "version": "1.0",
  "fsm_ids": ["<fsm_a.fsm_id>", "<fsm_b.fsm_id>"],
  "verdict_supported": true,
  "payload": {
    "equivalent": true,
    "pairs": [
      {"state_a": "q0", "state_b": "s0"},
      {"state_a": "q1", "state_b": "s1"}
    ]
  }
}"""

_CONSTRUCTIBLE_CHECKLIST = FINAL_SUBMISSION_CHECKLIST.replace(
    "9. F1 verdict=true requires equivalence_witness; verdict=false requires distinguishing_trace",
    "9. F1 verdict=true requires bisimulation_witness with state pairs; this study uses equivalent items only",
)


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
        tool_phase = "Explore both DFAs with step to discover matching states and transitions."
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

This item is from the F1 **equivalence subset** (verdict=true). You must eventually submit
`certificate_type=bisimulation_witness` with an explicit state-pair relation — **not**
`equivalence_witness` and **not** minimized hash digests.

## Item (evaluatee-visible)

{evaluatee}

## Phase 1: tool_plan

{tool_phase}

Allowed tools:
{tools_doc}

Emit:
{{"phase": "tool_plan", "tool_calls": [{{"call_id": "1", "tool": "...", "inputs": {{...}}}}]}}

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
    outputs_block = json.dumps(tool_outputs, indent=2, sort_keys=True)
    canonical_block = ""
    if canonical_certificate is not None and canonical_verdict is not None:
        canonical_block = f"""
## Canonical certificate from solver (R2C: copy verbatim into final submission)

verdict: {json.dumps(canonical_verdict)}
certificate:
{json.dumps(canonical_certificate, indent=2, sort_keys=True)}
"""

    return f"""Respond with a single JSON object only (no prose outside JSON).

## Phase 2: final_submission

Tool outputs from phase 1:
{outputs_block}
{canonical_block}
## Final submission envelope (exact)

{FINAL_SUBMISSION_ENVELOPE}

{SCHEMA_RULE}

## Valid certificate for this study (verdict=true)

### bisimulation_witness
{F1_BISIMULATION_WITNESS_EXAMPLE}

Each pair must relate states from fsm_a and fsm_b with matching acceptance and paired transitions.
Include the initial state pair. Do not emit hash fields.

## Invalid payload examples (do NOT emit)

{INVALID_PAYLOAD_EXAMPLES}

## Pre-submit checklist

{_CONSTRUCTIBLE_CHECKLIST}
"""
