"""Track-aware Ollama batch evaluation with two-phase tool protocol."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.evaluator.jsonl import write_jsonl
from fsmreasonbench.evaluator.models import ScoringRecord
from fsmreasonbench.evaluator.scorer import score_item
from fsmreasonbench.evaluator.summary import summarize_scoring_records
from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.runners.ollama_batch import (
    GenerateFn,
    OllamaBatchConfig,
    OllamaBatchResult,
    run_ollama_batch,
)
from fsmreasonbench.runners.prompts import prompt_metadata
from fsmreasonbench.runners.response_extract import extract_submission_payload
from fsmreasonbench.runners.tool_executor import execute_tool_plan
from fsmreasonbench.runners.track_prompts import render_track_prompt
from fsmreasonbench.runners.track_protocol import (
    TrackProtocolError,
    parse_final_submission,
    parse_tool_plan,
)
from fsmreasonbench.tracks.audit import AuditLogBuilder
from fsmreasonbench.tracks.models import TrackId, TRACKS_VERSION
from fsmreasonbench.tracks.replay import replay_audit_log


def _fsm_index(item: BenchmarkItem) -> dict:
    index = {item.fsm.fsm_id: item.fsm}
    if item.fsm_b is not None:
        index[item.fsm_b.fsm_id] = item.fsm_b
    return index


@dataclass(frozen=True, slots=True)
class LLMTrackTranscript:
    transcript_version: str
    tracks_version: str
    track: str
    model: str
    temperature: float
    timestamp: str
    item: dict[str, Any]
    messages: tuple[dict[str, Any], ...]
    tool_calls_requested: tuple[dict[str, Any], ...]
    tool_calls_executed: tuple[dict[str, Any], ...]
    tool_outputs: tuple[dict[str, Any], ...]
    raw_response: Any
    parsed_submission: dict[str, Any] | None
    scoring_record: ScoringRecord
    audit_log: dict[str, Any]
    protocol_errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "transcript_version": self.transcript_version,
            "tracks_version": self.tracks_version,
            "track": self.track,
            "model": self.model,
            "temperature": self.temperature,
            "timestamp": self.timestamp,
            "item": self.item,
            "messages": list(self.messages),
            "tool_calls_requested": list(self.tool_calls_requested),
            "tool_calls_executed": list(self.tool_calls_executed),
            "tool_outputs": list(self.tool_outputs),
            "raw_response": self.raw_response,
            "parsed_submission": self.parsed_submission,
            "scoring_record": self.scoring_record.to_dict(),
            "audit_log": self.audit_log,
            "protocol_errors": list(self.protocol_errors),
            "tool_invocation_count": len(self.audit_log.get("tool_invocations", [])),
        }


def run_ollama_track_batch(
    items: list[BenchmarkItem],
    generate: GenerateFn,
    out_path: str | Path,
    config: OllamaBatchConfig,
    track: TrackId | str,
    *,
    out_dir: str | Path | None = None,
    write_summary: bool = True,
) -> OllamaBatchResult:
    """Run Ollama under R0/R1/R2; R0 delegates to legacy single-shot runner."""
    resolved = TrackId(track) if isinstance(track, str) else track
    if resolved == TrackId.R0:
        return run_ollama_batch(
            items,
            generate,
            out_path,
            config,
            out_dir=out_dir,
            write_summary=write_summary,
        )

    if not items:
        raise ValueError("items list is empty")

    family = items[0].family
    if family not in {"C2", "F1"}:
        raise ValueError(f"unsupported family: {family!r}")
    if any(item.family != family for item in items):
        raise ValueError("all items in batch must share the same family")

    selected = items if config.max_items is None else items[: config.max_items]
    root = Path(out_dir) if out_dir is not None else Path(out_path).with_suffix("")
    transcript_dir = root / "transcripts"
    transcript_dir.mkdir(parents=True, exist_ok=True)

    from fsmreasonbench.evaluator.transcript import utc_timestamp

    results: list[dict[str, Any]] = []
    scoring_rows: list[dict[str, Any]] = []
    tool_invocation_counts: list[int] = []

    for item in selected:
        run = _evaluate_item_with_tools(
            item,
            generate,
            config,
            resolved,
            timestamp=utc_timestamp(),
        )
        transcript_path = transcript_dir / f"{item.item_id}.json"
        dump_json(transcript_path, run["transcript"].to_dict())

        scoring_dict = run["transcript"].scoring_record.to_dict()
        scoring_dict["track"] = resolved.value
        scoring_dict["model"] = config.model
        scoring_dict["tool_invocation_count"] = run["transcript"].to_dict()[
            "tool_invocation_count"
        ]
        scoring_rows.append(scoring_dict)
        tool_invocation_counts.append(scoring_dict["tool_invocation_count"])

        results.append(
            {
                "item_id": item.item_id,
                "family": item.family,
                "track": resolved.value,
                "model": config.model,
                "temperature": config.temperature,
                "prompt_metadata": prompt_metadata(item),
                "messages": list(run["transcript"].messages),
                "tool_calls_requested": list(run["transcript"].tool_calls_requested),
                "tool_outputs": list(run["transcript"].tool_outputs),
                "raw_response_text": run["raw_response_text"],
                "raw_response": run["transcript"].raw_response,
                "transcript_path": str(transcript_path.relative_to(root)),
                "scoring_record": scoring_dict,
                "protocol_errors": list(run["transcript"].protocol_errors),
            }
        )

    write_jsonl(out_path, results)
    write_jsonl(root / "scores.jsonl", scoring_rows)

    parsed_records = [ScoringRecord.from_dict(row) for row in scoring_rows]
    summary = {
        "model": config.model,
        "family": family,
        "track": resolved.value,
        "n": len(parsed_records),
        **summarize_scoring_records(parsed_records),
        "tool_invocation_rate": (
            sum(1 for count in tool_invocation_counts if count > 0) / len(tool_invocation_counts)
            if tool_invocation_counts
            else 0.0
        ),
        "average_tool_calls_per_item": (
            sum(tool_invocation_counts) / len(tool_invocation_counts)
            if tool_invocation_counts
            else 0.0
        ),
    }
    if write_summary:
        dump_json(root / "summary.json", summary)
        dump_json(root / "track_summary.json", summary)

    return OllamaBatchResult(results=results, summary=summary, out_dir=root)


def _evaluate_item_with_tools(
    item: BenchmarkItem,
    generate: GenerateFn,
    config: OllamaBatchConfig,
    track: TrackId,
    *,
    timestamp: str,
) -> dict[str, Any]:
    audit = AuditLogBuilder(track)
    messages: list[dict[str, Any]] = []
    protocol_errors: list[str] = []

    plan_prompt = render_track_prompt(item, track, phase="initial")
    plan_text = generate(
        plan_prompt,
        model=config.model,
        temperature=config.temperature,
        timeout=config.timeout,
    )
    messages.append({"role": "user", "phase": "tool_plan", "content": plan_prompt})
    messages.append({"role": "assistant", "phase": "tool_plan", "content": plan_text})

    tool_calls_requested: list[dict[str, Any]] = []
    tool_outputs: list[dict[str, Any]] = []
    try:
        tool_calls_requested, notes = parse_tool_plan(plan_text)
        if notes:
            audit.scratchpad("model_notes", notes)
        tool_outputs = execute_tool_plan(item, track, tool_calls_requested, audit)
    except TrackProtocolError as exc:
        protocol_errors.append(str(exc))
        audit.scratchpad("protocol_error", str(exc))

    results_prompt = render_track_prompt(
        item,
        track,
        phase="tool_results",
        tool_results=tool_outputs,
    )
    final_text = generate(
        results_prompt,
        model=config.model,
        temperature=config.temperature,
        timeout=config.timeout,
    )
    messages.append({"role": "user", "phase": "final_submission", "content": results_prompt})
    messages.append(
        {"role": "assistant", "phase": "final_submission", "content": final_text}
    )

    raw_response: Any
    try:
        submission = parse_final_submission(final_text)
        raw_response = submission
    except TrackProtocolError:
        raw_response = extract_submission_payload(final_text)
        protocol_errors.append("final phase did not match protocol; used best-effort extraction")

    scoring_record = score_item(item, raw_response)
    parsed_submission = None
    if scoring_record.extractable:
        if isinstance(raw_response, dict):
            parsed_submission = {
                "item_id": raw_response.get("item_id"),
                "verdict": raw_response.get("verdict"),
                "certificate": raw_response.get("certificate"),
            }

    audit_log = audit.build()
    replay_audit_log(audit_log, fsm_by_id=_fsm_index(item))

    executed = [row for row in tool_outputs if row.get("status") == "executed"]
    transcript = LLMTrackTranscript(
        transcript_version="1.1",
        tracks_version=TRACKS_VERSION,
        track=track.value,
        model=config.model,
        temperature=config.temperature,
        timestamp=timestamp,
        item=item.to_full_dict(),
        messages=tuple(messages),
        tool_calls_requested=tuple(tool_calls_requested),
        tool_calls_executed=tuple(executed),
        tool_outputs=tuple(tool_outputs),
        raw_response=raw_response,
        parsed_submission=parsed_submission,
        scoring_record=scoring_record,
        audit_log=audit_log.to_dict(),
        protocol_errors=tuple(protocol_errors),
    )
    return {
        "transcript": transcript,
        "raw_response_text": final_text,
    }
