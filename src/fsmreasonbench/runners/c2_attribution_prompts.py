"""Prompts for C2 R2 attribution ablations (R2A/R2B)."""

from __future__ import annotations

import json
from enum import Enum
from typing import Any

from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.runners.c2_attribution_tools import (
    C2_R2A_VERIFY_TOOL,
    C2_R2B_REPAIR_TOOL,
)
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


class C2AttributionMode(str, Enum):
    R2A = "R2A"
    R2B = "R2B"
    R2C = "R2C"


MODE_CONDITION_IDS = {
    C2AttributionMode.R2A: "c2_r2a_verify_only",
    C2AttributionMode.R2B: "c2_r2b_repair_only",
    C2AttributionMode.R2C: "c2_r2c_generator_assisted",
}

MODE_TRACK_LABELS = {
    C2AttributionMode.R2A: "C2-R2A-verify-only",
    C2AttributionMode.R2B: "C2-R2B-repair-only",
    C2AttributionMode.R2C: "C2-R2C-generator-assisted",
}


def attribution_prompt_metadata(item: BenchmarkItem, mode: C2AttributionMode) -> dict[str, Any]:
    return {
        "family": item.family,
        "item_id": item.item_id,
        "ablation_condition": MODE_CONDITION_IDS[mode],
        "c2_attribution_mode": mode.value,
        "prompt_id": item.question.get("prompt_id"),
    }


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


def _mode_rules(mode: C2AttributionMode) -> str:
    if mode == C2AttributionMode.R2A:
        return f"""## R2A verify-only attribution rules

- **You** must construct the complete certificate (verdict + certificate object).
- The tool `{C2_R2A_VERIFY_TOOL}` may **only validate** a certificate you supply; it does not generate, repair, search, or complete certificates.
- **Forbidden:** `solver.is_reachable`, `solver.reachability_certificate`, and any tool that synthesizes witness content.
- Use validation feedback to revise your own certificate before final submission."""
    if mode == C2AttributionMode.R2B:
        return f"""## R2B repair-only attribution rules

- **You** must author the initial certificate semantics (trace, state_sequence, reachable_states, target_state).
- The tool `{C2_R2B_REPAIR_TOOL}` may fix **formatting and schema wrappers only** (JSON fences, smart quotes, certificate encoded as string).
- The repair tool **must not** alter semantic certificate payload fields; rejected repairs indicate your content is already formatted or non-repairable.
- **Forbidden:** solver certificate generators and validation-only shortcuts that bypass your construction."""
    raise ValueError(f"unsupported mode for C2 attribution prompts: {mode}")


def _tools_doc(mode: C2AttributionMode) -> str:
    if mode == C2AttributionMode.R2A:
        return f"""- `{C2_R2A_VERIFY_TOOL}`: inputs {{"certificate": {{ ... full certificate object ... }} }}
  Returns {{"valid": boolean, "errors": [string, ...]}} using the benchmark verifier.
  Does **not** modify or generate certificates."""
    if mode == C2AttributionMode.R2B:
        return f"""- `{C2_R2B_REPAIR_TOOL}`: inputs {{"submission": {{ "item_id", "verdict", "certificate" }} }}
  Returns {{"submission": {{ ... }} }} with harmless formatting repairs only.
  Does **not** change semantic certificate payload fields."""
    raise ValueError(mode)


def render_c2_attribution_tool_plan_prompt(item: BenchmarkItem, mode: C2AttributionMode) -> str:
    evaluatee = json.dumps(item.to_evaluatee_dict(), indent=2, sort_keys=True)
    track_label = MODE_TRACK_LABELS[mode]
    return f"""You are solving an FSMReasonBench {item.family} task under C2 attribution condition {mode.value} ({track_label}).

Evaluatee item (JSON):
{evaluatee}

Target state: {item.question.get("target_state")!r}

{_mode_rules(mode)}

## Allowed tools (this round)

{_tools_doc(mode)}

## Tool plan protocol

Return JSON:
{{
  "tool_calls": [
    {{"call_id": "1", "tool": "<allowed tool>", "inputs": {{ ... }} }}
  ],
  "notes": "optional short string"
}}

You may request zero tool calls if you already have a final certificate ready.
Track: {TrackId.R2.value} (certificate construction with restricted tools).
"""


def render_c2_attribution_final_prompt(
    item: BenchmarkItem,
    mode: C2AttributionMode,
    tool_outputs: list[dict[str, Any]],
) -> str:
    evaluatee = json.dumps(item.to_evaluatee_dict(), indent=2, sort_keys=True)
    outputs_block = json.dumps(tool_outputs, indent=2, sort_keys=True)
    return f"""{_PROTOCOL_HEADER}You are completing an FSMReasonBench C2 task under condition {mode.value} ({MODE_TRACK_LABELS[mode]}).

Evaluatee item (JSON):
{evaluatee}

Tool outputs from your plan (may be empty):
{outputs_block}

{_mode_rules(mode)}

{_phase2_schema_block(item)}

Submit the final JSON object only.
"""
