"""Paired risk-difference analysis for confirmatory RQ2/RQ3 (item-level)."""

from __future__ import annotations

import math
import random
from typing import Any, Callable, Sequence


def cell_proportion(successes: int, attempts: int) -> float | None:
    if attempts <= 0:
        return None
    return successes / attempts


def paired_differences(
    p_a: Sequence[float | None],
    p_b: Sequence[float | None],
) -> list[float]:
    """D_i = p_a(i) - p_b(i); drop items with missing either side."""
    out: list[float] = []
    for a, b in zip(p_a, p_b, strict=True):
        if a is None or b is None:
            continue
        out.append(float(a) - float(b))
    return out


def mean_rd(diffs: Sequence[float]) -> float | None:
    if not diffs:
        return None
    return sum(diffs) / len(diffs)


def _percentile(sorted_vals: Sequence[float], p: float) -> float:
    if not sorted_vals:
        raise ValueError("empty")
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    return sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f)


def bootstrap_bca_mean(
    diffs: Sequence[float],
    *,
    n_boot: int,
    seed: int,
    alpha: float = 0.05,
) -> dict[str, Any]:
    """
    BCa bootstrap CI for mean(D_i). Items are the resample unit.

    Boundary degeneracy: if all observed diffs identical (incl. all 0 or all 1/-1
    cell props yielding constant D), mark degenerate and recommend boundary-safe fallback.
    """
    diffs = list(diffs)
    n = len(diffs)
    point = mean_rd(diffs)
    if n == 0 or point is None:
        return {
            "estimate": None,
            "ci_low": None,
            "ci_high": None,
            "method": "bca",
            "degenerate": True,
            "n_items": 0,
            "fallback_recommended": True,
        }
    if len(set(round(d, 12) for d in diffs)) == 1:
        return {
            "estimate": point,
            "ci_low": point,
            "ci_high": point,
            "method": "bca",
            "degenerate": True,
            "n_items": n,
            "fallback_recommended": True,
            "note": "constant paired differences; BCa degenerate at boundary/constant",
        }

    rng = random.Random(seed)
    boots: list[float] = []
    for _ in range(n_boot):
        sample = [diffs[rng.randrange(n)] for _ in range(n)]
        boots.append(sum(sample) / n)
    boots.sort()

    # Acceleration via jackknife.
    jack = []
    for i in range(n):
        leave = diffs[:i] + diffs[i + 1 :]
        jack.append(sum(leave) / (n - 1))
    jack_mean = sum(jack) / n
    num = sum((jack_mean - j) ** 3 for j in jack)
    den = sum((jack_mean - j) ** 2 for j in jack)
    acc = num / (6.0 * (den ** 1.5)) if den > 0 else 0.0

    # Bias correction.
    prop_below = sum(1 for b in boots if b < point) / n_boot
    prop_below = min(max(prop_below, 1e-16), 1 - 1e-16)
    z0 = _norm_ppf(prop_below)
    z_alpha = _norm_ppf(alpha / 2)
    z_1alpha = _norm_ppf(1 - alpha / 2)

    def adj(z: float) -> float:
        return _norm_cdf(z0 + (z0 + z) / (1 - acc * (z0 + z)))

    a1 = adj(z_alpha)
    a2 = adj(z_1alpha)
    lo = _percentile(boots, a1)
    hi = _percentile(boots, a2)
    return {
        "estimate": point,
        "ci_low": lo,
        "ci_high": hi,
        "method": "bca",
        "degenerate": False,
        "n_items": n,
        "n_boot": n_boot,
        "seed": seed,
        "acceleration": acc,
        "bias_correction_z0": z0,
        "fallback_recommended": False,
    }


def sign_flip_permutation_pvalue(
    diffs: Sequence[float],
    *,
    n_draws: int,
    seed: int,
) -> dict[str, Any]:
    """Two-sided sign-flip permutation test on mean(D_i)."""
    diffs = list(diffs)
    n = len(diffs)
    obs = mean_rd(diffs)
    if n == 0 or obs is None:
        return {"pvalue": None, "n_items": 0, "n_draws": 0, "statistic": None}
    # Exact enumeration when 2^n is cheaper.
    if n <= 20 and (1 << n) <= n_draws:
        extreme = 0
        total = 1 << n
        abs_obs = abs(obs)
        for mask in range(total):
            s = 0.0
            for i in range(n):
                s += diffs[i] if (mask >> i) & 1 else -diffs[i]
            if abs(s / n) >= abs_obs - 1e-15:
                extreme += 1
        return {
            "pvalue": extreme / total,
            "n_items": n,
            "n_draws": total,
            "method": "exact_sign_flip",
            "statistic": obs,
            "seed": seed,
        }
    rng = random.Random(seed)
    abs_obs = abs(obs)
    extreme = 0
    for _ in range(n_draws):
        s = 0.0
        for d in diffs:
            s += d if rng.random() < 0.5 else -d
        if abs(s / n) >= abs_obs - 1e-15:
            extreme += 1
    return {
        "pvalue": extreme / n_draws,
        "n_items": n,
        "n_draws": n_draws,
        "method": "monte_carlo_sign_flip",
        "statistic": obs,
        "seed": seed,
    }


def wilson_score_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    if n <= 0:
        return None
    p = successes / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centre - margin) / denom, (centre + margin) / denom


def paired_risk_difference_newcombe(
    successes_a: int,
    n_a: int,
    successes_b: int,
    n_b: int,
    z: float = 1.96,
) -> dict[str, Any]:
    """
    Boundary-safe approximate interval for independent proportions difference
    (Newcombe / Wilson-based). Used as fallback when item-level BCa is degenerate
    and we collapse to marginal paired summaries is not available.

    For confirmatory item-level analysis, prefer bootstrap; this is the
    pre-specified boundary-safe alternative when BCa collapses.
    """
    wa = wilson_score_interval(successes_a, n_a, z=z)
    wb = wilson_score_interval(successes_b, n_b, z=z)
    if wa is None or wb is None:
        return {"estimate": None, "ci_low": None, "ci_high": None, "method": "newcombe_wilson"}
    pa = successes_a / n_a if n_a else None
    pb = successes_b / n_b if n_b else None
    est = None if pa is None or pb is None else pa - pb
    # Newcombe method 10 style bounds.
    lo = wa[0] - wb[1]
    hi = wa[1] - wb[0]
    return {
        "estimate": est,
        "ci_low": lo,
        "ci_high": hi,
        "method": "newcombe_wilson",
        "note": (
            "Pre-specified boundary-safe fallback (Newcombe–Wilson). "
            "Tango score not used (no existing reliable dependency in-repo)."
        ),
    }


def holm_bonferroni(
    pvalues: Sequence[tuple[str, float | None]],
    *,
    alpha: float = 0.05,
) -> list[dict[str, Any]]:
    """Holm-Bonferroni FWER control; pvalues are (label, p)."""
    indexed = [(i, label, p) for i, (label, p) in enumerate(pvalues)]
    # Missing p → non-rejectable.
    sortable = sorted(
        indexed,
        key=lambda t: (math.inf if t[2] is None else t[2], t[0]),
    )
    m = len(sortable)
    decisions: list[dict[str, Any] | None] = [None] * m
    reject_rest = False
    for rank, (orig_i, label, p) in enumerate(sortable, start=1):
        threshold = alpha / (m - rank + 1)
        if reject_rest or p is None or p > threshold:
            reject_rest = True
            decisions[orig_i] = {
                "label": label,
                "pvalue": p,
                "holm_threshold": threshold,
                "reject": False,
                "holm_rank": rank,
            }
        else:
            decisions[orig_i] = {
                "label": label,
                "pvalue": p,
                "holm_threshold": threshold,
                "reject": True,
                "holm_rank": rank,
            }
    return [d for d in decisions if d is not None]  # type: ignore[misc]


# --- normal helpers (no scipy dependency) ---

def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_ppf(p: float) -> float:
    """Acklam approximate inverse normal CDF."""
    if p <= 0.0 or p >= 1.0:
        raise ValueError("p in (0,1)")
    a = [
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577459677091e02,
        -3.066479806614736e01,
        2.506628277459239e00,
    ]
    b = [
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    ]
    c = [
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    ]
    d = [
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    ]
    plow = 0.02425
    phigh = 1 - plow
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
        )
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
        )
    q = p - 0.5
    r = q * q
    return (
        (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q
    ) / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
