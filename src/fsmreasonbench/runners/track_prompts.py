"""Track-specific prompts for LLM evaluation."""

from __future__ import annotations

import json
from typing import Any

from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.runners.prompts import _render_c2_prompt, _render_f1_prompt
from fsmreasonbench.runners.track_prompt_schemas import (
    CERTIFICATE_EXAMPLES_BY_FAMILY,
    FINAL_SUBMISSION_CHECKLIST,
    FINAL_SUBMISSION_ENVELOPE,
    INVALID_PAYLOAD_EXAMPLES,
    SCHEMA_RULE,
)
from fsmreasonbench.tracks.models import TrackId

_PROTOCOL_HEADER = """Respond with a single JSON object only (no prose outside JSON).

"""


def render_track_prompt(
    item: BenchmarkItem,
    track: TrackId,
    *,
    phase: str = "initial",
    tool_results: list[dict[str, Any]] | None = None,
) -> str:
    if track == TrackId.R0:
        return _render_r0_prompt(item)
    if phase == "tool_results":
        return _render_tool_results_prompt(item, track, tool_results or [])
    return _render_tool_plan_prompt(item, track)


def _render_r0_prompt(item: BenchmarkItem) -> str:
    if item.family == "C2":
        return _render_c2_prompt(item)
    if item.family == "F1":
        return _render_f1_prompt(item)
    raise ValueError(f"unsupported family: {item.family!r}")


def _certificate_examples_block(family: str) -> str:
    lines = ["Valid certificate examples for this family:", ""]
    for label, example in CERTIFICATE_EXAMPLES_BY_FAMILY[family]:
        lines.append(f"### {label}")
        lines.append(example)
        lines.append("")
    return "\n".join(lines)


def _phase2_schema_block(item: BenchmarkItem) -> str:
    family_examples = _certificate_examples_block(item.family)
    return f"""## Final submission envelope (exact)

{FINAL_SUBMISSION_ENVELOPE}

{SCHEMA_RULE}

{family_examples}
## Invalid payload examples (do NOT emit)

{INVALID_PAYLOAD_EXAMPLES}

## Pre-submit checklist

{FINAL_SUBMISSION_CHECKLIST}
"""


def _render_tool_plan_prompt(item: BenchmarkItem, track: TrackId) -> str:
    evaluatee = json.dumps(item.to_evaluatee_dict(), indent=2, sort_keys=True)
    if track == TrackId.R1:
        tools_doc = (
            '- "step": inputs {{"fsm_id": string, "state": string, "symbol": string}}\n'
            "  Returns {{success, next_state?, error?}}. Use only this tool."
        )
    else:
        tools_doc = (
            '- "solver.is_reachable": inputs {{"fsm_id", "target_state"}}\n'
            '- "solver.reachability_certificate": inputs {{"fsm_id", "target_state"}}\n'
            '- "solver.check_separation": inputs {{"fsm_id_a", "fsm_id_b"}}\n'
            '- "solver.equivalence_certificate": inputs {{"fsm_id_a", "fsm_id_b"}}\n'
            '- "solver.distinguishing_certificate": inputs {{"fsm_id_a", "fsm_id_b"}}\n'
            "Use only registered solver tools above."
        )

    return f"""You are solving an FSMReasonBench {item.family} task under track {track.value}.

Evaluatee item (JSON):
{evaluatee}

Track {track.value} rules:
- You may NOT access answer keys or oracle certificates.
- Phase 1 ONLY: request tool calls; do NOT emit final_submission yet.
- Phase 2 (next message) will provide tool results and require final_submission.

{tools_doc}

{_PROTOCOL_HEADER}{{
  "phase": "tool_plan",
  "tool_calls": [
    {{"call_id": "1", "tool": "...", "inputs": {{ ... }}}}
  ],
  "notes": "optional reasoning scratchpad"
}}
"""


def _render_tool_results_prompt(
    item: BenchmarkItem,
    track: TrackId,
    tool_results: list[dict[str, Any]],
) -> str:
    evaluatee = json.dumps(item.to_evaluatee_dict(), indent=2, sort_keys=True)
    results_json = json.dumps(tool_results, indent=2, sort_keys=True)
    schema_block = _phase2_schema_block(item)
    item_id = item.item_id

    return f"""You are solving an FSMReasonBench {item.family} task under track {track.value}.

Evaluatee item (JSON):
{evaluatee}

Tool execution results from your plan:
{results_json}

Phase 2: emit final_submission ONLY. Use tool results to decide verdict and build a schema-valid certificate.

{schema_block}

Emit JSON matching this envelope with item_id="{item_id}":

{_PROTOCOL_HEADER}{FINAL_SUBMISSION_ENVELOPE}
"""
