"""C2 batch generation and baseline evaluation."""

from __future__ import annotations

from typing import Any

from fsmreasonbench.baselines.c2 import (
    run_invalid_baseline,
    run_oracle_baseline,
    run_random_baseline,
)
from fsmreasonbench.evaluator.models import ScoringRecord
from fsmreasonbench.evaluator.scorer import score_c2_item
from fsmreasonbench.generator.reachability import (
    ReachabilityGeneratorConfig,
    generate_reachability_item,
)
from fsmreasonbench.items.assembly import BenchmarkItem, self_verify_item

_BASELINES = frozenset({"oracle", "random", "invalid"})


def generate_c2_batch(
    n: int,
    seed: int,
    *,
    config: ReachabilityGeneratorConfig | None = None,
) -> list[BenchmarkItem]:
    """Generate ``n`` self-verifying C2 items with deterministic per-item seeds."""
    if n < 1:
        raise ValueError("n must be >= 1")

    items: list[BenchmarkItem] = []
    for index in range(n):
        item_seed = seed + index
        item = generate_reachability_item(item_seed, config)
        self_verify_item(item)
        items.append(item)
    return items


def baseline_response(
    baseline: str,
    item: BenchmarkItem,
    *,
    seed: int = 0,
) -> Any:
    if baseline == "oracle":
        return run_oracle_baseline(item)
    if baseline == "random":
        return run_random_baseline(item, seed=seed)
    if baseline == "invalid":
        return run_invalid_baseline(item)
    raise ValueError(f"unknown baseline {baseline!r}")


def evaluate_baseline_on_items(
    baseline: str,
    items: list[BenchmarkItem],
    *,
    seed: int = 0,
) -> list[ScoringRecord]:
    if baseline not in _BASELINES:
        raise ValueError(f"unknown baseline {baseline!r}")

    records: list[ScoringRecord] = []
    for index, item in enumerate(items):
        item_seed = seed + index
        raw_response = baseline_response(baseline, item, seed=item_seed)
        records.append(score_c2_item(item, raw_response))
    return records
