"""Multi-model R0/R1/R2 track pilot evaluation across frozen exploratory cohorts."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.evaluator.jsonl import load_items_jsonl
from fsmreasonbench.evaluator.models import FailureStage
from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.runners.ollama_batch import GenerateFn, OllamaBatchConfig
from fsmreasonbench.runners.ollama_track_batch import run_ollama_track_batch
from fsmreasonbench.runners.pilot_models import model_dir_name
from fsmreasonbench.tracks.delegation import DELEGATION_GAP_METRICS, compute_delegation_gap
from fsmreasonbench.tracks.models import TrackId

GenerateFactory = Callable[[str], GenerateFn]

DEFAULT_C2_ITEMS = "cohorts/v0.1-exploratory/c2-reachability-level3/items.jsonl"
DEFAULT_F1_ITEMS = "cohorts/v0.1-exploratory/f1-mixed-level3/items.jsonl"
DEFAULT_C2_COHORT_ID = "c2-reachability-level3-v0.1-exploratory"
DEFAULT_F1_COHORT_ID = "f1-mixed-level3-v0.1-exploratory"

_TRACK_ROW_FIELDS = (
    "model",
    "model_dir",
    "family",
    "track",
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


@dataclass(frozen=True, slots=True)
class TrackPilotModelsConfig:
    models: tuple[str, ...]
    families: tuple[str, ...]
    tracks: tuple[str, ...]
    c2_items_path: str | Path
    f1_items_path: str | Path
    out_dir: str | Path
    max_items: int = 20
    temperature: float = 0.0
    timeout: float = 120.0
    skip_completed: bool = True
    c2_cohort_id: str = DEFAULT_C2_COHORT_ID
    f1_cohort_id: str = DEFAULT_F1_COHORT_ID


@dataclass(frozen=True, slots=True)
class TrackPilotModelsResult:
    track_rows: list[dict[str, Any]]
    delegation_rows: list[dict[str, Any]]
    failed_cells: list[dict[str, Any]]
    out_dir: Path


def cell_dir(out_dir: Path, model: str, family: str, track: str) -> Path:
    return out_dir / model_dir_name(model) / family / track


def is_cell_complete(run_dir: Path) -> bool:
    for name in ("track_summary.json", "summary.json"):
        if (run_dir / name).exists():
            return True
    return False


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
    cohort_id: str,
    run_dir: Path,
    status: str = "completed",
) -> dict[str, Any]:
    return {
        "model": model,
        "model_dir": model_dir_name(model),
        "family": family,
        "track": track,
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


def build_delegation_rows(track_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compute R1−R0, R2−R0, and R2−R1 delegation gaps per model × family."""
    indexed: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in track_rows:
        if row.get("status") != "completed":
            continue
        indexed[(row["model"], row["family"], row["track"])] = row

    delegation_rows: list[dict[str, Any]] = []
    models = list(dict.fromkeys(row["model"] for row in track_rows))
    families = list(dict.fromkeys(row["family"] for row in track_rows))

    for model in models:
        for family in families:
            r0 = indexed.get((model, family, "R0"))
            r1 = indexed.get((model, family, "R1"))
            r2 = indexed.get((model, family, "R2"))
            if r0 is None:
                continue

            row: dict[str, Any] = {
                "model": model,
                "family": family,
                "cohort_id": r0.get("cohort_id"),
                "n": r0.get("n"),
            }
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


def _summary_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "family": row["family"],
        "n": row["n"],
        "track": row["track"],
        "cohort_id": row.get("cohort_id"),
        **{metric: row[metric] for metric in DELEGATION_GAP_METRICS},
    }


def run_track_pilot_models(
    config: TrackPilotModelsConfig,
    generate_factory: GenerateFactory,
) -> TrackPilotModelsResult:
    """
    Run R0/R1/R2 track batches for each model × family cell.

    Layout::

        {out_dir}/{model_dir}/{family}/{track}/results.jsonl
        {out_dir}/{model_dir}/{family}/{track}/scores.jsonl
        {out_dir}/{model_dir}/{family}/{track}/transcripts/
        {out_dir}/{model_dir}/{family}/{track}/summary.json
        {out_dir}/combined_summary.json
        {out_dir}/combined_summary.csv
        {out_dir}/report.md
    """
    if not config.models:
        raise ValueError("at least one model is required")
    if not config.families:
        raise ValueError("at least one family is required")
    if not config.tracks:
        raise ValueError("at least one track is required")
    if config.max_items < 1:
        raise ValueError("max_items must be >= 1")

    for track in config.tracks:
        TrackId(track)

    root = Path(config.out_dir)
    root.mkdir(parents=True, exist_ok=True)

    family_items = _load_family_items(config)
    cohort_ids = {"C2": config.c2_cohort_id, "F1": config.f1_cohort_id}

    track_rows: list[dict[str, Any]] = []
    failed_cells: list[dict[str, Any]] = []

    for model in config.models:
        generate = generate_factory(model)
        for family in config.families:
            items = family_items[family]
            cohort_id = cohort_ids[family]
            for track in config.tracks:
                run_dir = cell_dir(root, model, family, track)
                run_dir.mkdir(parents=True, exist_ok=True)

                if config.skip_completed and is_cell_complete(run_dir):
                    summary = load_cell_summary(run_dir)
                    track_rows.append(
                        build_track_row(
                            summary,
                            model=model,
                            family=family,
                            track=track,
                            cohort_id=cohort_id,
                            run_dir=run_dir,
                        )
                    )
                    continue

                try:
                    batch_result = run_ollama_track_batch(
                        items,
                        generate,
                        run_dir / "results.jsonl",
                        OllamaBatchConfig(
                            model=model,
                            temperature=config.temperature,
                            timeout=config.timeout,
                            max_items=config.max_items,
                        ),
                        track=track,
                        out_dir=run_dir,
                    )
                    track_rows.append(
                        build_track_row(
                            batch_result.summary,
                            model=model,
                            family=family,
                            track=track,
                            cohort_id=cohort_id,
                            run_dir=run_dir,
                        )
                    )
                except Exception as exc:  # noqa: BLE001 — pilot continues after cell failure
                    failed_cells.append(
                        {
                            "model": model,
                            "family": family,
                            "track": track,
                            "run_dir": str(run_dir),
                            "error": str(exc),
                        }
                    )
                    track_rows.append(
                        {
                            "model": model,
                            "model_dir": model_dir_name(model),
                            "family": family,
                            "track": track,
                            "cohort_id": cohort_id,
                            "run_dir": str(run_dir),
                            "status": "failed",
                            "error": str(exc),
                        }
                    )

    delegation_rows = build_delegation_rows(track_rows)
    payload = {
        "models": list(config.models),
        "families": list(config.families),
        "tracks": list(config.tracks),
        "max_items": config.max_items,
        "temperature": config.temperature,
        "timeout": config.timeout,
        "cohort_ids": cohort_ids,
        "track_rows": track_rows,
        "delegation_rows": delegation_rows,
        "failed_cells": failed_cells,
    }
    dump_json(root / "combined_summary.json", payload)
    write_track_pilot_csv(root / "combined_summary.csv", track_rows, delegation_rows)
    (root / "report.md").write_text(
        render_track_pilot_report(payload),
        encoding="utf-8",
    )
    return TrackPilotModelsResult(
        track_rows=track_rows,
        delegation_rows=delegation_rows,
        failed_cells=failed_cells,
        out_dir=root,
    )


def write_track_pilot_csv(
    path: str | Path,
    track_rows: list[dict[str, Any]],
    delegation_rows: list[dict[str, Any]],
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
            delegation_fieldnames = ["row_type", "model", "family", "cohort_id", "n"]
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


def render_track_pilot_report(payload: dict[str, Any]) -> str:
    models = payload["models"]
    families = payload["families"]
    tracks = payload["tracks"]
    cohort_ids = payload["cohort_ids"]
    track_rows = [row for row in payload["track_rows"] if row.get("status") == "completed"]
    delegation_rows = payload["delegation_rows"]
    failed_cells = payload.get("failed_cells", [])

    lines = [
        "# Track Pilot Report",
        "",
        "## Overview",
        "",
        f"- **Models:** {', '.join(f'`{model}`' for model in models)}",
        f"- **Families:** {', '.join(families)}",
        f"- **Tracks:** {', '.join(tracks)}",
        f"- **Items per cell:** n={payload['max_items']}",
        f"- **Temperature:** {payload['temperature']}",
        f"- **Timeout (s):** {payload.get('timeout', 120.0)}",
        "",
        "### Cohort IDs",
        "",
    ]
    for family, cohort_id in cohort_ids.items():
        lines.append(f"- **{family}:** `{cohort_id}`")

    if failed_cells:
        lines.extend(["", "### Failed cells", ""])
        for cell in failed_cells:
            lines.append(
                f"- `{cell['model']}` / {cell['family']} / {cell['track']}: {cell['error']}"
            )

    metric_headers = (
        "extract",
        "verdict",
        "cert",
        "full",
        "tool_rate",
        "avg_tools",
    )
    indexed = {(row["model"], row["family"], row["track"]): row for row in track_rows}

    for family in families:
        family_models = [
            model
            for model in models
            if any((model, family, track) in indexed for track in tracks)
        ]
        lines.extend(["", f"## {family} — per-track metrics", ""])
        header = "| Model | Track | n | " + " | ".join(metric_headers) + " |"
        lines.append(header)
        lines.append("|-------|-------|--:|" + "|".join(["------:"] * len(metric_headers)) + "|")
        for model in family_models:
            for track in tracks:
                row = indexed.get((model, family, track))
                if row is None:
                    continue
                lines.append(
                    "| `{model}` | {track} | {n} | "
                    "{extract:.3f} | {verdict:.3f} | {cert:.3f} | {full:.3f} | "
                    "{tool_rate:.3f} | {avg_tools:.1f} |".format(
                        model=model,
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

        lines.extend(["", f"## {family} — delegation gaps", ""])
        lines.append(
            "| Model | Δ_R1−R0 verdict | Δ_R1−R0 cert | Δ_R1−R0 full | "
            "Δ_R2−R0 verdict | Δ_R2−R0 cert | Δ_R2−R0 full | "
            "Δ_R2−R1 verdict | Δ_R2−R1 cert | Δ_R2−R1 full |"
        )
        lines.append(
            "|-------|----------------:|-------------:|-----------:|"
            "----------------:|-------------:|-----------:|"
            "----------------:|-------------:|-----------:|"
        )
        for row in delegation_rows:
            if row["family"] != family:
                continue
            lines.append(
                "| `{model}` | "
                "{d11:+.3f} | {d12:+.3f} | {d13:+.3f} | "
                "{d21:+.3f} | {d22:+.3f} | {d23:+.3f} | "
                "{d31:+.3f} | {d32:+.3f} | {d33:+.3f} |".format(
                    model=row["model"],
                    d11=row.get("delta_R1_minus_R0_verdict_accuracy", float("nan")),
                    d12=row.get("delta_R1_minus_R0_certificate_valid_rate", float("nan")),
                    d13=row.get("delta_R1_minus_R0_fully_correct_rate", float("nan")),
                    d21=row.get("delta_R2_minus_R0_verdict_accuracy", float("nan")),
                    d22=row.get("delta_R2_minus_R0_certificate_valid_rate", float("nan")),
                    d23=row.get("delta_R2_minus_R0_fully_correct_rate", float("nan")),
                    d31=row.get("delta_R2_minus_R1_verdict_accuracy", float("nan")),
                    d32=row.get("delta_R2_minus_R1_certificate_valid_rate", float("nan")),
                    d33=row.get("delta_R2_minus_R1_fully_correct_rate", float("nan")),
                )
            )

        lines.extend(["", f"## {family} — failure movement", ""])
        failure_labels = list(_TOOL_FAILURE_CLASSES) + list(_SUBMISSION_FAILURE_CLASSES)
        lines.append("| Model | Track | " + " | ".join(failure_labels) + " |")
        lines.append("|-------|-------|" + "|".join(["---:"] * len(failure_labels)) + "|")
        for model in family_models:
            for track in tracks:
                row = indexed.get((model, family, track))
                if row is None:
                    continue
                counts = row.get("track_failure_counts", {})
                values = " | ".join(str(counts.get(label, 0)) for label in failure_labels)
                lines.append(f"| `{model}` | {track} | {values} |")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This report is **exploratory** only:",
            "",
            "- n=20 items per model × family × track cell.",
            "- Local Ollama models only (no frontier API panel).",
            "- Frozen **v0.1-exploratory** cohorts — not `v1.0-public`.",
            "- **Not a final benchmark claim.**",
            "",
            "When reading delegation gaps, ask whether tools improve **verdict accuracy only**, "
            "**certificate validity**, or **both** (fully correct). A positive Δ_R2−R0 on "
            "certificate_valid_rate with flat verdict_accuracy suggests solver delegation helps "
            "witness construction without changing boolean answers.",
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
