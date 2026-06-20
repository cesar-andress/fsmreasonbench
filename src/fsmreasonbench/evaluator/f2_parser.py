"""F2 composition submission parsing and materialization guard."""

from __future__ import annotations

from typing import Any

from fsmreasonbench.evaluator.models import ParseResult, ParsedSubmission
from fsmreasonbench.evaluator.parser import _load_submission_object
from fsmreasonbench.verifier.composition import check_materialization_violation

_F2_CERTIFICATE_TYPES = frozenset({"projected_trace_witness"})


def parse_f2_response(raw_response: Any) -> ParseResult:
    """Parse an F2 submission envelope."""
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
        errors.extend(_validate_f2_certificate(certificate))

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


def _validate_f2_certificate(certificate: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    cert_type = certificate.get("certificate_type")
    if cert_type not in _F2_CERTIFICATE_TYPES:
        errors.append(f"unsupported F2 certificate_type: {cert_type!r}")
    payload = certificate.get("payload")
    if not isinstance(payload, dict):
        errors.append("certificate payload must be an object")
    else:
        errors.extend(check_materialization_violation({"payload": payload}))
    return errors
