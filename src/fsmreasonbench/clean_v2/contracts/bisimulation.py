"""Bisimulation witness contract (semantic relation check)."""

from __future__ import annotations

from typing import Any

from fsmreasonbench.models.fsm import ExecutableFSM
from fsmreasonbench.runtime.bisimulation import pairs_from_payload, verify_bisimulation_relation
from fsmreasonbench.verifier.result import VerifyResult


def verify_bisimulation_contract(
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
    certificate: dict[str, Any],
) -> VerifyResult:
    """Validate submitted relation semantically (not equality to one gold relation)."""
    if fsm_a.fsm_type.value != "DFA" or fsm_b.fsm_type.value != "DFA":
        return VerifyResult.fail("bisimulation_witness verification requires DFA inputs")
    if fsm_a.input_alphabet != fsm_b.input_alphabet:
        return VerifyResult.fail("DFA alphabets must match")
    if certificate.get("certificate_type") != "bisimulation_witness":
        return VerifyResult.fail(
            f"unsupported certificate_type: {certificate.get('certificate_type')!r}"
        )
    fsm_ids = certificate.get("fsm_ids")
    if not isinstance(fsm_ids, list) or len(fsm_ids) != 2:
        return VerifyResult.fail("fsm_ids must be an array of length 2")
    if fsm_ids != [fsm_a.fsm_id, fsm_b.fsm_id]:
        return VerifyResult.fail("fsm_ids mismatch")
    payload = certificate.get("payload")
    if not isinstance(payload, dict):
        return VerifyResult.fail("certificate payload must be an object")
    if payload.get("equivalent") is not True:
        return VerifyResult.fail("payload.equivalent must be true")
    try:
        relation = pairs_from_payload(payload)
    except ValueError as exc:
        return VerifyResult.fail(str(exc))
    valid, errors = verify_bisimulation_relation(fsm_a, fsm_b, relation)
    if not valid:
        return VerifyResult.fail(*errors)
    return VerifyResult.ok()
