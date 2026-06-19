"""Load benchmark items and evaluation artifacts from JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fsmreasonbench.evaluator.models import Transcript
from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.models.serialization import fsm_from_dict


def load_json(path: str | Path) -> Any:
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def dump_json(path: str | Path, payload: Any) -> None:
    with Path(path).open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def item_from_dict(data: dict[str, Any]) -> BenchmarkItem:
    """Build BenchmarkItem from full or evaluatee JSON."""
    if "answer_key" not in data:
        raise ValueError("item JSON must include answer_key for scoring")
    return BenchmarkItem(
        item_id=data["item_id"],
        family=data["family"],
        family_tier=data.get("family_tier", "calibration"),
        fsm=fsm_from_dict(data["fsm"]),
        question=data["question"],
        answer_key=data["answer_key"],
        difficulty=data.get("difficulty", {}),
        contamination=data.get("contamination", {}),
    )


def load_item(path: str | Path) -> BenchmarkItem:
    return item_from_dict(load_json(path))


def load_transcript(path: str | Path) -> Transcript:
    return Transcript.from_dict(load_json(path))
