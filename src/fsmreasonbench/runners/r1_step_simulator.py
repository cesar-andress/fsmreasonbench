"""R1 step-simulator runner facade."""

from __future__ import annotations

from pathlib import Path

from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.evaluator.jsonl import load_items_jsonl
from fsmreasonbench.evaluator.summary import summarize_scoring_records
from fsmreasonbench.tracks.models import TrackId
from fsmreasonbench.tracks.runner import run_track_batch

__all__ = ["run_r1_batch"]


def run_r1_batch(
    items_path: str | Path,
    out_dir: str | Path,
) -> dict:
    """Run R1 reference track on an items JSONL cohort."""
    items = load_items_jsonl(items_path)
    results = run_track_batch(items, TrackId.R1, out_dir=out_dir)
    records = [result.scoring_record for result in results]
    summary = {
        "track": TrackId.R1.value,
        "family": items[0].family if items else None,
        "n": len(records),
        **summarize_scoring_records(records),
    }
    dump_json(Path(out_dir) / "summary.json", summary)
    return summary
