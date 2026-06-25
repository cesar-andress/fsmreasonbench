"""Run-to-run replicate studies for frontier campaigns (Experiment A)."""

from __future__ import annotations

import json
import math
import random
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.experiments.frontier_campaigns import (
    FrontierCampaignConfig,
    build_track_pilot_config,
    load_frontier_campaign_config,
)

REPLICATE_METRICS: tuple[str, ...] = (
    "extractability_rate",
    "verdict_accuracy",
    "certificate_valid_rate",
    "fully_correct_rate",
)

DEFAULT_BOOTSTRAP_RESAMPLES = 1000
DEFAULT_BOOTSTRAP_ALPHA = 0.05


def replicate_dir_name(replicate_id: int) -> str:
    if replicate_id < 1:
        raise ValueError("replicate_id must be >= 1")
    return f"replicate_{replicate_id:02d}"


def replicate_study_root(base_out_dir: str | Path) -> Path:
    """Study root that holds replicate_* subdirectories."""
    base = Path(base_out_dir)
    if base.name.endswith("_replicates"):
        return base
    return base.parent / f"{base.name}_replicates"


@dataclass(frozen=True, slots=True)
class ReplicateStudyConfig:
    base_campaign_config: Path
    study_root: Path
    replicates: int = 1
    bootstrap_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES
    bootstrap_seed: int = 4242


def load_replicate_study_config(path: str | Path) -> ReplicateStudyConfig:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("replicate study config must be a JSON object")
    base_config = Path(payload["base_campaign_config"])
    study_root = payload.get("study_root")
    if study_root is None:
        campaign = load_frontier_campaign_config(base_config)
        study_root = str(replicate_study_root(campaign.out_dir))
    return ReplicateStudyConfig(
        base_campaign_config=base_config,
        study_root=Path(study_root),
        replicates=int(payload.get("replicates", 1)),
        bootstrap_resamples=int(payload.get("bootstrap_resamples", DEFAULT_BOOTSTRAP_RESAMPLES)),
        bootstrap_seed=int(payload.get("bootstrap_seed", 4242)),
    )


def replicate_campaign_out_dir(study_root: Path, replicate_id: int) -> Path:
    return study_root / replicate_dir_name(replicate_id)


def build_replicate_track_pilot_config(
    campaign: FrontierCampaignConfig,
    repo_root: Path,
    *,
    replicate_id: int,
    study_root: Path,
) -> Any:
    """Return TrackPilotModelsConfig with out_dir under replicate_XX/."""
    from dataclasses import replace

    replicate_out = replicate_campaign_out_dir(study_root, replicate_id)
    try:
        rel_out = replicate_out.relative_to(repo_root)
    except ValueError:
        rel_out = replicate_out
    campaign_copy = replace(campaign, out_dir=str(rel_out))
    return build_track_pilot_config(campaign_copy, repo_root)


def _cell_key(row: dict[str, Any]) -> tuple[str, ...]:
    return (
        str(row.get("model_dir") or row.get("model", "")),
        str(row.get("family", "")),
        str(row.get("track", "")),
        str(row.get("temperature", "")),
    )


def _metric_value(row: dict[str, Any], metric: str) -> float | None:
    if metric not in row or row[metric] is None:
        return None
    try:
        return float(row[metric])
    except (TypeError, ValueError):
        return None


def _aggregate_metric_stats(
    values: list[float],
    *,
    bootstrap_resamples: int,
    seed: int,
) -> dict[str, float | None]:
    if not values:
        return {
            "mean": None,
            "std": None,
            "min": None,
            "max": None,
            "coefficient_of_variation": None,
            "bootstrap_ci_low": None,
            "bootstrap_ci_high": None,
            "n_replicates": 0,
        }
    mean = statistics.fmean(values)
    std = statistics.pstdev(values) if len(values) > 1 else 0.0
    cv = (std / mean) if mean not in (0.0,) and mean is not None else None
    low_q = DEFAULT_BOOTSTRAP_ALPHA / 2.0
    high_q = 1.0 - DEFAULT_BOOTSTRAP_ALPHA / 2.0
    if len(values) == 1:
        ci_low, ci_high = values[0], values[0]
    else:
        rng = random.Random(seed)
        samples: list[float] = []
        for _ in range(bootstrap_resamples):
            draw = [values[rng.randrange(len(values))] for _ in range(len(values))]
            samples.append(statistics.fmean(draw))
        samples.sort()
        ci_low = _percentile(samples, low_q)
        ci_high = _percentile(samples, high_q)
    return {
        "mean": round(mean, 6),
        "std": round(std, 6),
        "min": round(min(values), 6),
        "max": round(max(values), 6),
        "coefficient_of_variation": round(cv, 6) if cv is not None else None,
        "bootstrap_ci_low": round(ci_low, 6),
        "bootstrap_ci_high": round(ci_high, 6),
        "n_replicates": len(values),
    }


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    rank = quantile * (len(values) - 1)
    low = int(math.floor(rank))
    high = int(math.ceil(rank))
    if low == high:
        return values[low]
    weight = rank - low
    return values[low] * (1.0 - weight) + values[high] * weight


def collect_replicate_track_rows(study_root: Path) -> dict[tuple[str, ...], list[dict[str, Any]]]:
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for rep_dir in sorted(study_root.glob("replicate_*")):
        if not rep_dir.is_dir():
            continue
        combined_path = rep_dir / "combined_summary.json"
        if not combined_path.exists():
            continue
        payload = json.loads(combined_path.read_text(encoding="utf-8"))
        rows = payload.get("track_rows") or payload.get("cell_inventory") or []
        for row in rows:
            if row.get("extended_status", row.get("cell_status", "completed")) != "completed":
                if row.get("status") != "completed":
                    continue
            key = _cell_key(row)
            grouped.setdefault(key, []).append(dict(row))
    return grouped


def build_aggregate_replicates(
    study_root: Path,
    *,
    campaign_id: str,
    provider: str,
    model: str,
    bootstrap_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    bootstrap_seed: int = 4242,
) -> dict[str, Any]:
    grouped = collect_replicate_track_rows(study_root)
    cells: list[dict[str, Any]] = []
    for key, rows in sorted(grouped.items()):
        model_dir, family, track, temperature = key
        cell_payload: dict[str, Any] = {
            "model_dir": model_dir,
            "family": family,
            "track": track,
            "temperature": temperature,
            "replicate_dirs": [str(r.get("run_dir", "")) for r in rows],
            "metrics": {},
        }
        for metric in REPLICATE_METRICS:
            values = [
                v
                for v in (_metric_value(row, metric) for row in rows)
                if v is not None
            ]
            cell_payload["metrics"][metric] = _aggregate_metric_stats(
                values,
                bootstrap_resamples=bootstrap_resamples,
                seed=bootstrap_seed + hash((family, track, metric)) % 10_000,
            )
        cells.append(cell_payload)
    return {
        "experiment": "frontier_replicate_study",
        "campaign_id": campaign_id,
        "provider": provider,
        "model": model,
        "study_root": str(study_root),
        "replicate_count": len(list(study_root.glob("replicate_*"))),
        "cells": cells,
    }


def write_aggregate_replicates(
    study_root: Path,
    payload: dict[str, Any],
) -> Path:
    study_root.mkdir(parents=True, exist_ok=True)
    out_path = study_root / "aggregate_replicates.json"
    dump_json(out_path, payload)
    return out_path


def list_pending_replicates(study_root: Path, replicates: int) -> list[int]:
    pending: list[int] = []
    for replicate_id in range(1, replicates + 1):
        rep_dir = replicate_campaign_out_dir(study_root, replicate_id)
        combined = rep_dir / "combined_summary.json"
        if not combined.exists():
            pending.append(replicate_id)
    return pending
