"""Local matrix cell path helpers and misplaced-output repair."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fsmreasonbench.evaluator.jsonl import append_jsonl, read_jsonl
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
NON_MODEL_DIR_NAMES = frozenset({"plots", "repair_log.json"})
DEFAULT_MATRIX_TEMPERATURES = (0.0, 0.2, 0.7)


def infer_model_from_artifacts(run_dir: Path, *, model_dir: str) -> str | None:
    payload = read_cell_status(run_dir)
    if payload is not None and payload.get("model"):
        return str(payload["model"])
    error_payload = read_cell_error(run_dir)
    if error_payload is not None and error_payload.get("model"):
        return str(error_payload["model"])
    return None


def infer_temperature_from_artifacts(run_dir: Path) -> float | None:
    payload = read_cell_status(run_dir)
    if payload is not None and payload.get("temperature") is not None:
        return float(payload["temperature"])
    error_payload = read_cell_error(run_dir)
    if error_payload is not None and error_payload.get("temperature") is not None:
        return float(error_payload["temperature"])
    return None


def infer_temperature_for_misplaced_cell(
    root: Path,
    *,
    model: str,
    family: str,
    track: str,
    run_dir: Path,
) -> float | None:
    temperature = infer_temperature_from_artifacts(run_dir)
    if temperature is not None:
        return temperature
    for candidate_temp in DEFAULT_MATRIX_TEMPERATURES:
        target = build_cell_dir(
            root,
            model,
            family,
            candidate_temp,
            track,
            matrix_layout=True,
        )
        if target.exists() and read_cell_status(target) is not None:
            payload = read_cell_status(target)
            if payload is not None and payload.get("temperature") is not None:
                return float(payload["temperature"])
            return candidate_temp
    return None


def discover_model_roots(
    root: Path,
    *,
    models: tuple[str, ...] | None = None,
) -> list[tuple[str | None, Path]]:
    """Return model roots as (canonical model name if known, directory path)."""
    entries: list[tuple[str | None, Path]] = []
    seen_dirs: set[str] = set()

    if models:
        for model in models:
            mdir = model_dir_name(model)
            if mdir in seen_dirs:
                continue
            seen_dirs.add(mdir)
            entries.append((model, root / mdir))

    summary_path = root / "combined_summary.json"
    if summary_path.exists():
        try:
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        summary_models = payload.get("models", [])
        if isinstance(summary_models, list):
            for model in summary_models:
                mdir = model_dir_name(str(model))
                if mdir in seen_dirs:
                    continue
                seen_dirs.add(mdir)
                entries.append((str(model), root / mdir))

    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name in NON_MODEL_DIR_NAMES:
            continue
        if not any((child / family).is_dir() for family in ("C2", "F1")):
            continue
        if child.name in seen_dirs:
            continue
        seen_dirs.add(child.name)
        entries.append((None, child))

    return entries


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

    rows: list[dict[str, Any]] = []
    for model_hint, model_root in discover_model_roots(root, models=models):
        if not model_root.is_dir():
            continue
        mdir = model_root.name
        for family in families:
            family_root = model_root / family
            if not family_root.is_dir():
                continue
            for child in sorted(family_root.iterdir()):
                if not is_misplaced_cell_dir(child, tracks=tracks):
                    continue
                track = child.name
                model = infer_model_from_artifacts(child, model_dir=mdir) or model_hint
                if model is None:
                    model = mdir
                temperature = infer_temperature_for_misplaced_cell(
                    root,
                    model=model,
                    family=family,
                    track=track,
                    run_dir=child,
                )
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


def _merge_jsonl_by_item_id(source: Path, target: Path) -> tuple[RepairActionStatus, str]:
    source_rows = read_jsonl(source)
    if target.exists():
        target_ids = {
            str(row.get("item_id"))
            for row in read_jsonl(target)
            if row.get("item_id") is not None
        }
    else:
        target_ids = set()
    appended = 0
    for row in source_rows:
        item_id = row.get("item_id")
        if item_id is None or str(item_id) in target_ids:
            continue
        append_jsonl(target, row)
        target_ids.add(str(item_id))
        appended += 1
    source.unlink()
    return "applied", f"merged {appended} row(s) from {source.name} into {target.name}"


def _merge_path(source: Path, target: Path) -> tuple[RepairActionStatus, str]:
    if not target.exists():
        shutil.move(str(source), str(target))
        return "applied", f"moved {source.name} -> {target}"

    if source.is_dir() and target.is_dir():
        for child in sorted(source.iterdir()):
            status, message = _merge_path(child, target / child.name)
            if status == "conflict":
                return status, message
        if source.exists() and not any(source.iterdir()):
            source.rmdir()
        return "applied", f"merged directory {source.name} into {target}"

    if source.is_file() and target.is_file():
        if source.name in {"scores.jsonl", "results.jsonl"}:
            return _merge_jsonl_by_item_id(source, target)
        if source.name in {"cell_status.json", "error.json", "summary.json", "track_summary.json"}:
            source.unlink()
            return "applied", f"kept existing {target.name}; removed misplaced {source.name}"
        if "transcripts" in source.parts and target.exists():
            source.unlink()
            return "applied", f"kept existing transcript {target.name}; removed misplaced duplicate"
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
        verb = "merge" if target.exists() and any(target.iterdir()) else "move"
        actions.append(
            RepairAction(
                source_dir=source,
                target_dir=target,
                model=row["model"],
                family=row["family"],
                track=row["track"],
                temperature=float(temperature),
                status="planned",
                message=f"{verb} {source} -> {target}",
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
