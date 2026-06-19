"""Prompt rendering for C2 and F1 benchmark items."""

from __future__ import annotations

import json
from typing import Any

from fsmreasonbench.items.assembly import BenchmarkItem


def render_prompt(item: BenchmarkItem) -> str:
    """Render an evaluatee-facing prompt for a C2 or F1 item."""
    if item.family == "C2":
        return _render_c2_prompt(item)
    if item.family == "F1":
        return _render_f1_prompt(item)
    raise ValueError(f"unsupported family for prompts: {item.family!r}")


def _render_c2_prompt(item: BenchmarkItem) -> str:
    evaluatee = item.to_evaluatee_dict()
    target = item.question["target_state"]
    payload = json.dumps(evaluatee, indent=2, sort_keys=True)
    return f"""You are solving an FSMReasonBench C2 reachability task.

Benchmark item (evaluatee view, JSON):
{payload}

Question: Is state {target!r} reachable from the initial state in the given DFA?

Respond with a single JSON object only (no prose outside JSON) using this schema:
{{
  "item_id": "{item.item_id}",
  "verdict": true or false,
  "certificate": {{
    "certificate_type": "trace_witness" or "unreachability_witness",
    "version": "1.0",
    "payload": {{ ... }}
  }}
}}

Rules:
- verdict=true means the target IS reachable; use certificate_type=trace_witness with payload.trace and payload.state_sequence.
- verdict=false means the target is NOT reachable; use certificate_type=unreachability_witness with payload.reachable_states and payload.target_state.
- item_id must match exactly.
"""


def _render_f1_prompt(item: BenchmarkItem) -> str:
    if item.fsm_b is None:
        raise ValueError("F1 item requires fsm_b")
    evaluatee = item.to_evaluatee_dict()
    payload = json.dumps(evaluatee, indent=2, sort_keys=True)
    return f"""You are solving an FSMReasonBench F1 separation task (DFA non-equivalence).

Benchmark item (evaluatee view, JSON):
{payload}

Question: Are DFA A and DFA B language-equivalent?

Respond with a single JSON object only (no prose outside JSON) using this schema:
{{
  "item_id": "{item.item_id}",
  "verdict": true or false,
  "certificate": {{
    "certificate_type": "distinguishing_trace",
    "version": "1.0",
    "fsm_ids": ["{item.fsm_a.fsm_id}", "{item.fsm_b.fsm_id}"],
    "payload": {{
      "trace": ["..."],
      "acceptance": {{ "A": true or false, "B": true or false }}
    }}
  }}
}}

Rules:
- verdict=true means the DFAs ARE equivalent.
- verdict=false means the DFAs are NOT equivalent; supply a distinguishing_trace where acceptance.A != acceptance.B.
- item_id and fsm_ids must match exactly.
"""


def prompt_metadata(item: BenchmarkItem) -> dict[str, Any]:
    return {
        "family": item.family,
        "item_id": item.item_id,
        "prompt_id": item.question.get("prompt_id"),
    }
