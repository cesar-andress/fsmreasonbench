"""Balanced C2 reachability cohort (50 reachable / 50 unreachable, n=100)."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from fsmreasonbench.cohort.expanded_n100 import C2_GENERATOR_CONFIG
from fsmreasonbench.cohort.freeze import freeze_cohort
from fsmreasonbench.evaluator.batch import assert_unique_item_ids
from fsmreasonbench.evaluator.jsonl import write_jsonl
from fsmreasonbench.generator.reachability import ReachabilityGeneratorConfig, generate_reachability_item
from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.runtime.reachability import reachable_states

BALANCED_COHORT_VERSION = "v0.1-expanded-n100"
BALANCED_C2_SUBDIR = "c2-reachability-balanced-n100"
BALANCED_C2_COHORT_ID = "c2-reachability-balanced-n100-v0.1-expanded"
DEFAULT_ITEM_COUNT = 100
BALANCED_BATCH_SEED = 5001
_SLOT_STRIDE = 100_003


def _slot_seed(index: int, *, positive: bool, slot_retry: int = 0) -> int:
    base = BALANCED_BATCH_SEED + (0 if positive else 50_000)
    return base + index * _SLOT_STRIDE + slot_retry * _SLOT_STRIDE * _SLOT_STRIDE


def enrich_c2_item_metadata(item: BenchmarkItem) -> BenchmarkItem:
    """Add subtype stratification fields to difficulty.core."""
    certificate = item.answer_key["certificate"]
    cert_type = certificate["certificate_type"]
    reachable = bool(item.answer_key["verdict"])
    core = dict(item.difficulty.get("core") or {})
    core.update(
        {
            "reachable": reachable,
            "certificate_type": cert_type,
            "state_count": len(item.fsm.states),
            "alphabet_size": len(item.fsm.input_alphabet),
            "transition_count": len(item.fsm.transitions),
            "subtype": "existential" if reachable else "universal",
        }
    )
    if not reachable:
        payload = certificate.get("payload") or {}
        reachable_states_list = payload.get("reachable_states")
        if isinstance(reachable_states_list, list):
            core["reachable_set_size"] = len(reachable_states_list)
        else:
            core["reachable_set_size"] = len(reachable_states(item.fsm))
    difficulty = {**item.difficulty, "core": core}
    return replace(item, difficulty=difficulty)


def generate_c2_balanced_items(
    n: int = DEFAULT_ITEM_COUNT,
    *,
    config: ReachabilityGeneratorConfig | None = None,
) -> list[BenchmarkItem]:
    if n < 2 or n % 2 != 0:
        raise ValueError("balanced C2 cohort requires even n >= 2")
    config = config or C2_GENERATOR_CONFIG
    half = n // 2
    items: list[BenchmarkItem] = []
    seen_ids: set[str] = set()

    for want_positive, count in ((True, half), (False, half)):
        for index in range(count):
            item: BenchmarkItem | None = None
            for slot_retry in range(16):
                candidate = generate_reachability_item(
                    _slot_seed(index, positive=want_positive, slot_retry=slot_retry),
                    config,
                    force_positive=want_positive,
                )
                candidate = enrich_c2_item_metadata(candidate)
                if bool(candidate.answer_key["verdict"]) != want_positive:
                    continue
                if candidate.item_id not in seen_ids:
                    item = candidate
                    break
            if item is None:
                raise RuntimeError(
                    f"failed to generate unique balanced C2 item "
                    f"(positive={want_positive}, index={index})"
                )
            seen_ids.add(item.item_id)
            items.append(item)

    assert_unique_item_ids(items)
    verdicts = [item.answer_key["verdict"] for item in items]
    if sum(verdicts) != half:
        raise ValueError(f"expected {half} reachable items, got {sum(verdicts)}")
    return items


def build_balanced_c2_cohort(
    repo_root: str | Path,
    *,
    item_count: int = DEFAULT_ITEM_COUNT,
    cohort_root: str | Path | None = None,
) -> dict[str, Any]:
    repo_root = Path(repo_root)
    root = Path(cohort_root) if cohort_root is not None else repo_root / "cohorts" / BALANCED_COHORT_VERSION
    cohort_dir = root / BALANCED_C2_SUBDIR
    staging = repo_root / "runs" / "_c2_balanced_n100_staging" / "items.jsonl"

    items = generate_c2_balanced_items(item_count)
    write_jsonl(staging, (item.to_full_dict() for item in items))
    manifest = freeze_cohort(
        staging,
        BALANCED_C2_COHORT_ID,
        cohort_dir,
        generator_notes=(
            f"Balanced C2 reachability cohort: {item_count // 2} reachable (trace_witness) + "
            f"{item_count // 2} unreachable (unreachability_witness), "
            f"batch_seed={BALANCED_BATCH_SEED}, generator config matches expanded-n100 level-3 slice."
        ),
        generation_parameters={
            "family": "C2",
            "item_count": item_count,
            "balanced": True,
            "reachable_count": item_count // 2,
            "unreachable_count": item_count // 2,
            "batch_seed": BALANCED_BATCH_SEED,
            "config": {
                "min_witness_length": C2_GENERATOR_CONFIG.min_witness_length,
                "max_witness_length": C2_GENERATOR_CONFIG.max_witness_length,
                "state_count": C2_GENERATOR_CONFIG.state_count,
                "include_negative": C2_GENERATOR_CONFIG.include_negative,
            },
        },
    )
    return {"cohort_dir": str(cohort_dir), "manifest": manifest, "item_count": item_count}


def resolve_balanced_c2_cohort(cohort_root: str | Path) -> tuple[Path, str]:
    root = Path(cohort_root)
    cohort_dir = root / BALANCED_C2_SUBDIR
    from fsmreasonbench.cohort.expanded_n100 import load_cohort_id_from_manifest

    return cohort_dir / "items.jsonl", load_cohort_id_from_manifest(cohort_dir)
