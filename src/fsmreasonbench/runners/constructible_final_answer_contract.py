"""Provider-independent final-answer contract for A1 constructible equivalence."""

from __future__ import annotations

import json

from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.runners.tool_executor import MAX_TOOL_CALLS_PER_ROUND

STUDY_CONDITION_ID = "F1-constructible-equivalence-v1"
WITNESS_CONTRACT = "bisimulation_witness"
CERTIFICATE_TYPE = "bisimulation_witness"
CERTIFICATE_VERSION = "1.0"

# Soft guidance in prompts; executor still allows up to MAX_TOOL_CALLS_PER_ROUND step calls.
R1_MAX_STEP_CALLS = 16
R1_EXECUTOR_MAX_STEP_CALLS = MAX_TOOL_CALLS_PER_ROUND


def render_canonical_submission(item: BenchmarkItem) -> dict[str, object]:
    """Canonical nested submission object (provider-independent)."""
    if item.fsm_b is None:
        raise ValueError("F1 constructible contract requires fsm_b")
    return {
        "item_id": item.item_id,
        "verdict": True,
        "certificate": {
            "certificate_type": CERTIFICATE_TYPE,
            "version": CERTIFICATE_VERSION,
            "fsm_ids": [item.fsm_a.fsm_id, item.fsm_b.fsm_id],
            "verdict_supported": True,
            "payload": {
                "equivalent": True,
                "pairs": [
                    {
                        "state_a": item.fsm_a.initial_state,
                        "state_b": item.fsm_b.initial_state,
                    }
                ],
            },
        },
    }


def render_canonical_final_envelope(item: BenchmarkItem) -> dict[str, object]:
    """Canonical phase-2 envelope: one JSON object, no markdown fences."""
    return {
        "phase": "final_submission",
        "submission": render_canonical_submission(item),
    }


def render_canonical_submission_json(item: BenchmarkItem) -> str:
    return json.dumps(render_canonical_submission(item), indent=2, sort_keys=True)


def render_canonical_final_envelope_json(item: BenchmarkItem) -> str:
    return json.dumps(render_canonical_final_envelope(item), indent=2, sort_keys=True)


def render_final_answer_contract_block(item: BenchmarkItem) -> str:
    """Strict final-answer instructions shared by all providers."""
    return f"""## Provider-independent final-answer contract

Emit **one** JSON object only (no prose, no markdown fences, no commentary).

Required top-level shape:
{{"phase": "final_submission", "submission": {{...}}}}

Mandatory fields inside `submission`:
- `item_id`: exactly {json.dumps(item.item_id)}
- `verdict`: JSON boolean `true`
- `certificate.certificate_type`: exactly "{CERTIFICATE_TYPE}"
- `certificate.version`: "{CERTIFICATE_VERSION}"
- `certificate.fsm_ids`: exactly [{json.dumps(item.fsm_a.fsm_id)}, {json.dumps(item.fsm_b.fsm_id)}]
- `certificate.verdict_supported`: true
- `certificate.payload.equivalent`: true
- `certificate.payload.pairs`: non-empty array of {{"state_a": "...", "state_b": "..."}}

Forbidden:
- Placeholder tokens (`<must match item>`, `<fsm_a.fsm_id>`, etc.)
- Omitting `fsm_ids`
- `equivalence_witness` or hash fields
- Bare submission without the `phase`/`submission` envelope

Only `certificate.payload.pairs` may differ from the template (add valid pairs discovered via tools).

Canonical example (replace pair states with your witness; keep ids exactly):

{render_canonical_final_envelope_json(item)}
"""
