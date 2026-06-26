"""Tests for Clopper--Pearson boundary interval fallback."""

from __future__ import annotations

from fsmreasonbench.evaluator.clopper_pearson import (
    clopper_pearson_interval,
    is_degenerate_proportion_ci,
    proportion_ci_with_boundary_fallback,
)


def test_clopper_pearson_zero_successes() -> None:
    lo, hi = clopper_pearson_interval(0, 51)
    assert lo == 0.0
    assert 0.06 < hi < 0.08


def test_clopper_pearson_all_successes() -> None:
    lo, hi = clopper_pearson_interval(50, 50)
    assert 0.92 < lo < 0.94
    assert hi == 1.0


def test_degenerate_bootstrap_replaced_at_boundary() -> None:
    lo, hi = proportion_ci_with_boundary_fallback(0, 51, 0.0, 0.0)
    assert lo == 0.0
    assert hi > 0.0
    lo, hi = proportion_ci_with_boundary_fallback(50, 50, 1.0, 1.0)
    assert lo < 1.0
    assert hi == 1.0


def test_interior_bootstrap_preserved() -> None:
    lo, hi = proportion_ci_with_boundary_fallback(46, 49, 0.857, 1.0)
    assert lo == 0.857
    assert hi == 1.0


def test_is_degenerate_proportion_ci() -> None:
    assert is_degenerate_proportion_ci(0.0, 0.0)
    assert is_degenerate_proportion_ci(1.0, 1.0)
    assert not is_degenerate_proportion_ci(0.857, 1.0)
