"""Falsification gates and RQ classification rules (pre-data freeze)."""

from __future__ import annotations

from typing import Any

from fsmreasonbench.clean_v2.confirmatory.constants import (
    INFRA_LOSS_DIFF_PP,
    RQ2_NO_LARGE_EFFECT_PP,
    RQ2_POWER_COMPATIBLE_PP,
    RQ2_STRONG_RD_PP,
    RQ2_VERDICT_CONTROL_PP,
    RQ3_T0_T1_STRONG_RD_PP,
    RQ3_T1_T3_STRONG_RD_PP,
)


def gate_f0a_digest_control(witness_valid_rate: float | None, n: int) -> dict[str, Any]:
    """F0a: digest_control witness_valid > 0 invalidates campaign until explained."""
    rate = witness_valid_rate or 0.0
    triggered = n > 0 and rate > 0.0
    return {
        "gate": "F0a",
        "triggered": triggered,
        "witness_valid_rate": witness_valid_rate,
        "n": n,
        "action": "campaign_invalid_until_explained" if triggered else "pass",
    }


def gate_f0b_sentinel(failed_checks: list[str]) -> dict[str, Any]:
    triggered = bool(failed_checks)
    return {
        "gate": "F0b",
        "triggered": triggered,
        "failed_checks": failed_checks,
        "action": "affected_campaign_invalid" if triggered else "pass",
    }


def gate_f0c_rq2_verdict_control(
    delta_pp: float | None,
    ci_low_pp: float | None,
    ci_high_pp: float | None,
    threshold_pp: float = RQ2_VERDICT_CONTROL_PP,
) -> dict[str, Any]:
    """Withdraw clean RQ2 witness-only interpretation if |delta|>10pp and CI excludes 0."""
    if delta_pp is None or ci_low_pp is None or ci_high_pp is None:
        return {"gate": "F0c", "triggered": False, "action": "insufficient_data"}
    excludes_zero = ci_high_pp < 0 or ci_low_pp > 0
    triggered = abs(delta_pp) > threshold_pp and excludes_zero
    return {
        "gate": "F0c",
        "triggered": triggered,
        "delta_pp": delta_pp,
        "ci_pp": [ci_low_pp, ci_high_pp],
        "threshold_pp": threshold_pp,
        "action": "withdraw_rq2_clean_witness_only_interpretation" if triggered else "pass",
    }


def gate_f0d_infra_loss(
    infra_loss_pp_a: float,
    infra_loss_pp_b: float,
    tipping_sign_flip: bool,
    threshold_pp: float = INFRA_LOSS_DIFF_PP,
) -> dict[str, Any]:
    diff = abs(infra_loss_pp_a - infra_loss_pp_b)
    mandatory_tipping = diff > threshold_pp
    inconclusive = mandatory_tipping and tipping_sign_flip
    return {
        "gate": "F0d",
        "triggered": mandatory_tipping,
        "infra_loss_diff_pp": diff,
        "threshold_pp": threshold_pp,
        "tipping_sign_flip": tipping_sign_flip,
        "action": (
            "INCONCLUSIVE DUE TO MISSINGNESS"
            if inconclusive
            else ("mandatory_tipping_point_analysis" if mandatory_tipping else "pass")
        ),
    }


def classify_rq2(
    *,
    rd_pp_by_model: dict[str, float | None],
    ci_by_model: dict[str, tuple[float | None, float | None]],
    holm_reject_by_model: dict[str, bool],
    both_floor_zero: bool,
    invalidated_f0c: bool,
) -> dict[str, Any]:
    if invalidated_f0c:
        return {"classification": "invalidated_by_diagnostic", "rule": "F0c"}
    if both_floor_zero:
        return {
            "classification": "not_estimable",
            "label": "NOT ESTIMABLE AT THIS CAPABILITY LEVEL",
        }
    models = list(rd_pp_by_model.keys())
    strong = []
    for m in models:
        rd = rd_pp_by_model.get(m)
        if rd is None:
            continue
        if abs(rd) >= RQ2_STRONG_RD_PP and holm_reject_by_model.get(m, False):
            strong.append(m)
    if len(strong) == 2:
        signs = [1 if (rd_pp_by_model[m] or 0) >= 0 else -1 for m in strong]
        if signs[0] == signs[1]:
            return {"classification": "supported", "rule": "strong_replicated", "models": strong}
        return {"classification": "inconclusive", "rule": "opposite_signs"}
    if len(strong) == 1:
        return {"classification": "snapshot_specific", "models": strong}

    no_large = True
    for m in models:
        rd = rd_pp_by_model.get(m)
        lo, hi = ci_by_model.get(m, (None, None))
        if rd is None or lo is None or hi is None:
            no_large = False
            break
        # Compatible with no effect larger than ~20pp: interval within [-20,20] roughly
        # and |RD| < 10.
        if abs(rd) >= RQ2_NO_LARGE_EFFECT_PP:
            no_large = False
        if hi > RQ2_POWER_COMPATIBLE_PP or lo < -RQ2_POWER_COMPATIBLE_PP:
            no_large = False
    if no_large and len(models) >= 2:
        return {
            "classification": "inconclusive",
            "label": "no_meaningful_large_effect_detected",
            "wording": "cautious: do not write 'no effect'",
        }
    return {"classification": "inconclusive"}


def classify_rq3_t0_t1(
    *,
    rd_pp_by_model: dict[str, float | None],
    holm_reject_by_model: dict[str, bool],
) -> dict[str, Any]:
    strong = []
    for m, rd in rd_pp_by_model.items():
        if rd is None:
            continue
        if rd >= RQ3_T0_T1_STRONG_RD_PP and holm_reject_by_model.get(m, False):
            strong.append(m)
    if len(strong) == 2:
        signs = [1 if (rd_pp_by_model[m] or 0) >= 0 else -1 for m in strong]
        if signs[0] == signs[1]:
            return {"classification": "supported", "rule": "t0_t1_strong"}
        return {"classification": "inconclusive", "rule": "opposite_signs"}
    if len(strong) == 1:
        return {"classification": "snapshot_specific", "models": strong}
    return {"classification": "inconclusive"}


def classify_rq3_t1_t3(
    *,
    final_rd_pp_by_model: dict[str, float | None],
    first_rd_pp_by_model: dict[str, float | None],
    holm_reject_by_model: dict[str, bool],
    almost_exclusive_cap_exhaustion: bool = False,
) -> dict[str, Any]:
    """
    Stronger witness-construction interpretation requires BOTH final and first
    improvements (>=10pp) with inferential criterion and same sign across snapshots.
    Search-only: final improves, first does not.
    """
    construction = []
    search_only = []
    for m in final_rd_pp_by_model:
        final_rd = final_rd_pp_by_model.get(m)
        first_rd = first_rd_pp_by_model.get(m)
        if final_rd is None:
            continue
        holm_ok = holm_reject_by_model.get(m, False)
        final_ok = final_rd >= RQ3_T1_T3_STRONG_RD_PP and holm_ok
        first_ok = first_rd is not None and first_rd >= RQ3_T1_T3_STRONG_RD_PP
        if final_ok and first_ok:
            construction.append(m)
        elif final_ok and not first_ok:
            search_only.append(m)
    out: dict[str, Any] = {}
    if len(construction) == 2:
        out = {
            "classification": "supported",
            "interpretation": "improved_witness_construction",
            "rule": "intersection_final_and_first",
        }
    elif len(construction) == 1:
        out = {
            "classification": "snapshot_specific",
            "interpretation": "improved_witness_construction",
            "models": construction,
        }
    elif len(search_only) >= 1:
        out = {
            "classification": "supported" if len(search_only) == 2 else "snapshot_specific",
            "interpretation": "verifier_guided_search_only",
            "wording": (
                "bounded verifier feedback helped search/refine candidate witnesses, "
                "but did not improve first-attempt witness construction"
            ),
            "models": search_only,
        }
    else:
        out = {"classification": "inconclusive"}
    if almost_exclusive_cap_exhaustion:
        out["flag"] = "attempt_budget_dependence"
        out["wording_caution"] = "avoid wording about general tool capability"
    return out
