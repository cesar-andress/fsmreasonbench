"""Reachability certificate verification (C2 / trace_witness / unreachability_witness)."""

from __future__ import annotations

from typing import Any

from fsmreasonbench.models.fsm import ExecutableFSM
from fsmreasonbench.runtime.reachability import reachable_states
from fsmreasonbench.runtime.simulation import simulate
from fsmreasonbench.verifier.result import VerifyResult


def verify_reachability_certificate(
    fsm: ExecutableFSM,
    target_state: str,
    certificate: dict[str, Any],
) -> VerifyResult:
    """
    Verify a reachability certificate independently of the oracle.

    Accepts certificate types:
    - trace_witness (positive)
    - unreachability_witness (negative)
    """
    cert_type = certificate.get("certificate_type")
    if cert_type not in {"trace_witness", "unreachability_witness"}:
        return VerifyResult.fail(f"unsupported certificate_type: {cert_type!r}")

    payload = certificate.get("payload")
    if not isinstance(payload, dict):
        return VerifyResult.fail("certificate payload must be an object")

    if cert_type == "trace_witness":
        return _verify_trace_witness(fsm, target_state, payload)
    return _verify_unreachability_witness(fsm, target_state, payload)


def _verify_trace_witness(
    fsm: ExecutableFSM,
    target_state: str,
    payload: dict[str, Any],
) -> VerifyResult:
    trace = payload.get("trace")
    state_sequence = payload.get("state_sequence")
    if not isinstance(trace, list) or not isinstance(state_sequence, list):
        return VerifyResult.fail("trace and state_sequence must be arrays")
    if not all(isinstance(symbol, str) for symbol in trace):
        return VerifyResult.fail("trace symbols must be strings")
    if not all(isinstance(state, str) for state in state_sequence):
        return VerifyResult.fail("state_sequence entries must be strings")
    if len(state_sequence) != len(trace) + 1:
        return VerifyResult.fail(
            f"state_sequence length must be len(trace)+1, got {len(state_sequence)} vs {len(trace)}"
        )
    if state_sequence[0] != fsm.initial_state:
        return VerifyResult.fail(
            f"state_sequence must start at initial state {fsm.initial_state!r}"
        )
    if state_sequence[-1] != target_state:
        return VerifyResult.fail(
            f"state_sequence must end at target {target_state!r}, got {state_sequence[-1]!r}"
        )

    branch_choices = payload.get("branching_choices")
    if branch_choices is not None:
        if not isinstance(branch_choices, list):
            return VerifyResult.fail("branching_choices must be an array when present")
        try:
            choices = tuple(int(value) for value in branch_choices)
        except (TypeError, ValueError):
            return VerifyResult.fail("branching_choices must contain integers")
    else:
        choices = None

    try:
        simulation = simulate(fsm, trace, branch_choices=choices)
    except Exception as exc:  # noqa: BLE001 — verifier returns structured failure
        return VerifyResult.fail(f"simulation failed: {exc}")

    if simulation.state_sequence != tuple(state_sequence):
        return VerifyResult.fail(
            "state_sequence does not match replay: "
            f"expected {simulation.state_sequence}, got {tuple(state_sequence)}"
        )
    return VerifyResult.ok()


def _verify_unreachability_witness(
    fsm: ExecutableFSM,
    target_state: str,
    payload: dict[str, Any],
) -> VerifyResult:
    reachable = payload.get("reachable_states")
    declared_target = payload.get("target_state")
    if not isinstance(reachable, list):
        return VerifyResult.fail("reachable_states must be an array")
    if not all(isinstance(state, str) for state in reachable):
        return VerifyResult.fail("reachable_states entries must be strings")
    if declared_target != target_state:
        return VerifyResult.fail(
            f"target_state mismatch: expected {target_state!r}, got {declared_target!r}"
        )
    if target_state in reachable:
        return VerifyResult.fail(f"target {target_state!r} listed as reachable")

    computed = reachable_states(fsm)
    witness_set = frozenset(reachable)
    if witness_set != computed:
        missing = sorted(computed - witness_set)
        extra = sorted(witness_set - computed)
        errors: list[str] = []
        if missing:
            errors.append(f"missing reachable states: {missing}")
        if extra:
            errors.append(f"extra non-reachable states: {extra}")
        return VerifyResult.fail(*errors)
    return VerifyResult.ok()
