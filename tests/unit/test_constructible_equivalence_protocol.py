"""Protocol tests for F1 constructible equivalence witness study (A1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fsmreasonbench.cohort.expanded_n100 import EXPANDED_COHORT_ROOT, resolve_cohort_bundle
from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.evaluator.jsonl import load_items_jsonl
from fsmreasonbench.evaluator.models import FailureStage
from fsmreasonbench.evaluator.scorer import score_item
from fsmreasonbench.experiments.constructible_equivalence_study import filter_equivalence_subset
from fsmreasonbench.runners.constructible_equivalence_batch import validate_constructible_smoke_gate
from fsmreasonbench.runners.constructible_equivalence_prompts import (
    R1_MAX_STEP_CALLS,
    render_constructible_final_prompt,
    render_constructible_tool_plan_prompt,
)
from fsmreasonbench.runners.constructible_final_answer_contract import (
    CERTIFICATE_TYPE,
    render_canonical_final_envelope,
)
from fsmreasonbench.runners.constructible_submission_normalize import (
    extract_constructible_final_submission,
)
from fsmreasonbench.runners.ollama_batch import OllamaBatchResult
from fsmreasonbench.tracks.models import TrackId
from fsmreasonbench.tracks.replay import replay_tool_invocation
from fsmreasonbench.tracks.audit import AuditLogBuilder
from fsmreasonbench.tracks.models import ToolInvocation


def _first_equivalence_item():
    repo = find_repo_root()
    _, f1_items, _, _ = resolve_cohort_bundle(repo / EXPANDED_COHORT_ROOT)
    items = filter_equivalence_subset(load_items_jsonl(f1_items))
    assert items
    return items[0]


def _smoke_result(
    item,
    *,
    track: str,
    submission,
    diagnostics,
    scoring,
    audit_log: dict | None = None,
) -> OllamaBatchResult:
    return OllamaBatchResult(
        results=[
            {
                "item_id": item.item_id,
                "scoring_record": scoring,
                "final_submission_diagnostics": diagnostics,
                "audit_log": audit_log or {},
            }
        ],
        summary={
            "n": 1,
            "extractability_rate": 1.0,
            "provider_error_count": 0,
        },
        out_dir=Path("/tmp/unused"),
        infrastructure_failures=0,
    )


def test_constructible_prompts_use_real_ids_not_template_literals() -> None:
    item = _first_equivalence_item()
    plan = render_constructible_tool_plan_prompt(item, TrackId.R1)
    final_prompt = render_constructible_final_prompt(item, TrackId.R1, [])

    assert item.item_id in plan
    assert item.item_id in final_prompt
    assert item.fsm_a.fsm_id in final_prompt
    assert item.fsm_b is not None
    assert item.fsm_b.fsm_id in final_prompt
    assert '"item_id": "<must match item>"' not in final_prompt
    assert str(R1_MAX_STEP_CALLS) in plan
    assert CERTIFICATE_TYPE in final_prompt


def test_provider_independent_prompts_are_identical_for_openai_and_claude() -> None:
    item = _first_equivalence_item()
    r1_plan = render_constructible_tool_plan_prompt(item, TrackId.R1)
    r1_final = render_constructible_final_prompt(item, TrackId.R1, [])
    r2c_final = render_constructible_final_prompt(
        item,
        TrackId.R2,
        [{"call_id": "1", "tool": "solver.bisimulation_certificate", "status": "executed", "outputs": {}}],
        canonical_certificate={"certificate_type": CERTIFICATE_TYPE, "payload": {"pairs": []}},
        canonical_verdict=True,
    )
    assert "Provider-independent final-answer contract" in r1_final
    assert render_canonical_final_envelope(item)["phase"] == "final_submission"
    assert r1_plan == render_constructible_tool_plan_prompt(item, TrackId.R1)
    assert r1_final == render_constructible_final_prompt(item, TrackId.R1, [])
    assert "openai" not in r1_plan.lower()
    assert "anthropic" not in r1_final.lower()
    assert "claude" not in r2c_final.lower()


def test_extract_recovers_gpt_placeholder_literals() -> None:
    item = _first_equivalence_item()
    final_text = json.dumps(
        {
            "phase": "final_submission",
            "submission": {
                "item_id": "<must match item>",
                "verdict": True,
                "certificate": {
                    "certificate_type": "bisimulation_witness",
                    "version": "1.0",
                    "fsm_ids": ["<fsm_a.fsm_id>", "<fsm_b.fsm_id>"],
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
            },
        }
    )
    submission, diagnostics = extract_constructible_final_submission(final_text, item)

    assert isinstance(submission, dict)
    assert diagnostics["final_json_found"] is True
    assert diagnostics["certificate_type_recognized"] is True
    assert diagnostics["parse_errors"] == []
    record = score_item(item, submission)
    assert record.extractable is True
    assert record.certificate_valid is not None


def test_extract_recovers_claude_markdown_fence_missing_fsm_ids_wrong_item_id() -> None:
    item = _first_equivalence_item()
    final_text = f"""```json
{{
  "phase": "final_submission",
  "submission": {{
    "item_id": "F1_bisim_pair_00",
    "verdict": true,
    "certificate": {{
      "certificate_type": "bisimulation_witness",
      "version": "1.0",
      "payload": {{
        "equivalent": true,
        "pairs": [
          {{"state_a": {json.dumps(item.fsm_a.initial_state)}, "state_b": {json.dumps(item.fsm_b.initial_state)}}}
        ]
      }}
    }}
  }}
}}
```"""
    submission, diagnostics = extract_constructible_final_submission(final_text, item)

    assert isinstance(submission, dict)
    assert diagnostics["final_json_found"] is True
    assert diagnostics["parse_path"] in {"best_effort", "protocol"}
    assert diagnostics["certificate_type"] == "bisimulation_witness"
    record = score_item(item, submission)
    assert record.extractable is True
    assert record.failure_stage in {
        FailureStage.CERTIFICATE_INVALID,
        FailureStage.CORRECT,
    }
    assert record.certificate_valid is not None


@pytest.mark.parametrize(
    ("track", "audit_log"),
    [
        ("R1", {}),
        (
            "R2C",
            {
                "certificate_assembly": [
                    {"phase": "certificate_assembly", "step": "invoke solver.bisimulation_certificate"}
                ]
            },
        ),
    ],
)
def test_smoke_gate_passes_for_provider_independent_extractable_submission(
    track: str,
    audit_log: dict,
) -> None:
    item = _first_equivalence_item()
    submission, diagnostics = extract_constructible_final_submission(
        json.dumps(render_canonical_final_envelope(item)),
        item,
    )
    scoring = score_item(item, submission).to_dict()
    diagnostics["verifier_invoked"] = scoring["certificate_valid"] is not None
    diagnostics["certificate_valid"] = scoring["certificate_valid"]
    diagnostics["failure_stage"] = scoring["failure_stage"]

    ok, report = validate_constructible_smoke_gate(
        _smoke_result(
            item,
            track=track,
            submission=submission,
            diagnostics=diagnostics,
            scoring=scoring,
            audit_log=audit_log,
        ),
        track=track,
    )
    assert ok is True, report
    assert report["certificate_type"] == "bisimulation_witness"
    assert report["verifier_invoked"] is True


@pytest.mark.parametrize("track", ["R1", "R2C"])
def test_smoke_gate_fails_when_not_extractable(track: str) -> None:
    ok, report = validate_constructible_smoke_gate(
        OllamaBatchResult(
            results=[
                {
                    "item_id": "x",
                    "scoring_record": {
                        "extractable": False,
                        "failure_stage": "not_extractable",
                        "certificate_valid": None,
                    },
                    "final_submission_diagnostics": {
                        "certificate_type_recognized": False,
                        "final_json_found": False,
                        "parse_errors": ["item_id mismatch"],
                        "verifier_invoked": False,
                    },
                    "audit_log": {},
                }
            ],
            summary={
                "n": 1,
                "extractability_rate": 0.0,
                "provider_error_count": 0,
            },
            out_dir=Path("/tmp/unused"),
            infrastructure_failures=0,
        ),
        track=track,
    )
    assert ok is False
    assert report["failures"]


def test_replay_supports_solver_bisimulation_certificate() -> None:
    item = _first_equivalence_item()
    audit = AuditLogBuilder(TrackId.R2)
    invocation = ToolInvocation(
        sequence=1,
        tool_name="solver.bisimulation_certificate",
        tool_version="1.0",
        provenance="test",
        inputs={"fsm_id_a": item.fsm_a.fsm_id, "fsm_id_b": item.fsm_b.fsm_id},
        outputs={
            "certificate_type": "bisimulation_witness",
            "verdict_supported": True,
            "pair_count": 3,
        },
    )
    replayed = replay_tool_invocation(
        invocation,
        fsm_by_id={item.fsm_a.fsm_id: item.fsm_a, item.fsm_b.fsm_id: item.fsm_b},
        audit=audit,
    )
    assert replayed["certificate_type"] == "bisimulation_witness"
