"""Batch runner for F1 constructible bisimulation equivalence witness study (A1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.evaluator.jsonl import append_jsonl, read_jsonl
from fsmreasonbench.evaluator.scorer import score_item
from fsmreasonbench.evaluator.track_failure_taxonomy import classify_track_failure
from fsmreasonbench.evaluator.transcript import utc_timestamp
from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.runners.cell_failure import SCORES_JSONL
from fsmreasonbench.runners.constructible_equivalence_prompts import (
    STUDY_CONDITION_ID,
    WITNESS_CONTRACT,
    constructible_prompt_metadata,
    render_constructible_final_prompt,
    render_constructible_tool_plan_prompt,
)
from fsmreasonbench.runners.constructible_equivalence_r2c import (
    ensure_f1_constructible_r2c_certificate_synthesis,
)
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
from fsmreasonbench.runners.ollama_track_batch import LLMTrackTranscript, _failed_item_run
from fsmreasonbench.runners.provider_errors import classify_generate_failure
from fsmreasonbench.runners.response_extract import extract_submission_payload
from fsmreasonbench.runners.tool_executor import F1_R2_CONSTRUCTIBLE_EQUIVALENCE_TOOLS, execute_tool_plan
from fsmreasonbench.runners.track_protocol import (
    TrackProtocolError,
    parse_final_submission,
    parse_tool_plan,
)
from fsmreasonbench.tracks.audit import AuditLogBuilder
from fsmreasonbench.tracks.models import TRACKS_VERSION, TrackId
from fsmreasonbench.tracks.replay import replay_audit_log


def _fsm_index(item: BenchmarkItem) -> dict:
    index = {item.fsm.fsm_id: item.fsm}
    if item.fsm_b is not None:
        index[item.fsm_b.fsm_id] = item.fsm_b
    return index


def run_constructible_equivalence_batch(
    items: list[BenchmarkItem],
    generate: GenerateFn,
    out_dir: Path,
    config: OllamaBatchConfig,
    track: TrackId | str,
) -> OllamaBatchResult:
    resolved = TrackId(track) if isinstance(track, str) else track
    if resolved not in {TrackId.R1, TrackId.R2}:
        raise ValueError("constructible equivalence study supports R1 and R2C (TrackId.R2) only")
    if not items:
        raise ValueError("items list is empty")
    if any(item.family != "F1" for item in items):
        raise ValueError("constructible equivalence study requires F1 items only")

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
    infrastructure_failures = 0
    watchdog = _watchdog_config(config)
    track_label = "R2C" if resolved == TrackId.R2 else resolved.value

    for item in items:
        if item.item_id in done_ids:
            continue
        try:
            run = _evaluate_constructible_item(
                item,
                generate,
                config,
                resolved,
                timestamp=utc_timestamp(),
                watchdog=watchdog,
            )
        except ItemInfrastructureError as exc:
            infrastructure_failures += 1
            run = _failed_item_run(
                item,
                config,
                resolved,
                timestamp=utc_timestamp(),
                error=str(exc),
                infrastructure_failure=True,
                provider_error_type=exc.provider_error_type,
                http_status=exc.http_status,
            )
            _maybe_raise_item_failure_limit(infrastructure_failures, config)
        except Exception as exc:  # noqa: BLE001
            provider_failure = classify_generate_failure(exc)
            if provider_failure is not None:
                infrastructure_failures += 1
                run = _failed_item_run(
                    item,
                    config,
                    resolved,
                    timestamp=utc_timestamp(),
                    error=provider_failure.message,
                    infrastructure_failure=True,
                    provider_error_type=provider_failure.provider_error_type,
                    http_status=provider_failure.http_status,
                )
                _maybe_raise_item_failure_limit(infrastructure_failures, config)
            else:
                run = _failed_item_run(
                    item,
                    config,
                    resolved,
                    timestamp=utc_timestamp(),
                    error=str(exc),
                )

        transcript_path = transcript_dir / f"{item.item_id}.json"
        dump_json(transcript_path, run["transcript"].to_dict())

        scoring_dict = run["transcript"].scoring_record.to_dict()
        scoring_dict["track"] = track_label
        scoring_dict["model"] = config.model
        scoring_dict["provider"] = config.provider
        scoring_dict["study_condition"] = STUDY_CONDITION_ID
        scoring_dict["witness_contract"] = WITNESS_CONTRACT
        scoring_dict["tool_invocation_count"] = len(
            run["transcript"].audit_log.get("tool_invocations", [])
        )
        scoring_dict["track_failure_class"] = run["track_failure_class"]
        if run.get("infrastructure_failure"):
            enrich_infrastructure_scoring_dict(
                scoring_dict,
                provider_error_type=run.get("provider_error_type", "timeout"),
                http_status=run.get("provider_http_status"),
            )

        run_record = {
            "item_id": item.item_id,
            "family": item.family,
            "track": track_label,
            "model": config.model,
            "temperature": config.temperature,
            "prompt_metadata": constructible_prompt_metadata(item),
            "study_condition": STUDY_CONDITION_ID,
            "witness_contract": WITNESS_CONTRACT,
            "messages": list(run["transcript"].messages),
            "tool_outputs": list(run["transcript"].tool_outputs),
            "raw_response_text": run["raw_response_text"],
            "transcript_path": str(transcript_path.relative_to(root)),
            "scoring_record": scoring_dict,
            "protocol_errors": list(run["transcript"].protocol_errors),
            "track_failure_class": run["track_failure_class"],
        }
        append_jsonl(results_path, run_record)
        append_jsonl(scores_path, scoring_dict)
        update_cell_item_progress(
            root,
            items_completed=len(completed_item_ids(root)),
            max_items=len(items),
            last_item_id=item.item_id,
        )

    scoring_rows = read_jsonl(scores_path) if scores_path.exists() else []
    summary = _build_summary_from_scores(
        scoring_rows=scoring_rows,
        model=config.model,
        family="F1",
        track=track_label,
        provider=config.provider,
        max_tokens=config.max_tokens,
    )
    summary["study_condition"] = STUDY_CONDITION_ID
    summary["witness_contract"] = WITNESS_CONTRACT
    summary["subset"] = "f1_equivalence_n51"
    dump_json(root / "summary.json", summary)
    all_results = read_jsonl(results_path) if results_path.exists() else []
    return OllamaBatchResult(
        results=all_results,
        summary=summary,
        out_dir=root,
        infrastructure_failures=infrastructure_failures,
    )


def _evaluate_constructible_item(
    item: BenchmarkItem,
    generate: GenerateFn,
    config: OllamaBatchConfig,
    track: TrackId,
    *,
    timestamp: str,
    watchdog: ItemWatchdogConfig,
) -> dict[str, Any]:
    audit = AuditLogBuilder(track)
    audit.scratchpad("study_condition", STUDY_CONDITION_ID)
    audit.scratchpad("witness_contract", WITNESS_CONTRACT)
    messages: list[dict[str, Any]] = []
    protocol_errors: list[str] = []

    plan_prompt = render_constructible_tool_plan_prompt(item, track)
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
    canonical_certificate: dict[str, Any] | None = None
    canonical_verdict: bool | None = None

    try:
        tool_calls_requested, notes = parse_tool_plan(plan_text)
        tool_plan_valid = True
        if notes:
            audit.scratchpad("model_notes", notes)
        if track == TrackId.R2:
            tool_outputs = execute_tool_plan(
                item,
                track,
                tool_calls_requested,
                audit,
                r2_allowed_tools=F1_R2_CONSTRUCTIBLE_EQUIVALENCE_TOOLS,
            )
            synthesis = ensure_f1_constructible_r2c_certificate_synthesis(
                item, tool_outputs, audit
            )
            tool_outputs = synthesis.tool_outputs
            canonical_certificate = synthesis.certificate
            canonical_verdict = synthesis.verdict
        else:
            tool_outputs = execute_tool_plan(item, track, tool_calls_requested, audit)
    except TrackProtocolError as exc:
        protocol_errors.append(str(exc))
        audit.scratchpad("protocol_error", str(exc))
    except (ValueError, RuntimeError) as exc:
        tool_execution_error = str(exc)
        protocol_errors.append(str(exc))
        audit.scratchpad("tool_execution_error", str(exc))

    results_prompt = render_constructible_final_prompt(
        item,
        track,
        tool_outputs,
        canonical_certificate=canonical_certificate,
        canonical_verdict=canonical_verdict,
    )
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
    audit_log = audit.build()
    replay_audit_log(audit_log, fsm_by_id=_fsm_index(item))

    track_label = "R2C" if track == TrackId.R2 else track.value
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
        parsed_submission=None,
        scoring_record=scoring_record,
        audit_log=audit_log.to_dict(),
        protocol_errors=tuple(protocol_errors),
    )
    scoring_dict = scoring_record.to_dict()
    track_failure_class = classify_track_failure(
        track=track.value,
        scoring_record=scoring_dict,
        tool_calls_requested=tool_calls_requested,
        tool_outputs=tool_outputs,
        tool_plan_valid=tool_plan_valid,
        tool_execution_error=tool_execution_error,
    )
    return {
        "transcript": transcript,
        "raw_response_text": final_text,
        "track_failure_class": track_failure_class,
    }
