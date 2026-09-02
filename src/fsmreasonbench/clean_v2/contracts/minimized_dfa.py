"""Minimized DFA structural witness contract for clean_v2."""

from __future__ import annotations

from typing import Any

from fsmreasonbench.models.fsm import ExecutableFSM, FSMType
from fsmreasonbench.models.serialization import fsm_from_dict
from fsmreasonbench.runtime.dfa_minimize import (
    _reachable_states,
    are_equivalent_dfas,
    complete_dfa,
    minimize_dfa,
)
from fsmreasonbench.verifier.result import VerifyResult


def _parse_machine(payload_key: str, raw: Any) -> tuple[ExecutableFSM | None, str | None]:
    if not isinstance(raw, dict):
        return None, f"payload.{payload_key} must be an object"
    try:
        # Allow omitted fsm_id; assign temporary id for parsing.
        data = dict(raw)
        data.setdefault("fsm_id", f"submitted:{payload_key}")
        data.setdefault("fsm_type", "DFA")
        machine = fsm_from_dict(data)
    except Exception as exc:  # noqa: BLE001
        return None, f"payload.{payload_key} malformed: {exc}"
    if machine.fsm_type != FSMType.DFA:
        return None, f"payload.{payload_key} must be a DFA"
    return machine, None


def is_minimal_dfa(fsm: ExecutableFSM) -> bool:
    """
    A DFA is minimal iff every reachable completed state is a distinct Myhill–Nerode class.

    Unreachable extras make the machine non-minimal for this witness contract.
    """
    completed = complete_dfa(fsm)
    reachable = _reachable_states(completed, completed.initial_state)
    if set(fsm.states) - reachable:
        # Unreachable extras in the submitted machine.
        return False
    minimized = minimize_dfa(fsm)
    return len(minimized.states) == len(reachable)


def verify_minimized_dfa_contract(
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
    certificate: dict[str, Any],
) -> VerifyResult:
    """
    Check submitted minimized machines A' and B':

    1. A' ~ A, B' ~ B (behavioral equivalence)
    2. A' and B' are minimal
    3. payload.equivalent is true and A' ~ B' (supports claimed equivalence verdict)
    """
    if fsm_a.fsm_type != FSMType.DFA or fsm_b.fsm_type != FSMType.DFA:
        return VerifyResult.fail("minimized_dfa_witness verification requires DFA inputs")
    if fsm_a.input_alphabet != fsm_b.input_alphabet:
        return VerifyResult.fail("DFA alphabets must match")
    if certificate.get("certificate_type") != "minimized_dfa_witness":
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

    minimized_a, err_a = _parse_machine("minimized_a", payload.get("minimized_a"))
    if err_a:
        return VerifyResult.fail(err_a)
    minimized_b, err_b = _parse_machine("minimized_b", payload.get("minimized_b"))
    if err_b:
        return VerifyResult.fail(err_b)
    assert minimized_a is not None and minimized_b is not None

    if minimized_a.input_alphabet != fsm_a.input_alphabet:
        return VerifyResult.fail("minimized_a alphabet mismatch")
    if minimized_b.input_alphabet != fsm_b.input_alphabet:
        return VerifyResult.fail("minimized_b alphabet mismatch")

    try:
        if not are_equivalent_dfas(minimized_a, fsm_a):
            return VerifyResult.fail("behavioral equivalence failed for minimized_a")
        if not are_equivalent_dfas(minimized_b, fsm_b):
            return VerifyResult.fail("behavioral equivalence failed for minimized_b")
    except ValueError as exc:
        return VerifyResult.fail(str(exc))

    if not is_minimal_dfa(minimized_a):
        return VerifyResult.fail("minimization requirement failed for minimized_a")
    if not is_minimal_dfa(minimized_b):
        return VerifyResult.fail("minimization requirement failed for minimized_b")

    if not are_equivalent_dfas(minimized_a, minimized_b):
        return VerifyResult.fail("behavioral equivalence failed between minimized_a and minimized_b")

    # Underlying originals must themselves be equivalent for a true equivalence witness.
    if not are_equivalent_dfas(fsm_a, fsm_b):
        return VerifyResult.fail("behavioral equivalence failed for original machines")

    return VerifyResult.ok()
