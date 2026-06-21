"""Cell status, classification, and incremental experiment planning."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fsmreasonbench.evaluator.jsonl import read_jsonl
from fsmreasonbench.runners.cell_failure import (
    CELL_STATE_JSON,
    ERROR_JSON,
    ERROR_PREVIOUS_JSON,
    SCORES_JSONL,
    SUMMARY_FILES,
    CellErrorType,
    CellStatus,
    build_incomplete_cell_record,
    error_message_from_payload,
    has_partial_outputs,
    has_scores,
    has_summary,
    read_cell_error,
    utc_timestamp,
    write_cell_error,
)

CELL_STATUS_JSON = "cell_status.json"
RESULTS_JSONL = "results.jsonl"

ExtendedCellStatus = Literal[
    "completed",
    "failed",
    "missing",
    "partial",
    "running",
    "stale-running",
]

DEFAULT_STALE_RUNNING_SECONDS = 3600.0


def compute_config_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def read_cell_status(run_dir: Path) -> dict[str, Any] | None:
    for name in (CELL_STATUS_JSON, CELL_STATE_JSON):
        path = run_dir / name
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return None


def write_cell_status(run_dir: Path, *, status: str, **fields: Any) -> None:
    payload = {
        "status": status,
        "updated_at": utc_timestamp(),
        **fields,
    }
    (run_dir / CELL_STATUS_JSON).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def cell_status_mtime(run_dir: Path) -> float | None:
    path = run_dir / CELL_STATUS_JSON
    if not path.exists():
        return None
    return path.stat().st_mtime


def is_stale_running(
    run_dir: Path,
    *,
    threshold_seconds: float = DEFAULT_STALE_RUNNING_SECONDS,
) -> bool:
    payload = read_cell_status(run_dir)
    if payload is None or payload.get("status") != "running":
        return False
    mtime = cell_status_mtime(run_dir)
    if mtime is None:
        return False
    age = datetime.now(timezone.utc).timestamp() - mtime
    return age > threshold_seconds


def detect_cell_status(
    run_dir: Path,
    *,
    stale_threshold_seconds: float = DEFAULT_STALE_RUNNING_SECONDS,
) -> ExtendedCellStatus:
    payload = read_cell_status(run_dir)
    if payload is not None and payload.get("status") == "running":
        if is_stale_running(run_dir, threshold_seconds=stale_threshold_seconds):
            return "stale-running"
        return "running"
    if (run_dir / ERROR_JSON).exists():
        return "failed"
    if has_summary(run_dir) and has_scores(run_dir):
        return "completed"
    if has_partial_outputs(run_dir) or has_summary(run_dir) or has_scores(run_dir):
        return "partial"
    return "missing"


def classify_cell(run_dir: Path) -> CellStatus:
    """Map extended status to legacy inventory categories."""
    status = detect_cell_status(run_dir)
    if status in {"running", "stale-running"}:
        return "partial"
    return status  # type: ignore[return-value]


def completed_item_ids(run_dir: Path) -> set[str]:
    ids: set[str] = set()
    scores_path = run_dir / SCORES_JSONL
    if scores_path.exists():
        for row in read_jsonl(scores_path):
            item_id = row.get("item_id")
            if isinstance(item_id, str):
                ids.add(item_id)
    return ids


def prepare_cell_rerun(
    run_dir: Path,
    *,
    force_cell: bool = False,
    resume_items: bool = True,
) -> None:
    """Archive errors; optionally wipe outputs for a forced cell restart."""
    error_path = run_dir / ERROR_JSON
    if error_path.exists():
        shutil.copy2(error_path, run_dir / ERROR_PREVIOUS_JSON)
        error_path.unlink()

    if force_cell or not resume_items:
        for name in (RESULTS_JSONL, SCORES_JSONL, *SUMMARY_FILES):
            path = run_dir / name
            if path.exists():
                path.unlink()
        transcript_dir = run_dir / "transcripts"
        if transcript_dir.is_dir():
            shutil.rmtree(transcript_dir)


def mark_cell_running(
    run_dir: Path,
    *,
    model: str,
    model_dir: str,
    family: str,
    track: str,
    temperature: float,
    item_source: str,
    config_hash: str,
    max_items: int,
) -> str:
    started_at = utc_timestamp()
    write_cell_status(
        run_dir,
        status="running",
        model=model,
        model_dir=model_dir,
        family=family,
        track=track,
        temperature=temperature,
        item_source=item_source,
        config_hash=config_hash,
        max_items=max_items,
        started_at=started_at,
    )
    return started_at


def mark_cell_completed(
    run_dir: Path,
    *,
    started_at: str,
    items_completed: int,
) -> None:
    payload = read_cell_status(run_dir) or {}
    write_cell_status(
        run_dir,
        status="completed",
        started_at=started_at,
        ended_at=utc_timestamp(),
        items_completed=items_completed,
        model=payload.get("model"),
        model_dir=payload.get("model_dir"),
        family=payload.get("family"),
        track=payload.get("track"),
        temperature=payload.get("temperature"),
        item_source=payload.get("item_source"),
        config_hash=payload.get("config_hash"),
    )


def mark_cell_failed(
    run_dir: Path,
    *,
    error_type: CellErrorType,
    error_message: str,
    model: str,
    model_dir: str,
    family: str,
    track: str,
    temperature: float,
    out_dir: str | Path,
    started_at: str,
    exc_type: str | None = None,
    tb: str | None = None,
    root_cause: str | None = None,
) -> None:
    write_cell_error(
        run_dir,
        error_type=error_type,
        error_message=error_message,
        model=model,
        model_dir=model_dir,
        family=family,
        track=track,
        temperature=temperature,
        out_dir=out_dir,
        started_at=started_at,
        ended_at=utc_timestamp(),
        partial_outputs_present=has_partial_outputs(run_dir),
        retryable=True,
        exc_type=exc_type,
        tb=tb,
        root_cause=root_cause,
    )
    write_cell_status(
        run_dir,
        status="failed",
        model=model,
        model_dir=model_dir,
        family=family,
        track=track,
        temperature=temperature,
        started_at=started_at,
        ended_at=utc_timestamp(),
        error_type=error_type,
        error_message=error_message,
    )


def should_run_cell(
    run_dir: Path,
    *,
    skip_completed: bool,
    retry_failed: bool,
    skip_failed: bool,
    force_all: bool,
    force_cell: bool,
    stale_threshold_seconds: float = DEFAULT_STALE_RUNNING_SECONDS,
    status: ExtendedCellStatus | None = None,
) -> bool:
    cell_status = status or detect_cell_status(
        run_dir,
        stale_threshold_seconds=stale_threshold_seconds,
    )
    if force_all or force_cell:
        return True
    if cell_status == "running":
        return False
    if cell_status == "completed" and skip_completed:
        return False
    if cell_status == "failed":
        if skip_failed:
            return False
        return retry_failed
    if cell_status == "stale-running":
        return retry_failed
    if cell_status == "missing":
        return True
    if cell_status == "partial":
        return True
    return cell_status != "completed"


@dataclass(frozen=True, slots=True)
class CellPlan:
    model: str
    model_dir: str
    family: str
    track: str
    temperature: float
    run_dir: Path
    cohort_id: str
    item_source: str
    status: ExtendedCellStatus
    action: Literal["run", "skip"]


def summarize_extended_inventory(
    inventory: list[dict[str, Any]],
) -> dict[str, int]:
    counts = {
        "completed": 0,
        "failed": 0,
        "missing": 0,
        "partial": 0,
        "running": 0,
        "stale-running": 0,
        "expected": len(inventory),
    }
    for row in inventory:
        status = row.get("extended_status", row.get("cell_status", "missing"))
        if status in counts:
            counts[status] += 1
    return counts


def build_incomplete_from_status(
    *,
    model: str,
    model_dir: str,
    family: str,
    track: str,
    temperature: float,
    run_dir: Path,
    cohort_id: str,
    status: ExtendedCellStatus,
) -> dict[str, Any]:
    legacy = "partial" if status in {"running", "stale-running"} else status
    if legacy in {"failed", "missing", "partial"}:
        record = build_incomplete_cell_record(
            model=model,
            model_dir=model_dir,
            family=family,
            track=track,
            temperature=temperature,
            run_dir=run_dir,
            cohort_id=cohort_id,
            status=legacy,  # type: ignore[arg-type]
        )
    else:
        record = {
            "model": model,
            "model_dir": model_dir,
            "family": family,
            "track": track,
            "temperature": temperature,
            "run_dir": str(run_dir),
            "cohort_id": cohort_id,
        }
    record["extended_status"] = status
    record["cell_status"] = legacy if legacy != "running" else "partial"
    if status == "stale-running":
        record["error_type"] = "internal_runner_error"
        record["error_message"] = "cell_status.json stuck in running (stale)"
        record["error"] = record["error_message"]
    elif status == "running":
        record["error_type"] = "unknown"
        record["error_message"] = "cell currently running"
        record["error"] = record["error_message"]
    status_payload = read_cell_status(run_dir)
    if status_payload is not None:
        record["cell_status_started_at"] = status_payload.get("started_at")
    error_payload = read_cell_error(run_dir)
    if error_payload is not None:
        record["error_type"] = error_payload.get("error_type", "unknown")
        record["error_message"] = error_message_from_payload(error_payload)
        record["error"] = record["error_message"]
    return record


def build_cell_plans(
    *,
    models: tuple[str, ...],
    families: tuple[str, ...],
    tracks: tuple[str, ...],
    temperatures: tuple[float, ...],
    out_dir: Path,
    item_sources: dict[str, str],
    cohort_ids: dict[str, str],
    use_temperature_dirs: bool,
    skip_completed: bool,
    retry_failed: bool,
    skip_failed: bool,
    force_all: bool,
    force_cell: bool,
    stale_threshold_seconds: float = DEFAULT_STALE_RUNNING_SECONDS,
) -> list[CellPlan]:
    from fsmreasonbench.runners.pilot_models import model_dir_name

    plans: list[CellPlan] = []
    for model in models:
        mdir = model_dir_name(model)
        for temperature in temperatures:
            for family in families:
                item_source = item_sources[family]
                cohort_id = cohort_ids[family]
                for track in tracks:
                    run_dir = _cell_dir(
                        out_dir,
                        model,
                        family,
                        track,
                        temperature=temperature,
                        use_temperature_dirs=use_temperature_dirs,
                    )
                    status = detect_cell_status(
                        run_dir,
                        stale_threshold_seconds=stale_threshold_seconds,
                    )
                    action: Literal["run", "skip"] = (
                        "run"
                        if should_run_cell(
                            run_dir,
                            skip_completed=skip_completed,
                            retry_failed=retry_failed,
                            skip_failed=skip_failed,
                            force_all=force_all,
                            force_cell=force_cell,
                            stale_threshold_seconds=stale_threshold_seconds,
                            status=status,
                        )
                        else "skip"
                    )
                    plans.append(
                        CellPlan(
                            model=model,
                            model_dir=mdir,
                            family=family,
                            track=track,
                            temperature=temperature,
                            run_dir=run_dir,
                            cohort_id=cohort_id,
                            item_source=item_source,
                            status=status,
                            action=action,
                        )
                    )
    return plans


def _cell_dir(
    out_dir: Path,
    model: str,
    family: str,
    track: str,
    *,
    temperature: float,
    use_temperature_dirs: bool,
) -> Path:
    from fsmreasonbench.runners.track_pilot_models import cell_dir

    return cell_dir(
        out_dir,
        model,
        family,
        track,
        temperature=temperature,
        use_temperature_dirs=use_temperature_dirs,
    )


def suggested_retry_command(
    *,
    root: Path,
    models: tuple[str, ...] | None = None,
    families: tuple[str, ...] = ("C2", "F1"),
    tracks: tuple[str, ...] = ("R0", "R1", "R2"),
    temperatures: tuple[float, ...] = (0.0, 0.2, 0.7),
    max_items: int = 20,
    timeout: float = 900.0,
) -> str:
    model_arg = ",".join(models) if models else "qwen2.5-coder:7b,llama3.1:8b,mistral-nemo:12b,gemma2:9b"
    temp_arg = ",".join(str(t) for t in temperatures)
    return (
        "PYTHONPATH=src python -m fsmreasonbench.cli.run_track_pilot_models "
        f"--models {model_arg} "
        f"--families {','.join(families)} "
        f"--tracks {','.join(tracks)} "
        f"--temperatures {temp_arg} "
        f"--max-items {max_items} --timeout {timeout:g} "
        f"--out-dir {root} --retry-failed --incremental-safe"
    )
