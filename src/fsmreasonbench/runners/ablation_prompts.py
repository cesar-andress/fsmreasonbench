"""Prompts for FSMReasonBench ablation conditions."""

from __future__ import annotations

import json
from typing import Any

from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.runners.track_prompt_schemas import (
    F1_DISTINGUISHING_TRACE_EXAMPLE,
    F1_EQUIVALENCE_WITNESS_EXAMPLE,
    INVALID_PAYLOAD_EXAMPLES,
)

ABLATION_CONDITION_ID = "f1_oracle_verdict_format_control"
ABLATION_TRACK_LABEL = "AB1-oracle-verdict"


def render_f1_oracle_verdict_certificate_prompt(item: BenchmarkItem) -> str:
    """
    Certificate-only ablation: gold verdict is fixed; model must emit a valid certificate.

    No tool access, no solver delegation, no re-deriving the boolean verdict.
    """
    if item.fsm_b is None:
        raise ValueError("F1 item requires fsm_b")
    gold_verdict: bool = item.answer_key["verdict"]
    evaluatee = item.to_evaluatee_dict()
    payload = json.dumps(evaluatee, indent=2, sort_keys=True)
    verdict_literal = "true" if gold_verdict else "false"
    if gold_verdict:
        verdict_explanation = "true — the two DFAs ARE language-equivalent"
        required_type = "equivalence_witness"
        required_note = (
            "Use certificate_type=equivalence_witness with payload.equivalent=true and "
            "correct minimized_hash_A / minimized_hash_B for the minimized reachable cores."
        )
    else:
        verdict_explanation = "false — the two DFAs are NOT language-equivalent"
        required_type = "distinguishing_trace"
        required_note = (
            "Use certificate_type=distinguishing_trace with payload.trace and "
            "payload.acceptance where acceptance.A != acceptance.B."
        )

    return f"""You are completing an FSMReasonBench F1 ablation task (certificate construction only).

Benchmark item (evaluatee view, JSON):
{payload}

## Fixed oracle verdict (do NOT re-derive)

The correct boolean verdict for this item is **{verdict_explanation}**.

This verdict is **fixed by the benchmark oracle**. Do not attempt to re-prove or change it.
Your task is **only** to construct a machine-verifiable certificate that supports this verdict.

## Constraints

- **No tools.** Do not call solvers, simulators, or external APIs.
- **No tool plans.** Do not emit tool_use blocks or delegation requests.
- **Single JSON object only.** No markdown fences, no prose before or after the JSON.
- Top-level keys must be exactly: item_id, verdict, certificate.
- verdict MUST be the JSON boolean {verdict_literal} (exactly matching the oracle above).
- certificate MUST be a JSON object (never null, never a string, never an array).
- For this item you MUST use certificate_type={required_type!r}.
- {required_note}
- item_id must be exactly {item.item_id!r}.
- fsm_ids must be exactly [{item.fsm_a.fsm_id!r}, {item.fsm_b.fsm_id!r}].

## Required submission schema

{{
  "item_id": "{item.item_id}",
  "verdict": {verdict_literal},
  "certificate": {{
    "certificate_type": "{required_type}",
    "version": "1.0",
    "fsm_ids": ["{item.fsm_a.fsm_id}", "{item.fsm_b.fsm_id}"],
    "payload": {{ ... }}
  }}
}}

## Worked examples (structural templates — adapt fields to this item)

Example A — distinguishing_trace (used when verdict=false):
{F1_DISTINGUISHING_TRACE_EXAMPLE.strip()}

Example B — equivalence_witness (used when verdict=true):
{F1_EQUIVALENCE_WITNESS_EXAMPLE.strip()}

{INVALID_PAYLOAD_EXAMPLES.strip()}

Respond with the JSON object only.
"""


def ablation_prompt_metadata(item: BenchmarkItem) -> dict[str, Any]:
    return {
        "family": item.family,
        "item_id": item.item_id,
        "ablation_condition": ABLATION_CONDITION_ID,
        "oracle_verdict": item.answer_key["verdict"],
        "prompt_id": item.question.get("prompt_id"),
    }
