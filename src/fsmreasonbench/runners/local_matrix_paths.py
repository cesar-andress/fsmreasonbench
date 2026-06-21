"""Local matrix cell path helpers and misplaced-output repair."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fsmreasonbench.runners.cell_failure import read_cell_error
from fsmreasonbench.runners.experiment_cells import (
    detect_cell_status,
    read_cell_status,
)
from fsmreasonbench.runners.pilot_models import model_dir_name
from fsmreasonbench.runners.track_pilot_models import (
    TRACK_IDS,
    build_cell_dir,
    infer_matrix_layout,
)

RepairActionStatus = Literal["planned", "applied", "skipped", "ambiguous", "conflict"]
MisplacedExtendedStatus = Literal[
    "misplaced_partial",
    "misplaced_running",
    "misplaced_failed",
    "misplaced_completed",
]

REPAIR_LOG_JSON = "repair_log.json"


def infer_temperature_from_artifacts(run_dir: Path) -> float | None:
    payload = read_cell_status(run_dir)
    if payload is not None and payload.get("temperature") is not None:
        return float(payload["temperature"])
    error_payload = read_cell_error(run_dir)
    if error_payload is not None and error_payload.get("temperature") is not None:
        return float(error_payload["temperature"])
    return None


def misplaced_extended_status(run_dir: Path, *, stale_threshold_seconds: float) -> MisplacedExtendedStatus:
    base = detect_cell_status(run_dir, stale_threshold_seconds=stale_threshold_seconds)
    if base in {"running", "stale-running"}:
        return "misplaced_running"
    if base == "failed":
        return "misplaced_failed"
    if base == "completed":
        return "misplaced_completed"
    return "misplaced_partial"


def is_misplaced_cell_dir(path: Path, *, tracks: tuple[str, ...] = TRACK_IDS) -> bool:
    if not path.is_dir():
        return False
    if path.name not in tracks:
        return False
    parent = path.parent
    if parent.name.startswith("temp_"):
        return False
    return parent.name in {"C2", "F1"}


def scan_misplaced_cells(
    root: Path,
    *,
    models: tuple[str, ...] | None = None,
    families: tuple[str, ...] = ("C2", "F1"),
    tracks: tuple[str, ...] = TRACK_IDS,
    stale_running_seconds: float = 3600.0,
) -> list[dict[str, Any]]:
    if not infer_matrix_layout(root):
        return []

    model_entries: list[tuple[str, str]] = []
    if models:
        model_entries = [(model, model_dir_name(model)) for model in models]
    else:
        summary_path = root / "combined_summary.json"
        if summary_path.exists():
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
            summary_models = payload.get("models", [])
            if isinstance(summary_models, list):
                model_entries = [
                    (str(model), model_dir_name(str(model))) for model in summary_models
                ]
        if not model_entries:
            for child in sorted(root.iterdir()):
                if child.is_dir() and child.name not in {REPAIR_LOG_JSON}:
                    model_entries.append((child.name, child.name))
    rows: list[dict[str, Any]] = []
    for model, mdir in model_entries:
        model_root = root / mdir
        if not model_root.is_dir():
            continue
        for family in families:
            family_root = model_root / family
            if not family_root.is_dir():
                continue
            for child in sorted(family_root.iterdir()):
                if not is_misplaced_cell_dir(child, tracks=tracks):
                    continue
                track = child.name
                temperature = infer_temperature_from_artifacts(child)
                extended = misplaced_extended_status(
                    child,
                    stale_threshold_seconds=stale_running_seconds,
                )
                target_dir = (
                    build_cell_dir(
                        root,
                        model,
                        family,
                        temperature,
                        track,
                        matrix_layout=True,
                    )
                    if temperature is not None
                    else None
                )
                rows.append(
                    {
                        "model": model,
                        "model_dir": mdir,
                        "family": family,
                        "track": track,
                        "temperature": temperature,
                        "run_dir": str(child),
                        "expected_run_dir": str(target_dir) if target_dir else None,
                        "extended_status": extended,
                        "cell_status": "partial",
                        "ambiguous": temperature is None,
                    }
                )
    return rows


@dataclass(frozen=True, slots=True)
class RepairAction:
    source_dir: Path
    target_dir: Path
    model: str
    family: str
    track: str
    temperature: float | None
    status: RepairActionStatus
    message: str


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _merge_path(source: Path, target: Path) -> tuple[RepairActionStatus, str]:
    if not target.exists():
        shutil.move(str(source), str(target))
        return "applied", f"moved {source.name} -> {target}"

    if source.is_dir() and target.is_dir():
        for child in sorted(source.iterdir()):
            status, message = _merge_path(child, target / child.name)
            if status == "conflict":
                return status, message
        if not any(source.iterdir()):
            source.rmdir()
        return "applied", f"merged directory {source.name} into {target}"

    if source.is_file() and target.is_file():
        if _file_digest(source) == _file_digest(target):
            source.unlink()
            return "applied", f"removed duplicate file {source.name} (identical to target)"
        return "conflict", f"target file exists with different content: {target}"

    return "conflict", f"cannot merge {source} onto existing {target}"


def plan_repair_actions(
    root: Path,
    *,
    models: tuple[str, ...] | None = None,
    families: tuple[str, ...] = ("C2", "F1"),
    tracks: tuple[str, ...] = TRACK_IDS,
) -> list[RepairAction]:
    actions: list[RepairAction] = []
    for row in scan_misplaced_cells(
        root,
        models=models,
        families=families,
        tracks=tracks,
    ):
        source = Path(row["run_dir"])
        temperature = row.get("temperature")
        if temperature is None:
            actions.append(
                RepairAction(
                    source_dir=source,
                    target_dir=source,
                    model=row["model"],
                    family=row["family"],
                    track=row["track"],
                    temperature=None,
                    status="ambiguous",
                    message="temperature could not be inferred from cell_status.json or error.json",
                )
            )
            continue
        target = build_cell_dir(
            root,
            row["model"],
            row["family"],
            float(temperature),
            row["track"],
            matrix_layout=True,
        )
        if target.exists() and any(target.iterdir()) and any(source.iterdir()):
            actions.append(
                RepairAction(
                    source_dir=source,
                    target_dir=target,
                    model=row["model"],
                    family=row["family"],
                    track=row["track"],
                    temperature=float(temperature),
                    status="conflict",
                    message=f"target already exists and is non-empty: {target}",
                )
            )
            continue
        actions.append(
            RepairAction(
                source_dir=source,
                target_dir=target,
                model=row["model"],
                family=row["family"],
                track=row["track"],
                temperature=float(temperature),
                status="planned",
                message=f"move {source} -> {target}",
            )
        )
    return actions


def apply_repair_actions(
    actions: list[RepairAction],
    *,
    dry_run: bool = True,
) -> list[RepairAction]:
    applied: list[RepairAction] = []
    for action in actions:
        if action.status in {"ambiguous", "conflict"}:
            applied.append(action)
            continue
        if dry_run:
            applied.append(action)
            continue
        target = action.target_dir
        target.parent.mkdir(parents=True, exist_ok=True)
        status, message = _merge_path(action.source_dir, target)
        applied.append(
            RepairAction(
                source_dir=action.source_dir,
                target_dir=action.target_dir,
                model=action.model,
                family=action.family,
                track=action.track,
                temperature=action.temperature,
                status=status,
                message=message,
            )
        )
    return applied


def write_repair_log(root: Path, actions: list[RepairAction], *, dry_run: bool) -> Path:
    payload = {
        "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "dry_run": dry_run,
        "actions": [
            {
                "source_dir": str(action.source_dir),
                "target_dir": str(action.target_dir),
                "model": action.model,
                "family": action.family,
                "track": action.track,
                "temperature": action.temperature,
                "status": action.status,
                "message": action.message,
            }
            for action in actions
        ],
    }
    path = root / REPAIR_LOG_JSON
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
