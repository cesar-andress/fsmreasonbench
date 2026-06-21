"""Multi-model R0/R1/R2 track pilot evaluation across frozen exploratory cohorts."""

from __future__ import annotations

import csv
import json
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.evaluator.jsonl import load_items_jsonl
from fsmreasonbench.evaluator.models import FailureStage
from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.runners.cell_failure import (
    build_incomplete_cell_record,
    classify_cell,
    classify_cell_error,
    error_message_from_payload,
    has_partial_outputs,
    infer_distinguishing_trace_root_cause,
    is_cell_complete,
    prepare_cell_rerun,
    read_cell_error,
    should_run_cell,
    summarize_cell_inventory,
    utc_timestamp,
    write_cell_error,
    write_cell_state,
)
from fsmreasonbench.runners.ollama_batch import GenerateFn, OllamaBatchConfig
from fsmreasonbench.runners.ollama_track_batch import run_ollama_track_batch
from fsmreasonbench.runners.pilot_models import model_dir_name
from fsmreasonbench.tracks.delegation import DELEGATION_GAP_METRICS, compute_delegation_gap
from fsmreasonbench.tracks.models import TrackId

GenerateFactory = Callable[[str, float], GenerateFn]

DEFAULT_C2_ITEMS = "cohorts/v0.1-exploratory/c2-reachability-level3/items.jsonl"
DEFAULT_F1_ITEMS = "cohorts/v0.1-exploratory/f1-mixed-level3/items.jsonl"
DEFAULT_C2_COHORT_ID = "c2-reachability-level3-v0.1-exploratory"
DEFAULT_F1_COHORT_ID = "f1-mixed-level3-v0.1-exploratory"

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
    timeout: float = 120.0
    skip_completed: bool = True
    retry_failed: bool = False
    skip_failed: bool = False
    force: bool = False
    report_only: bool = False
    c2_cohort_id: str = DEFAULT_C2_COHORT_ID
    f1_cohort_id: str = DEFAULT_F1_COHORT_ID

    @property
    def use_temperature_dirs(self) -> bool:
        return len(self.temperatures) > 1


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


def cell_dir(
    out_dir: Path,
    model: str,
    family: str,
    track: str,
    *,
    temperature: float = 0.0,
    use_temperature_dirs: bool = False,
) -> Path:
    base = out_dir / model_dir_name(model) / family
    if use_temperature_dirs:
        base = base / temperature_dir_name(temperature)
    return base / track


# Re-export for tests and downstream callers
__all__ = [
    "TrackPilotModelsConfig",
    "TrackPilotModelsResult",
    "build_delegation_rows",
    "build_temperature_delta_rows",
    "build_track_row",
    "cell_dir",
    "finalize_matrix_run",
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
                    run_dir = cell_dir(
                        root,
                        model,
                        family,
                        track,
                        temperature=temperature,
                        use_temperature_dirs=config.use_temperature_dirs,
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
                    }
                    if status == "completed":
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
                            row["status"] = "partial"
                    elif status in {"failed", "missing", "partial"}:
                        incomplete = build_incomplete_cell_record(
                            model=model,
                            model_dir=mdir,
                            family=family,
                            track=track,
                            temperature=temperature,
                            run_dir=run_dir,
                            cohort_id=cohort_id,
                            status=status,
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
    track_rows = [row for row in inventory if row.get("cell_status") == "completed"]
    incomplete = [row for row in inventory if row.get("cell_status") != "completed"]
    failed_cells = incomplete
    delegation_rows = build_delegation_rows(track_rows)
    temperature_delta_rows = build_temperature_delta_rows(track_rows)
    status_counts = summarize_cell_inventory(inventory)
    payload = {
        "experiment": "local_matrix" if config.use_temperature_dirs else "track_pilot",
        "models": list(config.models),
        "families": list(config.families),
        "tracks": list(config.tracks),
        "temperatures": list(config.temperatures),
        "max_items": config.max_items,
        "timeout": config.timeout,
        "cohort_ids": cohort_ids,
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

    root = Path(config.out_dir)
    root.mkdir(parents=True, exist_ok=True)
    cohort_ids = {"C2": config.c2_cohort_id, "F1": config.f1_cohort_id}

    if config.report_only:
        inventory = scan_matrix_inventory(root, config, cohort_ids=cohort_ids)
        return finalize_matrix_run(root, config, inventory, cohort_ids=cohort_ids)

    family_items = _load_family_items(config)

    for model in config.models:
        mdir = model_dir_name(model)
        for temperature in config.temperatures:
            generate = generate_factory(model, temperature)
            for family in config.families:
                items = family_items[family]
                cohort_id = cohort_ids[family]
                for track in config.tracks:
                    run_dir = cell_dir(
                        root,
                        model,
                        family,
                        track,
                        temperature=temperature,
                        use_temperature_dirs=config.use_temperature_dirs,
                    )
                    run_dir.mkdir(parents=True, exist_ok=True)
                    cell_status = classify_cell(run_dir)

                    if not should_run_cell(
                        run_dir,
                        skip_completed=config.skip_completed,
                        retry_failed=config.retry_failed,
                        skip_failed=config.skip_failed,
                        force=config.force,
                        status=cell_status,
                    ):
                        continue

                    prepare_cell_rerun(run_dir)
                    started_at = utc_timestamp()

                    try:
                        batch_result = run_ollama_track_batch(
                            items,
                            generate,
                            run_dir / "results.jsonl",
                            OllamaBatchConfig(
                                model=model,
                                temperature=temperature,
                                timeout=config.timeout,
                                max_items=config.max_items,
                            ),
                            track=track,
                            out_dir=run_dir,
                        )
                        write_cell_state(
                            run_dir,
                            status="completed",
                            model=model,
                            family=family,
                            track=track,
                            temperature=temperature,
                            started_at=started_at,
                        )
                    except Exception as exc:  # noqa: BLE001 — pilot continues after cell failure
                        message = str(exc)
                        error_type = classify_cell_error(message)
                        root_cause = None
                        if "cannot build distinguishing trace" in message:
                            root_cause = infer_distinguishing_trace_root_cause(
                                family=family,
                                track=track,
                            )
                        write_cell_error(
                            run_dir,
                            error_type=error_type,
                            error_message=message,
                            model=model,
                            model_dir=mdir,
                            family=family,
                            track=track,
                            temperature=temperature,
                            out_dir=run_dir,
                            started_at=started_at,
                            ended_at=utc_timestamp(),
                            partial_outputs_present=has_partial_outputs(run_dir),
                            retryable=True,
                            exc_type=type(exc).__name__,
                            tb=traceback.format_exc(),
                            root_cause=root_cause,
                        )

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
        f"- **Timeout (s):** {payload.get('timeout', 120.0)}",
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
            ]
        )

    if incomplete_cells:
        lines.extend(
            [
                "",
                "### Incomplete cells (failed / missing / partial)",
                "",
                "| Model | Family | Track | Temp | Status | error_type | Message |",
                "|-------|--------|-------|-----:|--------|------------|---------|",
            ]
        )
        for cell in incomplete_cells:
            msg = error_message_from_payload(cell).replace("|", "\\|")
            if len(msg) > 80:
                msg = msg[:77] + "..."
            lines.append(
                "| `{model}` | {family} | {track} | {temp:g} | {status} | "
                "{error_type} | {msg} |".format(
                    model=cell["model"],
                    family=cell["family"],
                    track=cell["track"],
                    temp=float(cell.get("temperature", 0.0)),
                    status=cell.get("cell_status", cell.get("status", "failed")),
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
    metric_headers = ("extract", "verdict", "cert", "full", "tool_rate", "avg_tools")

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
                    lines.append(
                        "| `{model}` | {temp:g} | {track} | {n} | "
                        "{extract:.3f} | {verdict:.3f} | {cert:.3f} | {full:.3f} | "
                        "{tool_rate:.3f} | {avg_tools:.1f} |".format(
                            model=model,
                            temp=float(temperature),
                            track=track,
                            n=row.get("n", 0),
                            extract=row.get("extractability_rate", 0.0),
                            verdict=row.get("verdict_accuracy", 0.0),
                            cert=row.get("certificate_valid_rate", 0.0),
                            full=row.get("fully_correct_rate", 0.0),
                            tool_rate=row.get("tool_invocation_rate", 0.0),
                            avg_tools=row.get("average_tool_calls_per_item", 0.0),
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

        lines.extend(["", f"## {family} — failure movement", ""])
        failure_labels = list(_SUBMISSION_FAILURE_CLASSES)
        lines.append("| Model | Temp | Track | " + " | ".join(failure_labels) + " |")
        lines.append("|-------|-----:|-------|" + "|".join(["---:"] * len(failure_labels)) + "|")
        for model in family_models:
            for temperature in temperatures:
                for track in tracks:
                    row = indexed.get((model, family, float(temperature), track))
                    if row is None:
                        continue
                    counts = row.get("track_failure_counts", {})
                    values = " | ".join(str(counts.get(label, 0)) for label in failure_labels)
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
