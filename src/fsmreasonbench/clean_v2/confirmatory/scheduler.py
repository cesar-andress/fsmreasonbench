"""Interleaved randomized confirmatory execution scheduler."""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Sequence

from fsmreasonbench.clean_v2.confirmatory.constants import EXECUTION_ORDER_SEED


@dataclass(frozen=True, slots=True)
class PlannedTask:
    item_id: str
    model: str
    condition_id: str
    contract: str
    tool_palette: str
    oracle_info: str
    format_assist: str
    repetition_index: int
    rq_family: str
    condition_fingerprint: str
    planned_position: int
    execution_order_seed: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def task_key(task: PlannedTask | dict[str, Any]) -> str:
    if isinstance(task, PlannedTask):
        d = task.to_dict()
    else:
        d = task
    return "|".join(
        [
            str(d["item_id"]),
            str(d["model"]),
            str(d["condition_id"]),
            str(d["repetition_index"]),
        ]
    )


def build_cartesian_tasks(
    *,
    item_ids: Sequence[str],
    models: Sequence[str],
    conditions: Sequence[dict[str, Any]],
    repetitions: Sequence[int],
    execution_order_seed: int = EXECUTION_ORDER_SEED,
) -> list[dict[str, Any]]:
    """Enumerate item × model × condition × repetition (unsorted)."""
    raw: list[dict[str, Any]] = []
    for item_id in item_ids:
        for model in models:
            for cond in conditions:
                for rep in repetitions:
                    raw.append(
                        {
                            "item_id": item_id,
                            "model": model,
                            "condition_id": cond["condition_id"],
                            "contract": cond["contract"],
                            "tool_palette": cond["tool_palette"],
                            "oracle_info": cond.get("oracle_info", "none"),
                            "format_assist": cond.get("format_assist", "off"),
                            "repetition_index": int(rep),
                            "rq_family": cond.get("rq_family", ""),
                            "condition_fingerprint": cond.get("condition_fingerprint", ""),
                        }
                    )
    return shuffle_tasks(raw, execution_order_seed=execution_order_seed)


def shuffle_tasks(
    tasks: Iterable[dict[str, Any]],
    *,
    execution_order_seed: int = EXECUTION_ORDER_SEED,
) -> list[dict[str, Any]]:
    """
    Deterministic shuffle of the full task list.

    Reconstructible: same seed + same unsorted multiset → same planned_position.
    """
    # Canonical sort before shuffle so input iteration order cannot bias.
    ordered = sorted(
        list(tasks),
        key=lambda t: (
            t["item_id"],
            t["model"],
            t["condition_id"],
            int(t["repetition_index"]),
        ),
    )
    rng = random.Random(execution_order_seed)
    rng.shuffle(ordered)
    planned: list[dict[str, Any]] = []
    for pos, task in enumerate(ordered, start=1):
        row = dict(task)
        row["planned_position"] = pos
        row["execution_order_seed"] = execution_order_seed
        row["actual_start_timestamp"] = None
        row["actual_completion_timestamp"] = None
        row["provider_request_id"] = None
        row["cache_status"] = None
        planned.append(row)
    return planned


def reconstruct_ordering(
    tasks: Iterable[dict[str, Any]],
    *,
    execution_order_seed: int,
) -> list[dict[str, Any]]:
    """Rebuild exact intended ordering from task multiset + seed."""
    stripped = []
    for t in tasks:
        row = {
            k: t[k]
            for k in (
                "item_id",
                "model",
                "condition_id",
                "contract",
                "tool_palette",
                "oracle_info",
                "format_assist",
                "repetition_index",
                "rq_family",
                "condition_fingerprint",
            )
            if k in t
        }
        stripped.append(row)
    return shuffle_tasks(stripped, execution_order_seed=execution_order_seed)


def interleaving_audit(planned: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Check that treatment condition is not deterministically tied to wall-clock order."""
    if not planned:
        return {"n": 0, "condition_run_length_max": 0, "spearman_position_vs_condition_rank": None}
    positions = [int(t["planned_position"]) for t in planned]
    conds = [str(t["condition_id"]) for t in planned]
    # Max consecutive same condition.
    max_run = 1
    run = 1
    for i in range(1, len(conds)):
        if conds[i] == conds[i - 1]:
            run += 1
            max_run = max(max_run, run)
        else:
            run = 1
    # Rank correlation proxy: mean planned position per condition.
    by_cond: dict[str, list[int]] = {}
    for t in planned:
        by_cond.setdefault(str(t["condition_id"]), []).append(int(t["planned_position"]))
    means = {c: sum(v) / len(v) for c, v in by_cond.items()}
    # Fraction of adjacent pairs that share condition (should be ~1/C for random).
    same_adj = sum(1 for i in range(1, len(conds)) if conds[i] == conds[i - 1])
    n_adj = max(len(conds) - 1, 1)
    return {
        "n": len(planned),
        "n_conditions": len(by_cond),
        "condition_run_length_max": max_run,
        "adjacent_same_condition_rate": same_adj / n_adj,
        "mean_planned_position_by_condition": means,
        "position_min": min(positions),
        "position_max": max(positions),
        "execution_order_seed": planned[0].get("execution_order_seed"),
    }


def fingerprint_task_list(planned: Sequence[dict[str, Any]]) -> str:
    payload = [
        {
            "planned_position": t["planned_position"],
            "item_id": t["item_id"],
            "model": t["model"],
            "condition_id": t["condition_id"],
            "repetition_index": t["repetition_index"],
            "execution_order_seed": t["execution_order_seed"],
        }
        for t in planned
    ]
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()
