"""JSONL helpers for batch evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

from fsmreasonbench.evaluator.io import item_from_dict
from fsmreasonbench.items.assembly import BenchmarkItem


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                records.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON on line {line_number} of {path}: {exc}") from exc
    return records


def write_jsonl(path: str | Path, records: Iterator[dict[str, Any]] | list[dict[str, Any]]) -> None:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True))
            handle.write("\n")


def append_jsonl(path: str | Path, record: dict[str, Any]) -> None:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True))
        handle.write("\n")


def load_items_jsonl(path: str | Path) -> list[BenchmarkItem]:
    return [item_from_dict(record) for record in read_jsonl(path)]
