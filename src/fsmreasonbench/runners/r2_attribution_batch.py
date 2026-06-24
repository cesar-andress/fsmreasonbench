"""Batch runner for F1 R2 attribution ablations (R2A/R2B/R2C)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.evaluator.jsonl import append_jsonl, read_jsonl
from fsmreasonbench.evaluator.scorer import score_item
from fsmreasonbench.evaluator.track_failure_taxonomy import classify_track_failure
from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.runners.cell_failure import SCORES_JSONL
from fsmreasonbench.runners.experiment_cells import (
    RESULTS_JSONL,
    completed_item_ids,
    update_cell_item_progress,
)
from fsmreasonbench.runners.generate_fn import GenerateFn
from fsmreasonbench.runners.infrastructure_failure import enrich_infrastructure_scoring_dict
from fsmreasonbench.runners.item_watchdog import (
    ItemInfrastructureError,
    ItemWatchdogConfig,
    call_generate_with_watchdog,
)
from fsmreasonbench.runners.ollama_batch import (
    OllamaBatchConfig,
    OllamaBatchResult,
    _build_summary_from_scores,
    _maybe_raise_item_failure_limit,
    _watchdog_config,
)
from fsmreasonbench.runners.ollama_track_batch import (
    LLMTrackTranscript,
    _evaluate_item_with_tools,
    _failed_item_run,
)
from fsmreasonbench.runners.provider_errors import classify_generate_failure
from fsmreasonbench.runners.prompts import prompt_metadata
from fsmreasonbench.runners.r2_attribution_prompts import (
    MODE_CONDITION_IDS,
    MODE_TRACK_LABELS,
    R2AttributionMode,
    attribution_prompt_metadata,
    render_r2_attribution_final_prompt,
    render_r2_attribution_tool_plan_prompt,
)
from fsmreasonbench.runners.r2_attribution_tools import (
    F1_R2A_ALLOWED_TOOLS,
    F1_R2B_ALLOWED_TOOLS,
    execute_r2_attribution_tool_plan,
)
from fsmreasonbench.runners.response_extract import extract_submission_payload
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


def _allowed_tools(mode: R2AttributionMode) -> frozenset[str]:
    if mode == R2AttributionMode.R2A:
        return F1_R2A_ALLOWED_TOOLS
    if mode == R2AttributionMode.R2B:
        return F1_R2B_ALLOWED_TOOLS
    raise ValueError(f"mode {mode} uses standard R2 tools via _evaluate_item_with_tools")


@dataclass(frozen=True, slots=True)
class R2AttributionBatchResult:
    results: list[dict[str, Any]]
    summary: dict[str, Any]
    out_dir: Path
    mode: R2AttributionMode
    infrastructure_failures: int = 0


def _evaluate_r2_attribution_item(
    item: BenchmarkItem,
    generate: GenerateFn,
    config: OllamaBatchConfig,
    mode: R2AttributionMode,
    *,
    timestamp: str,
    watchdog: ItemWatchdogConfig,
) -> dict[str, Any]:
    if mode == R2AttributionMode.R2C:
        return _evaluate_item_with_tools(
            item,
            generate,
            config,
            TrackId.R2,
            timestamp=timestamp,
            watchdog=watchdog,
        )

    audit = AuditLogBuilder(TrackId.R2)
    audit.scratchpad("r2_attribution_mode", mode.value)
    audit.scratchpad("ablation_condition", MODE_CONDITION_IDS[mode])
    messages: list[dict[str, Any]] = []
    protocol_errors: list[str] = []
    allowed = _allowed_tools(mode)
    track_label = MODE_TRACK_LABELS[mode]

    plan_prompt = render_r2_attribution_tool_plan_prompt(item, mode)
    plan_text = call_generate_with_watchdog(
        generate,
        prompt=plan_prompt,
        model=config.model,
        temperature=config.temperature,
        timeout=config.timeout,
        config=watchdog,
    )
    messages.append({"role": "user", "phase": "tool_plan", "content": plan_prompt})
    messages.append({"role": "assistant", "phase": "tool_plan", "content": plan_text})

    tool_calls_requested: list[dict[str, Any]] = []
    tool_outputs: list[dict[str, Any]] = []
    tool_execution_error: str | None = None
    tool_plan_valid = False
    try:
        tool_calls_requested, notes = parse_tool_plan(plan_text)
        tool_plan_valid = True
        if notes:
            audit.scratchpad("model_notes", notes)
        tool_outputs = execute_r2_attribution_tool_plan(
            item,
            tool_calls_requested,
            allowed=allowed,
            audit=audit,
        )
    except TrackProtocolError as exc:
        protocol_errors.append(str(exc))
        audit.scratchpad("protocol_error", str(exc))
    except (ValueError, RuntimeError) as exc:
        tool_execution_error = str(exc)
        protocol_errors.append(str(exc))
        audit.scratchpad("tool_execution_error", str(exc))

    results_prompt = render_r2_attribution_final_prompt(item, mode, tool_outputs)
    final_text = call_generate_with_watchdog(
        generate,
        prompt=results_prompt,
        model=config.model,
        temperature=config.temperature,
        timeout=config.timeout,
        config=watchdog,
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
    if scoring_record.extractable and isinstance(raw_response, dict):
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
        track=track_label,
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
    scoring_dict = scoring_record.to_dict()
    scoring_dict["track"] = track_label
    scoring_dict["model"] = config.model
    scoring_dict["tool_invocation_count"] = len(executed)
    scoring_dict["ablation_condition"] = MODE_CONDITION_IDS[mode]
    scoring_dict["r2_attribution_mode"] = mode.value
    scoring_dict["track_failure_class"] = classify_track_failure(
        track=TrackId.R2.value,
        scoring_record=scoring_dict,
        tool_calls_requested=tool_calls_requested,
        tool_outputs=tool_outputs,
        tool_plan_valid=tool_plan_valid,
        tool_execution_error=tool_execution_error,
    )
    return {
        "transcript": transcript,
        "raw_response_text": final_text,
        "track_failure_class": scoring_dict["track_failure_class"],
        "scoring_dict": scoring_dict,
    }


def run_r2_attribution_batch(
    items: list[BenchmarkItem],
    generate: GenerateFn,
    out_dir: str | Path,
    config: OllamaBatchConfig,
    mode: R2AttributionMode,
    *,
    write_summary: bool = True,
) -> R2AttributionBatchResult:
    """Run F1 R2 attribution ablation for one mode (R2A, R2B, or R2C)."""
    if not items:
        raise ValueError("items list is empty")
    if any(item.family != "F1" for item in items):
        raise ValueError("R2 attribution ablations require F1 items only")

    selected = items if config.max_items is None else items[: config.max_items]
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    transcript_dir = root / "transcripts"
    transcript_dir.mkdir(parents=True, exist_ok=True)

    results_path = root / RESULTS_JSONL
    scores_path = root / SCORES_JSONL
    done_ids = (
        completed_item_ids(root)
        if config.resume_items and not config.force_cell
        else set()
    )
    watchdog = _watchdog_config(config)
    max_items = config.max_items if config.max_items is not None else len(selected)
    infrastructure_failures = 0
    track_label = MODE_TRACK_LABELS[mode]

    from fsmreasonbench.evaluator.transcript import utc_timestamp

    for item in selected:
        if item.item_id in done_ids:
            continue
        try:
            run = _evaluate_r2_attribution_item(
                item,
                generate,
                config,
                mode,
                timestamp=utc_timestamp(),
                watchdog=watchdog,
            )
        except ItemInfrastructureError as exc:
            infrastructure_failures += 1
            run = _failed_item_run(
                item,
                config,
                TrackId.R2,
                timestamp=utc_timestamp(),
                error=str(exc),
                infrastructure_failure=True,
                provider_error_type=exc.provider_error_type,
                http_status=exc.http_status,
            )
            _maybe_raise_item_failure_limit(infrastructure_failures, config)
        except Exception as exc:  # noqa: BLE001
            provider_failure = classify_generate_failure(exc)
            if provider_failure is None:
                raise
            infrastructure_failures += 1
            run = _failed_item_run(
                item,
                config,
                TrackId.R2,
                timestamp=utc_timestamp(),
                error=provider_failure.message,
                infrastructure_failure=True,
                provider_error_type=provider_failure.provider_error_type,
                http_status=provider_failure.http_status,
            )
            _maybe_raise_item_failure_limit(infrastructure_failures, config)

        transcript = run["transcript"]
        transcript_path = transcript_dir / f"{item.item_id}.json"
        dump_json(transcript_path, transcript.to_dict())

        if "scoring_dict" in run:
            scoring_dict = run["scoring_dict"]
        else:
            scoring_dict = transcript.scoring_record.to_dict()
            scoring_dict["tool_invocation_count"] = transcript.to_dict().get(
                "tool_invocation_count", 0
            )
            if run.get("infrastructure_failure"):
                enrich_infrastructure_scoring_dict(
                    scoring_dict,
                    provider_error_type=run.get("provider_error_type", "timeout"),
                    http_status=run.get("provider_http_status"),
                )
        scoring_dict["track"] = track_label
        scoring_dict["model"] = config.model
        scoring_dict["ablation_condition"] = MODE_CONDITION_IDS[mode]
        scoring_dict["r2_attribution_mode"] = mode.value
        if "track_failure_class" not in scoring_dict:
            scoring_dict["track_failure_class"] = run["track_failure_class"]

        run_record = {
            "item_id": item.item_id,
            "family": item.family,
            "track": track_label,
            "model": config.model,
            "temperature": config.temperature,
            "ablation_condition": MODE_CONDITION_IDS[mode],
            "r2_attribution_mode": mode.value,
            "prompt_metadata": attribution_prompt_metadata(item, mode),
            "messages": list(transcript.messages),
            "tool_calls_requested": list(transcript.tool_calls_requested),
            "tool_outputs": list(transcript.tool_outputs),
            "raw_response_text": run["raw_response_text"],
            "raw_response": transcript.raw_response,
            "transcript_path": str(transcript_path.relative_to(root)),
            "scoring_record": scoring_dict,
            "protocol_errors": list(transcript.protocol_errors),
            "track_failure_class": run["track_failure_class"],
        }
        append_jsonl(results_path, run_record)
        append_jsonl(scores_path, scoring_dict)
        update_cell_item_progress(
            root,
            items_completed=len(completed_item_ids(root)),
            max_items=max_items,
            last_item_id=item.item_id,
        )
        if config.provider_sleep_between_items > 0:
            time.sleep(config.provider_sleep_between_items)

    scoring_rows = read_jsonl(scores_path) if scores_path.exists() else []
    summary = _build_summary_from_scores(
        scoring_rows=scoring_rows,
        model=config.model,
        family="F1",
        track=track_label,
        provider=config.provider,
        max_tokens=config.max_tokens,
    )
    summary["experiment"] = "r2_attribution_ablation"
    summary["ablation_condition"] = MODE_CONDITION_IDS[mode]
    summary["r2_attribution_mode"] = mode.value
    if write_summary:
        dump_json(root / "summary.json", summary)
        dump_json(root / "track_summary.json", summary)
    dump_json(
        root / "ablation_metadata.json",
        {
            "condition_id": MODE_CONDITION_IDS[mode],
            "r2_attribution_mode": mode.value,
            "track_label": track_label,
            "family": "F1",
            "description": _mode_description(mode),
        },
    )
    return R2AttributionBatchResult(
        results=read_jsonl(results_path) if results_path.exists() else [],
        summary=summary,
        out_dir=root,
        mode=mode,
        infrastructure_failures=infrastructure_failures,
    )


def _mode_description(mode: R2AttributionMode) -> str:
    if mode == R2AttributionMode.R2A:
        return "Model constructs certificate; tool validates only (verifier.validate_f1_certificate)"
    if mode == R2AttributionMode.R2B:
        return "Model constructs certificate; tool repairs formatting only (format.repair_f1_submission)"
    return "Standard R2 solver certificate generators (matches frozen R2 protocol)"
