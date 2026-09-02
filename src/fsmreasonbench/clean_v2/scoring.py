"""Parsing and scoring for clean_v2 submissions."""

from __future__ import annotations

import json
from typing import Any

from fsmreasonbench.clean_v2.condition import ConditionSpec, ContractId
from fsmreasonbench.clean_v2.contracts import contract_burden_metadata, verify_certificate_for_contract
from fsmreasonbench.clean_v2.provenance import WitnessOrigin, WitnessProvenance
from fsmreasonbench.clean_v2.versions import PARSER_VERSION, SCORER_VERSION, VERIFIER_VERSION
from fsmreasonbench.clean_v2.views import EvaluatorOnly
from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.runners.response_extract import extract_submission_payload


def parse_clean_submission(raw_response: Any) -> tuple[dict[str, Any] | None, tuple[str, ...]]:
    """Parse model output into a submission object or return errors."""
    payload: Any
    if isinstance(raw_response, str):
        payload = extract_submission_payload(raw_response)
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError as exc:
                return None, (f"invalid JSON: {exc}",)
    elif isinstance(raw_response, dict):
        payload = raw_response
    else:
        return None, (f"unsupported response type: {type(raw_response).__name__}",)

    if not isinstance(payload, dict):
        return None, ("top-level JSON must be an object",)

    # Unwrap phase envelope if present (syntactic only).
    if payload.get("phase") == "final_submission" and isinstance(payload.get("submission"), dict):
        payload = payload["submission"]

    errors: list[str] = []
    for field in ("item_id", "verdict", "certificate"):
        if field not in payload:
            errors.append(f"missing required field: {field}")
    if errors:
        return None, tuple(errors)
    if not isinstance(payload["item_id"], str) or not payload["item_id"]:
        errors.append("item_id must be a non-empty string")
    if not isinstance(payload["verdict"], bool):
        errors.append("verdict must be boolean")
    if not isinstance(payload["certificate"], dict):
        errors.append("certificate must be an object")
    if errors:
        return None, tuple(errors)
    return payload, ()


def _first_failure(
    *,
    extractable: bool,
    verdict_correct: bool | None,
    witness_valid: bool | None,
) -> str:
    if not extractable:
        return "not_extractable"
    if verdict_correct is not True:
        return "verdict_wrong"
    if witness_valid is not True:
        return "witness_invalid"
    return "correct"


def score_clean_submission(
    item: BenchmarkItem,
    evaluator: EvaluatorOnly,
    raw_response: Any,
    condition: ConditionSpec,
    *,
    provenance: WitnessProvenance | None = None,
    tool_outputs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Score one attempt with common-denominator fields and provenance."""
    submission, parse_errors = parse_clean_submission(raw_response)
    extractable = submission is not None and not parse_errors
    verdict_correct: bool | None = None
    witness_valid: bool | None = None
    certificate_errors: tuple[str, ...] = ()
    certificate: dict[str, Any] | None = None

    if extractable and submission is not None:
        verdict_correct = submission["verdict"] == evaluator.gold_verdict
        certificate = submission["certificate"]
        if item.fsm_b is None:
            witness_valid = False
            certificate_errors = ("missing fsm_b",)
        else:
            result = verify_certificate_for_contract(
                item.fsm_a,
                item.fsm_b,
                certificate,
                contract=condition.contract,
            )
            witness_valid = result.valid
            certificate_errors = result.errors

    fully_correct = bool(extractable and verdict_correct is True and witness_valid is True)
    first_failure = _first_failure(
        extractable=extractable,
        verdict_correct=verdict_correct,
        witness_valid=witness_valid,
    )

    resolved_provenance = provenance or WitnessProvenance.model_generated()
    # If orchestration is scientific, force model_generated unless explicitly marked.
    if condition.orchestration_mode.value == "two_phase_no_inject":
        if resolved_provenance.witness_origin in {
            WitnessOrigin.TOOL_CONSTRUCTED,
            WitnessOrigin.RUNNER_INJECTED,
        }:
            # Keep declared origin for ceiling/legacy rows; scientific runner must not produce these.
            pass

    return {
        "item_id": item.item_id,
        "family": item.family,
        "extractable": extractable,
        "verdict_correct": verdict_correct,
        "witness_valid": witness_valid,
        "fully_correct": fully_correct,
        "first_failure": first_failure,
        "parse_errors": list(parse_errors),
        "certificate_errors": list(certificate_errors),
        "contract": condition.contract.value,
        "tool_palette": condition.tool_palette.value,
        "oracle_info": condition.oracle_info.value,
        "format_assist": condition.format_assist.value,
        "repetition_index": condition.repetition_index,
        "model": condition.model,
        "provider": condition.provider,
        "witness_provenance": resolved_provenance.to_dict(),
        "contract_burden": contract_burden_metadata(certificate),
        "tool_outputs_count": len(tool_outputs or []),
        "parser_version": PARSER_VERSION,
        "scorer_version": SCORER_VERSION,
        "verifier_version": VERIFIER_VERSION,
        "namespace": "clean_v2",
    }
