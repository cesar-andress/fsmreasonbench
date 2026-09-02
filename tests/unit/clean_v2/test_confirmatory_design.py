"""Tests for missingness classifier, scheduler, pilot guard, analysis pipeline."""

from __future__ import annotations

import copy

from fsmreasonbench.clean_v2.confirmatory.analysis.paired_rd import holm_bonferroni
from fsmreasonbench.clean_v2.confirmatory.analysis.pipeline import (
    run_confirmatory_analysis,
    tipping_point_sign_flip,
)
from fsmreasonbench.clean_v2.confirmatory.constants import EXECUTION_ORDER_SEED, MAX_VERIFIER_CALLS
from fsmreasonbench.clean_v2.confirmatory.missingness import classify_generation_attempt
from fsmreasonbench.clean_v2.confirmatory.pilot_guard import (
    assert_pilot_report_safe,
    build_pilot_report,
    validate_pilot_report,
)
from fsmreasonbench.clean_v2.confirmatory.scheduler import (
    fingerprint_task_list,
    interleaving_audit,
    reconstruct_ordering,
    shuffle_tasks,
)


def _task_key(t):
    return (t["item_id"], t["model"], t["condition_id"], t["repetition_index"])


def test_missingness_infrastructure_rerun():
    out = classify_generation_attempt(
        {"provider_error_type": "timeout", "http_status": None, "harness_exception": None}
    )
    assert out["missingness_class"] == "infrastructure"
    assert out["enters_n_attempted"] is False
    assert out["rerun_same_repetition"] is True


def test_missingness_experimental_counts():
    out = classify_generation_attempt(
        {
            "safety_refusal": True,
            "provider_error_type": None,
            "http_status": 200,
            "harness_exception": None,
        }
    )
    assert out["missingness_class"] == "experimental_outcome"
    assert out["enters_n_attempted"] is True
    assert out["rerun_same_repetition"] is False
    assert out["reason_code"] == "safety_refusal"


def test_scheduler_reconstructible_and_interleaved():
    raw = []
    for item in ["a", "b", "c"]:
        for model in ["m1", "m2"]:
            for cond in ["c1", "c2"]:
                for rep in [1, 2]:
                    raw.append(
                        {
                            "item_id": item,
                            "model": model,
                            "condition_id": cond,
                            "contract": "bisimulation",
                            "tool_palette": "T1_STEP",
                            "oracle_info": "none",
                            "format_assist": "off",
                            "repetition_index": rep,
                            "rq_family": "RQ2",
                            "condition_fingerprint": "fp",
                        }
                    )
    planned = shuffle_tasks(raw, execution_order_seed=EXECUTION_ORDER_SEED)
    again = reconstruct_ordering(raw, execution_order_seed=EXECUTION_ORDER_SEED)
    assert [t["planned_position"] for t in planned] == list(range(1, len(planned) + 1))
    assert fingerprint_task_list(planned) == fingerprint_task_list(again)
    assert [_task_key(t) for t in planned] == [_task_key(t) for t in again]
    audit = interleaving_audit(planned)
    assert audit["n_conditions"] == 2
    # Not executed condition-by-condition: max run should be << n.
    assert audit["condition_run_length_max"] < len(planned) // 2
    assert MAX_VERIFIER_CALLS == 3


def _synth_records(
    *,
    models=("claude", "gpt"),
    items=("i1", "i2", "i3", "i4", "i5"),
    effect="null",
):
    """Synthetic generation table for analysis tests (no real model data)."""
    records = []
    conds = {
        "bisimulation_T0": 0.1,
        "bisimulation_T1": 0.1,
        "bisimulation_T3": 0.1,
        "minimized_dfa_T1": 0.1,
        "digest_control_T1": 0.0,
    }
    if effect == "positive_rq2":
        conds["bisimulation_T1"] = 0.8
        conds["minimized_dfa_T1"] = 0.2
    if effect == "positive_rq3":
        conds["bisimulation_T0"] = 0.1
        conds["bisimulation_T1"] = 0.4
        conds["bisimulation_T3"] = 0.7
    if effect == "boundary_zero":
        for k in list(conds):
            conds[k] = 0.0
    if effect == "search_only_t3":
        conds["bisimulation_T1"] = 0.2
        # final high via witness_valid; first stays low
        conds["bisimulation_T3"] = 0.6

    for model in models:
        for item in items:
            for cond, rate in conds.items():
                for rep in range(1, 6):
                    # Deterministic pseudo-success from hashes.
                    h = (hash((model, item, cond, rep, effect)) & 0xFFFF) / 0xFFFF
                    wv = h < rate
                    wvf = wv
                    if effect == "search_only_t3" and cond == "bisimulation_T3":
                        wvf = h < 0.2
                        wv = h < 0.6
                    if effect == "incomplete" and item == "i5" and cond == "bisimulation_T3" and rep > 1:
                        continue
                    records.append(
                        {
                            "item_id": item,
                            "model": model,
                            "condition_id": cond,
                            "witness_valid": wv,
                            "witness_valid_first": wvf,
                            "verdict_correct": True,
                            "enters_n_attempted": True,
                            "is_infrastructure": False,
                            "verifier_call_count": 3 if cond == "bisimulation_T3" else 0,
                            "verifier_call_cap_reached": cond == "bisimulation_T3",
                            "repetition_index": rep,
                        }
                    )
    return records


def test_analysis_null_synthetic():
    records = _synth_records(effect="null")
    out = run_confirmatory_analysis(records, models=["claude", "gpt"], eq_item_ids=["i1", "i2", "i3", "i4", "i5"])
    assert out["gates"]["F0a"]["triggered"] is False
    for model in ("claude", "gpt"):
        rd = out["per_model"][model]["RQ2_witness_valid"]["mean_paired_rd_pp"]
        assert rd is not None
        assert abs(rd) < 25  # null-ish under synthetic noise
    assert "holm" in out["per_model"]["claude"]
    assert out["per_model"]["claude"]["holm_note"]


def test_analysis_positive_rq2_synthetic():
    records = _synth_records(effect="positive_rq2")
    out = run_confirmatory_analysis(records, models=["claude", "gpt"])
    for model in ("claude", "gpt"):
        rd = out["per_model"][model]["RQ2_witness_valid"]["mean_paired_rd_pp"]
        assert rd is not None and rd > 20


def test_analysis_boundary_zero():
    records = _synth_records(effect="boundary_zero")
    out = run_confirmatory_analysis(records, models=["claude"])
    assert out["per_model"]["claude"]["RQ2_witness_valid"]["both_sides_floor_zero"] is True
    assert out["classifications"]["RQ2"]["classification"] == "not_estimable"


def test_analysis_incomplete_cells_exclusion():
    records = _synth_records(effect="incomplete")
    out = run_confirmatory_analysis(records, models=["claude"])
    excluded = out["per_model"]["claude"]["rq3_retention"]["excluded_item_ids"]
    assert "i5" in excluded


def test_tipping_point_sign_flip():
    tip = tipping_point_sign_flip(0.2, excluded_n=10, retained_n=5)
    assert tip["sign_flip"] is True
    assert tip["label_if_flip"] == "INCONCLUSIVE DUE TO MISSINGNESS"


def test_holm_family_of_three():
    decisions = holm_bonferroni(
        [("a", 0.01), ("b", 0.04), ("c", 0.10)],
        alpha=0.05,
    )
    assert len(decisions) == 3
    assert decisions[0]["reject"] is True


def test_pilot_guard_blocks_scientific_rates():
    good = build_pilot_report(
        {
            "artifact_completeness": {"scores_jsonl": True},
            "schema_health": {"ok": True},
            "token_usage": {"total": 123},
            "latency": {"p50_ms": 10},
            "cost": {"usd": 0.0},
            "infrastructure_errors": [],
            "verifier_call_counts": {"mean": 1.2},
            "at_least_one_valid_witness_feasibility": {"bisimulation": True},
            "pilot_item_ids": ["x"],
            "n_generations": 10,
            "models_wired": ["claude"],
            "conditions_wired": ["bisimulation_T1"],
            # Attempted leak keys must be stripped / not accepted as scientific tables.
            "witness_valid_rate_by_condition": {"bisimulation_T1": 0.9},
        }
    )
    assert good["blinded"] is True
    assert "witness_valid_rate_by_condition" not in good
    assert_pilot_report_safe(good)

    leak = copy.deepcopy(good)
    leak["per_condition"] = {"bisimulation_T1": {"witness_valid_rate": 0.5}}
    assert validate_pilot_report(leak)
    leak2 = {"notes": "RQ2 contrast p=0.01 risk difference significant"}
    assert validate_pilot_report(leak2)
