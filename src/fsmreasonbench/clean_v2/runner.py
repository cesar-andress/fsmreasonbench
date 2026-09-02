"""Clean_v2 scientific runner (no certificate injection)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from fsmreasonbench.clean_v2.artifacts import (
    append_jsonl,
    ensure_run_paths,
    read_jsonl,
    run_id_for,
    utc_timestamp,
    write_json,
)
from fsmreasonbench.clean_v2.condition import ConditionSpec, OracleInfoId, OrchestrationMode, ToolPaletteId
from fsmreasonbench.clean_v2.confirmatory.constants import MAX_VERIFIER_CALLS
from fsmreasonbench.clean_v2.confirmatory.t3_budget import (
    compute_witness_valid_first,
    strip_silent_audit_for_model_export,
)
from fsmreasonbench.clean_v2.fingerprint import fingerprint_condition
from fsmreasonbench.clean_v2.metrics import summarize_attempt_records
from fsmreasonbench.clean_v2.prompts import render_final_prompt, render_tool_plan_prompt
from fsmreasonbench.clean_v2.provenance import WitnessProvenance, assert_model_performance_row_allowed
from fsmreasonbench.clean_v2.scoring import parse_clean_submission, score_clean_submission
from fsmreasonbench.clean_v2.tools import execute_clean_tool_plan
from fsmreasonbench.clean_v2.views import build_evaluatee_view, build_evaluator_only
from fsmreasonbench.items.assembly import BenchmarkItem

GenerateFn = Callable[..., str]


def _parse_tool_plan(raw_text: str) -> list[dict[str, Any]]:
    from fsmreasonbench.runners.response_extract import extract_submission_payload

    payload = extract_submission_payload(raw_text)
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return []
    if not isinstance(payload, dict):
        return []
    if payload.get("phase") == "final_submission":
        return []
    tool_calls = payload.get("tool_calls")
    if payload.get("phase") == "tool_plan" and isinstance(tool_calls, list):
        return [call for call in tool_calls if isinstance(call, dict)]
    # Allow direct final submission without tools.
    return []


def run_clean_item(
    item: BenchmarkItem,
    condition: ConditionSpec,
    generate: GenerateFn,
    *,
    item_manifest_fingerprint: str,
    out_dir: Path,
    overwrite: bool = False,
) -> dict[str, Any]:
    """
    Execute one item×condition×repetition.

    Scientific path forbids runner certificate synthesis/injection.
    """
    if condition.orchestration_mode != OrchestrationMode.TWO_PHASE_NO_INJECT:
        raise ValueError(
            "run_clean_item only supports orchestration_mode=two_phase_no_inject; "
            "use an explicit SYS_CEILING entrypoint for ceilings"
        )

    cell_dir = ensure_run_paths(out_dir, condition)
    scores_path = cell_dir / "scores.jsonl"
    results_path = cell_dir / "results.jsonl"
    run_id = run_id_for(
        condition,
        item_id=item.item_id,
        item_manifest_fingerprint=item_manifest_fingerprint,
    )
    existing_scores = read_jsonl(scores_path)
    existing_ids = {row.get("run_id") for row in existing_scores}
    if run_id in existing_ids and not overwrite:
        raise FileExistsError(
            f"refusing to overwrite existing run_id={run_id} under {cell_dir}; "
            "pass overwrite=True to replace"
        )
    if overwrite and run_id in existing_ids:
        remaining_scores = [row for row in existing_scores if row.get("run_id") != run_id]
        scores_path.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in remaining_scores),
            encoding="utf-8",
        )
        existing_results = read_jsonl(results_path) if results_path.exists() else []
        remaining_results = [row for row in existing_results if row.get("run_id") != run_id]
        results_path.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in remaining_results),
            encoding="utf-8",
        )

    evaluatee = build_evaluatee_view(item)
    evaluator = build_evaluator_only(item)
    gold_for_oracle = (
        evaluator.gold_verdict if condition.oracle_info == OracleInfoId.GOLD_VERDICT else None
    )

    tool_outputs: list[dict[str, Any]] = []
    tool_calls: list[dict[str, Any]] = []
    tool_audit: dict[str, Any] = {
        "max_verifier_calls": MAX_VERIFIER_CALLS,
        "verifier_call_count": 0,
        "verifier_call_cap_reached": False,
        "coarse_verifier_responses": [],
    }
    messages: list[dict[str, Any]] = []

    if condition.tool_palette != ToolPaletteId.T0_NONE:
        plan_prompt = render_tool_plan_prompt(
            condition,
            evaluatee,
            gold_verdict_for_oracle=gold_for_oracle,
        )
        plan_text = generate(prompt=plan_prompt, model=condition.model, temperature=condition.temperature)
        messages.append({"role": "user", "phase": "tool_plan", "content": plan_prompt})
        messages.append({"role": "assistant", "phase": "tool_plan", "content": plan_text})
        tool_calls = _parse_tool_plan(plan_text)
        tool_outputs, tool_audit = execute_clean_tool_plan(
            item,
            evaluatee,
            tool_calls,
            palette=condition.tool_palette,
            contract=condition.contract,
            tool_call_budget=condition.tool_call_budget,
            max_verifier_calls=MAX_VERIFIER_CALLS,
        )

    final_prompt = render_final_prompt(
        condition,
        evaluatee,
        gold_verdict_for_oracle=gold_for_oracle,
        tool_results=tool_outputs,
    )
    final_text = generate(
        prompt=final_prompt,
        model=condition.model,
        temperature=condition.temperature,
    )
    messages.append({"role": "user", "phase": "final_submission", "content": final_prompt})
    messages.append({"role": "assistant", "phase": "final_submission", "content": final_text})

    provenance = WitnessProvenance.model_generated(
        tool_contributed=bool(tool_outputs),
        verifier_only_feedback=any(
            row.get("tool") == "verifier.validate_certificate_coarse"
            and row.get("status") == "executed"
            for row in tool_outputs
        ),
    )
    score = score_clean_submission(
        item,
        evaluator,
        final_text,
        condition,
        provenance=provenance,
        tool_outputs=tool_outputs,
    )
    # Silent first-proposal evaluation: never injected into messages/tool_outputs.
    submission, _ = parse_clean_submission(final_text)
    final_cert = submission.get("certificate") if isinstance(submission, dict) else None
    first_audit = compute_witness_valid_first(
        item,
        contract=condition.contract,
        tool_calls=tool_calls,
        final_certificate=final_cert if isinstance(final_cert, dict) else None,
    )
    score["witness_valid_first"] = first_audit.get("witness_valid_first")
    score["first_proposal_present"] = first_audit.get("first_proposal_present")
    score["first_proposal_source"] = first_audit.get("first_proposal_source")
    score["verifier_call_count"] = tool_audit.get("verifier_call_count", 0)
    score["verifier_call_cap_reached"] = tool_audit.get("verifier_call_cap_reached", False)
    score["coarse_verifier_responses"] = tool_audit.get("coarse_verifier_responses", [])
    score["max_verifier_calls"] = tool_audit.get("max_verifier_calls", MAX_VERIFIER_CALLS)
    score["run_id"] = run_id
    score["condition_fingerprint"] = fingerprint_condition(
        condition, item_manifest_fingerprint=item_manifest_fingerprint
    )
    score["item_manifest_fingerprint"] = item_manifest_fingerprint
    score["timestamp"] = utc_timestamp()
    score["seed"] = condition.seed
    score["request_parameters"] = {
        "temperature": condition.temperature,
        "max_tokens": condition.max_tokens,
        "top_p": condition.top_p,
    }
    assert_model_performance_row_allowed(score)

    # Evaluator-only silent audit (not model-visible).
    silent_audit = strip_silent_audit_for_model_export(first_audit)

    transcript = {
        "run_id": run_id,
        "item_id": item.item_id,
        "condition": condition.to_dict(),
        "evaluatee": evaluatee.to_dict(),
        "messages": messages,
        "tool_calls": tool_calls,
        "tool_outputs": tool_outputs,
        "tool_audit": tool_audit,
        "silent_first_witness_audit": silent_audit,
        "raw_response": final_text,
        "score": score,
        # Evaluator-only gold is stored separately from model-visible evaluatee.
        "evaluator_only_ref": {"item_id": item.item_id},
    }
    write_json(cell_dir / "transcripts" / f"{item.item_id}.json", transcript)
    append_jsonl(results_path, transcript)
    append_jsonl(scores_path, score)
    return score


def summarize_cell(cell_dir: Path) -> dict[str, Any]:
    scores = read_jsonl(cell_dir / "scores.jsonl")
    summary = summarize_attempt_records(scores)
    summary["cell_dir"] = str(cell_dir)
    write_json(cell_dir / "summary.json", summary)
    return summary
