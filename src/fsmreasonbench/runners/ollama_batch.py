"""Batch evaluation via Ollama for C2 and F1 items."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.evaluator.jsonl import write_jsonl
from fsmreasonbench.evaluator.summary import summarize_scoring_records
from fsmreasonbench.evaluator.transcript import record_transcript
from fsmreasonbench.items.assembly import BenchmarkItem
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
    timeout: float = 120.0
    max_items: int | None = None


@dataclass(frozen=True, slots=True)
class OllamaBatchResult:
    results: list[dict[str, Any]]
    summary: dict[str, Any]
    out_dir: Path


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

    Writes:
    - ``{out_path}`` JSONL run records
    - ``{out_dir}/scores.jsonl`` scoring records
    - ``{out_dir}/transcripts/{item_id}.json`` per item
    - ``{out_dir}/summary.json`` when ``write_summary`` is true
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

    results: list[dict[str, Any]] = []
    scoring_records: list[dict[str, Any]] = []

    for item in selected:
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
        }
        results.append(run_record)
        scoring_records.append(scoring_dict)

    write_jsonl(out_path, results)
    write_jsonl(root / "scores.jsonl", scoring_records)

    from fsmreasonbench.evaluator.models import ScoringRecord

    parsed_records = [ScoringRecord.from_dict(record) for record in scoring_records]
    summary = {
        "model": config.model,
        "family": family,
        "n": len(parsed_records),
        **summarize_scoring_records(parsed_records),
    }
    if write_summary:
        dump_json(root / "summary.json", summary)

    return OllamaBatchResult(results=results, summary=summary, out_dir=root)
