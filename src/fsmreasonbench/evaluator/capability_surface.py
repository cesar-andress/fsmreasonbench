"""Exploratory capability-surface batch runs for C2 and F1 baselines."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fsmreasonbench.evaluator.batch import (
    _SMOKE_BASELINES,
    evaluate_baseline_on_items,
    generate_batch,
)
from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.evaluator.jsonl import write_jsonl
from fsmreasonbench.evaluator.summary import summarize_scoring_records
from fsmreasonbench.generator.reachability import ReachabilityGeneratorConfig
from fsmreasonbench.generator.separation import SeparationGeneratorConfig

C2_DIFFICULTY_AXIS = "min_witness_length"
F1_DIFFICULTY_AXIS = "min_distinguishing_trace_length"
DEFAULT_C2_LEVELS = (1, 2, 3, 4, 5)
DEFAULT_F1_LEVELS = (1, 2, 3, 4, 5)

_CSV_FIELDS = (
    "family",
    "difficulty_axis",
    "difficulty_level",
    "baseline",
    "n",
    "extractability_rate",
    "verdict_accuracy",
    "certificate_valid_rate",
    "fully_correct_rate",
    "failure_stage_counts",
)


@dataclass(frozen=True, slots=True)
class CapabilitySurfaceConfig:
    families: tuple[str, ...] = ("C2", "F1")
    n_per_level: int = 50
    seed: int = 1
    c2_levels: tuple[int, ...] = DEFAULT_C2_LEVELS
    f1_levels: tuple[int, ...] = DEFAULT_F1_LEVELS
    baseline_seed: int = 0
    skip_failed_levels: bool = False


def run_capability_surface(
    out_dir: str | Path,
    config: CapabilitySurfaceConfig | None = None,
) -> dict[str, Any]:
    """
    Sweep difficulty levels for C2/F1, run baselines, and write summaries.

    Raises ``RuntimeError`` when a level cannot produce ``n_per_level`` items
    unless ``skip_failed_levels`` is enabled.
    """
    config = config or CapabilitySurfaceConfig()
    if config.n_per_level < 1:
        raise ValueError("n_per_level must be >= 1")

    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    skipped_levels: list[dict[str, Any]] = []

    for family in config.families:
        if family == "C2":
            axis = C2_DIFFICULTY_AXIS
            levels = config.c2_levels
        elif family == "F1":
            axis = F1_DIFFICULTY_AXIS
            levels = config.f1_levels
        else:
            raise ValueError(f"unsupported family: {family!r}")

        for level in levels:
            level_dir = root / family / f"{axis}_{level}"
            level_seed = _level_seed(config.seed, family, level)
            try:
                level_rows = _run_family_level(
                    family,
                    axis,
                    level,
                    config.n_per_level,
                    level_seed,
                    level_dir,
                    baseline_seed=config.baseline_seed,
                )
            except RuntimeError as exc:
                if not config.skip_failed_levels:
                    raise RuntimeError(
                        f"failed to generate {config.n_per_level} {family} items for "
                        f"{axis}={level}: {exc}"
                    ) from exc
                skipped_levels.append(
                    {
                        "family": family,
                        "difficulty_axis": axis,
                        "difficulty_level": level,
                        "error": str(exc),
                    }
                )
                continue
            rows.extend(level_rows)

    payload = {
        "families": list(config.families),
        "n_per_level": config.n_per_level,
        "seed": config.seed,
        "baseline_seed": config.baseline_seed,
        "rows": rows,
        "skipped_levels": skipped_levels,
    }
    dump_json(root / "combined_summary.json", payload)
    write_capability_surface_csv(root / "combined_summary.csv", rows)
    return payload


def _run_family_level(
    family: str,
    axis: str,
    level: int,
    n: int,
    seed: int,
    level_dir: Path,
    *,
    baseline_seed: int,
) -> list[dict[str, Any]]:
    level_dir.mkdir(parents=True, exist_ok=True)

    if family == "C2":
        batch_config = ReachabilityGeneratorConfig(
            min_witness_length=level,
            max_witness_length=12,
        )
        items = generate_batch(
            "C2",
            n,
            seed,
            c2_config=batch_config,
        )
    else:
        batch_config = SeparationGeneratorConfig(
            min_distinguishing_trace_length=level,
            max_distinguishing_trace_length=12,
        )
        items = generate_batch(
            "F1",
            n,
            seed,
            f1_config=batch_config,
        )

    write_jsonl(level_dir / "items.jsonl", (item.to_full_dict() for item in items))

    rows: list[dict[str, Any]] = []
    for baseline in _SMOKE_BASELINES:
        records = evaluate_baseline_on_items(baseline, items, seed=baseline_seed)
        write_jsonl(
            level_dir / f"{baseline}_scores.jsonl",
            (record.to_dict() for record in records),
        )
        summary = summarize_scoring_records(records)
        summary_payload = {
            "family": family,
            "difficulty_axis": axis,
            "difficulty_level": level,
            "baseline": baseline,
            **summary,
        }
        dump_json(level_dir / f"{baseline}_summary.json", summary_payload)
        rows.append(summary_payload)
    return rows


def _level_seed(base_seed: int, family: str, level: int) -> int:
    family_offset = 0 if family == "C2" else 100_000
    return base_seed + family_offset + level * 1_000


def write_capability_surface_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "family": row["family"],
                    "difficulty_axis": row["difficulty_axis"],
                    "difficulty_level": row["difficulty_level"],
                    "baseline": row["baseline"],
                    "n": row["n"],
                    "extractability_rate": row["extractability_rate"],
                    "verdict_accuracy": row["verdict_accuracy"],
                    "certificate_valid_rate": row["certificate_valid_rate"],
                    "fully_correct_rate": row["fully_correct_rate"],
                    "failure_stage_counts": json.dumps(
                        row["failure_stage_counts"],
                        sort_keys=True,
                    ),
                }
            )
