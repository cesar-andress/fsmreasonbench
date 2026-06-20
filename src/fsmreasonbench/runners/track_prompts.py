"""Track-specific prompts for LLM evaluation."""

from __future__ import annotations

import json
from typing import Any

from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.runners.prompts import _render_c2_prompt, _render_f1_prompt
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


def _submission_schema_hint(item: BenchmarkItem) -> str:
    if item.family == "C2":
        return (
            '  "item_id": "...",\n'
            '  "verdict": true or false,\n'
            '  "certificate": { "certificate_type": "trace_witness" or '
            '"unreachability_witness", "version": "1.0", "payload": { ... } }'
        )
    return (
        '  "item_id": "...",\n'
        '  "verdict": true or false,\n'
        '  "certificate": { "certificate_type": "distinguishing_trace" or '
        '"equivalence_witness", "version": "1.0", "payload": { ... } }'
    )


def _render_tool_plan_prompt(item: BenchmarkItem, track: TrackId) -> str:
    evaluatee = json.dumps(item.to_evaluatee_dict(), indent=2, sort_keys=True)
    if track == TrackId.R1:
        tools_doc = (
            '- "step": inputs {"fsm_id": string, "state": string, "symbol": string}\n'
            "  Returns {success, next_state?, error?}. Use only this tool."
        )
    else:
        tools_doc = (
            '- "solver.is_reachable": inputs {"fsm_id", "target_state"}\n'
            '- "solver.reachability_certificate": inputs {"fsm_id", "target_state"}\n'
            '- "solver.check_separation": inputs {"fsm_id_a", "fsm_id_b"}\n'
            '- "solver.equivalence_certificate": inputs {"fsm_id_a", "fsm_id_b"}\n'
            '- "solver.distinguishing_certificate": inputs {"fsm_id_a", "fsm_id_b"}\n'
            "Use only registered solver tools above."
        )

    return f"""You are solving an FSMReasonBench {item.family} task under track {track.value}.

Evaluatee item (JSON):
{evaluatee}

Track {track.value} rules:
- You may NOT access answer keys or oracle certificates.
- Phase 1: request tool calls only; do NOT emit the final submission yet.
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
    return f"""You are solving an FSMReasonBench {item.family} task under track {track.value}.

Evaluatee item (JSON):
{evaluatee}

Tool execution results from your plan:
{results_json}

Phase 2: emit the final benchmark submission JSON only.

{_PROTOCOL_HEADER}{{
  "phase": "final_submission",
  "submission": {{
{_submission_schema_hint(item)}
  }}
}}
"""
