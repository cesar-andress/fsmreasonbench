"""End-to-end confirmatory analysis on generation records (synthetic-safe)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable, Sequence

from fsmreasonbench.clean_v2.confirmatory.analysis.gates import (
    classify_rq2,
    classify_rq3_t0_t1,
    classify_rq3_t1_t3,
    gate_f0a_digest_control,
    gate_f0c_rq2_verdict_control,
    gate_f0d_infra_loss,
)
from fsmreasonbench.clean_v2.confirmatory.analysis.paired_rd import (
    bootstrap_bca_mean,
    cell_proportion,
    holm_bonferroni,
    mean_rd,
    paired_differences,
    paired_risk_difference_newcombe,
    sign_flip_permutation_pvalue,
)
from fsmreasonbench.clean_v2.confirmatory.constants import (
    BOOTSTRAP_SEED,
    HOLM_ALPHA,
    ITEM_EXCLUSION_TIPPING_FRACTION,
    K_REPETITIONS,
    MIN_VALID_GENERATIONS_PER_CONDITION,
    N_BOOTSTRAP,
    N_PERMUTATION,
    PERMUTATION_SEED,
)


def _attempted(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        r
        for r in rows
        if r.get("enters_n_attempted", True) and not r.get("is_infrastructure", False)
    ]


def item_cell_rate(
    rows: Sequence[dict[str, Any]],
    *,
    outcome: str,
) -> tuple[float | None, int, int]:
    """Return (p_hat, successes, n_attempted) for one item-condition cell."""
    attempted = _attempted(rows)
    n = len(attempted)
    if n == 0:
        return None, 0, 0
    succ = sum(1 for r in attempted if r.get(outcome) is True)
    return cell_proportion(succ, n), succ, n


def retain_items_for_family(
    records: Sequence[dict[str, Any]],
    *,
    model: str,
    condition_ids: Sequence[str],
    min_valid: int = MIN_VALID_GENERATIONS_PER_CONDITION,
) -> dict[str, Any]:
    """Keep items with ≥min_valid attempted gens in EVERY condition of the family."""
    by_item_cond: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for r in records:
        if r.get("model") != model:
            continue
        if r.get("condition_id") not in condition_ids:
            continue
        if r.get("is_infrastructure"):
            continue
        by_item_cond[str(r["item_id"])][str(r["condition_id"])].append(r)

    retained: list[str] = []
    excluded: list[str] = []
    for item_id, cond_map in by_item_cond.items():
        ok = True
        for cid in condition_ids:
            n = len(_attempted(cond_map.get(cid, [])))
            if n < min_valid:
                ok = False
                break
        (retained if ok else excluded).append(item_id)
    # Items that never appear still excluded implicitly.
    n_universe = len(by_item_cond)
    frac = (len(excluded) / n_universe) if n_universe else 0.0
    return {
        "retained_item_ids": sorted(retained),
        "excluded_item_ids": sorted(excluded),
        "n_universe_seen": n_universe,
        "exclusion_fraction": frac,
        "tipping_point_required": frac > ITEM_EXCLUSION_TIPPING_FRACTION,
        "min_valid_generations_per_condition": min_valid,
        "equal_item_weight": True,
    }


def contrast_paired_rd(
    records: Sequence[dict[str, Any]],
    *,
    model: str,
    condition_a: str,
    condition_b: str,
    outcome: str,
    item_ids: Sequence[str],
    bootstrap_seed: int = BOOTSTRAP_SEED,
    permutation_seed: int = PERMUTATION_SEED,
) -> dict[str, Any]:
    """Primary estimand: mean_i (p_hat(i,a) - p_hat(i,b)) with BCa + sign-flip."""
    by_item: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for r in records:
        if r.get("model") != model:
            continue
        if r.get("item_id") not in set(item_ids):
            continue
        if r.get("condition_id") not in {condition_a, condition_b}:
            continue
        by_item[str(r["item_id"])][str(r["condition_id"])].append(r)

    p_a: list[float | None] = []
    p_b: list[float | None] = []
    ordered_items: list[str] = []
    succ_a = succ_b = n_a = n_b = 0
    for item_id in sorted(item_ids):
        ra, sa, na = item_cell_rate(by_item[item_id].get(condition_a, []), outcome=outcome)
        rb, sb, nb = item_cell_rate(by_item[item_id].get(condition_b, []), outcome=outcome)
        if ra is None or rb is None:
            continue
        ordered_items.append(item_id)
        p_a.append(ra)
        p_b.append(rb)
        succ_a += sa
        n_a += na
        succ_b += sb
        n_b += nb

    diffs = paired_differences(p_a, p_b)
    est = mean_rd(diffs)
    # Floor-zero both sides.
    both_floor = bool(diffs) and all(d == 0.0 for d in diffs) and all(x == 0.0 for x in p_a) and all(
        x == 0.0 for x in p_b
    )
    boot = bootstrap_bca_mean(diffs, n_boot=N_BOOTSTRAP, seed=bootstrap_seed)
    perm = sign_flip_permutation_pvalue(diffs, n_draws=N_PERMUTATION, seed=permutation_seed)
    fallback = None
    if boot.get("fallback_recommended"):
        fallback = paired_risk_difference_newcombe(succ_a, n_a, succ_b, n_b)

    # Majority-vote sensitivity (descriptive helper).
    majority = _majority_vote_discordant(by_item, ordered_items, condition_a, condition_b, outcome)

    return {
        "model": model,
        "condition_a": condition_a,
        "condition_b": condition_b,
        "outcome": outcome,
        "n_items": len(diffs),
        "item_ids": ordered_items,
        "mean_paired_rd": est,
        "mean_paired_rd_pp": None if est is None else 100.0 * est,
        "marginal_rate_a": (succ_a / n_a) if n_a else None,
        "marginal_rate_b": (succ_b / n_b) if n_b else None,
        "raw_n_a": n_a,
        "raw_n_b": n_b,
        "raw_successes_a": succ_a,
        "raw_successes_b": succ_b,
        "bootstrap": boot,
        "bootstrap_ci_pp": (
            None
            if boot.get("ci_low") is None
            else [100.0 * boot["ci_low"], 100.0 * boot["ci_high"]]
        ),
        "permutation": perm,
        "boundary_fallback": fallback,
        "both_sides_floor_zero": both_floor,
        "majority_vote": majority,
        "k_design": K_REPETITIONS,
        "inferential_unit": "item_within_model",
        "note": "Repetitions collapse within item; k does not inflate inferential n.",
    }


def _majority_vote_discordant(
    by_item: dict[str, dict[str, list[dict[str, Any]]]],
    item_ids: Sequence[str],
    condition_a: str,
    condition_b: str,
    outcome: str,
) -> dict[str, Any]:
    b = c = 0  # McNemar-style discordant (a majority True vs b)
    for item_id in item_ids:
        ra, _, na = item_cell_rate(by_item[item_id].get(condition_a, []), outcome=outcome)
        rb, _, nb = item_cell_rate(by_item[item_id].get(condition_b, []), outcome=outcome)
        if ra is None or rb is None:
            continue
        maj_a = ra >= 0.5
        maj_b = rb >= 0.5
        if maj_a and not maj_b:
            b += 1
        elif maj_b and not maj_a:
            c += 1
    n = b + c
    return {
        "b": b,
        "c": c,
        "discordant_n": n,
        "discordant_proportion": (n / len(item_ids)) if item_ids else None,
    }


def run_confirmatory_analysis(
    records: Sequence[dict[str, Any]],
    *,
    models: Sequence[str],
    rq2_conditions: tuple[str, str] = ("bisimulation_T1", "minimized_dfa_T1"),
    rq3_conditions: tuple[str, str, str] = ("bisimulation_T0", "bisimulation_T1", "bisimulation_T3"),
    digest_condition: str = "digest_control_T1",
    eq_item_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    """
    Full confirmatory pipeline for one synthetic or real score table.

    Each record needs: item_id, model, condition_id, witness_valid, verdict_correct,
    enters_n_attempted, is_infrastructure, optional witness_valid_first.
    """
    if eq_item_ids is None:
        eq_item_ids = sorted({str(r["item_id"]) for r in records})

    out: dict[str, Any] = {
        "primary_outcome": "witness_valid",
        "co_primary_diagnostic_t1_t3": "witness_valid_first",
        "models": list(models),
        "per_model": {},
        "gates": {},
        "classifications": {},
    }

    # Digest F0a across models (pooled descriptive).
    digest_rows = [r for r in records if r.get("condition_id") == digest_condition]
    d_att = _attempted(digest_rows)
    d_succ = sum(1 for r in d_att if r.get("witness_valid") is True)
    out["gates"]["F0a"] = gate_f0a_digest_control(
        (d_succ / len(d_att)) if d_att else None, len(d_att)
    )

    holm_inputs_by_model: dict[str, list[tuple[str, float | None]]] = {}

    for model in models:
        rq2_ret = retain_items_for_family(
            records, model=model, condition_ids=list(rq2_conditions)
        )
        rq3_ret = retain_items_for_family(
            records, model=model, condition_ids=list(rq3_conditions)
        )
        items_rq2 = [i for i in eq_item_ids if i in set(rq2_ret["retained_item_ids"])]
        items_rq3 = [i for i in eq_item_ids if i in set(rq3_ret["retained_item_ids"])]

        c_rq2 = contrast_paired_rd(
            records,
            model=model,
            condition_a=rq2_conditions[0],
            condition_b=rq2_conditions[1],
            outcome="witness_valid",
            item_ids=items_rq2,
        )
        c_verdict = contrast_paired_rd(
            records,
            model=model,
            condition_a=rq2_conditions[0],
            condition_b=rq2_conditions[1],
            outcome="verdict_correct",
            item_ids=items_rq2,
        )
        c_t0_t1 = contrast_paired_rd(
            records,
            model=model,
            condition_a=rq3_conditions[1],
            condition_b=rq3_conditions[0],
            outcome="witness_valid",
            item_ids=items_rq3,
        )
        c_t1_t3 = contrast_paired_rd(
            records,
            model=model,
            condition_a=rq3_conditions[2],
            condition_b=rq3_conditions[1],
            outcome="witness_valid",
            item_ids=items_rq3,
        )
        c_t1_t3_first = contrast_paired_rd(
            records,
            model=model,
            condition_a=rq3_conditions[2],
            condition_b=rq3_conditions[1],
            outcome="witness_valid_first",
            item_ids=items_rq3,
        )
        c_t0_t3 = contrast_paired_rd(
            records,
            model=model,
            condition_a=rq3_conditions[2],
            condition_b=rq3_conditions[0],
            outcome="witness_valid",
            item_ids=items_rq3,
        )

        f0c = gate_f0c_rq2_verdict_control(
            c_verdict["mean_paired_rd_pp"],
            None if c_verdict["bootstrap_ci_pp"] is None else c_verdict["bootstrap_ci_pp"][0],
            None if c_verdict["bootstrap_ci_pp"] is None else c_verdict["bootstrap_ci_pp"][1],
        )

        holm_family = [
            ("RQ2_bisim_vs_min_dfa", c_rq2["permutation"]["pvalue"]),
            ("RQ3_T0_vs_T1", c_t0_t1["permutation"]["pvalue"]),
            ("RQ3_T1_vs_T3", c_t1_t3["permutation"]["pvalue"]),
        ]
        holm = holm_bonferroni(holm_family, alpha=HOLM_ALPHA)
        holm_inputs_by_model[model] = holm_family

        # Verifier diagnostics for T3.
        t3_rows = [
            r
            for r in _attempted(records)
            if r.get("model") == model and r.get("condition_id") == rq3_conditions[2]
        ]
        cap_frac = None
        if t3_rows:
            cap_frac = sum(1 for r in t3_rows if r.get("verifier_call_cap_reached")) / len(t3_rows)
        call_dist: dict[str, int] = defaultdict(int)
        for r in t3_rows:
            call_dist[str(r.get("verifier_call_count", "NA"))] += 1

        out["per_model"][model] = {
            "rq2_retention": rq2_ret,
            "rq3_retention": rq3_ret,
            "RQ2_witness_valid": c_rq2,
            "RQ2_verdict_control": c_verdict,
            "RQ2_F0c": f0c,
            "RQ3_T0_vs_T1": c_t0_t1,
            "RQ3_T1_vs_T3_final": c_t1_t3,
            "RQ3_T1_vs_T3_first": c_t1_t3_first,
            "RQ3_T0_vs_T3_secondary": c_t0_t3,
            "holm": holm,
            "holm_note": (
                "Holm applies to inferential decisions/p-values only; "
                "confidence intervals remain nominal 95%."
            ),
            "t3_diagnostics": {
                "verifier_call_count_distribution": dict(call_dist),
                "fraction_hitting_call_cap": cap_frac,
                "final_vs_first_improvement_pp": (
                    None
                    if c_t1_t3["mean_paired_rd_pp"] is None
                    or c_t1_t3_first["mean_paired_rd_pp"] is None
                    else c_t1_t3["mean_paired_rd_pp"] - c_t1_t3_first["mean_paired_rd_pp"]
                ),
            },
        }

    # Cross-model classifications.
    rd2 = {
        m: out["per_model"][m]["RQ2_witness_valid"]["mean_paired_rd_pp"] for m in models
    }
    ci2 = {
        m: (
            None
            if out["per_model"][m]["RQ2_witness_valid"]["bootstrap_ci_pp"] is None
            else tuple(out["per_model"][m]["RQ2_witness_valid"]["bootstrap_ci_pp"])
        )
        for m in models
    }
    holm_rq2 = {
        m: next(
            h["reject"]
            for h in out["per_model"][m]["holm"]
            if h["label"] == "RQ2_bisim_vs_min_dfa"
        )
        for m in models
    }
    f0c_any = any(out["per_model"][m]["RQ2_F0c"]["triggered"] for m in models)
    both_floor = all(
        out["per_model"][m]["RQ2_witness_valid"]["both_sides_floor_zero"] for m in models
    )
    out["classifications"]["RQ2"] = classify_rq2(
        rd_pp_by_model=rd2,
        ci_by_model=ci2,  # type: ignore[arg-type]
        holm_reject_by_model=holm_rq2,
        both_floor_zero=both_floor,
        invalidated_f0c=f0c_any,
    )
    out["classifications"]["RQ3_T0_T1"] = classify_rq3_t0_t1(
        rd_pp_by_model={
            m: out["per_model"][m]["RQ3_T0_vs_T1"]["mean_paired_rd_pp"] for m in models
        },
        holm_reject_by_model={
            m: next(
                h["reject"]
                for h in out["per_model"][m]["holm"]
                if h["label"] == "RQ3_T0_vs_T1"
            )
            for m in models
        },
    )
    out["classifications"]["RQ3_T1_T3"] = classify_rq3_t1_t3(
        final_rd_pp_by_model={
            m: out["per_model"][m]["RQ3_T1_vs_T3_final"]["mean_paired_rd_pp"] for m in models
        },
        first_rd_pp_by_model={
            m: out["per_model"][m]["RQ3_T1_vs_T3_first"]["mean_paired_rd_pp"] for m in models
        },
        holm_reject_by_model={
            m: next(
                h["reject"]
                for h in out["per_model"][m]["holm"]
                if h["label"] == "RQ3_T1_vs_T3"
            )
            for m in models
        },
    )

    # Placeholder F0d (caller supplies infra rates for real data).
    out["gates"]["F0d_template"] = gate_f0d_infra_loss(0.0, 0.0, tipping_sign_flip=False)
    return out


def tipping_point_sign_flip(
    base_rd: float,
    *,
    excluded_n: int,
    retained_n: int,
    extreme_assign_positive_to_control: bool = True,
) -> dict[str, Any]:
    """
    Extreme missing-outcome tipping: assign excluded items to reverse the contrast.

    If sign of RD flips under extreme assumptions → INCONCLUSIVE DUE TO MISSINGNESS.
    """
    if retained_n + excluded_n == 0:
        return {"sign_flip": False, "extreme_rd": None}
    # Treat excluded as contributing ±1 paired difference extremes.
    if extreme_assign_positive_to_control:
        extreme_sum = base_rd * retained_n + (-1.0) * excluded_n
    else:
        extreme_sum = base_rd * retained_n + (1.0) * excluded_n
    extreme_rd = extreme_sum / (retained_n + excluded_n)
    return {
        "base_rd": base_rd,
        "extreme_rd": extreme_rd,
        "sign_flip": (base_rd > 0 > extreme_rd) or (base_rd < 0 < extreme_rd),
        "label_if_flip": "INCONCLUSIVE DUE TO MISSINGNESS",
    }
