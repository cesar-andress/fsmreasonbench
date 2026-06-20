"""Batch generation, baseline evaluation, and smoke runners."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fsmreasonbench.baselines.runner import run_baseline
from fsmreasonbench.evaluator.models import ScoringRecord
from fsmreasonbench.evaluator.scorer import score_item
from fsmreasonbench.evaluator.summary import (
    combine_baseline_summaries,
    summarize_with_baseline,
)
from fsmreasonbench.generator.reachability import (
    ReachabilityGeneratorConfig,
    generate_reachability_item,
)
from fsmreasonbench.generator.separation import (
    SeparationGeneratorConfig,
    generate_separation_item,
)
from fsmreasonbench.items.assembly import BenchmarkItem, self_verify_item

_BASELINES = frozenset({"oracle", "random", "invalid"})
_SMOKE_BASELINES = ("oracle", "random", "invalid")
_BATCH_SEED_STRIDE = 100_003
_MAX_BATCH_ITEM_RETRIES = 16


def assert_unique_item_ids(items: list[BenchmarkItem]) -> None:
    """Raise ``ValueError`` when ``items`` contains duplicate ``item_id`` values."""
    seen: set[str] = set()
    duplicates: list[str] = []
    for item in items:
        if item.item_id in seen:
            duplicates.append(item.item_id)
        seen.add(item.item_id)
    if duplicates:
        raise ValueError(
            "duplicate item_id in batch: "
            + ", ".join(sorted(set(duplicates)))
        )


def _batch_slot_seed(batch_seed: int, index: int, slot_retry: int = 0) -> int:
    return batch_seed + index * _BATCH_SEED_STRIDE + slot_retry * _BATCH_SEED_STRIDE * _BATCH_SEED_STRIDE


def generate_c2_batch(
    n: int,
    seed: int,
    *,
    config: ReachabilityGeneratorConfig | None = None,
) -> list[BenchmarkItem]:
    """Generate ``n`` self-verifying C2 items with deterministic per-item seeds."""
    if n < 1:
        raise ValueError("n must be >= 1")

    config = config or ReachabilityGeneratorConfig()
    items: list[BenchmarkItem] = []
    seen_ids: set[str] = set()
    for index in range(n):
        item: BenchmarkItem | None = None
        for slot_retry in range(_MAX_BATCH_ITEM_RETRIES):
            candidate = generate_reachability_item(_batch_slot_seed(seed, index, slot_retry), config)
            self_verify_item(candidate)
            if candidate.item_id not in seen_ids:
                item = candidate
                break
        if item is None:
            raise RuntimeError(
                f"failed to generate unique C2 item_id for batch index={index} "
                f"after {_MAX_BATCH_ITEM_RETRIES} seed retries"
            )
        seen_ids.add(item.item_id)
        items.append(item)

    assert_unique_item_ids(items)
    return items


def generate_f1_batch(
    n: int,
    seed: int,
    *,
    config: SeparationGeneratorConfig | None = None,
) -> list[BenchmarkItem]:
    """Generate ``n`` self-verifying F1 items with deterministic per-item seeds."""
    if n < 1:
        raise ValueError("n must be >= 1")

    items: list[BenchmarkItem] = []
    seen_ids: set[str] = set()
    for index in range(n):
        item: BenchmarkItem | None = None
        for slot_retry in range(_MAX_BATCH_ITEM_RETRIES):
            candidate = generate_separation_item(_batch_slot_seed(seed, index, slot_retry), config)
            if candidate.item_id not in seen_ids:
                item = candidate
                break
        if item is None:
            raise RuntimeError(
                f"failed to generate unique F1 item_id for batch index={index} "
                f"after {_MAX_BATCH_ITEM_RETRIES} seed retries"
            )
        seen_ids.add(item.item_id)
        items.append(item)

    assert_unique_item_ids(items)
    return items


def generate_batch(
    family: str,
    n: int,
    seed: int,
    *,
    c2_config: ReachabilityGeneratorConfig | None = None,
    f1_config: SeparationGeneratorConfig | None = None,
) -> list[BenchmarkItem]:
    if family == "C2":
        return generate_c2_batch(n, seed, config=c2_config)
    if family == "F1":
        return generate_f1_batch(n, seed, config=f1_config)
    raise ValueError(f"unsupported batch family: {family!r}")


def baseline_response(
    baseline: str,
    item: BenchmarkItem,
    *,
    seed: int = 0,
) -> Any:
    return run_baseline(baseline, item, seed=seed)


def evaluate_baseline_on_items(
    baseline: str,
    items: list[BenchmarkItem],
    *,
    seed: int = 0,
) -> list[ScoringRecord]:
    if baseline not in _BASELINES:
        raise ValueError(f"unknown baseline {baseline!r}")
    if not items:
        return []

    family = items[0].family
    if any(item.family != family for item in items):
        raise ValueError("batch items must share the same family")

    records: list[ScoringRecord] = []
    for index, item in enumerate(items):
        item_seed = seed + index
        raw_response = baseline_response(baseline, item, seed=item_seed)
        records.append(score_item(item, raw_response))
    return records


def _run_smoke_baselines(
    family: str,
    n: int,
    seed: int,
    out_dir: str | Path,
    *,
    items: list[BenchmarkItem],
    items_filename: str,
    baseline_seed: int = 0,
) -> list[dict[str, Any]]:
    from fsmreasonbench.evaluator.io import dump_json
    from fsmreasonbench.evaluator.jsonl import write_jsonl

    if n < 1:
        raise ValueError("n must be >= 1")

    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    write_jsonl(root / items_filename, (item.to_full_dict() for item in items))

    combined: list[dict[str, Any]] = []
    for baseline in _SMOKE_BASELINES:
        records = evaluate_baseline_on_items(baseline, items, seed=baseline_seed)
        write_jsonl(root / f"{baseline}_scores.jsonl", (record.to_dict() for record in records))
        summary = summarize_with_baseline(baseline, records)
        dump_json(root / f"{baseline}_summary.json", summary)
        combined.append(summary)

    dump_json(
        root / "combined_summary.json",
        combine_baseline_summaries(combined),
    )
    _ = family
    return combined


def run_c2_smoke_baselines(
    n: int,
    seed: int,
    out_dir: str | Path,
    *,
    config: ReachabilityGeneratorConfig | None = None,
    baseline_seed: int = 0,
) -> list[dict[str, Any]]:
    """Generate one C2 batch and evaluate oracle, random, and invalid baselines."""
    items = generate_c2_batch(n, seed, config=config)
    return _run_smoke_baselines(
        "C2",
        n,
        seed,
        out_dir,
        items=items,
        items_filename="c2_items.jsonl",
        baseline_seed=baseline_seed,
    )


def run_f1_smoke_baselines(
    n: int,
    seed: int,
    out_dir: str | Path,
    *,
    config: SeparationGeneratorConfig | None = None,
    baseline_seed: int = 0,
) -> list[dict[str, Any]]:
    """Generate one F1 batch and evaluate oracle, random, and invalid baselines."""
    items = generate_f1_batch(n, seed, config=config)
    return _run_smoke_baselines(
        "F1",
        n,
        seed,
        out_dir,
        items=items,
        items_filename="f1_items.jsonl",
        baseline_seed=baseline_seed,
    )
