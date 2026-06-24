"""Batch runner for F1 oracle-verdict certificate-only ablation."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.evaluator.jsonl import append_jsonl, read_jsonl
from fsmreasonbench.evaluator.models import ScoringRecord
from fsmreasonbench.evaluator.scorer import score_item
from fsmreasonbench.evaluator.summary import summarize_scoring_records
from fsmreasonbench.evaluator.track_failure_taxonomy import classify_track_failure
from fsmreasonbench.evaluator.transcript import utc_timestamp
from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.runners.ablation_prompts import (
    ABLATION_CONDITION_ID,
    ABLATION_TRACK_LABEL,
    ablation_prompt_metadata,
    render_f1_oracle_verdict_certificate_prompt,
)
from fsmreasonbench.runners.cell_failure import SCORES_JSONL
from fsmreasonbench.runners.experiment_cells import (
    RESULTS_JSONL,
    completed_item_ids,
    update_cell_item_progress,
)
from fsmreasonbench.runners.generate_fn import GenerateFn
from fsmreasonbench.runners.infrastructure_failure import (
    build_infrastructure_scoring_record,
    enrich_infrastructure_scoring_dict,
    summarize_provider_errors,
)
from fsmreasonbench.runners.item_watchdog import (
    ItemInfrastructureError,
    ItemWatchdogConfig,
    call_generate_with_watchdog,
)
from fsmreasonbench.runners.ollama_batch import (
    OllamaBatchConfig,
    _maybe_raise_item_failure_limit,
    _watchdog_config,
)
from fsmreasonbench.runners.provider_errors import classify_generate_failure
from fsmreasonbench.runners.response_extract import (
    extract_submission_payload,
    extract_submission_payload_with_json_repair,
)


@dataclass(frozen=True, slots=True)
class AblationBatchResult:
    results: list[dict[str, Any]]
    summary: dict[str, Any]
    out_dir: Path
    infrastructure_failures: int = 0


def _score_response(item: BenchmarkItem, payload: object) -> ScoringRecord:
    return score_item(item, payload)


def _scoring_dict(
    record: ScoringRecord,
    *,
    model: str,
    track: str,
) -> dict[str, Any]:
    scoring_dict = record.to_dict()
    scoring_dict["track"] = track
    scoring_dict["model"] = model
    scoring_dict["tool_invocation_count"] = 0
    scoring_dict["ablation_condition"] = ABLATION_CONDITION_ID
    scoring_dict["track_failure_class"] = classify_track_failure(
        track=track,
        scoring_record=scoring_dict,
    )
    return scoring_dict


def _build_summary(
    scoring_rows: list[dict[str, Any]],
    *,
    model: str,
    family: str,
    track: str,
    provider: str | None,
    max_tokens: int | None,
    json_repair_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    parsed_records = [ScoringRecord.from_dict(row) for row in scoring_rows]
    provider_counts = summarize_provider_errors(scoring_rows)
    extractable_count = sum(1 for record in parsed_records if record.extractable)
    scored_n = len(parsed_records) - provider_counts["provider_error_count"]
    summary: dict[str, Any] = {
        "experiment": "ablation",
        "ablation_condition": ABLATION_CONDITION_ID,
        "model": model,
        "family": family,
        "track": track,
        "n": len(parsed_records),
        **summarize_scoring_records(parsed_records),
        "model_extractability_rate": (
            extractable_count / scored_n if scored_n > 0 else 0.0
        ),
        "model_scored_n": scored_n,
        "tool_invocation_rate": 0.0,
        "average_tool_calls_per_item": 0.0,
        "infrastructure_failure_count": sum(
            1 for row in scoring_rows if row.get("infrastructure_failure")
        ),
        **provider_counts,
    }
    if provider is not None:
        summary["provider"] = provider
    if max_tokens is not None:
        summary["max_tokens"] = max_tokens
    if json_repair_rows is not None:
        repair_records = [ScoringRecord.from_dict(row) for row in json_repair_rows]
        summary["json_repair_metrics"] = summarize_scoring_records(repair_records)
        summary["json_repair_delta"] = {
            metric: summary["json_repair_metrics"].get(metric, 0.0)
            - summary.get(metric, 0.0)
            for metric in (
                "extractability_rate",
                "verdict_accuracy",
                "certificate_valid_rate",
                "fully_correct_rate",
            )
        }
    return summary


def run_f1_oracle_verdict_ablation_batch(
    items: list[BenchmarkItem],
    generate: GenerateFn,
    out_dir: str | Path,
    config: OllamaBatchConfig,
    *,
    json_repair: bool = True,
    write_summary: bool = True,
) -> AblationBatchResult:
    """Run certificate-only ablation on F1 items with optional JSON-repair scoring."""
    if not items:
        raise ValueError("items list is empty")
    if any(item.family != "F1" for item in items):
        raise ValueError("ablation batch requires F1 items only")

    selected = items if config.max_items is None else items[: config.max_items]
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    transcript_dir = root / "transcripts"
    transcript_dir.mkdir(parents=True, exist_ok=True)

    results_path = root / RESULTS_JSONL
    scores_path = root / SCORES_JSONL
    repair_scores_path = root / "scores_json_repair.jsonl"

    done_ids = (
        completed_item_ids(root)
        if config.resume_items and not config.force_cell
        else set()
    )

    watchdog = _watchdog_config(config)
    max_items = config.max_items if config.max_items is not None else len(selected)
    infrastructure_failures = 0
    track = ABLATION_TRACK_LABEL

    for item in selected:
        if item.item_id in done_ids:
            continue

        prompt = render_f1_oracle_verdict_certificate_prompt(item)
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
            scoring_record = build_infrastructure_scoring_record(
                item,
                error=str(exc),
                provider_error_type=exc.provider_error_type,
            )
            scoring_dict = scoring_record.to_dict()
            scoring_dict["track"] = track
            scoring_dict["model"] = config.model
            scoring_dict["tool_invocation_count"] = 0
            scoring_dict["ablation_condition"] = ABLATION_CONDITION_ID
            enrich_infrastructure_scoring_dict(
                scoring_dict,
                provider_error_type=exc.provider_error_type,
                http_status=exc.http_status,
            )
            scoring_dict["track_failure_class"] = classify_track_failure(
                track=track,
                scoring_record=scoring_dict,
            )
            run_record = {
                "item_id": item.item_id,
                "family": item.family,
                "model": config.model,
                "temperature": config.temperature,
                "ablation_condition": ABLATION_CONDITION_ID,
                "prompt_metadata": ablation_prompt_metadata(item),
                "raw_response_text": str(exc),
                "raw_response": {"infrastructure_error": str(exc)},
                "scoring_record": scoring_dict,
                "track_failure_class": scoring_dict["track_failure_class"],
                "infrastructure_failure": True,
            }
            append_jsonl(results_path, run_record)
            append_jsonl(scores_path, scoring_dict)
            _maybe_raise_item_failure_limit(infrastructure_failures, config)
            update_cell_item_progress(
                root,
                items_completed=len(completed_item_ids(root)),
                max_items=max_items,
                last_item_id=item.item_id,
            )
            if config.provider_sleep_between_items > 0:
                time.sleep(config.provider_sleep_between_items)
            continue
        except Exception as exc:  # noqa: BLE001
            provider_failure = classify_generate_failure(exc)
            if provider_failure is None:
                raise
            infrastructure_failures += 1
            scoring_record = build_infrastructure_scoring_record(
                item,
                error=provider_failure.message,
                provider_error_type=provider_failure.provider_error_type,
            )
            scoring_dict = scoring_record.to_dict()
            scoring_dict["track"] = track
            scoring_dict["model"] = config.model
            scoring_dict["tool_invocation_count"] = 0
            scoring_dict["ablation_condition"] = ABLATION_CONDITION_ID
            enrich_infrastructure_scoring_dict(
                scoring_dict,
                provider_error_type=provider_failure.provider_error_type,
                http_status=provider_failure.http_status,
            )
            scoring_dict["track_failure_class"] = classify_track_failure(
                track=track,
                scoring_record=scoring_dict,
            )
            run_record = {
                "item_id": item.item_id,
                "family": item.family,
                "model": config.model,
                "temperature": config.temperature,
                "ablation_condition": ABLATION_CONDITION_ID,
                "prompt_metadata": ablation_prompt_metadata(item),
                "raw_response_text": provider_failure.message,
                "raw_response": {"infrastructure_error": provider_failure.message},
                "scoring_record": scoring_dict,
                "track_failure_class": scoring_dict["track_failure_class"],
                "infrastructure_failure": True,
            }
            append_jsonl(results_path, run_record)
            append_jsonl(scores_path, scoring_dict)
            _maybe_raise_item_failure_limit(infrastructure_failures, config)
            update_cell_item_progress(
                root,
                items_completed=len(completed_item_ids(root)),
                max_items=max_items,
                last_item_id=item.item_id,
            )
            if config.provider_sleep_between_items > 0:
                time.sleep(config.provider_sleep_between_items)
            continue

        raw_payload = extract_submission_payload(raw_text)
        primary_score = _score_response(item, raw_payload)
        scoring_dict = _scoring_dict(primary_score, model=config.model, track=track)

        repair_scoring_dict: dict[str, Any] | None = None
        if json_repair:
            repair_payload = extract_submission_payload_with_json_repair(raw_text)
            repair_score = _score_response(item, repair_payload)
            repair_scoring_dict = _scoring_dict(
                repair_score,
                model=config.model,
                track=track,
            )
            scoring_dict["json_repair_scoring"] = repair_scoring_dict
            scoring_dict["json_repair_changed_outcome"] = (
                repair_scoring_dict.get("fully_correct")
                != scoring_dict.get("fully_correct")
                or repair_scoring_dict.get("extractable")
                != scoring_dict.get("extractable")
            )

        transcript_path = transcript_dir / f"{item.item_id}.json"
        dump_json(
            transcript_path,
            {
                "transcript_version": "1.0",
                "timestamp": utc_timestamp(),
                "ablation_condition": ABLATION_CONDITION_ID,
                "item": item.to_full_dict(),
                "prompt_metadata": ablation_prompt_metadata(item),
                "raw_response_text": raw_text,
                "raw_response": raw_payload,
                "parsed_submission": raw_payload if isinstance(raw_payload, dict) else None,
                "scoring_record": scoring_dict,
                "json_repair_scoring": repair_scoring_dict,
            },
        )

        run_record = {
            "item_id": item.item_id,
            "family": item.family,
            "model": config.model,
            "temperature": config.temperature,
            "ablation_condition": ABLATION_CONDITION_ID,
            "prompt_metadata": ablation_prompt_metadata(item),
            "raw_response_text": raw_text,
            "raw_response": raw_payload,
            "transcript_path": str(transcript_path.relative_to(root)),
            "scoring_record": scoring_dict,
            "track_failure_class": scoring_dict["track_failure_class"],
        }
        append_jsonl(results_path, run_record)
        append_jsonl(scores_path, scoring_dict)
        if repair_scoring_dict is not None:
            append_jsonl(repair_scores_path, repair_scoring_dict)

        update_cell_item_progress(
            root,
            items_completed=len(completed_item_ids(root)),
            max_items=max_items,
            last_item_id=item.item_id,
        )
        if config.provider_sleep_between_items > 0:
            time.sleep(config.provider_sleep_between_items)

    scoring_rows = read_jsonl(scores_path) if scores_path.exists() else []
    repair_rows = read_jsonl(repair_scores_path) if repair_scores_path.exists() else None
    summary = _build_summary(
        scoring_rows,
        model=config.model,
        family="F1",
        track=track,
        provider=config.provider,
        max_tokens=config.max_tokens,
        json_repair_rows=repair_rows,
    )
    if write_summary:
        dump_json(root / "summary.json", summary)
        if repair_rows is not None:
            dump_json(root / "summary_json_repair.json", summary["json_repair_metrics"])

    dump_json(
        root / "ablation_metadata.json",
        {
            "condition_id": ABLATION_CONDITION_ID,
            "track_label": track,
            "family": "F1",
            "description": (
                "Oracle verdict fixed; model constructs certificate only; "
                "no tools; format-control schema + examples"
            ),
            "json_repair_enabled": json_repair,
        },
    )

    return AblationBatchResult(
        results=read_jsonl(results_path) if results_path.exists() else [],
        summary=summary,
        out_dir=root,
        infrastructure_failures=infrastructure_failures,
    )
