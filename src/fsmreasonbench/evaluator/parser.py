"""Family-aware submission parsing."""

from __future__ import annotations

import json
from typing import Any

from fsmreasonbench.evaluator.models import ParseResult, ParsedSubmission

_C2_CERTIFICATE_TYPES = frozenset({"trace_witness", "unreachability_witness"})
_F1_CERTIFICATE_TYPES = frozenset(
    {"distinguishing_trace", "equivalence_witness", "bisimulation_witness"}
)


def parse_submission(raw_response: Any, family: str) -> ParseResult:
    """Parse a model/system response for the given benchmark family."""
    payload, errors = _load_submission_object(raw_response)
    if errors:
        return ParseResult(extractable=False, errors=tuple(errors))
    assert payload is not None

    for field in ("item_id", "verdict", "certificate"):
        if field not in payload:
            errors.append(f"missing required field: {field}")
    if errors:
        return ParseResult(extractable=False, errors=tuple(errors))

    item_id = payload["item_id"]
    verdict = payload["verdict"]
    certificate = payload["certificate"]

    if not isinstance(item_id, str) or not item_id:
        errors.append("item_id must be a non-empty string")
    if not isinstance(verdict, bool):
        errors.append("verdict must be boolean")
    if not isinstance(certificate, dict):
        errors.append("certificate must be an object")
    else:
        if family == "C2":
            errors.extend(_validate_c2_certificate(certificate))
        elif family == "F1":
            errors.extend(_validate_f1_certificate(certificate))
        else:
            errors.append(f"unsupported family for parsing: {family!r}")

    if errors:
        return ParseResult(extractable=False, errors=tuple(errors))

    return ParseResult(
        extractable=True,
        submission=ParsedSubmission(
            item_id=item_id,
            verdict=verdict,
            certificate=certificate,
        ),
    )


def parse_c2_response(raw_response: Any) -> ParseResult:
    return parse_submission(raw_response, "C2")


def parse_f1_response(raw_response: Any) -> ParseResult:
    return parse_submission(raw_response, "F1")


def _load_submission_object(raw_response: Any) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    if isinstance(raw_response, str):
        try:
            payload = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            return None, [f"invalid JSON: {exc}"]
        if not isinstance(payload, dict):
            return None, ["top-level JSON must be an object"]
        return payload, errors

    if not isinstance(raw_response, dict):
        return None, [
            f"response must be object or JSON string, got {type(raw_response).__name__}",
        ]
    return raw_response, errors


def _validate_c2_certificate(certificate: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    cert_type = certificate.get("certificate_type")
    if cert_type not in _C2_CERTIFICATE_TYPES:
        errors.append(
            f"certificate_type must be trace_witness or unreachability_witness, got {cert_type!r}"
        )
    if "payload" not in certificate or not isinstance(certificate["payload"], dict):
        errors.append("certificate.payload must be an object")
    if cert_type == "trace_witness":
        payload = certificate.get("payload", {})
        if "trace" not in payload or not isinstance(payload["trace"], list):
            errors.append("trace_witness.payload.trace must be an array")
        if "state_sequence" not in payload or not isinstance(payload["state_sequence"], list):
            errors.append("trace_witness.payload.state_sequence must be an array")
    if cert_type == "unreachability_witness":
        payload = certificate.get("payload", {})
        if "reachable_states" not in payload or not isinstance(payload["reachable_states"], list):
            errors.append("unreachability_witness.payload.reachable_states must be an array")
        if "target_state" not in payload or not isinstance(payload["target_state"], str):
            errors.append("unreachability_witness.payload.target_state must be a string")
    return errors


def _validate_f1_certificate(certificate: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    cert_type = certificate.get("certificate_type")
    if cert_type not in _F1_CERTIFICATE_TYPES:
        errors.append(
            "certificate_type must be distinguishing_trace, equivalence_witness, "
            f"or bisimulation_witness, got {cert_type!r}"
        )
    fsm_ids = certificate.get("fsm_ids")
    if not isinstance(fsm_ids, list) or len(fsm_ids) != 2:
        errors.append("fsm_ids must be an array of length 2")
    elif not all(isinstance(value, str) and value for value in fsm_ids):
        errors.append("fsm_ids entries must be non-empty strings")
    if "payload" not in certificate or not isinstance(certificate["payload"], dict):
        errors.append("certificate.payload must be an object")
    elif cert_type == "distinguishing_trace":
        errors.extend(_validate_distinguishing_trace_payload(certificate["payload"]))
    elif cert_type == "equivalence_witness":
        errors.extend(_validate_equivalence_witness_payload(certificate["payload"]))
    elif cert_type == "bisimulation_witness":
        errors.extend(_validate_bisimulation_witness_payload(certificate["payload"]))
    return errors


def _validate_distinguishing_trace_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if "trace" not in payload or not isinstance(payload["trace"], list):
        errors.append("distinguishing_trace.payload.trace must be an array")
    acceptance = payload.get("acceptance")
    if not isinstance(acceptance, dict):
        errors.append("distinguishing_trace.payload.acceptance must be an object")
    else:
        for key in ("A", "B"):
            if key not in acceptance or not isinstance(acceptance[key], bool):
                errors.append(f"distinguishing_trace.payload.acceptance.{key} must be boolean")
    return errors


def _validate_equivalence_witness_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("equivalent") is not True:
        errors.append("equivalence_witness.payload.equivalent must be true")
    for field in ("minimized_hash_A", "minimized_hash_B"):
        value = payload.get(field)
        if not isinstance(value, str) or not value:
            errors.append(f"equivalence_witness.payload.{field} must be a non-empty string")
    return errors


def _validate_bisimulation_witness_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("equivalent") is not True:
        errors.append("bisimulation_witness.payload.equivalent must be true")
    pairs = payload.get("pairs")
    if not isinstance(pairs, list) or not pairs:
        errors.append("bisimulation_witness.payload.pairs must be a non-empty array")
    elif pairs:
        for index, entry in enumerate(pairs):
            if not isinstance(entry, dict):
                errors.append(f"bisimulation_witness.payload.pairs[{index}] must be an object")
                continue
            for field in ("state_a", "state_b"):
                value = entry.get(field)
                if not isinstance(value, str) or not value:
                    errors.append(
                        f"bisimulation_witness.payload.pairs[{index}].{field} "
                        "must be a non-empty string"
                    )
    return errors
