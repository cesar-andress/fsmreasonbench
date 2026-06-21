"""Structured failure recording and cell status for track pilot / local matrix runs."""

from __future__ import annotations

import json
import shutil
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

CellStatus = Literal["completed", "failed", "missing", "partial"]
CellErrorType = Literal[
    "timeout",
    "internal_runner_error",
    "model_protocol_error",
    "tool_execution_error",
    "unknown",
]

ERROR_JSON = "error.json"
ERROR_PREVIOUS_JSON = "error.previous.json"
CELL_STATE_JSON = "cell_state.json"
SCORES_JSONL = "scores.jsonl"
SUMMARY_FILES = ("summary.json", "track_summary.json")
PARTIAL_MARKERS = ("results.jsonl", SCORES_JSONL)


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def classify_cell_error(message: str) -> CellErrorType:
    lowered = message.lower()
    if "timed out" in lowered or "timeout" in lowered:
        return "timeout"
    if "cannot build distinguishing trace" in lowered:
        return "tool_execution_error"
    if "protocol" in lowered or "tool plan" in lowered:
        return "model_protocol_error"
    if "equivalence_certificate" in lowered and "distinguishing" in lowered:
        return "tool_execution_error"
    if "not allowed for family" in lowered:
        return "tool_execution_error"
    return "internal_runner_error"


def has_partial_outputs(run_dir: Path) -> bool:
    for name in PARTIAL_MARKERS:
        if (run_dir / name).exists():
            return True
    transcript_dir = run_dir / "transcripts"
    if transcript_dir.is_dir():
        try:
            next(transcript_dir.iterdir())
            return True
        except StopIteration:
            pass
    return False


def has_summary(run_dir: Path) -> bool:
    return any((run_dir / name).exists() for name in SUMMARY_FILES)


def has_scores(run_dir: Path) -> bool:
    return (run_dir / SCORES_JSONL).exists()


def classify_cell(run_dir: Path) -> CellStatus:
    from fsmreasonbench.runners.experiment_cells import classify_cell as _classify

    return _classify(run_dir)


def is_cell_failed(run_dir: Path) -> bool:
    return classify_cell(run_dir) == "failed"


def is_cell_complete(run_dir: Path) -> bool:
    return classify_cell(run_dir) == "completed"


def error_message_from_payload(payload: dict[str, Any]) -> str:
    return str(payload.get("error_message") or payload.get("error") or "")


def write_cell_error(
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
    started_at: str | None = None,
    ended_at: str | None = None,
    partial_outputs_present: bool | None = None,
    retryable: bool = True,
    exc_type: str | None = None,
    tb: str | None = None,
    root_cause: str | None = None,
) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    ended = ended_at or utc_timestamp()
    payload: dict[str, Any] = {
        "model": model,
        "model_dir": model_dir,
        "family": family,
        "track": track,
        "temperature": temperature,
        "out_dir": str(out_dir),
        "error_type": error_type,
        "error_message": error_message,
        "error": error_message,
        "started_at": started_at or ended,
        "ended_at": ended,
        "partial_outputs_present": (
            partial_outputs_present
            if partial_outputs_present is not None
            else has_partial_outputs(run_dir)
        ),
        "retryable": retryable,
    }
    if exc_type is not None:
        payload["exception_type"] = exc_type
    if tb:
        payload["traceback"] = tb
    if root_cause is not None:
        payload["root_cause"] = root_cause
    path = run_dir / ERROR_JSON
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def read_cell_error(run_dir: Path) -> dict[str, Any] | None:
    path = run_dir / ERROR_JSON
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def prepare_cell_rerun(
    run_dir: Path,
    *,
    force_cell: bool = False,
    resume_items: bool = True,
) -> None:
    """Archive prior error.json; optionally wipe outputs for a forced cell restart."""
    from fsmreasonbench.runners.experiment_cells import prepare_cell_rerun as _prepare

    _prepare(run_dir, force_cell=force_cell, resume_items=resume_items)


def clear_cell_error(run_dir: Path) -> None:
    path = run_dir / ERROR_JSON
    if path.exists():
        path.unlink()


def write_cell_state(run_dir: Path, *, status: str, **fields: Any) -> None:
    payload = {"status": status, "timestamp": utc_timestamp(), **fields}
    (run_dir / CELL_STATE_JSON).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def should_run_cell(
    run_dir: Path,
    *,
    skip_completed: bool,
    retry_failed: bool,
    skip_failed: bool,
    force: bool,
    status: CellStatus | None = None,
    force_cell: bool = False,
) -> bool:
    from fsmreasonbench.runners.experiment_cells import should_run_cell as _should

    return _should(
        run_dir,
        skip_completed=skip_completed,
        retry_failed=retry_failed,
        skip_failed=skip_failed,
        force_all=force,
        force_cell=force_cell,
        status=status,  # type: ignore[arg-type]
    )


def infer_distinguishing_trace_root_cause(*, family: str, track: str) -> str:
    if family == "C2":
        return (
            "model_requested_wrong_tool: F1 solver.distinguishing_certificate invoked on "
            "single-FSM C2 item (pre-fix: no family tool guard; uncaught RuntimeError)"
        )
    if family == "F1" and track == "R2":
        return (
            "model_requested_wrong_tool: distinguishing_certificate on equivalent pair "
            "without prior check_separation (use equivalence_certificate)"
        )
    return "internal_runner_error"


def build_incomplete_cell_record(
    *,
    model: str,
    model_dir: str,
    family: str,
    track: str,
    temperature: float,
    run_dir: Path,
    cohort_id: str,
    status: CellStatus,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "model": model,
        "model_dir": model_dir,
        "family": family,
        "track": track,
        "temperature": temperature,
        "run_dir": str(run_dir),
        "cohort_id": cohort_id,
        "cell_status": status,
        "status": status if status != "completed" else "completed",
    }
    error_payload = read_cell_error(run_dir)
    if error_payload is not None:
        record["error_type"] = error_payload.get("error_type", "unknown")
        record["error_message"] = error_message_from_payload(error_payload)
        record["error"] = record["error_message"]
        record["retryable"] = error_payload.get("retryable", True)
        record["partial_outputs_present"] = error_payload.get(
            "partial_outputs_present", has_partial_outputs(run_dir)
        )
        if "root_cause" in error_payload:
            record["root_cause"] = error_payload["root_cause"]
    elif status == "missing":
        record["error_type"] = "unknown"
        record["error_message"] = "cell never completed; no summary.json or error.json on disk"
        record["error"] = record["error_message"]
        record["retryable"] = True
        record["partial_outputs_present"] = False
    elif status == "partial":
        record["error_type"] = "internal_runner_error"
        record["error_message"] = (
            "partial outputs present but cell incomplete (missing summary.json or scores.jsonl)"
        )
        record["error"] = record["error_message"]
        record["retryable"] = True
        record["partial_outputs_present"] = True
    return record


def summarize_cell_inventory(inventory: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"completed": 0, "failed": 0, "missing": 0, "partial": 0}
    for row in inventory:
        status = row.get("cell_status", "missing")
        if status in counts:
            counts[status] += 1
    return counts
