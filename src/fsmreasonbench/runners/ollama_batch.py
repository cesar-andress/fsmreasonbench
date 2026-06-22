"""Batch evaluation via Ollama for C2 and F1 items."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.evaluator.jsonl import append_jsonl, read_jsonl, write_jsonl
from fsmreasonbench.evaluator.models import ScoringRecord
from fsmreasonbench.evaluator.summary import summarize_scoring_records
from fsmreasonbench.evaluator.track_failure_taxonomy import (
    classify_track_failure,
    summarize_track_failure_taxonomy,
)
from fsmreasonbench.evaluator.transcript import record_transcript
from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.runners.cell_failure import SCORES_JSONL
from fsmreasonbench.runners.experiment_cells import RESULTS_JSONL, completed_item_ids
from fsmreasonbench.runners.prompts import prompt_metadata, render_prompt
from fsmreasonbench.runners.response_extract import extract_submission_payload


class GenerateFn(Protocol):
    def __call__(
        self,
        prompt: str,
        *,
        model: str,
        temperature: float,
        timeout: float,
    ) -> str: ...


@dataclass(frozen=True, slots=True)
class OllamaBatchConfig:
    model: str
    temperature: float = 0.0
    timeout: float | None = 120.0
    max_items: int | None = None
    resume_items: bool = True
    force_cell: bool = False
    provider: str = "ollama"
    max_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class OllamaBatchResult:
    results: list[dict[str, Any]]
    summary: dict[str, Any]
    out_dir: Path


def _load_scoring_rows(run_dir: Path) -> list[dict[str, Any]]:
    path = run_dir / SCORES_JSONL
    if not path.exists():
        return []
    return read_jsonl(path)


def _build_summary_from_scores(
    *,
    scoring_rows: list[dict[str, Any]],
    model: str,
    family: str,
    track: str,
    provider: str | None = None,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    parsed_records = [ScoringRecord.from_dict(row) for row in scoring_rows]
    tool_counts = [int(row.get("tool_invocation_count", 0)) for row in scoring_rows]
    item_records = [{"track_failure_class": row.get("track_failure_class"), "scoring_record": row} for row in scoring_rows]
    summary = {
        "model": model,
        "family": family,
        "track": track,
        "n": len(parsed_records),
        **summarize_scoring_records(parsed_records),
        "tool_invocation_rate": (
            sum(1 for count in tool_counts if count > 0) / len(tool_counts)
            if tool_counts
            else 0.0
        ),
        "average_tool_calls_per_item": (
            sum(tool_counts) / len(tool_counts) if tool_counts else 0.0
        ),
        **summarize_track_failure_taxonomy(item_records),
    }
    if provider is not None:
        summary["provider"] = provider
    if max_tokens is not None:
        summary["max_tokens"] = max_tokens
    return summary


def run_ollama_batch(
    items: list[BenchmarkItem],
    generate: GenerateFn,
    out_path: str | Path,
    config: OllamaBatchConfig,
    *,
    out_dir: str | Path | None = None,
    write_summary: bool = True,
) -> OllamaBatchResult:
    """
    Run Ollama on items, score via existing parser/scorer, write transcripts.

    Writes incrementally when ``resume_items`` is true:
    - append ``results.jsonl`` and ``scores.jsonl`` after each item
    - skip items already present in ``scores.jsonl`` unless ``force_cell``
    """
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

    results_path = root / RESULTS_JSONL if out_dir is not None else Path(out_path)
    scores_path = root / SCORES_JSONL

    done_ids = (
        completed_item_ids(root)
        if config.resume_items and not config.force_cell
        else set()
    )

    new_results: list[dict[str, Any]] = []

    for item in selected:
        if item.item_id in done_ids:
            continue

        prompt = render_prompt(item)
        raw_text = generate(
            prompt,
            model=config.model,
            temperature=config.temperature,
            timeout=config.timeout,
        )
        raw_response = extract_submission_payload(raw_text)
        transcript = record_transcript(item, raw_response)
        transcript_path = transcript_dir / f"{item.item_id}.json"
        dump_json(transcript_path, transcript.to_dict())

        scoring_dict = transcript.scoring_record.to_dict()
        scoring_dict["track"] = "R0"
        scoring_dict["model"] = config.model
        scoring_dict["tool_invocation_count"] = 0
        scoring_dict["track_failure_class"] = classify_track_failure(
            track="R0",
            scoring_record=scoring_dict,
        )
        run_record = {
            "item_id": item.item_id,
            "family": item.family,
            "model": config.model,
            "temperature": config.temperature,
            "prompt_metadata": prompt_metadata(item),
            "raw_response_text": raw_text,
            "raw_response": raw_response,
            "transcript_path": str(transcript_path.relative_to(root)),
            "scoring_record": scoring_dict,
            "track_failure_class": scoring_dict["track_failure_class"],
        }
        append_jsonl(results_path, run_record)
        append_jsonl(scores_path, scoring_dict)
        new_results.append(run_record)

    scoring_rows = _load_scoring_rows(root)
    summary = _build_summary_from_scores(
        scoring_rows=scoring_rows,
        model=config.model,
        family=family,
        track="R0",
        provider=config.provider,
        max_tokens=config.max_tokens,
    )
    if write_summary:
        dump_json(root / "summary.json", summary)
        dump_json(root / "track_summary.json", summary)

    all_results = read_jsonl(results_path) if results_path.exists() else new_results
    return OllamaBatchResult(results=all_results, summary=summary, out_dir=root)
