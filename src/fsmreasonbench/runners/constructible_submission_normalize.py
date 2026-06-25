"""Parse and normalize constructible-equivalence final submissions (study-local)."""

from __future__ import annotations

import json
from typing import Any

from fsmreasonbench.evaluator.parser import parse_f1_response
from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.runners.response_extract import (
    extract_submission_payload,
    extract_submission_payload_with_json_repair,
)
from fsmreasonbench.runners.track_protocol import TrackProtocolError, parse_final_submission

PLACEHOLDER_ITEM_IDS = frozenset(
    {
        "<must match item>",
        "<item_id>",
        "item",
        "<must match item_id>",
    }
)
PLACEHOLDER_FSM_ID_TOKENS = frozenset(
    {
        "<fsm_a.fsm_id>",
        "<fsm_b.fsm_id>",
        "<fsm_id>",
    }
)


def _top_level_keys(payload: Any) -> list[str]:
    if isinstance(payload, dict):
        return sorted(str(key) for key in payload.keys())
    return []


def _detect_placeholder_literals(text: str) -> list[str]:
    found: list[str] = []
    for token in sorted(PLACEHOLDER_ITEM_IDS | PLACEHOLDER_FSM_ID_TOKENS):
        if token in text:
            found.append(token)
    return found


def _certificate_type(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    submission = payload
    if payload.get("phase") == "final_submission":
        submission = payload.get("submission")
    if not isinstance(submission, dict):
        return None
    certificate = submission.get("certificate")
    if not isinstance(certificate, dict):
        return None
    cert_type = certificate.get("certificate_type")
    return str(cert_type) if cert_type is not None else None


def normalize_constructible_submission(
    submission: dict[str, Any],
    item: BenchmarkItem,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Repair study-template literals and missing fsm_ids without changing witness semantics.
    """
    repairs: dict[str, Any] = {}
    normalized = dict(submission)
    item_id = normalized.get("item_id")
    if isinstance(item_id, str) and item_id.strip() in PLACEHOLDER_ITEM_IDS:
        normalized["item_id"] = item.item_id
        repairs["item_id_repaired_from_placeholder"] = item_id
    elif item_id != item.item_id:
        normalized["item_id"] = item.item_id
        repairs["item_id_repaired_from_model_value"] = item_id

    certificate = normalized.get("certificate")
    if isinstance(certificate, dict) and item.fsm_b is not None:
        cert = dict(certificate)
        fsm_ids = cert.get("fsm_ids")
        expected = [item.fsm_a.fsm_id, item.fsm_b.fsm_id]
        needs_repair = False
        if not isinstance(fsm_ids, list) or len(fsm_ids) != 2:
            cert["fsm_ids"] = expected
            repairs["fsm_ids_autofilled"] = True
            needs_repair = True
        elif any(
            not isinstance(value, str) or value.strip() in PLACEHOLDER_FSM_ID_TOKENS
            for value in fsm_ids
        ):
            cert["fsm_ids"] = expected
            repairs["fsm_ids_repaired_from_placeholder"] = fsm_ids
            needs_repair = True
        if needs_repair:
            normalized["certificate"] = cert
    return normalized, repairs


def extract_constructible_final_submission(
    final_text: str,
    item: BenchmarkItem,
) -> tuple[dict[str, Any] | str, dict[str, Any]]:
    """
    Parse phase-2 output and return submission payload plus diagnostics.
    """
    diagnostics: dict[str, Any] = {
        "raw_final_response_text": final_text,
        "placeholder_literals_detected": _detect_placeholder_literals(final_text),
        "final_json_found": False,
        "parse_path": "failed",
        "protocol_error": None,
        "top_level_keys": [],
        "phase": None,
        "submission_keys": [],
        "certificate_type": None,
        "certificate_type_recognized": False,
        "item_id_seen": None,
        "item_id_expected": item.item_id,
        "repairs_applied": {},
        "parse_errors": [],
    }

    submission: dict[str, Any] | str
    try:
        submission = parse_final_submission(final_text)
        diagnostics["parse_path"] = "protocol"
        diagnostics["final_json_found"] = True
        diagnostics["phase"] = "final_submission"
    except TrackProtocolError as exc:
        diagnostics["protocol_error"] = str(exc)
        extracted = extract_submission_payload_with_json_repair(final_text)
        if isinstance(extracted, str):
            extracted = extract_submission_payload(final_text)
        if isinstance(extracted, dict):
            diagnostics["parse_path"] = "best_effort"
            diagnostics["final_json_found"] = True
            diagnostics["top_level_keys"] = _top_level_keys(extracted)
            diagnostics["phase"] = extracted.get("phase")
            if extracted.get("phase") == "final_submission" and isinstance(
                extracted.get("submission"), dict
            ):
                submission = extracted["submission"]
            elif all(key in extracted for key in ("item_id", "verdict", "certificate")):
                submission = extracted
            else:
                submission = final_text
        else:
            submission = final_text

    if isinstance(submission, dict):
        diagnostics["top_level_keys"] = _top_level_keys(
            {"phase": "final_submission", "submission": submission}
        )
        diagnostics["submission_keys"] = sorted(str(k) for k in submission.keys())
        diagnostics["item_id_seen"] = submission.get("item_id")
        cert_type = _certificate_type(
            {"phase": "final_submission", "submission": submission}
        )
        diagnostics["certificate_type"] = cert_type
        diagnostics["certificate_type_recognized"] = cert_type == "bisimulation_witness"
        submission, repairs = normalize_constructible_submission(submission, item)
        if repairs:
            diagnostics["repairs_applied"] = repairs
        parse_result = parse_f1_response(submission)
        diagnostics["parse_errors"] = list(parse_result.errors) if not parse_result.extractable else []
    else:
        diagnostics["parse_errors"] = ["final response is not a JSON submission object"]

    return submission, diagnostics
