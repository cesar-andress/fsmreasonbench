"""Track evaluation runner and batch dispatch."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.evaluator.jsonl import load_items_jsonl, write_jsonl
from fsmreasonbench.evaluator.track_guards import validate_track_audit_log
from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.tracks.agents import run_r0_agent, run_r1_agent, run_r2_agent
from fsmreasonbench.tracks.models import TrackId, TrackRunResult, TrackScoringRecord
from fsmreasonbench.tracks.transcript import record_track_transcript

_TRACK_AGENTS: dict[TrackId, Callable[[BenchmarkItem], TrackRunResult]] = {
    TrackId.R0: run_r0_agent,
    TrackId.R1: run_r1_agent,
    TrackId.R2: run_r2_agent,
}


def run_track(item: BenchmarkItem, track: TrackId | str) -> TrackRunResult:
    """Run a reference track agent on one item and score through the public path."""
    resolved = TrackId(track) if isinstance(track, str) else track
    agent = _TRACK_AGENTS[resolved]
    result = agent(item)
    validate_track_audit_log(result.audit_log)
    return result


def run_track_batch(
    items: list[BenchmarkItem],
    track: TrackId | str,
    *,
    out_dir: str | Path,
) -> list[TrackRunResult]:
    """Evaluate a track on all items; write transcripts and scores."""
    if not items:
        return []

    family = items[0].family
    if any(item.family != family for item in items):
        raise ValueError("batch items must share the same family")

    root = Path(out_dir)
    transcript_dir = root / "transcripts"
    transcript_dir.mkdir(parents=True, exist_ok=True)

    results: list[TrackRunResult] = []
    scoring_rows: list[dict[str, Any]] = []

    for item in items:
        result = run_track(item, track)
        transcript = record_track_transcript(item, result)
        transcript_path = transcript_dir / f"{item.item_id}.json"
        dump_json(transcript_path, transcript.to_dict())
        results.append(result)
        scoring_rows.append(
            TrackScoringRecord(
                track=result.track,
                scoring_record=result.scoring_record,
                audit_log=result.audit_log,
            ).to_dict()
        )

    resolved_track = TrackId(track) if isinstance(track, str) else track
    write_jsonl(root / f"{resolved_track.value.lower()}_scores.jsonl", scoring_rows)
    return results
