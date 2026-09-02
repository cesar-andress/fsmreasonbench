"""Fingerprint, metrics, provenance, and scoring tests."""

from __future__ import annotations

import pytest

from fsmreasonbench.clean_v2.condition import (
    ContractId,
    FormatAssistId,
    OracleInfoId,
    ToolPaletteId,
)
from fsmreasonbench.clean_v2.exports import export_primary_model_rows
from fsmreasonbench.clean_v2.fingerprint import assert_single_factor_diff, base_condition
from fsmreasonbench.clean_v2.metrics import summarize_attempt_records
from fsmreasonbench.clean_v2.provenance import WitnessOrigin, WitnessProvenance
from fsmreasonbench.clean_v2.scoring import parse_clean_submission, score_clean_submission
from fsmreasonbench.clean_v2.views import build_evaluator_only
from fsmreasonbench.evaluator.jsonl import load_items_jsonl


def _eq_item(repo_root):
    items = load_items_jsonl(repo_root / "cohorts/v0.1-expanded-n100/f1-mixed-level3/items.jsonl")
    return next(item for item in items if item.answer_key["verdict"] is True)


def test_diff_experiment_single_factors():
    assert_single_factor_diff(
        base_condition(contract=ContractId.BISIMULATION),
        base_condition(contract=ContractId.MINIMIZED_DFA),
        "contract",
    )
    assert_single_factor_diff(
        base_condition(tool_palette=ToolPaletteId.T0_NONE),
        base_condition(tool_palette=ToolPaletteId.T1_STEP),
        "tool_palette",
    )
    assert_single_factor_diff(
        base_condition(oracle_info=OracleInfoId.NONE),
        base_condition(oracle_info=OracleInfoId.GOLD_VERDICT),
        "oracle_info",
    )
    assert_single_factor_diff(
        base_condition(format_assist=FormatAssistId.OFF),
        base_condition(format_assist=FormatAssistId.ON),
        "format_assist",
    )


def test_common_denominator_metrics():
    rows = [
        {
            "extractable": True,
            "verdict_correct": True,
            "witness_valid": False,
            "fully_correct": False,
            "first_failure": "witness_invalid",
        },
        {
            "extractable": False,
            "verdict_correct": None,
            "witness_valid": None,
            "fully_correct": False,
            "first_failure": "not_extractable",
        },
        {
            "extractable": True,
            "verdict_correct": True,
            "witness_valid": True,
            "fully_correct": True,
            "first_failure": "correct",
        },
    ]
    summary = summarize_attempt_records(rows)
    assert summary["n_attempted"] == 3
    assert summary["extractable"]["numerator"] == 2
    assert summary["extractable"]["denominator"] == 3
    assert summary["verdict_correct"]["denominator"] == 3
    assert summary["witness_valid"]["numerator"] == 1
    assert summary["fully_correct"]["numerator"] == 1
    assert summary["conditional"]["witness_valid_given_verdict_correct"]["denominator"] == 2
    assert summary["deprecated_mixed_gap"]["status"] == "deprecated"


def test_primary_export_rejects_injected():
    rows = [
        {
            "witness_provenance": WitnessProvenance(
                witness_origin=WitnessOrigin.RUNNER_INJECTED
            ).to_dict()
        }
    ]
    with pytest.raises(ValueError):
        export_primary_model_rows(rows)


def test_parse_and_first_failure_order(repo_root):
    item = _eq_item(repo_root)
    evaluator = build_evaluator_only(item)
    condition = base_condition()
    malformed = score_clean_submission(item, evaluator, "not-json", condition)
    assert malformed["first_failure"] == "not_extractable"
    assert malformed["extractable"] is False

    wrong = score_clean_submission(
        item,
        evaluator,
        {
            "item_id": item.item_id,
            "verdict": False,
            "certificate": {
                "certificate_type": "bisimulation_witness",
                "version": "1.0",
                "fsm_ids": [item.fsm_a.fsm_id, item.fsm_b.fsm_id],
                "payload": {"equivalent": True, "pairs": []},
            },
        },
        condition,
    )
    assert wrong["first_failure"] == "verdict_wrong"

    parsed, errors = parse_clean_submission(
        {
            "phase": "final_submission",
            "submission": {
                "item_id": item.item_id,
                "verdict": True,
                "certificate": {"certificate_type": "bisimulation_witness"},
            },
        }
    )
    assert parsed is not None
    assert not errors
