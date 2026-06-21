"""Summarize on-disk experiment cell status for matrix-style runs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fsmreasonbench.runners.experiment_cells import (
    DEFAULT_STALE_RUNNING_SECONDS,
    suggested_retry_command,
    summarize_extended_inventory,
)
from fsmreasonbench.runners.track_pilot_models import (
    TrackPilotModelsConfig,
    scan_matrix_inventory,
)


@dataclass(frozen=True, slots=True)
class ExperimentStatusResult:
    root: Path
    inventory: list[dict[str, Any]]
    status_counts: dict[str, int]
    incomplete_cells: list[dict[str, Any]]
    suggested_retry: str


def scan_experiment_status(
    root: Path,
    *,
    models: tuple[str, ...],
    families: tuple[str, ...] = ("C2", "F1"),
    tracks: tuple[str, ...] = ("R0", "R1", "R2"),
    temperatures: tuple[float, ...] = (0.0, 0.2, 0.7),
    stale_running_seconds: float = DEFAULT_STALE_RUNNING_SECONDS,
    c2_cohort_id: str = "c2-reachability-level3-v0.1-exploratory",
    f1_cohort_id: str = "f1-mixed-level3-v0.1-exploratory",
) -> ExperimentStatusResult:
    config = TrackPilotModelsConfig(
        models=models,
        families=families,
        tracks=tracks,
        c2_items_path=".",
        f1_items_path=".",
        out_dir=root,
        temperatures=temperatures,
        stale_running_seconds=stale_running_seconds,
        c2_cohort_id=c2_cohort_id,
        f1_cohort_id=f1_cohort_id,
    )
    inventory = scan_matrix_inventory(
        root,
        config,
        cohort_ids={"C2": c2_cohort_id, "F1": f1_cohort_id},
    )
    status_counts = summarize_extended_inventory(inventory)
    incomplete = [
        row
        for row in inventory
        if row.get("extended_status", row.get("cell_status")) != "completed"
    ]
    retry = suggested_retry_command(
        root=root,
        models=models,
        families=families,
        tracks=tracks,
        temperatures=temperatures,
    )
    return ExperimentStatusResult(
        root=root,
        inventory=inventory,
        status_counts=status_counts,
        incomplete_cells=incomplete,
        suggested_retry=retry,
    )


def format_experiment_status_report(result: ExperimentStatusResult) -> str:
    counts = result.status_counts
    lines = [
        f"# Experiment status — {result.root}",
        "",
        "## Summary",
        "",
        f"- **Expected cells:** {counts.get('expected', len(result.inventory))}",
        f"- **Completed:** {counts.get('completed', 0)}",
        f"- **Failed:** {counts.get('failed', 0)}",
        f"- **Missing:** {counts.get('missing', 0)}",
        f"- **Partial:** {counts.get('partial', 0)}",
        f"- **Running:** {counts.get('running', 0)}",
        f"- **Stale-running:** {counts.get('stale-running', 0)}",
        "",
    ]
    if result.incomplete_cells:
        lines.extend(
            [
                "## Incomplete cells",
                "",
                "| Model | Family | Track | Temp | Status |",
                "|-------|--------|-------|-----:|--------|",
            ]
        )
        for cell in result.incomplete_cells:
            status = cell.get("extended_status", cell.get("cell_status", "unknown"))
            lines.append(
                "| `{model}` | {family} | {track} | {temp:g} | {status} |".format(
                    model=cell["model"],
                    family=cell["family"],
                    track=cell["track"],
                    temp=float(cell.get("temperature", 0.0)),
                    status=status,
                )
            )
        lines.append("")
    lines.extend(
        [
            "## Suggested retry",
            "",
            "```bash",
            result.suggested_retry,
            "```",
            "",
        ]
    )
    return "\n".join(lines)
