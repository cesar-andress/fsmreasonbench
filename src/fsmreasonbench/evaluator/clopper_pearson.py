"""Exact binomial (Clopper--Pearson) confidence intervals for proportion rates."""

from __future__ import annotations

from math import isclose


def clopper_pearson_interval(
    successes: int,
    n: int,
    *,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Two-sided exact binomial interval for ``successes`` in ``n`` trials."""
    if n <= 0:
        return 0.0, 0.0
    if successes < 0 or successes > n:
        raise ValueError(f"successes must be in [0, n]; got {successes}/{n}")

    from scipy.stats import beta

    lo = 0.0 if successes == 0 else float(beta.ppf(alpha / 2.0, successes, n - successes + 1))
    hi = 1.0 if successes == n else float(beta.ppf(1.0 - alpha / 2.0, successes + 1, n - successes))
    return lo, hi


def is_degenerate_proportion_ci(ci_low: float, ci_high: float) -> bool:
    """True when a percentile bootstrap interval collapses to a boundary."""
    return (
        isclose(ci_low, ci_high, abs_tol=1e-9)
        and (isclose(ci_low, 0.0, abs_tol=1e-9) or isclose(ci_low, 1.0, abs_tol=1e-9))
    )


def proportion_ci_with_boundary_fallback(
    successes: int,
    n: int,
    bootstrap_lo: float,
    bootstrap_hi: float,
    *,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Use Clopper--Pearson when bootstrap collapses or the observed rate is 0/1."""
    if n <= 0:
        return bootstrap_lo, bootstrap_hi
    if successes in (0, n) or is_degenerate_proportion_ci(bootstrap_lo, bootstrap_hi):
        return clopper_pearson_interval(successes, n, alpha=alpha)
    return bootstrap_lo, bootstrap_hi
