"""Tests for F1 oracle-verdict ablation prompts."""

from __future__ import annotations

import json

from fsmreasonbench.generator.separation import generate_separation_item
from fsmreasonbench.runners.ablation_prompts import (
    ABLATION_CONDITION_ID,
    render_f1_oracle_verdict_certificate_prompt,
)


def test_oracle_prompt_fixes_verdict_and_forbids_tools() -> None:
    item = generate_separation_item(42)
    prompt = render_f1_oracle_verdict_certificate_prompt(item)
    gold = item.answer_key["verdict"]
    assert ABLATION_CONDITION_ID in prompt or "ablation" in prompt.lower()
    assert "Fixed oracle verdict" in prompt
    assert "Do not attempt to re-prove" in prompt
    assert "No tools" in prompt
    assert "equivalence_witness" in prompt
    assert "distinguishing_trace" in prompt
    assert item.item_id in prompt
    assert item.fsm_a.fsm_id in prompt
    assert item.fsm_b.fsm_id in prompt
    assert json.dumps(gold).replace("true", "true")  # noqa: sanity
    if gold:
        assert "verdict\": true" in prompt.replace(" ", "") or '"verdict": true' in prompt
        assert "equivalence_witness" in prompt
    else:
        assert '"verdict": false' in prompt or "verdict\": false" in prompt.replace(" ", "")


def test_oracle_prompt_includes_both_worked_examples() -> None:
    item = generate_separation_item(7)
    prompt = render_f1_oracle_verdict_certificate_prompt(item)
    assert "Example A — distinguishing_trace" in prompt
    assert "Example B — equivalence_witness" in prompt
