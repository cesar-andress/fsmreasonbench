"""Batch evaluation via Ollama for C2 and F1 items."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.evaluator.jsonl import append_jsonl, read_jsonl, write_jsonl
from fsmreasonbench.evaluator.models import ScoringRecord
from fsmreasonbench.evaluator.summary import summarize_scoring_records
from fsmreasonbench.evaluator.track_failure_taxonomy import (
    classify_track_failure,
    summarize_track_failure_taxonomy,
)
from fsmreasonbench.evaluator.transcript import utc_timestamp
from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.runners.cell_failure import SCORES_JSONL
from fsmreasonbench.runners.experiment_cells import (
    RESULTS_JSONL,
    completed_item_ids,
    update_cell_item_progress,
)
from fsmreasonbench.runners.generate_fn import GenerateFn
from fsmreasonbench.runners.item_watchdog import (
    CellItemFailureLimitExceeded,
    ItemInfrastructureError,
    ItemWatchdogConfig,
    call_generate_with_watchdog,
)
from fsmreasonbench.runners.infrastructure_failure import (
    build_infrastructure_scoring_record,
    enrich_infrastructure_scoring_dict,
    summarize_provider_errors,
)
from fsmreasonbench.runners.provider_errors import DEFAULT_MAX_PROVIDER_RETRY_DELAY_SECONDS
from fsmreasonbench.runners.prompts import prompt_metadata, render_prompt
from fsmreasonbench.runners.response_extract import extract_submission_payload


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
    ollama_retries: int = 0
    provider_retries: int = 0
    ollama_restart_on_timeout: bool = False
    skip_item_on_timeout: bool = True
    ollama_stop_delay_seconds: float = 5.0
    provider_retry_backoff_seconds: float = 5.0
    provider_max_retry_delay_seconds: float = DEFAULT_MAX_PROVIDER_RETRY_DELAY_SECONDS
    provider_sleep_between_items: float = 0.0
    ollama_base_url: str = "http://localhost:11434"
    fail_cell_after_item_failures: int | None = None


@dataclass(frozen=True, slots=True)
class OllamaBatchResult:
    results: list[dict[str, Any]]
    summary: dict[str, Any]
    out_dir: Path
    infrastructure_failures: int = 0


def _load_scoring_rows(run_dir: Path) -> list[dict[str, Any]]:
    path = run_dir / SCORES_JSONL
    if not path.exists():
        return []
    return read_jsonl(path)


def _watchdog_config(config: OllamaBatchConfig) -> ItemWatchdogConfig:
    return ItemWatchdogConfig(
        item_timeout=config.timeout,
        provider_retries=config.provider_retries,
        ollama_retries=config.ollama_retries,
        ollama_restart_on_timeout=config.ollama_restart_on_timeout,
        skip_item_on_timeout=config.skip_item_on_timeout,
        ollama_stop_delay_seconds=config.ollama_stop_delay_seconds,
        provider_retry_backoff_seconds=config.provider_retry_backoff_seconds,
        provider_max_retry_delay_seconds=config.provider_max_retry_delay_seconds,
        provider_sleep_between_items=config.provider_sleep_between_items,
        provider=config.provider,
        ollama_base_url=config.ollama_base_url,
    )


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
    item_records = []
    for row in scoring_rows:
        track_failure_class = row.get("track_failure_class")
        if track_failure_class is None:
            track_failure_class = classify_track_failure(
                track=str(row.get("track", track)),
                scoring_record=row,
            )
        item_records.append(
            {
                "track_failure_class": track_failure_class,
                "scoring_record": row,
            }
        )
    infrastructure_failure_count = sum(
        1 for row in scoring_rows if row.get("infrastructure_failure")
    )
    provider_counts = summarize_provider_errors(scoring_rows)
    extractable_count = sum(1 for record in parsed_records if record.extractable)
    scored_n = len(parsed_records) - provider_counts["provider_error_count"]
    summary = {
        "model": model,
        "family": family,
        "track": track,
        "n": len(parsed_records),
        **summarize_scoring_records(parsed_records),
        "model_extractability_rate": (
            extractable_count / scored_n if scored_n > 0 else 0.0
        ),
        "model_scored_n": scored_n,
        "tool_invocation_rate": (
            sum(1 for count in tool_counts if count > 0) / len(tool_counts)
            if tool_counts
            else 0.0
        ),
        "average_tool_calls_per_item": (
            sum(tool_counts) / len(tool_counts) if tool_counts else 0.0
        ),
        **summarize_track_failure_taxonomy(item_records),
        "infrastructure_failure_count": infrastructure_failure_count,
        **provider_counts,
    }
    if infrastructure_failure_count:
        summary["infrastructure_failure_note"] = (
            "Items marked infrastructure_failure=true use failure_stage=provider_error "
            "and are excluded from model extractability denominators; they are not model "
            "submission failures."
        )
        if provider_counts["provider_error_count"] >= len(parsed_records) / 2:
            summary["provider_failure_warning"] = (
                "Provider failures dominate this cell; headline extractability_rate is not "
                "interpretable as model output quality."
            )
    if provider is not None:
        summary["provider"] = provider
    if max_tokens is not None:
        summary["max_tokens"] = max_tokens
    return summary


def _record_r0_infrastructure_failure(
    item: BenchmarkItem,
    config: OllamaBatchConfig,
    *,
    error: str,
    provider_error_type: str,
    http_status: int | None = None,
    root: Path,
    transcript_dir: Path,
) -> dict[str, Any]:
    scoring_record = build_infrastructure_scoring_record(
        item,
        error=error,
        provider_error_type=provider_error_type,
    )
    transcript_path = transcript_dir / f"{item.item_id}.json"
    transcript_payload = {
        "transcript_version": "1.0",
        "timestamp": utc_timestamp(),
        "item": item.to_full_dict(),
        "raw_response": {"infrastructure_error": error},
        "parsed_submission": None,
        "scoring_record": scoring_record.to_dict(),
        "infrastructure_failure": True,
        "provider_error_type": provider_error_type,
    }
    dump_json(transcript_path, transcript_payload)

    scoring_dict = scoring_record.to_dict()
    scoring_dict["track"] = "R0"
    scoring_dict["model"] = config.model
    scoring_dict["tool_invocation_count"] = 0
    enrich_infrastructure_scoring_dict(
        scoring_dict,
        provider_error_type=provider_error_type,
        http_status=http_status,
    )
    scoring_dict["track_failure_class"] = classify_track_failure(
        track="R0",
        scoring_record=scoring_dict,
    )
    return {
        "item_id": item.item_id,
        "family": item.family,
        "model": config.model,
        "temperature": config.temperature,
        "prompt_metadata": prompt_metadata(item),
        "raw_response_text": error,
        "raw_response": {"infrastructure_error": error},
        "transcript_path": str(transcript_path.relative_to(root)),
        "scoring_record": scoring_dict,
        "track_failure_class": scoring_dict["track_failure_class"],
        "infrastructure_failure": True,
        "provider_error_type": provider_error_type,
    }


def _after_item_written(
    *,
    root: Path,
    item_id: str,
    max_items: int,
) -> None:
    completed = len(completed_item_ids(root))
    update_cell_item_progress(
        root,
        items_completed=completed,
        max_items=max_items,
        last_item_id=item_id,
    )


def _maybe_raise_item_failure_limit(
    infrastructure_failures: int,
    config: OllamaBatchConfig,
) -> None:
    limit = config.fail_cell_after_item_failures
    if limit is not None and infrastructure_failures >= limit:
        raise CellItemFailureLimitExceeded(
            f"cell exceeded item infrastructure failure limit ({infrastructure_failures})"
        )


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
    infrastructure_failures = 0
    watchdog = _watchdog_config(config)
    max_items = config.max_items if config.max_items is not None else len(selected)

    import time

    for item in selected:
        if item.item_id in done_ids:
            continue

        prompt = render_prompt(item, provider=config.provider)
        try:
            raw_text = call_generate_with_watchdog(
                generate,
                prompt=prompt,
                model=config.model,
                temperature=config.temperature,
                timeout=config.timeout,
                config=watchdog,
            )
        except ItemInfrastructureError as exc:
            infrastructure_failures += 1
            run_record = _record_r0_infrastructure_failure(
                item,
                config,
                error=str(exc),
                provider_error_type=exc.provider_error_type,
                http_status=exc.http_status,
                root=root,
                transcript_dir=transcript_dir,
            )
            append_jsonl(results_path, run_record)
            append_jsonl(scores_path, run_record["scoring_record"])
            new_results.append(run_record)
            _after_item_written(root=root, item_id=item.item_id, max_items=max_items)
            _maybe_raise_item_failure_limit(infrastructure_failures, config)
            if config.provider_sleep_between_items > 0:
                time.sleep(config.provider_sleep_between_items)
            continue

        raw_response = extract_submission_payload(raw_text)
        from fsmreasonbench.evaluator.transcript import record_transcript

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
        _after_item_written(root=root, item_id=item.item_id, max_items=max_items)
        if config.provider_sleep_between_items > 0:
            time.sleep(config.provider_sleep_between_items)

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
    return OllamaBatchResult(
        results=all_results,
        summary=summary,
        out_dir=root,
        infrastructure_failures=infrastructure_failures,
    )
