"""Multi-model R0/R1/R2 track pilot evaluation across frozen exploratory cohorts."""

from __future__ import annotations

import csv
import json
import os
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable

from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.evaluator.jsonl import load_items_jsonl
from fsmreasonbench.evaluator.models import FailureStage
from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.runners.cell_failure import (
    classify_cell_error,
    error_message_from_payload,
    infer_distinguishing_trace_root_cause,
    is_cell_complete,
)
from fsmreasonbench.runners.experiment_cells import (
    DEFAULT_STALE_RUNNING_SECONDS,
    build_cell_plans,
    build_incomplete_from_status,
    classify_cell,
    completed_item_ids,
    compute_config_hash,
    detect_cell_status,
    finalize_abandoned_running_cell,
    mark_cell_completed,
    mark_cell_failed,
    mark_cell_running,
    prepare_cell_rerun,
    should_run_cell,
    summarize_extended_inventory,
)
from fsmreasonbench.runners.item_watchdog import CellItemFailureLimitExceeded
from fsmreasonbench.runners.ollama_batch import GenerateFn, OllamaBatchConfig, OllamaBatchResult
from fsmreasonbench.runners.ollama_track_batch import run_ollama_track_batch
from fsmreasonbench.runners.pilot_models import model_dir_name
from fsmreasonbench.runners.providers.base import (
    API_PROVIDERS_WITH_MAX_TOKENS,
    estimate_frontier_run,
    validate_provider_tracks,
    write_provider_dry_run_diagnostic,
)
from fsmreasonbench.runners.provider_errors import DEFAULT_MAX_PROVIDER_RETRY_DELAY_SECONDS
from fsmreasonbench.tracks.delegation import DELEGATION_GAP_METRICS, compute_delegation_gap
from fsmreasonbench.tracks.models import TrackId

GenerateFactory = Callable[[str, float], GenerateFn]

DEFAULT_C2_ITEMS = "cohorts/v0.1-exploratory/c2-reachability-level3/items.jsonl"
DEFAULT_F1_ITEMS = "cohorts/v0.1-exploratory/f1-mixed-level3/items.jsonl"
DEFAULT_C2_COHORT_ID = "c2-reachability-level3-v0.1-exploratory"
DEFAULT_F1_COHORT_ID = "f1-mixed-level3-v0.1-exploratory"
EXPANDED_COHORT_ROOT = "cohorts/v0.1-expanded-n100"
EXPANDED_C2_ITEMS = f"{EXPANDED_COHORT_ROOT}/c2-reachability-level3/items.jsonl"
EXPANDED_F1_ITEMS = f"{EXPANDED_COHORT_ROOT}/f1-mixed-level3/items.jsonl"
EXPANDED_C2_COHORT_ID = "c2-reachability-level3-v0.1-expanded-n100"
EXPANDED_F1_COHORT_ID = "f1-mixed-level3-v0.1-expanded-n100"
TRACK_IDS = ("R0", "R1", "R2")
FAMILY_IDS = ("C2", "F1")

_TRACK_ROW_FIELDS = (
    "model",
    "model_dir",
    "family",
    "track",
    "temperature",
    "cohort_id",
    "n",
    "extractability_rate",
    "verdict_accuracy",
    "certificate_valid_rate",
    "fully_correct_rate",
    "tool_invocation_rate",
    "average_tool_calls_per_item",
    "failure_stage_counts",
    "track_failure_counts",
    "run_dir",
    "status",
)

_FAILURE_STAGE_ORDER = tuple(stage.value for stage in FailureStage)

_TOOL_FAILURE_CLASSES = (
    "no_tool_plan",
    "invalid_tool_plan",
    "disallowed_tool",
    "tool_execution_error",
)

_SUBMISSION_FAILURE_CLASSES = (
    "final_submission_not_extractable",
    "verdict_wrong",
    "certificate_invalid",
    "correct",
)

_RESEARCH_QUESTIONS = (
    ("RQ-L1", "Does tool access improve verdict accuracy, certificate validity, or both?"),
    ("RQ-L2", "Does temperature improve exploration or degrade certificate compliance?"),
    (
        "RQ-L3",
        "Do larger/local-coder models improve contract-verified success more than verdict accuracy?",
    ),
    ("RQ-L4", "Are delegation gaps family-specific?"),
)


@dataclass(frozen=True, slots=True)
class TrackPilotModelsConfig:
    models: tuple[str, ...]
    families: tuple[str, ...]
    tracks: tuple[str, ...]
    c2_items_path: str | Path
    f1_items_path: str | Path
    out_dir: str | Path
    max_items: int = 20
    temperatures: tuple[float, ...] = (0.0,)
    timeout: float | None = 120.0
    skip_completed: bool = True
    retry_failed: bool = False
    skip_failed: bool = False
    force: bool = False
    force_all: bool = False
    force_cell: bool = False
    resume_items: bool = True
    dry_run: bool = False
    report_only: bool = False
    max_cells: int | None = None
    cell_timeout: float | None = None
    item_timeout: float | None = None
    ollama_retries: int = 0
    provider_retries: int = 0
    ollama_restart_on_timeout: bool = False
    skip_item_on_timeout: bool = True
    ollama_stop_delay_seconds: float = 5.0
    provider_retry_backoff_seconds: float = 5.0
    provider_max_retry_delay_seconds: float = DEFAULT_MAX_PROVIDER_RETRY_DELAY_SECONDS
    provider_sleep_between_items: float = 0.0
    fail_cell_after_item_failures: int | None = None
    sleep_between_cells: float = 5.0
    stop_after_failures: int = 3
    stale_running_seconds: float = DEFAULT_STALE_RUNNING_SECONDS
    incremental_safe: bool = False
    matrix_layout: bool = False
    provider: str = "ollama"
    max_tokens: int = 8192
    provider_dry_run: bool = False
    estimate_only: bool = False
    ollama_base_url: str = "http://localhost:11434"
    c2_cohort_id: str = DEFAULT_C2_COHORT_ID
    f1_cohort_id: str = DEFAULT_F1_COHORT_ID

    @property
    def use_temperature_dirs(self) -> bool:
        return self.matrix_layout

    @property
    def effective_force_all(self) -> bool:
        return self.force or self.force_all


@dataclass(frozen=True, slots=True)
class TrackPilotModelsResult:
    track_rows: list[dict[str, Any]]
    delegation_rows: list[dict[str, Any]]
    temperature_delta_rows: list[dict[str, Any]]
    failed_cells: list[dict[str, Any]]
    cell_inventory: list[dict[str, Any]]
    cell_status_counts: dict[str, int]
    out_dir: Path


def parse_temperatures(raw: str) -> tuple[float, ...]:
    values: list[float] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        values.append(float(part))
    if not values:
        raise ValueError("expected at least one temperature")
    return tuple(values)


def temperature_dir_name(temperature: float) -> str:
    return f"temp_{temperature:g}"


def infer_matrix_layout(out_dir: str | Path) -> bool:
    """Return True when ``out_dir`` uses local-matrix temp_* cell directories."""
    root = Path(out_dir)
    summary_path = root / "combined_summary.json"
    if summary_path.exists():
        try:
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        if payload.get("experiment") == "local_matrix":
            return True
    return "local_matrix" in root.name


def build_cell_dir(
    out_dir: str | Path,
    model: str,
    family: str,
    temperature: float,
    track: str,
    *,
    matrix_layout: bool = True,
) -> Path:
    base = Path(out_dir) / model_dir_name(model) / family
    if matrix_layout:
        base = base / temperature_dir_name(temperature)
    return base / track


def cell_dir(
    out_dir: Path,
    model: str,
    family: str,
    track: str,
    *,
    temperature: float = 0.0,
    use_temperature_dirs: bool = False,
    matrix_layout: bool | None = None,
) -> Path:
    """Backward-compatible alias for :func:`build_cell_dir`."""
    layout = use_temperature_dirs if matrix_layout is None else matrix_layout
    return build_cell_dir(
        out_dir,
        model,
        family,
        temperature,
        track,
        matrix_layout=layout,
    )


# Re-export for tests and downstream callers
__all__ = [
    "TrackPilotModelsConfig",
    "TrackPilotModelsResult",
    "build_cell_dir",
    "build_delegation_rows",
    "build_temperature_delta_rows",
    "build_track_row",
    "cell_dir",
    "format_cell_timeout_message",
    "format_item_timeout_message",
    "resolved_item_timeout",
    "hydrate_report_only_config",
    "infer_matrix_layout",
    "is_cell_complete",
    "load_cell_summary",
    "parse_temperatures",
    "render_track_pilot_report",
    "run_track_pilot_models",
    "scan_matrix_inventory",
    "temperature_dir_name",
    "write_track_pilot_csv",
]


def load_cell_summary(run_dir: Path) -> dict[str, Any]:
    for name in ("track_summary.json", "summary.json"):
        candidate = run_dir / name
        if candidate.exists():
            return json.loads(candidate.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"no summary under {run_dir}")


def build_track_row(
    summary: dict[str, Any],
    *,
    model: str,
    family: str,
    track: str,
    temperature: float,
    cohort_id: str,
    run_dir: Path,
    status: str = "completed",
) -> dict[str, Any]:
    return {
        "model": model,
        "model_dir": model_dir_name(model),
        "family": family,
        "track": track,
        "temperature": temperature,
        "cohort_id": cohort_id,
        "n": summary.get("n"),
        "extractability_rate": summary.get("extractability_rate"),
        "verdict_accuracy": summary.get("verdict_accuracy"),
        "certificate_valid_rate": summary.get("certificate_valid_rate"),
        "fully_correct_rate": summary.get("fully_correct_rate"),
        "tool_invocation_rate": summary.get("tool_invocation_rate", 0.0),
        "average_tool_calls_per_item": summary.get("average_tool_calls_per_item", 0.0),
        "failure_stage_counts": summary.get("failure_stage_counts", {}),
        "track_failure_counts": summary.get("track_failure_counts", {}),
        "infrastructure_failure_count": summary.get("infrastructure_failure_count", 0),
        "provider_error_count": summary.get("provider_error_count", 0),
        "provider_quota_error_count": summary.get("provider_quota_error_count", 0),
        "provider_rate_limit_count": summary.get("provider_rate_limit_count", 0),
        "provider_insufficient_credit_count": summary.get(
            "provider_insufficient_credit_count", 0
        ),
        "model_extractability_rate": summary.get("model_extractability_rate"),
        "model_scored_n": summary.get("model_scored_n"),
        "provider_failure_warning": summary.get("provider_failure_warning"),
        "run_dir": str(run_dir),
        "status": status,
    }


def _row_index_key(row: dict[str, Any]) -> tuple[str, str, float, str]:
    return (row["model"], row["family"], float(row["temperature"]), row["track"])


def build_delegation_rows(track_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compute R1−R0, R2−R0, and R2−R1 delegation gaps per model × family × temperature."""
    indexed: dict[tuple[str, str, float, str], dict[str, Any]] = {}
    for row in track_rows:
        if row.get("status") != "completed":
            continue
        indexed[_row_index_key(row)] = row

    delegation_rows: list[dict[str, Any]] = []
    keys = sorted(
        {
            (row["model"], row["family"], float(row["temperature"]))
            for row in track_rows
            if row.get("status") == "completed"
        }
    )

    for model, family, temperature in keys:
        r0 = indexed.get((model, family, temperature, "R0"))
        r1 = indexed.get((model, family, temperature, "R1"))
        r2 = indexed.get((model, family, temperature, "R2"))
        if r0 is None:
            continue

        row: dict[str, Any] = {
            "model": model,
            "family": family,
            "temperature": temperature,
            "cohort_id": r0.get("cohort_id"),
            "n": r0.get("n"),
        }
        missing_tracks: list[str] = []
        if r1 is None:
            missing_tracks.append("R1")
        if r2 is None:
            missing_tracks.append("R2")
        if missing_tracks:
            row["missing_tracks"] = missing_tracks
            row["delegation_incomplete"] = True
        if r1 is not None:
            gap = compute_delegation_gap(_summary_from_row(r0), _summary_from_row(r1))
            for metric, value in gap["delegation_gap"].items():
                row[f"delta_R1_minus_R0_{metric}"] = value
        if r2 is not None:
            gap = compute_delegation_gap(_summary_from_row(r0), _summary_from_row(r2))
            for metric, value in gap["delegation_gap"].items():
                row[f"delta_R2_minus_R0_{metric}"] = value
        if r1 is not None and r2 is not None:
            gap = compute_delegation_gap(_summary_from_row(r1), _summary_from_row(r2))
            for metric, value in gap["delegation_gap"].items():
                row[f"delta_R2_minus_R1_{metric}"] = value
        delegation_rows.append(row)
    return delegation_rows


def build_temperature_delta_rows(track_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compute metric deltas between temperatures per model × family × track."""
    indexed: dict[tuple[str, str, float, str], dict[str, Any]] = {}
    for row in track_rows:
        if row.get("status") != "completed":
            continue
        indexed[_row_index_key(row)] = row

    delta_rows: list[dict[str, Any]] = []
    keys = sorted(
        {
            (row["model"], row["family"], row["track"])
            for row in track_rows
            if row.get("status") == "completed"
        }
    )
    baseline = 0.0
    comparisons = ((0.2, "delta_temp_0.2_minus_0.0"), (0.7, "delta_temp_0.7_minus_0.0"))

    for model, family, track in keys:
        base_row = indexed.get((model, family, baseline, track))
        if base_row is None:
            continue
        row: dict[str, Any] = {
            "model": model,
            "family": family,
            "track": track,
            "baseline_temperature": baseline,
            "n": base_row.get("n"),
        }
        for target_temp, prefix in comparisons:
            target_row = indexed.get((model, family, target_temp, track))
            if target_row is None:
                continue
            for metric in DELEGATION_GAP_METRICS:
                row[f"{prefix}_{metric}"] = target_row[metric] - base_row[metric]
        if any(key.startswith("delta_temp_") for key in row):
            delta_rows.append(row)
    return delta_rows


def _summary_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "family": row["family"],
        "n": row["n"],
        "track": row["track"],
        "cohort_id": row.get("cohort_id"),
        **{metric: row[metric] for metric in DELEGATION_GAP_METRICS},
    }


def apply_incremental_safe(config: TrackPilotModelsConfig) -> TrackPilotModelsConfig:
    if not config.incremental_safe:
        return config
    return replace(
        config,
        stop_after_failures=1,
        sleep_between_cells=10.0,
        resume_items=True,
    )


def hydrate_report_only_config(
    root: Path,
    config: TrackPilotModelsConfig,
) -> TrackPilotModelsConfig:
    """Load matrix axes from on-disk artifacts so --report-only matches the original run."""
    disk_axes = _discover_report_axes_from_disk(root)
    updates: dict[str, Any] = {
        "matrix_layout": disk_axes.get("matrix_layout", infer_matrix_layout(root)),
    }
    for field in ("models", "families", "tracks", "temperatures"):
        disk_value = disk_axes.get(field)
        if disk_value:
            updates[field] = disk_value

    summary_path = root / "combined_summary.json"
    if summary_path.exists():
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
        for field in ("models", "families", "tracks", "temperatures"):
            if field in updates:
                continue
            raw = payload.get(field)
            if raw:
                updates[field] = tuple(raw)
        if payload.get("max_items") is not None:
            updates["max_items"] = int(payload["max_items"])
        if "timeout" in payload:
            updates["timeout"] = payload["timeout"]
        if "item_timeout" in payload:
            updates["item_timeout"] = payload["item_timeout"]
        if payload.get("max_tokens") is not None:
            updates["max_tokens"] = int(payload["max_tokens"])
        if payload.get("provider"):
            updates["provider"] = payload["provider"]
        cohort_ids = payload.get("cohort_ids") or {}
        if cohort_ids.get("C2"):
            updates["c2_cohort_id"] = cohort_ids["C2"]
        if cohort_ids.get("F1"):
            updates["f1_cohort_id"] = cohort_ids["F1"]
    return replace(config, **updates)


def _discover_report_axes_from_disk(root: Path) -> dict[str, Any]:
    from fsmreasonbench.runners.local_matrix_paths import infer_model_from_artifacts

    matrix_layout = infer_matrix_layout(root)
    models: list[str] = []
    seen_models: set[str] = set()
    families: set[str] = set()
    tracks: set[str] = set()
    temperatures: set[float] = set()

    for model_path in sorted(root.iterdir()):
        if not model_path.is_dir() or model_path.name in {"plots"}:
            continue
        for family in ("C2", "F1"):
            family_path = model_path / family
            if not family_path.is_dir():
                continue
            families.add(family)
            if matrix_layout:
                for temp_path in sorted(family_path.iterdir()):
                    if not temp_path.is_dir() or not temp_path.name.startswith("temp_"):
                        continue
                    temperatures.add(float(temp_path.name.removeprefix("temp_")))
                    for track_path in sorted(temp_path.iterdir()):
                        if not track_path.is_dir():
                            continue
                        try:
                            TrackId(track_path.name)
                        except ValueError:
                            continue
                        tracks.add(track_path.name)
                        model = infer_model_from_artifacts(
                            track_path,
                            model_dir=model_path.name,
                        )
                        if model and model not in seen_models:
                            seen_models.add(model)
                            models.append(model)
            else:
                for track_path in sorted(family_path.iterdir()):
                    if not track_path.is_dir():
                        continue
                    try:
                        TrackId(track_path.name)
                    except ValueError:
                        continue
                    tracks.add(track_path.name)
                    model = infer_model_from_artifacts(
                        track_path,
                        model_dir=model_path.name,
                    )
                    if model and model not in seen_models:
                        seen_models.add(model)
                        models.append(model)

    result: dict[str, Any] = {"matrix_layout": matrix_layout}
    if models:
        result["models"] = tuple(models)
    if families:
        result["families"] = tuple(sorted(families))
    if tracks:
        result["tracks"] = tuple(sorted(tracks, key=lambda track: TRACK_IDS.index(track)))
    if temperatures:
        result["temperatures"] = tuple(sorted(temperatures))
    return result


def _item_sources(config: TrackPilotModelsConfig) -> dict[str, str]:
    return {"C2": str(config.c2_items_path), "F1": str(config.f1_items_path)}


def resolved_item_timeout(config: TrackPilotModelsConfig) -> float | None:
    """Return the per-item HTTP timeout, or None when disabled."""
    if config.item_timeout is not None:
        return config.item_timeout
    return config.timeout


def format_cell_timeout_message(cell_timeout: float) -> str:
    return f"cell exceeded timeout of {cell_timeout:g}s"


def format_item_timeout_message(item_timeout: float | None) -> str:
    if item_timeout is None:
        return "operation timed out (no item timeout configured)"
    return f"item request exceeded timeout of {item_timeout:g}s"


def _log_cell_startup(
    *,
    model: str,
    family: str,
    track: str,
    temperature: float,
    phase: str,
    **details: Any,
) -> None:
    suffix = " ".join(f"{key}={value!r}" for key, value in details.items())
    message = (
        f"cell-startup: model={model!r} family={family} track={track} "
        f"temp={temperature:g} phase={phase}"
    )
    if suffix:
        message = f"{message} {suffix}"
    print(message, file=sys.stderr, flush=True)


def _cell_execution_config_hash(
    *,
    model: str,
    family: str,
    track: str,
    temperature: float,
    item_source: str,
    max_items: int,
    timeout: float | None,
    item_timeout: float | None,
    provider: str,
    max_tokens: int,
) -> str:
    return compute_config_hash(
        {
            "model": model,
            "family": family,
            "track": track,
            "temperature": temperature,
            "item_source": item_source,
            "max_items": max_items,
            "timeout": timeout,
            "item_timeout": item_timeout,
            "provider": provider,
            "max_tokens": max_tokens,
        }
    )


def _run_cell_batch(
    *,
    items: list[BenchmarkItem],
    generate: GenerateFn,
    run_dir: Path,
    model: str,
    family: str,
    track: str,
    temperature: float,
    config: TrackPilotModelsConfig,
    item_timeout: float | None,
) -> OllamaBatchResult:
    _log_cell_startup(
        model=model,
        family=family,
        track=track,
        temperature=temperature,
        phase="run_ollama_track_batch",
        provider=config.provider,
        item_count=len(items),
        max_items=config.max_items,
    )
    return run_ollama_track_batch(
        items,
        generate,
        run_dir / "results.jsonl",
        OllamaBatchConfig(
            model=model,
            temperature=temperature,
            timeout=item_timeout,
            max_items=config.max_items,
            resume_items=config.resume_items,
            force_cell=config.force_cell or config.effective_force_all,
            provider=config.provider,
            max_tokens=(
                config.max_tokens
                if config.provider in API_PROVIDERS_WITH_MAX_TOKENS
                else None
            ),
            ollama_retries=config.ollama_retries,
            provider_retries=config.provider_retries,
            ollama_restart_on_timeout=config.ollama_restart_on_timeout,
            skip_item_on_timeout=config.skip_item_on_timeout,
            ollama_stop_delay_seconds=config.ollama_stop_delay_seconds,
            provider_retry_backoff_seconds=config.provider_retry_backoff_seconds,
            provider_max_retry_delay_seconds=config.provider_max_retry_delay_seconds,
            provider_sleep_between_items=config.provider_sleep_between_items,
            ollama_base_url=config.ollama_base_url,
            fail_cell_after_item_failures=config.fail_cell_after_item_failures,
        ),
        track=track,
        out_dir=run_dir,
    )


def format_dry_run_report(plans: list[Any]) -> str:
    lines = ["# Dry run — cell execution plan", ""]
    grouped: dict[str, list[Any]] = {}
    for plan in plans:
        grouped.setdefault(plan.status, []).append(plan)
    for status in (
        "completed",
        "failed",
        "missing",
        "partial",
        "running",
        "stale-running",
    ):
        bucket = grouped.get(status, [])
        if not bucket:
            continue
        lines.append(f"## {status} ({len(bucket)})")
        lines.append("")
        for plan in bucket:
            action = plan.action.upper()
            lines.append(
                f"- [{action}] `{plan.model}` / {plan.family} / {plan.track} "
                f"T={plan.temperature:g} → {plan.run_dir}"
            )
        lines.append("")
    run_count = sum(1 for plan in plans if plan.action == "run")
    skip_count = sum(1 for plan in plans if plan.action == "skip")
    lines.extend(
        [
            "## Summary",
            "",
            f"- **Would run:** {run_count}",
            f"- **Would skip:** {skip_count}",
            f"- **Total expected:** {len(plans)}",
            "",
        ]
    )
    return "\n".join(lines)


def scan_matrix_inventory(
    root: Path,
    config: TrackPilotModelsConfig,
    *,
    cohort_ids: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Scan all expected matrix cells on disk and classify each."""
    cohort_ids = cohort_ids or {"C2": config.c2_cohort_id, "F1": config.f1_cohort_id}
    inventory: list[dict[str, Any]] = []
    for model in config.models:
        mdir = model_dir_name(model)
        for temperature in config.temperatures:
            for family in config.families:
                cohort_id = cohort_ids[family]
                for track in config.tracks:
                    run_dir = build_cell_dir(
                        root,
                        model,
                        family,
                        temperature,
                        track,
                        matrix_layout=config.matrix_layout,
                    )
                    extended = detect_cell_status(
                        run_dir,
                        stale_threshold_seconds=config.stale_running_seconds,
                    )
                    status = classify_cell(run_dir)
                    row: dict[str, Any] = {
                        "model": model,
                        "model_dir": mdir,
                        "family": family,
                        "track": track,
                        "temperature": temperature,
                        "run_dir": str(run_dir),
                        "cohort_id": cohort_id,
                        "cell_status": status,
                        "extended_status": extended,
                    }
                    if extended == "completed":
                        try:
                            summary = load_cell_summary(run_dir)
                            row["status"] = "completed"
                            row.update(
                                build_track_row(
                                    summary,
                                    model=model,
                                    family=family,
                                    track=track,
                                    temperature=temperature,
                                    cohort_id=cohort_id,
                                    run_dir=run_dir,
                                )
                            )
                        except FileNotFoundError:
                            row["cell_status"] = "partial"
                            row["extended_status"] = "partial"
                            row["status"] = "partial"
                    elif extended in {
                        "failed",
                        "missing",
                        "partial",
                        "running",
                        "stale-running",
                    }:
                        incomplete = build_incomplete_from_status(
                            model=model,
                            model_dir=mdir,
                            family=family,
                            track=track,
                            temperature=temperature,
                            run_dir=run_dir,
                            cohort_id=cohort_id,
                            status=extended,
                        )
                        row.update(incomplete)
                    inventory.append(row)
    return inventory


def finalize_matrix_run(
    root: Path,
    config: TrackPilotModelsConfig,
    inventory: list[dict[str, Any]],
    *,
    cohort_ids: dict[str, str],
) -> TrackPilotModelsResult:
    track_rows = [
        row
        for row in inventory
        if row.get("extended_status", row.get("cell_status")) == "completed"
    ]
    incomplete = [
        row
        for row in inventory
        if row.get("extended_status", row.get("cell_status")) != "completed"
    ]
    failed_cells = incomplete
    delegation_rows = build_delegation_rows(track_rows)
    temperature_delta_rows = build_temperature_delta_rows(track_rows)
    status_counts = summarize_extended_inventory(inventory)
    payload = {
        "experiment": "local_matrix" if config.matrix_layout else "track_pilot",
        "models": list(config.models),
        "families": list(config.families),
        "tracks": list(config.tracks),
        "temperatures": list(config.temperatures),
        "max_items": config.max_items,
        "timeout": config.timeout,
        "item_timeout": resolved_item_timeout(config),
        "cohort_ids": cohort_ids,
        "provider": config.provider,
        "max_tokens": (
            config.max_tokens
            if config.provider in API_PROVIDERS_WITH_MAX_TOKENS
            else None
        ),
        "cell_status_counts": status_counts,
        "cell_inventory": inventory,
        "track_rows": track_rows,
        "delegation_rows": delegation_rows,
        "temperature_delta_rows": temperature_delta_rows,
        "failed_cells": failed_cells,
        "incomplete_cells": incomplete,
    }
    dump_json(root / "combined_summary.json", payload)
    write_track_pilot_csv(
        root / "combined_summary.csv",
        track_rows,
        delegation_rows,
        temperature_delta_rows,
    )
    (root / "report.md").write_text(
        render_track_pilot_report(payload),
        encoding="utf-8",
    )
    return TrackPilotModelsResult(
        track_rows=track_rows,
        delegation_rows=delegation_rows,
        temperature_delta_rows=temperature_delta_rows,
        failed_cells=failed_cells,
        cell_inventory=inventory,
        cell_status_counts=status_counts,
        out_dir=root,
    )


def run_track_pilot_models(
    config: TrackPilotModelsConfig,
    generate_factory: GenerateFactory,
) -> TrackPilotModelsResult:
    """
    Run R0/R1/R2 track batches for each model × family × temperature cell.

    Single-temperature layout::

        {out_dir}/{model_dir}/{family}/{track}/

    Multi-temperature layout::

        {out_dir}/{model_dir}/{family}/temp_{temperature}/{track}/
    """
    if not config.models:
        raise ValueError("at least one model is required")
    if not config.families:
        raise ValueError("at least one family is required")
    if not config.tracks:
        raise ValueError("at least one track is required")
    if not config.temperatures:
        raise ValueError("at least one temperature is required")
    if config.max_items < 1:
        raise ValueError("max_items must be >= 1")

    for track in config.tracks:
        TrackId(track)

    root = Path(config.out_dir)
    root.mkdir(parents=True, exist_ok=True)
    if config.report_only:
        config = hydrate_report_only_config(root, config)
    else:
        validate_provider_tracks(config.provider, config.tracks)

    config = apply_incremental_safe(config)
    cohort_ids = {"C2": config.c2_cohort_id, "F1": config.f1_cohort_id}
    item_sources = _item_sources(config)

    if config.report_only:
        inventory = scan_matrix_inventory(root, config, cohort_ids=cohort_ids)
        return finalize_matrix_run(root, config, inventory, cohort_ids=cohort_ids)

    plans = build_cell_plans(
        models=config.models,
        families=config.families,
        tracks=config.tracks,
        temperatures=config.temperatures,
        out_dir=root,
        item_sources=item_sources,
        cohort_ids=cohort_ids,
        matrix_layout=config.matrix_layout,
        skip_completed=config.skip_completed,
        retry_failed=config.retry_failed,
        skip_failed=config.skip_failed,
        force_all=config.effective_force_all,
        force_cell=config.force_cell,
        stale_threshold_seconds=config.stale_running_seconds,
    )

    if config.dry_run:
        print(format_dry_run_report(plans))

    family_items: dict[str, list] | None = None
    if config.estimate_only or config.provider_dry_run or not config.dry_run:
        family_items = _load_family_items(config)

    if config.estimate_only:
        estimate = estimate_frontier_run(
            provider=config.provider,
            models=config.models,
            families=config.families,
            tracks=config.tracks,
            temperatures=config.temperatures,
            max_items=config.max_items,
            max_cells=config.max_cells,
            max_tokens=config.max_tokens,
        )
        dump_json(root / "frontier_estimate.json", estimate)
        inventory = scan_matrix_inventory(root, config, cohort_ids=cohort_ids)
        return finalize_matrix_run(root, config, inventory, cohort_ids=cohort_ids)

    if config.provider_dry_run:
        assert family_items is not None
        diagnostic_path = write_provider_dry_run_diagnostic(
            out_dir=root,
            provider=config.provider,
            models=config.models,
            families=config.families,
            tracks=config.tracks,
            temperatures=config.temperatures,
            max_items=config.max_items,
            max_tokens=config.max_tokens,
            family_items=family_items,
        )
        print(f"Wrote provider dry-run diagnostic: {diagnostic_path}")
        inventory = scan_matrix_inventory(root, config, cohort_ids=cohort_ids)
        return finalize_matrix_run(root, config, inventory, cohort_ids=cohort_ids)

    if config.dry_run:
        inventory = scan_matrix_inventory(root, config, cohort_ids=cohort_ids)
        return finalize_matrix_run(root, config, inventory, cohort_ids=cohort_ids)

    assert family_items is not None
    run_plans = [plan for plan in plans if plan.action == "run"]
    item_timeout = resolved_item_timeout(config)
    cells_executed = 0
    consecutive_failures = 0

    for plan in run_plans:
        if config.max_cells is not None and cells_executed >= config.max_cells:
            break
        if consecutive_failures >= config.stop_after_failures:
            break

        run_dir = plan.run_dir
        run_dir.mkdir(parents=True, exist_ok=True)
        prepare_cell_rerun(
            run_dir,
            force_cell=config.force_cell or config.effective_force_all,
            resume_items=config.resume_items,
        )

        config_hash = _cell_execution_config_hash(
            model=plan.model,
            family=plan.family,
            track=plan.track,
            temperature=plan.temperature,
            item_source=plan.item_source,
            max_items=config.max_items,
            timeout=config.timeout,
            item_timeout=item_timeout,
            provider=config.provider,
            max_tokens=config.max_tokens,
        )
        started_at = mark_cell_running(
            run_dir,
            model=plan.model,
            model_dir=plan.model_dir,
            family=plan.family,
            track=plan.track,
            temperature=plan.temperature,
            item_source=plan.item_source,
            config_hash=config_hash,
            max_items=config.max_items,
        )

        batch_result: OllamaBatchResult | None = None
        cell_succeeded = False

        def _execute_cell() -> OllamaBatchResult:
            nonlocal batch_result
            batch_result = _run_cell_batch(
                items=items,
                generate=generate,
                run_dir=run_dir,
                model=plan.model,
                family=plan.family,
                track=plan.track,
                temperature=plan.temperature,
                config=config,
                item_timeout=item_timeout,
            )
            return batch_result

        def _finalize_cell_success() -> None:
            items_completed = len(completed_item_ids(run_dir))
            mark_cell_completed(
                run_dir,
                started_at=started_at,
                items_completed=items_completed,
            )

        try:
            _log_cell_startup(
                model=plan.model,
                family=plan.family,
                track=plan.track,
                temperature=plan.temperature,
                phase="provider_selected",
                provider=config.provider,
            )
            generate = generate_factory(plan.model, plan.temperature)
            items = family_items[plan.family]
            _log_cell_startup(
                model=plan.model,
                family=plan.family,
                track=plan.track,
                temperature=plan.temperature,
                phase="items_loaded",
                item_count=len(items),
                max_items=config.max_items,
            )
            if items:
                from fsmreasonbench.runners.prompts import render_prompt

                first_prompt = render_prompt(items[0], provider=config.provider)
                _log_cell_startup(
                    model=plan.model,
                    family=plan.family,
                    track=plan.track,
                    temperature=plan.temperature,
                    phase="first_prompt_built",
                    prompt_chars=len(first_prompt),
                )

            if config.cell_timeout is not None:
                pool = ThreadPoolExecutor(max_workers=1)
                future = pool.submit(_execute_cell)
                try:
                    future.result(timeout=config.cell_timeout)
                except TimeoutError:
                    if future.done():
                        inner = future.exception()
                        if inner is not None:
                            raise inner
                    mark_cell_failed(
                        run_dir,
                        error_type="timeout",
                        error_message=format_cell_timeout_message(config.cell_timeout),
                        model=plan.model,
                        model_dir=plan.model_dir,
                        family=plan.family,
                        track=plan.track,
                        temperature=plan.temperature,
                        out_dir=run_dir,
                        started_at=started_at,
                        exc_type="TimeoutError",
                    )
                    consecutive_failures += 1
                else:
                    _finalize_cell_success()
                    cell_succeeded = True
                    consecutive_failures = 0
                finally:
                    pool.shutdown(wait=False, cancel_futures=True)
            else:
                _execute_cell()
                _finalize_cell_success()
                cell_succeeded = True
                consecutive_failures = 0
        except KeyboardInterrupt:
            mark_cell_failed(
                run_dir,
                error_type="internal_runner_error",
                error_message="interrupted by user",
                model=plan.model,
                model_dir=plan.model_dir,
                family=plan.family,
                track=plan.track,
                temperature=plan.temperature,
                out_dir=run_dir,
                started_at=started_at,
                exc_type="KeyboardInterrupt",
            )
            inventory = scan_matrix_inventory(root, config, cohort_ids=cohort_ids)
            finalize_matrix_run(root, config, inventory, cohort_ids=cohort_ids)
            raise
        except CellItemFailureLimitExceeded as exc:
            mark_cell_failed(
                run_dir,
                error_type="internal_runner_error",
                error_message=str(exc),
                model=plan.model,
                model_dir=plan.model_dir,
                family=plan.family,
                track=plan.track,
                temperature=plan.temperature,
                out_dir=run_dir,
                started_at=started_at,
                exc_type=type(exc).__name__,
            )
            consecutive_failures += 1
        except TimeoutError:
            mark_cell_failed(
                run_dir,
                error_type="timeout",
                error_message=format_item_timeout_message(item_timeout),
                model=plan.model,
                model_dir=plan.model_dir,
                family=plan.family,
                track=plan.track,
                temperature=plan.temperature,
                out_dir=run_dir,
                started_at=started_at,
                exc_type="TimeoutError",
            )
            consecutive_failures += 1
        except Exception as exc:  # noqa: BLE001 — pilot continues after cell failure
            message = str(exc)
            error_type = classify_cell_error(message)
            root_cause = None
            if "cannot build distinguishing trace" in message:
                root_cause = infer_distinguishing_trace_root_cause(
                    family=plan.family,
                    track=plan.track,
                )
            mark_cell_failed(
                run_dir,
                error_type=error_type,
                error_message=message,
                model=plan.model,
                model_dir=plan.model_dir,
                family=plan.family,
                track=plan.track,
                temperature=plan.temperature,
                out_dir=run_dir,
                started_at=started_at,
                exc_type=type(exc).__name__,
                tb=traceback.format_exc(),
                root_cause=root_cause,
            )
            consecutive_failures += 1
        finally:
            if not cell_succeeded:
                finalize_abandoned_running_cell(
                    run_dir,
                    started_at=started_at,
                    model=plan.model,
                    model_dir=plan.model_dir,
                    family=plan.family,
                    track=plan.track,
                    temperature=plan.temperature,
                    out_dir=run_dir,
                    reason="cell exited before first scored item",
                )

        cells_executed += 1
        sleep_seconds = (
            0.0 if os.environ.get("PYTEST_CURRENT_TEST") else config.sleep_between_cells
        )
        if (
            sleep_seconds > 0
            and cells_executed < len(run_plans)
            and cells_executed < (config.max_cells or len(run_plans))
        ):
            time.sleep(sleep_seconds)

    inventory = scan_matrix_inventory(root, config, cohort_ids=cohort_ids)
    return finalize_matrix_run(root, config, inventory, cohort_ids=cohort_ids)


def write_track_pilot_csv(
    path: str | Path,
    track_rows: list[dict[str, Any]],
    delegation_rows: list[dict[str, Any]],
    temperature_delta_rows: list[dict[str, Any]] | None = None,
) -> None:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    track_fieldnames = list(_TRACK_ROW_FIELDS) + [
        f"track_failure_{label}" for label in _TOOL_FAILURE_CLASSES + _SUBMISSION_FAILURE_CLASSES
    ]
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=track_fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in track_rows:
            if row.get("status") != "completed":
                writer.writerow({field: row.get(field) for field in _TRACK_ROW_FIELDS})
                continue
            flat = {field: row.get(field) for field in _TRACK_ROW_FIELDS}
            flat["failure_stage_counts"] = json.dumps(
                row.get("failure_stage_counts", {}),
                sort_keys=True,
            )
            flat["track_failure_counts"] = json.dumps(
                row.get("track_failure_counts", {}),
                sort_keys=True,
            )
            counts = row.get("track_failure_counts", {})
            for label in _TOOL_FAILURE_CLASSES + _SUBMISSION_FAILURE_CLASSES:
                flat[f"track_failure_{label}"] = counts.get(label, 0)
            writer.writerow(flat)

        if delegation_rows:
            handle.write("\n")
            delegation_fieldnames = [
                "row_type",
                "model",
                "family",
                "temperature",
                "cohort_id",
                "n",
            ]
            for prefix in ("delta_R1_minus_R0", "delta_R2_minus_R0", "delta_R2_minus_R1"):
                for metric in DELEGATION_GAP_METRICS:
                    delegation_fieldnames.append(f"{prefix}_{metric}")
            delegation_writer = csv.DictWriter(
                handle,
                fieldnames=delegation_fieldnames,
                extrasaction="ignore",
            )
            delegation_writer.writeheader()
            for row in delegation_rows:
                delegation_writer.writerow({"row_type": "delegation", **row})

        if temperature_delta_rows:
            handle.write("\n")
            temp_fieldnames = [
                "row_type",
                "model",
                "family",
                "track",
                "baseline_temperature",
                "n",
            ]
            for prefix in ("delta_temp_0.2_minus_0.0", "delta_temp_0.7_minus_0.0"):
                for metric in DELEGATION_GAP_METRICS:
                    temp_fieldnames.append(f"{prefix}_{metric}")
            temp_writer = csv.DictWriter(
                handle,
                fieldnames=temp_fieldnames,
                extrasaction="ignore",
            )
            temp_writer.writeheader()
            for row in temperature_delta_rows:
                temp_writer.writerow({"row_type": "temperature_delta", **row})


_EXTRACTABILITY_UNSAFE_THRESHOLD = 0.5
_FAILURE_STAGE_LABELS = (
    "not_extractable",
    "provider_error",
    "verdict_wrong",
    "certificate_invalid",
    "correct",
)


def _failure_stage_counts(row: dict[str, Any]) -> dict[str, int]:
    raw = row.get("failure_stage_counts") or {}
    return {stage: int(raw.get(stage, 0)) for stage in _FAILURE_STAGE_LABELS}


def _row_item_count(row: dict[str, Any]) -> int:
    return int(row.get("n") or 0)


def _extractable_count(row: dict[str, Any]) -> int:
    counts = _failure_stage_counts(row)
    n = _row_item_count(row)
    if n:
        return max(0, n - counts["not_extractable"] - counts["provider_error"])
    extract_rate = row.get("extractability_rate")
    if extract_rate is None:
        return 0
    return int(round(float(extract_rate) * n))


def _provider_error_count(row: dict[str, Any]) -> int:
    if row.get("provider_error_count") is not None:
        return int(row["provider_error_count"])
    counts = _failure_stage_counts(row)
    return counts.get("provider_error", 0)


def _provider_dominates_cell(row: dict[str, Any]) -> bool:
    n = _row_item_count(row)
    if n == 0:
        return False
    provider_errors = _provider_error_count(row)
    return provider_errors >= max(1, n // 2)


def _format_extractability(row: dict[str, Any]) -> str:
    n = _row_item_count(row)
    extractable = _extractable_count(row)
    rate = row.get("extractability_rate")
    if rate is None or n == 0:
        return "—"
    provider_errors = _provider_error_count(row)
    model_rate = row.get("model_extractability_rate")
    base = f"{float(rate):.3f} ({extractable}/{n})"
    if provider_errors:
        model_n = int(row.get("model_scored_n") or max(0, n - provider_errors))
        if model_rate is not None and model_n > 0:
            return f"{base}; model={float(model_rate):.3f} ({extractable}/{model_n})"
        return f"{base}; provider_errors={provider_errors}"
    return base


def _format_verdict_accuracy(row: dict[str, Any]) -> str:
    counts = _failure_stage_counts(row)
    extractable = _extractable_count(row)
    if extractable == 0:
        return "undefined (0 extractable)"
    verdict_correct = counts["certificate_invalid"] + counts["correct"]
    rate = row.get("verdict_accuracy")
    if rate is None:
        return f"{verdict_correct}/{extractable} ext"
    return f"{float(rate):.3f} ({verdict_correct}/{extractable} ext)"


def _format_certificate_valid_rate(row: dict[str, Any]) -> str:
    counts = _failure_stage_counts(row)
    extractable = _extractable_count(row)
    if extractable == 0:
        return "undefined (0 extractable)"
    cert_valid = counts["correct"]
    rate = row.get("certificate_valid_rate")
    if rate is None:
        return f"{cert_valid}/{extractable} ext"
    return f"{float(rate):.3f} ({cert_valid}/{extractable} ext)"


def _format_fully_correct_rate(row: dict[str, Any]) -> str:
    n = _row_item_count(row)
    if n == 0:
        return "—"
    counts = _failure_stage_counts(row)
    fully_correct = counts["correct"]
    rate = row.get("fully_correct_rate")
    if rate is None:
        return f"{fully_correct}/{n}"
    return f"{float(rate):.3f} ({fully_correct}/{n})"


def _extractability_safety_flag(row: dict[str, Any]) -> str:
    if _provider_dominates_cell(row):
        rate_limit = int(row.get("provider_rate_limit_count") or 0)
        insufficient = int(row.get("provider_insufficient_credit_count") or 0)
        detail_parts: list[str] = []
        if rate_limit:
            detail_parts.append(f"rate-limit={rate_limit}")
        if insufficient:
            detail_parts.append(f"insufficient-credit={insufficient}")
        if detail_parts:
            return (
                "UNSAFE (provider failures dominate, "
                + ", ".join(detail_parts)
                + ")"
            )
        quota = int(row.get("provider_quota_error_count") or 0)
        suffix = f", quota/rate-limit={quota}" if quota else ""
        return f"UNSAFE (provider failures dominate{suffix})"
    rate = row.get("model_extractability_rate", row.get("extractability_rate"))
    if rate is None:
        return ""
    if float(rate) < _EXTRACTABILITY_UNSAFE_THRESHOLD:
        return "UNSAFE (<50% model-extractable)"
    return ""


def render_track_pilot_report(payload: dict[str, Any]) -> str:
    models = payload["models"]
    families = payload["families"]
    tracks = payload["tracks"]
    temperatures = payload.get("temperatures", [0.0])
    cohort_ids = payload["cohort_ids"]
    track_rows = [row for row in payload["track_rows"] if row.get("status", "completed") == "completed"]
    delegation_rows = payload["delegation_rows"]
    temperature_delta_rows = payload.get("temperature_delta_rows", [])
    incomplete_cells = payload.get("incomplete_cells", payload.get("failed_cells", []))
    status_counts = payload.get("cell_status_counts", {})
    is_matrix = payload.get("experiment") == "local_matrix" or len(temperatures) > 1

    title = "Local Model Track-Temperature Matrix Report" if is_matrix else "Track Pilot Report"
    lines = [
        f"# {title}",
        "",
        "## Matrix overview" if is_matrix else "## Overview",
        "",
        f"- **Models:** {', '.join(f'`{model}`' for model in models)}",
        f"- **Families:** {', '.join(families)}",
        f"- **Tracks:** {', '.join(tracks)}",
        f"- **Temperatures:** {', '.join(str(t) for t in temperatures)}",
        f"- **Items per cell:** n={payload['max_items']}",
        f"- **Timeout (s):** {payload.get('timeout') if payload.get('timeout') is not None else 'none (disabled)'}",
        f"- **Item timeout (s):** {payload.get('item_timeout') if payload.get('item_timeout') is not None else 'inherit --timeout'}",
        "",
        "### Cohort IDs",
        "",
    ]
    for family, cohort_id in cohort_ids.items():
        lines.append(f"- **{family}:** `{cohort_id}`")

    if status_counts:
        lines.extend(
            [
                "",
                "### Cell status",
                "",
                f"- **Completed:** {status_counts.get('completed', 0)}",
                f"- **Failed:** {status_counts.get('failed', 0)}",
                f"- **Missing:** {status_counts.get('missing', 0)}",
                f"- **Partial:** {status_counts.get('partial', 0)}",
                f"- **Running:** {status_counts.get('running', 0)}",
                f"- **Stale-running:** {status_counts.get('stale-running', 0)}",
            ]
        )

    if incomplete_cells:
        lines.extend(
            [
                "",
                "### Incomplete cells (failed / missing / partial / running / stale-running)",
                "",
                "| Model | Family | Track | Temp | Status | Progress | error_type | Message |",
                "|-------|--------|-------|-----:|--------|----------|------------|---------|",
            ]
        )
        for cell in incomplete_cells:
            msg = error_message_from_payload(cell).replace("|", "\\|")
            if len(msg) > 80:
                msg = msg[:77] + "..."
            ext = cell.get("extended_status", cell.get("cell_status", cell.get("status", "failed")))
            progress = cell.get("item_progress", "—")
            lines.append(
                "| `{model}` | {family} | {track} | {temp:g} | {status} | {progress} | "
                "{error_type} | {msg} |".format(
                    model=cell["model"],
                    family=cell["family"],
                    track=cell["track"],
                    temp=float(cell.get("temperature", 0.0)),
                    status=ext,
                    progress=progress,
                    error_type=cell.get("error_type", "unknown"),
                    msg=msg,
                )
            )
        lines.append("")

        by_type: dict[str, list[dict[str, Any]]] = {
            "timeout": [],
            "internal_runner_error": [],
            "model_protocol_error": [],
            "tool_execution_error": [],
            "unknown": [],
        }
        for cell in incomplete_cells:
            if cell.get("cell_status") == "missing":
                by_type["unknown"].append(cell)
                continue
            error_type = cell.get("error_type") or classify_cell_error(
                error_message_from_payload(cell)
            )
            bucket = by_type.get(error_type, by_type["unknown"])
            bucket.append(cell)
        lines.extend(["", "#### Error-type breakdown", ""])
        for error_type, label in (
            ("timeout", "Timeout"),
            ("tool_execution_error", "Tool execution error"),
            ("internal_runner_error", "Internal runner error"),
            ("model_protocol_error", "Model protocol error"),
            ("unknown", "Missing / unknown"),
        ):
            cells = by_type[error_type]
            if not cells:
                continue
            lines.append(f"**{label}** ({len(cells)})")
            for cell in cells:
                temp_label = f" T={cell.get('temperature', 0)}" if "temperature" in cell else ""
                root_cause = cell.get("root_cause")
                suffix = f" — _{root_cause}_" if root_cause else ""
                lines.append(
                    f"- `{cell['model']}` / {cell['family']} / {cell['track']}{temp_label} "
                    f"[{cell.get('cell_status', 'failed')}]: "
                    f"{error_message_from_payload(cell)}{suffix}"
                )
            lines.append("")

        lines.append(
            "Delegation gap tables use `—` when any track cell in a model×family×temperature "
            "group is incomplete; do not interpret as zero improvement."
        )

    indexed = {_row_index_key(row): row for row in track_rows}
    unsafe_cells = [
        row
        for row in track_rows
        if _extractability_safety_flag(row)
        and not _provider_dominates_cell(row)
    ]

    lines.extend(
        [
            "",
            "### Metric denominators",
            "",
            "- **extractability_rate:** extractable items / total n (includes provider-skipped items in denominator)",
            "- **model_extractability_rate:** extractable items / (n − provider_error_count); use when quota/rate-limit failures dominate",
            "- **verdict_accuracy:** correct verdict among extractable outputs "
            "(denominator = n − not_extractable − provider_error; undefined when extractable = 0)",
            "- **certificate_valid_rate:** valid certificate among extractable outputs "
            "(same denominator; undefined when extractable = 0)",
            "- **fully_correct_rate:** fully correct items / total n",
            "- **not_extractable** (failure-stage table): model output parse/extraction failures only",
            "- **provider_error** (failure-stage table): runner/provider quota, rate-limit, timeout, or unavailable errors",
            "- **provider_error_count / provider_quota_error_count:** per-cell provider failure totals (429 quota/rate-limit vs other infra)",
            "- **infrastructure_failure_count:** alias count of items with infrastructure_failure=true",
        ]
    )

    provider_dominated = [row for row in track_rows if _provider_dominates_cell(row)]
    if provider_dominated:
        lines.extend(["", "### Provider failures dominate (metrics not interpretable)", ""])
        for row in provider_dominated:
            rate_limit = int(row.get("provider_rate_limit_count") or 0)
            insufficient = int(row.get("provider_insufficient_credit_count") or 0)
            lines.append(
                "- `{model}` / {family} / {track} / T={temp:g}: "
                "provider_errors={provider}/{n}, rate-limit={rate_limit}, "
                "insufficient-credit={insufficient}, quota/rate-limit={quota} — "
                "use model_extractability_rate or rerun with throttling".format(
                    model=row["model"],
                    family=row["family"],
                    track=row["track"],
                    temp=float(row.get("temperature", 0.0)),
                    provider=_provider_error_count(row),
                    n=_row_item_count(row),
                    rate_limit=rate_limit,
                    insufficient=insufficient,
                    quota=int(row.get("provider_quota_error_count") or 0),
                )
            )

    if unsafe_cells:
        lines.extend(["", "### Low model-extractability cells (unsafe for reasoning comparisons)", ""])
        for row in unsafe_cells:
            extractable = _extractable_count(row)
            lines.append(
                "- `{model}` / {family} / {track} / T={temp:g}: "
                "extractability={rate:.3f} ({extractable}/{n} extractable) — "
                "do not treat verdict/certificate rates as reasoning signal".format(
                    model=row["model"],
                    family=row["family"],
                    track=row["track"],
                    temp=float(row.get("temperature", 0.0)),
                    rate=float(row.get("extractability_rate") or 0.0),
                    extractable=extractable,
                    n=_row_item_count(row),
                )
            )

    metric_headers = (
        "extract",
        "verdict",
        "cert",
        "full",
        "safety",
        "tool_rate",
        "avg_tools",
    )

    for family in families:
        family_models = [
            model
            for model in models
            if any(
                (model, family, float(temp), track) in indexed
                for temp in temperatures
                for track in tracks
            )
        ]
        lines.extend(["", f"## {family} — per-track metrics", ""])
        header = "| Model | Temp | Track | n | " + " | ".join(metric_headers) + " |"
        lines.append(header)
        lines.append(
            "|-------|-----:|-------|--:|" + "|".join(["------:"] * len(metric_headers)) + "|"
        )
        for model in family_models:
            for temperature in temperatures:
                for track in tracks:
                    row = indexed.get((model, family, float(temperature), track))
                    if row is None:
                        continue
                    safety = _extractability_safety_flag(row) or "—"
                    lines.append(
                        "| `{model}` | {temp:g} | {track} | {n} | "
                        "{extract} | {verdict} | {cert} | {full} | "
                        "{safety} | {tool_rate:.3f} | {avg_tools:.1f} |".format(
                            model=model,
                            temp=float(temperature),
                            track=track,
                            n=row.get("n", 0),
                            extract=_format_extractability(row),
                            verdict=_format_verdict_accuracy(row),
                            cert=_format_certificate_valid_rate(row),
                            full=_format_fully_correct_rate(row),
                            safety=safety,
                            tool_rate=float(row.get("tool_invocation_rate") or 0.0),
                            avg_tools=float(row.get("average_tool_calls_per_item") or 0.0),
                        )
                    )

        if is_matrix:
            lines.extend(["", f"## {family} — per-temperature summary (R2 fully correct)", ""])
            lines.append("| Model | Temp | full (R2) | cert (R2) | verdict (R2) |")
            lines.append("|-------|-----:|----------:|----------:|-------------:|")
            for model in family_models:
                for temperature in temperatures:
                    row = indexed.get((model, family, float(temperature), "R2"))
                    if row is None:
                        continue
                    lines.append(
                        "| `{model}` | {temp:g} | {full:.3f} | {cert:.3f} | {verdict:.3f} |".format(
                            model=model,
                            temp=float(temperature),
                            full=row.get("fully_correct_rate", 0.0),
                            cert=row.get("certificate_valid_rate", 0.0),
                            verdict=row.get("verdict_accuracy", 0.0),
                        )
                    )

        lines.extend(["", f"## {family} — delegation gaps by temperature", ""])
        lines.append(
            "| Model | Temp | Δ_R1−R0 full | Δ_R2−R0 full | Δ_R2−R1 full | "
            "Δ_R2−R0 cert | Δ_R2−R0 verdict |"
        )
        lines.append(
            "|-------|-----:|-------------:|-------------:|-------------:|"
            "-------------:|----------------:|"
        )
        for row in delegation_rows:
            if row["family"] != family:
                continue
            def _fmt_delta(key: str) -> str:
                value = row.get(key)
                if value is None:
                    return "—" if row.get("delegation_incomplete") else "+nan"
                return f"{value:+.3f}"

            lines.append(
                "| `{model}` | {temp:g} | "
                "{d13} | {d23} | {d33} | "
                "{d22} | {d21} |".format(
                    model=row["model"],
                    temp=float(row.get("temperature", 0.0)),
                    d13=_fmt_delta("delta_R1_minus_R0_fully_correct_rate"),
                    d23=_fmt_delta("delta_R2_minus_R0_fully_correct_rate"),
                    d33=_fmt_delta("delta_R2_minus_R1_fully_correct_rate"),
                    d22=_fmt_delta("delta_R2_minus_R0_certificate_valid_rate"),
                    d21=_fmt_delta("delta_R2_minus_R0_verdict_accuracy"),
                )
            )

        if is_matrix and temperature_delta_rows:
            lines.extend(["", f"## {family} — temperature sensitivity by track", ""])
            lines.append(
                "| Model | Track | Δ_T0.2−T0.0 full | Δ_T0.7−T0.0 full | "
                "Δ_T0.2−T0.0 cert | Δ_T0.7−T0.0 cert |"
            )
            lines.append(
                "|-------|-------|-----------------:|-----------------:|"
                "-----------------:|-----------------:|"
            )
            for row in temperature_delta_rows:
                if row["family"] != family:
                    continue
                lines.append(
                    "| `{model}` | {track} | "
                    "{d12:+.3f} | {d17:+.3f} | "
                    "{c12:+.3f} | {c17:+.3f} |".format(
                        model=row["model"],
                        track=row["track"],
                        d12=row.get("delta_temp_0.2_minus_0.0_fully_correct_rate", float("nan")),
                        d17=row.get("delta_temp_0.7_minus_0.0_fully_correct_rate", float("nan")),
                        c12=row.get("delta_temp_0.2_minus_0.0_certificate_valid_rate", float("nan")),
                        c17=row.get("delta_temp_0.7_minus_0.0_certificate_valid_rate", float("nan")),
                    )
                )

        lines.extend(["", f"## {family} — failure movement (failure_stage_counts)", ""])
        failure_labels = list(_FAILURE_STAGE_LABELS)
        lines.append("| Model | Temp | Track | " + " | ".join(failure_labels) + " |")
        lines.append("|-------|-----:|-------|" + "|".join(["---:"] * len(failure_labels)) + "|")
        for model in family_models:
            for temperature in temperatures:
                for track in tracks:
                    row = indexed.get((model, family, float(temperature), track))
                    if row is None:
                        continue
                    counts = _failure_stage_counts(row)
                    values = " | ".join(str(counts[label]) for label in failure_labels)
                    lines.append(
                        f"| `{model}` | {float(temperature):g} | {track} | {values} |"
                    )

    lines.extend(["", "## Research questions", ""])
    for rq_id, question in _RESEARCH_QUESTIONS:
        lines.append(f"- **{rq_id}:** {question}")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This report is **exploratory** only:",
            "",
            "- Local Ollama models only — reproducible on a single RTX 4090; **no paid APIs**.",
            f"- n={payload['max_items']} items per model × family × track × temperature cell (initial pilot).",
            "- Frozen **v0.1-exploratory** cohorts — not `v1.0-public`.",
            "- **Not a final benchmark score.**",
            "- Use results to decide whether a larger-n run (100–200 items/cell) is worth executing.",
            "",
            "When reading delegation gaps, ask whether tools improve **verdict accuracy only**, "
            "**certificate validity**, or **both** (fully correct). Compare temperature rows to "
            "see whether higher temperature helps exploration or hurts certificate compliance.",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _load_family_items(config: TrackPilotModelsConfig) -> dict[str, list[BenchmarkItem]]:
    items_by_family: dict[str, list[BenchmarkItem]] = {}
    paths = {"C2": config.c2_items_path, "F1": config.f1_items_path}
    for family in config.families:
        if family not in paths:
            raise ValueError(f"unsupported family: {family!r}")
        items = load_items_jsonl(paths[family])
        if not items:
            raise ValueError(f"{family} items JSONL is empty")
        if any(item.family != family for item in items):
            raise ValueError(f"all items must belong to family {family!r}")
        items_by_family[family] = items
    return items_by_family
