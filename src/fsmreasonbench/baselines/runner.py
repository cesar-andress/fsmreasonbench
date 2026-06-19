"""Family-aware reference baseline dispatch."""

from __future__ import annotations

from typing import Any

from fsmreasonbench.baselines import c2, f1
from fsmreasonbench.baselines.common import run_invalid_baseline
from fsmreasonbench.items.assembly import BenchmarkItem

_BASELINES = frozenset({"oracle", "random", "invalid"})


def run_baseline(
    baseline: str,
    item: BenchmarkItem,
    *,
    seed: int = 0,
) -> Any:
    if baseline not in _BASELINES:
        raise ValueError(f"unknown baseline {baseline!r}")
    if item.family == "C2":
        if baseline == "oracle":
            return c2.run_oracle_baseline(item)
        if baseline == "random":
            return c2.run_random_baseline(item, seed=seed)
        return run_invalid_baseline(item)
    if item.family == "F1":
        if baseline == "oracle":
            return f1.run_oracle_baseline(item)
        if baseline == "random":
            return f1.run_random_baseline(item, seed=seed)
        return run_invalid_baseline(item)
    raise ValueError(f"unsupported family for baselines: {item.family!r}")
