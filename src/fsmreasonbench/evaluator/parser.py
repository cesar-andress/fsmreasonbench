"""C2 reachability answer parser."""

from __future__ import annotations

import json
from typing import Any

from fsmreasonbench.evaluator.models import ParseResult, ParsedSubmission

_VALID_CERTIFICATE_TYPES = frozenset({"trace_witness", "unreachability_witness"})


def parse_c2_response(raw_response: Any) -> ParseResult:
    """
    Parse a model/system response into a C2 submission.

    Accepts a dict or JSON string. Returns extractable=False on failure.
    """
    errors: list[str] = []

    if isinstance(raw_response, str):
        try:
            payload = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            return ParseResult(extractable=False, errors=(f"invalid JSON: {exc}",))
        if not isinstance(payload, dict):
            return ParseResult(extractable=False, errors=("top-level JSON must be an object",))
        raw_response = payload

    if not isinstance(raw_response, dict):
        return ParseResult(
            extractable=False,
            errors=(f"response must be object or JSON string, got {type(raw_response).__name__}",),
        )

    for field in ("item_id", "verdict", "certificate"):
        if field not in raw_response:
            errors.append(f"missing required field: {field}")

    if errors:
        return ParseResult(extractable=False, errors=tuple(errors))

    item_id = raw_response["item_id"]
    verdict = raw_response["verdict"]
    certificate = raw_response["certificate"]

    if not isinstance(item_id, str) or not item_id:
        errors.append("item_id must be a non-empty string")
    if not isinstance(verdict, bool):
        errors.append("verdict must be boolean")
    if not isinstance(certificate, dict):
        errors.append("certificate must be an object")
    else:
        errors.extend(_validate_certificate(certificate))

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


def _validate_certificate(certificate: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    cert_type = certificate.get("certificate_type")
    if cert_type not in _VALID_CERTIFICATE_TYPES:
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
