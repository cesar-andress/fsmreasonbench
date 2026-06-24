"""C2 oracle-verdict + format-control ablation prompts."""

from __future__ import annotations

import json

from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.runners.track_prompt_schemas import (
    C2_TRACE_WITNESS_EXAMPLE,
    C2_UNREACHABILITY_WITNESS_EXAMPLE,
    INVALID_PAYLOAD_EXAMPLES,
)

C2_ABLATION_CONDITION_ID = "c2_oracle_verdict_format_control"
C2_ABLATION_TRACK_LABEL = "C2-oracle-verdict"


def render_c2_oracle_verdict_certificate_prompt(item: BenchmarkItem) -> str:
    if item.family != "C2":
        raise ValueError("C2 oracle ablation requires C2 items")
    gold_verdict: bool = item.answer_key["verdict"]
    evaluatee = item.to_evaluatee_dict()
    payload = json.dumps(evaluatee, indent=2, sort_keys=True)
    verdict_literal = "true" if gold_verdict else "false"
    target_state = item.question["target_state"]
    if gold_verdict:
        verdict_explanation = f"true — state {target_state!r} IS reachable from the initial state"
        required_type = "trace_witness"
        required_note = (
            "Use certificate_type=trace_witness with payload.trace and payload.state_sequence "
            f"ending at target {target_state!r}."
        )
    else:
        verdict_explanation = f"false — state {target_state!r} is NOT reachable"
        required_type = "unreachability_witness"
        required_note = (
            "Use certificate_type=unreachability_witness with payload.reachable_states equal to "
            f"the exact reachable set and payload.target_state={target_state!r}."
        )

    return f"""You are completing an FSMReasonBench C2 ablation task (certificate construction only).

Benchmark item (evaluatee view, JSON):
{payload}

## Fixed oracle verdict (do NOT re-derive)

The correct boolean verdict for this item is **{verdict_explanation}**.

This verdict is **fixed by the benchmark oracle**. Do not attempt to re-prove or change it.
Your task is **only** to construct a machine-verifiable certificate that supports this verdict.

## Constraints

- **No tools.** Do not call solvers, simulators, or external APIs.
- **Single JSON object only.** No markdown fences, no prose before or after the JSON.
- Top-level keys must be exactly: item_id, verdict, certificate.
- verdict MUST be the JSON boolean {verdict_literal}.
- certificate MUST be a JSON object (never null, never a string, never an array).
- For this item you MUST use certificate_type={required_type!r}.
- {required_note}
- item_id must be exactly {item.item_id!r}.
- certificate.fsm_id must be exactly {item.fsm.fsm_id!r}.

## Required submission schema

{{
  "item_id": "{item.item_id}",
  "verdict": {verdict_literal},
  "certificate": {{
    "certificate_type": "{required_type}",
    "version": "1.0",
    "fsm_id": "{item.fsm.fsm_id}",
    "payload": {{ ... }}
  }}
}}

## Worked examples

trace_witness (verdict=true):
{C2_TRACE_WITNESS_EXAMPLE.strip()}

unreachability_witness (verdict=false):
{C2_UNREACHABILITY_WITNESS_EXAMPLE.strip()}

{INVALID_PAYLOAD_EXAMPLES.strip()}

Respond with the JSON object only.
"""


def c2_ablation_prompt_metadata(item: BenchmarkItem) -> dict[str, object]:
    return {
        "family": item.family,
        "item_id": item.item_id,
        "ablation_condition": C2_ABLATION_CONDITION_ID,
        "oracle_verdict": item.answer_key["verdict"],
        "prompt_id": item.question.get("prompt_id"),
    }


ablation_prompt_metadata = c2_ablation_prompt_metadata
