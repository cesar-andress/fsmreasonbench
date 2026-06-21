"""Structured failure recording for track pilot / local matrix cells."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

CellErrorType = Literal[
    "timeout",
    "internal_runner_error",
    "model_protocol_error",
    "tool_execution_error",
]

ERROR_JSON = "error.json"
CELL_STATE_JSON = "cell_state.json"


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
    return "internal_runner_error"


def write_cell_error(
    run_dir: Path,
    *,
    error_type: CellErrorType,
    error: str,
    model: str,
    family: str,
    track: str,
    temperature: float,
    exc_type: str | None = None,
) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "error_type": error_type,
        "error": error,
        "model": model,
        "family": family,
        "track": track,
        "temperature": temperature,
        "timestamp": utc_timestamp(),
    }
    if exc_type is not None:
        payload["exception_type"] = exc_type
    path = run_dir / ERROR_JSON
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def read_cell_error(run_dir: Path) -> dict[str, Any] | None:
    path = run_dir / ERROR_JSON
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


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


def is_cell_failed(run_dir: Path) -> bool:
    return (run_dir / ERROR_JSON).exists()


def is_cell_complete(run_dir: Path) -> bool:
    if is_cell_failed(run_dir):
        return False
    for name in ("track_summary.json", "summary.json"):
        if (run_dir / name).exists():
            return True
    return False


def should_run_cell(
    run_dir: Path,
    *,
    skip_completed: bool,
    retry_failed: bool,
    skip_failed: bool,
    force: bool,
) -> bool:
    if force:
        return True
    if retry_failed:
        return is_cell_failed(run_dir)
    if skip_failed and is_cell_failed(run_dir):
        return False
    if skip_completed and is_cell_complete(run_dir):
        return False
    return True
