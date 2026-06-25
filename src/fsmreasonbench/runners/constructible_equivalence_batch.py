"""Batch runner for F1 constructible bisimulation equivalence witness study (A1)."""

from __future__ import annotations

import json
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
from fsmreasonbench.runners.constructible_submission_normalize import (
    extract_constructible_final_submission,
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
from fsmreasonbench.runners.tool_executor import F1_R2_CONSTRUCTIBLE_EQUIVALENCE_TOOLS, execute_tool_plan
from fsmreasonbench.runners.track_protocol import (
    TrackProtocolError,
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
            "audit_log": run["transcript"].audit_log,
            "final_submission_diagnostics": run.get("final_submission_diagnostics"),
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


def validate_constructible_smoke_gate(
    result: OllamaBatchResult,
    *,
    track: str,
) -> tuple[bool, dict[str, Any]]:
    """
    Return (passed, report) for a 1-item constructible-equivalence smoke run.
    """
    summary = result.summary
    failures: list[str] = []
    if summary.get("n", 0) != 1:
        failures.append(f"expected n=1 smoke item, got n={summary.get('n')}")
    if summary.get("extractability_rate") != 1.0:
        failures.append(
            f"extractability_rate must be 1.0, got {summary.get('extractability_rate')}"
        )
    if summary.get("provider_error_count", 0) != 0:
        failures.append(
            "provider_error_count must be 0, got "
            f"{summary.get('provider_error_count')}"
        )
    if not result.results:
        failures.append("no results rows recorded")
        return False, {"failures": failures, "track": track}

    row = result.results[0]
    diagnostics = row.get("final_submission_diagnostics") or {}
    scoring = row.get("scoring_record") or {}
    if not diagnostics.get("final_json_found"):
        failures.append("final JSON was not extracted from model response")
    if not scoring.get("extractable"):
        failures.append("scoring_record.extractable is false")
    if scoring.get("failure_stage") == "not_extractable":
        failures.append("failure_stage must not be not_extractable after extraction")
    if not diagnostics.get("certificate_type_recognized"):
        failures.append(
            "certificate_type must be recognized as bisimulation_witness "
            f"(got {diagnostics.get('certificate_type')!r})"
        )
    if diagnostics.get("certificate_type") != "bisimulation_witness":
        failures.append(
            "final answer certificate_type must be bisimulation_witness "
            f"(got {diagnostics.get('certificate_type')!r})"
        )
    if not diagnostics.get("verifier_invoked"):
        failures.append("verifier was not invoked (certificate_valid is null)")
    elif scoring.get("certificate_valid") is None:
        failures.append("certificate_valid must be true or false after verifier run")

    if track == "R2C":
        audit_log = row.get("audit_log") or {}
        assembly = audit_log.get("certificate_assembly") or []
        if not assembly:
            failures.append("R2C audit_log.certificate_assembly is empty")

    report = {
        "passed": not failures,
        "failures": failures,
        "track": track,
        "extractability_rate": summary.get("extractability_rate"),
        "provider_error_count": summary.get("provider_error_count"),
        "certificate_type": diagnostics.get("certificate_type"),
        "certificate_type_recognized": diagnostics.get("certificate_type_recognized"),
        "final_json_found": diagnostics.get("final_json_found"),
        "verifier_invoked": diagnostics.get("verifier_invoked"),
        "certificate_valid": diagnostics.get("certificate_valid"),
        "failure_stage": diagnostics.get("failure_stage"),
        "parse_errors": diagnostics.get("parse_errors"),
        "parse_path": diagnostics.get("parse_path"),
        "repairs_applied": diagnostics.get("repairs_applied"),
        "final_submission_diagnostics": {
            key: diagnostics.get(key)
            for key in (
                "raw_final_response_text",
                "protocol_error",
                "top_level_keys",
                "submission_keys",
                "phase",
                "certificate_type",
                "certificate_type_recognized",
                "item_id_seen",
                "item_id_expected",
                "placeholder_literals_detected",
                "final_json_found",
                "parse_errors",
                "parse_path",
                "repairs_applied",
                "verifier_invoked",
                "certificate_valid",
                "failure_stage",
                "certificate_errors",
            )
        },
    }
    return not failures, report


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
    final_submission_diagnostics: dict[str, Any]
    try:
        raw_response, final_submission_diagnostics = extract_constructible_final_submission(
            final_text,
            item,
        )
        if final_submission_diagnostics.get("protocol_error"):
            protocol_errors.append(
                f"final submission protocol fallback: {final_submission_diagnostics['protocol_error']}"
            )
    except Exception as exc:  # noqa: BLE001
        raw_response = final_text
        final_submission_diagnostics = {
            "raw_final_response_text": final_text,
            "parse_path": "failed",
            "parse_errors": [str(exc)],
        }
        protocol_errors.append(str(exc))

    audit.scratchpad(
        "final_submission_diagnostics",
        json.dumps(
            {
                key: final_submission_diagnostics.get(key)
                for key in (
                    "parse_path",
                    "protocol_error",
                    "top_level_keys",
                    "submission_keys",
                    "phase",
                    "certificate_type",
                    "certificate_type_recognized",
                    "item_id_seen",
                    "item_id_expected",
                    "placeholder_literals_detected",
                    "repairs_applied",
                    "parse_errors",
                    "final_json_found",
                    "verifier_invoked",
                    "certificate_valid",
                    "failure_stage",
                )
            },
            sort_keys=True,
        ),
    )

    scoring_record = score_item(item, raw_response)
    final_submission_diagnostics["verifier_invoked"] = (
        scoring_record.certificate_valid is not None
    )
    final_submission_diagnostics["certificate_valid"] = scoring_record.certificate_valid
    final_submission_diagnostics["failure_stage"] = scoring_record.failure_stage.value
    final_submission_diagnostics["certificate_errors"] = list(
        scoring_record.certificate_errors or ()
    )

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
        "final_submission_diagnostics": final_submission_diagnostics,
    }
