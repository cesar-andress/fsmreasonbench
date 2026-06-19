"""F1 separation certificate verification."""

from __future__ import annotations

from typing import Any

from fsmreasonbench.models.fsm import ExecutableFSM, FSMType
from fsmreasonbench.runtime.dfa_minimize import are_equivalent_dfas, minimized_dfa_hash
from fsmreasonbench.runtime.acceptance import accepts_trace
from fsmreasonbench.runtime.simulation import simulate
from fsmreasonbench.verifier.result import VerifyResult


def verify_f1_certificate(
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
    certificate: dict[str, Any],
) -> VerifyResult:
    """Verify an F1 certificate based on its declared type."""
    cert_type = certificate.get("certificate_type")
    if cert_type == "distinguishing_trace":
        return verify_distinguishing_trace_certificate(fsm_a, fsm_b, certificate)
    if cert_type == "equivalence_witness":
        return verify_equivalence_witness_certificate(fsm_a, fsm_b, certificate)
    return VerifyResult.fail(f"unsupported certificate_type: {cert_type!r}")


def verify_distinguishing_trace_certificate(
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
    certificate: dict[str, Any],
) -> VerifyResult:
    """
    Verify a distinguishing-trace certificate independently of the oracle.

    Checks replay on both DFAs, declared acceptance values, and that they differ.
    """
    if fsm_a.fsm_type != FSMType.DFA or fsm_b.fsm_type != FSMType.DFA:
        return VerifyResult.fail("distinguishing_trace verification requires DFA inputs")
    if fsm_a.input_alphabet != fsm_b.input_alphabet:
        return VerifyResult.fail("DFA alphabets must match")

    cert_type = certificate.get("certificate_type")
    if cert_type != "distinguishing_trace":
        return VerifyResult.fail(f"unsupported certificate_type: {cert_type!r}")

    fsm_ids = certificate.get("fsm_ids")
    if not isinstance(fsm_ids, list) or len(fsm_ids) != 2:
        return VerifyResult.fail("fsm_ids must be an array of length 2")
    if fsm_ids != [fsm_a.fsm_id, fsm_b.fsm_id]:
        return VerifyResult.fail(
            f"fsm_ids mismatch: expected {[fsm_a.fsm_id, fsm_b.fsm_id]!r}, got {fsm_ids!r}"
        )

    payload = certificate.get("payload")
    if not isinstance(payload, dict):
        return VerifyResult.fail("certificate payload must be an object")

    trace = payload.get("trace")
    acceptance = payload.get("acceptance")
    if not isinstance(trace, list) or not all(isinstance(symbol, str) for symbol in trace):
        return VerifyResult.fail("payload.trace must be an array of strings")
    if not isinstance(acceptance, dict):
        return VerifyResult.fail("payload.acceptance must be an object")

    for key in ("A", "B"):
        if key not in acceptance or not isinstance(acceptance[key], bool):
            return VerifyResult.fail(f"payload.acceptance.{key} must be boolean")

    try:
        acceptance_a = accepts_trace(fsm_a, trace)
        acceptance_b = accepts_trace(fsm_b, trace)
    except Exception as exc:  # noqa: BLE001
        return VerifyResult.fail(f"trace replay failed: {exc}")

    if acceptance_a != acceptance["A"]:
        return VerifyResult.fail(
            f"acceptance.A mismatch: replay={acceptance_a}, declared={acceptance['A']}"
        )
    if acceptance_b != acceptance["B"]:
        return VerifyResult.fail(
            f"acceptance.B mismatch: replay={acceptance_b}, declared={acceptance['B']}"
        )
    if acceptance_a == acceptance_b:
        return VerifyResult.fail("trace must distinguish A and B (acceptance values equal)")

    # Shortestness is oracle metadata only in this vertical slice.
    _ = simulate(fsm_a, trace)
    return VerifyResult.ok()


def verify_equivalence_witness_certificate(
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
    certificate: dict[str, Any],
) -> VerifyResult:
    """Verify an equivalence witness by recomputing minimization and equivalence."""
    if fsm_a.fsm_type != FSMType.DFA or fsm_b.fsm_type != FSMType.DFA:
        return VerifyResult.fail("equivalence_witness verification requires DFA inputs")
    if fsm_a.input_alphabet != fsm_b.input_alphabet:
        return VerifyResult.fail("DFA alphabets must match")

    cert_type = certificate.get("certificate_type")
    if cert_type != "equivalence_witness":
        return VerifyResult.fail(f"unsupported certificate_type: {cert_type!r}")

    fsm_ids = certificate.get("fsm_ids")
    if not isinstance(fsm_ids, list) or len(fsm_ids) != 2:
        return VerifyResult.fail("fsm_ids must be an array of length 2")
    if fsm_ids != [fsm_a.fsm_id, fsm_b.fsm_id]:
        return VerifyResult.fail(
            f"fsm_ids mismatch: expected {[fsm_a.fsm_id, fsm_b.fsm_id]!r}, got {fsm_ids!r}"
        )

    payload = certificate.get("payload")
    if not isinstance(payload, dict):
        return VerifyResult.fail("certificate payload must be an object")

    equivalent = payload.get("equivalent")
    hash_a = payload.get("minimized_hash_A")
    hash_b = payload.get("minimized_hash_B")
    if equivalent is not True:
        return VerifyResult.fail("payload.equivalent must be true")
    if not isinstance(hash_a, str) or not hash_a:
        return VerifyResult.fail("payload.minimized_hash_A must be a non-empty string")
    if not isinstance(hash_b, str) or not hash_b:
        return VerifyResult.fail("payload.minimized_hash_B must be a non-empty string")

    if not are_equivalent_dfas(fsm_a, fsm_b):
        return VerifyResult.fail("equivalence check reports non-equivalent DFAs")

    try:
        recomputed_a = minimized_dfa_hash(fsm_a)
        recomputed_b = minimized_dfa_hash(fsm_b)
    except Exception as exc:  # noqa: BLE001
        return VerifyResult.fail(f"minimization failed: {exc}")

    if recomputed_a != hash_a:
        return VerifyResult.fail("minimized_hash_A mismatch")
    if recomputed_b != hash_b:
        return VerifyResult.fail("minimized_hash_B mismatch")
    if recomputed_a != recomputed_b:
        return VerifyResult.fail("minimized hashes differ for equivalent DFAs")

    return VerifyResult.ok()
