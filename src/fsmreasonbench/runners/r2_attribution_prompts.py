"""Prompts for F1 R2 attribution ablations (R2A/R2B)."""

from __future__ import annotations

import json
from enum import Enum
from typing import Any

from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.runners.r2_attribution_tools import (
    R2A_VERIFY_TOOL,
    R2B_REPAIR_TOOL,
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


class R2AttributionMode(str, Enum):
    R2A = "R2A"
    R2B = "R2B"
    R2C = "R2C"


MODE_CONDITION_IDS = {
    R2AttributionMode.R2A: "f1_r2a_verify_only",
    R2AttributionMode.R2B: "f1_r2b_repair_only",
    R2AttributionMode.R2C: "f1_r2c_generator_assisted",
}

MODE_TRACK_LABELS = {
    R2AttributionMode.R2A: "R2A-verify-only",
    R2AttributionMode.R2B: "R2B-repair-only",
    R2AttributionMode.R2C: "R2C-generator-assisted",
}


def attribution_prompt_metadata(item: BenchmarkItem, mode: R2AttributionMode) -> dict[str, Any]:
    return {
        "family": item.family,
        "item_id": item.item_id,
        "ablation_condition": MODE_CONDITION_IDS[mode],
        "r2_attribution_mode": mode.value,
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


def _mode_rules(mode: R2AttributionMode) -> str:
    if mode == R2AttributionMode.R2A:
        return f"""## R2A verify-only attribution rules

- **You** must construct the complete certificate (verdict + certificate object).
- The tool `{R2A_VERIFY_TOOL}` may **only validate** a certificate you supply; it does not generate, repair, search, or complete certificates.
- **Forbidden:** solver certificate generators (`solver.equivalence_certificate`, `solver.distinguishing_certificate`), separation oracles, and any tool that synthesizes witness content.
- Use validation feedback to revise your own certificate before final submission."""
    if mode == R2AttributionMode.R2B:
        return f"""## R2B repair-only attribution rules

- **You** must author the initial certificate semantics (trace, acceptance, minimized hashes, etc.).
- The tool `{R2B_REPAIR_TOOL}` may fix **formatting and schema wrappers only** (JSON fences, smart quotes, certificate encoded as string).
- The repair tool **must not** alter semantic certificate payload fields; rejected repairs indicate your content is already formatted or non-repairable.
- **Forbidden:** solver certificate generators and validation-only shortcuts that bypass your construction."""
    raise ValueError(f"unsupported mode for attribution prompts: {mode}")


def _tools_doc(mode: R2AttributionMode) -> str:
    if mode == R2AttributionMode.R2A:
        return f"""- `{R2A_VERIFY_TOOL}`: inputs {{"certificate": {{ ... full certificate object ... }} }}
  Returns {{"valid": boolean, "errors": [string, ...]}} using the benchmark verifier.
  Does **not** modify or generate certificates."""
    if mode == R2AttributionMode.R2B:
        return f"""- `{R2B_REPAIR_TOOL}`: inputs {{"submission": {{ "item_id", "verdict", "certificate" }} }}
  Returns {{"submission": {{ ... }} }} with harmless formatting repairs only.
  Does **not** change semantic certificate payload fields."""
    raise ValueError(mode)


def render_r2_attribution_tool_plan_prompt(item: BenchmarkItem, mode: R2AttributionMode) -> str:
    evaluatee = json.dumps(item.to_evaluatee_dict(), indent=2, sort_keys=True)
    track_label = MODE_TRACK_LABELS[mode]
    return f"""You are solving an FSMReasonBench {item.family} task under R2 attribution condition {mode.value} ({track_label}).

Evaluatee item (JSON):
{evaluatee}

{_mode_rules(mode)}

Allowed tools (phase 1 ONLY):
{_tools_doc(mode)}

- Phase 1 ONLY: request tool calls; do NOT emit final_submission yet.
- Phase 2 (next message) will provide tool results and require final_submission that **you** constructed.

{_PROTOCOL_HEADER}{{
  "phase": "tool_plan",
  "tool_calls": [
    {{"call_id": "1", "tool": "...", "inputs": {{ ... }}}}
  ],
  "notes": "optional reasoning scratchpad"
}}
"""


def render_r2_attribution_final_prompt(
    item: BenchmarkItem,
    mode: R2AttributionMode,
    tool_results: list[dict[str, Any]],
) -> str:
    evaluatee = json.dumps(item.to_evaluatee_dict(), indent=2, sort_keys=True)
    results_json = json.dumps(tool_results, indent=2, sort_keys=True)
    schema_block = _phase2_schema_block(item)
    track_label = MODE_TRACK_LABELS[mode]
    return f"""You are solving an FSMReasonBench {item.family} task under R2 attribution condition {mode.value} ({track_label}).

Evaluatee item (JSON):
{evaluatee}

Tool execution results from your plan:
{results_json}

{_mode_rules(mode)}

Phase 2: emit final_submission ONLY with a certificate **you** constructed (not copied from forbidden solver generators).

{schema_block}

Emit JSON matching this envelope with item_id="{item.item_id}":

{_PROTOCOL_HEADER}{FINAL_SUBMISSION_ENVELOPE}
"""
