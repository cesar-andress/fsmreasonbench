"""Artifact layout and run identity for clean_v2."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fsmreasonbench.clean_v2.condition import ConditionSpec
from fsmreasonbench.clean_v2.fingerprint import fingerprint_condition
from fsmreasonbench.models.serialization import canonical_json


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def condition_cell_dirname(condition: ConditionSpec) -> str:
    return (
        f"contract-{condition.contract.value}"
        f"__tools-{condition.tool_palette.value}"
        f"__oracle-{condition.oracle_info.value}"
        f"__format-{condition.format_assist.value}"
        f"__model-{_safe(condition.model)}"
        f"__T-{condition.temperature}"
    )


def _safe(text: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-._" else "_" for ch in text)


def run_id_for(
    condition: ConditionSpec,
    *,
    item_id: str,
    item_manifest_fingerprint: str,
) -> str:
    fp = fingerprint_condition(condition, item_manifest_fingerprint=item_manifest_fingerprint)
    material = canonical_json(
        {
            "fingerprint": fp,
            "item_id": item_id,
            "repetition_index": condition.repetition_index,
        }
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def repetition_dir(root: Path, condition: ConditionSpec) -> Path:
    return root / condition_cell_dirname(condition) / f"rep_{condition.repetition_index:02d}"


def ensure_run_paths(root: Path, condition: ConditionSpec) -> Path:
    path = repetition_dir(root, condition)
    path.mkdir(parents=True, exist_ok=True)
    (path / "transcripts").mkdir(exist_ok=True)
    return path


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows
