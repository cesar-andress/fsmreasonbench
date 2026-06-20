"""F2 composition certificate verification (no submitted product materialization)."""

from __future__ import annotations

from typing import Any

from fsmreasonbench.models.fsm import ExecutableFSM, FSMType
from fsmreasonbench.runtime.composition import (
    product_state_sequence,
    replay_projected_traces,
)
from fsmreasonbench.runtime.simulation import simulate
from fsmreasonbench.verifier.result import VerifyResult

_FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {
        "product_states",
        "product_transitions",
        "full_product",
        "product_graph",
        "transition_table",
    }
)


def check_materialization_violation(payload: dict[str, Any]) -> tuple[str, ...]:
    """Return errors if payload contains forbidden product materialization."""
    errors: list[str] = []

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                full = f"{path}.{key}" if path else key
                if key in _FORBIDDEN_PAYLOAD_KEYS:
                    errors.append(f"materialization forbidden key: {full}")
                walk(nested, full)
        elif isinstance(value, list) and path.endswith("product_states"):
            errors.append(f"materialization forbidden array: {path}")

    walk(payload, "payload")
    return tuple(errors)


def verify_f2_certificate(
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
    question: dict[str, Any],
    certificate: dict[str, Any],
) -> VerifyResult:
    cert_type = certificate.get("certificate_type")
    if cert_type == "projected_trace_witness":
        return verify_projected_trace_witness_certificate(
            fsm_a,
            fsm_b,
            question,
            certificate,
        )
    return VerifyResult.fail(f"unsupported certificate_type: {cert_type!r}")


def verify_projected_trace_witness_certificate(
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
    question: dict[str, Any],
    certificate: dict[str, Any],
) -> VerifyResult:
    if fsm_a.fsm_type != FSMType.DFA or fsm_b.fsm_type != FSMType.DFA:
        return VerifyResult.fail("projected_trace_witness requires DFA inputs")

    cert_type = certificate.get("certificate_type")
    if cert_type != "projected_trace_witness":
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

    mat_errors = check_materialization_violation({"payload": payload})
    if mat_errors:
        return VerifyResult.fail(*mat_errors)

    required = (
        "component_trace_A",
        "component_trace_B",
        "synchronized_trace",
        "projected_states_A",
        "projected_states_B",
        "property_evaluation",
    )
    for field in required:
        if field not in payload:
            return VerifyResult.fail(f"payload missing required field: {field}")

    trace_a = payload["component_trace_A"]
    trace_b = payload["component_trace_B"]
    sync = payload["synchronized_trace"]
    states_a = payload["projected_states_A"]
    states_b = payload["projected_states_B"]
    prop_eval = payload["property_evaluation"]

    for name, value in (
        ("component_trace_A", trace_a),
        ("component_trace_B", trace_b),
        ("synchronized_trace", sync),
    ):
        if not isinstance(value, list) or not all(isinstance(symbol, str) for symbol in value):
            return VerifyResult.fail(f"payload.{name} must be an array of strings")

    for name, value in (("projected_states_A", states_a), ("projected_states_B", states_b)):
        if not isinstance(value, list) or not all(isinstance(state, str) for state in value):
            return VerifyResult.fail(f"payload.{name} must be an array of strings")

    if not isinstance(prop_eval, dict):
        return VerifyResult.fail("payload.property_evaluation must be an object")

    if len(states_a) != len(trace_a) + 1 or len(states_b) != len(trace_b) + 1:
        return VerifyResult.fail("projected state sequences must have length len(trace)+1")

    try:
        replay_a, replay_b = replay_projected_traces(
            fsm_a,
            fsm_b,
            component_trace_a=trace_a,
            component_trace_b=trace_b,
            synchronized_trace=sync,
        )
    except Exception as exc:  # noqa: BLE001
        return VerifyResult.fail(f"synchronization replay failed: {exc}")

    if tuple(states_a) != replay_a:
        return VerifyResult.fail("projected_states_A does not match replay on component A")
    if tuple(states_b) != replay_b:
        return VerifyResult.fail("projected_states_B does not match replay on component B")

    try:
        product_states = product_state_sequence(fsm_a, fsm_b, sync)
    except Exception as exc:  # noqa: BLE001
        return VerifyResult.fail(f"internal product replay failed: {exc}")

    prop = question["property"]
    if prop["kind"] != "safety":
        return VerifyResult.fail("first F2 verifier slice supports safety properties only")
    invariant = prop["invariant"]
    if invariant["type"] != "state_set":
        return VerifyResult.fail("first F2 verifier slice supports state_set invariants only")
    safe_states = set(invariant["satisfying_states"])

    if prop_eval.get("property_kind") != "safety":
        return VerifyResult.fail("property_evaluation.property_kind must be 'safety'")
    if prop_eval.get("satisfied") is not False:
        return VerifyResult.fail("projected_trace_witness requires property_evaluation.satisfied=false")

    step_index = prop_eval.get("violation_step_index")
    if not isinstance(step_index, int) or step_index < 0 or step_index > len(sync):
        return VerifyResult.fail("invalid violation_step_index")

    declared_product = prop_eval.get("product_state_at_violation")
    actual_product = product_states[step_index]
    if declared_product != actual_product:
        return VerifyResult.fail(
            "product_state_at_violation mismatch: "
            f"declared={declared_product!r}, replay={actual_product!r}"
        )
    if actual_product in safe_states:
        return VerifyResult.fail("witness must reach an unsafe product state")

    _ = simulate(fsm_a, trace_a)
    _ = simulate(fsm_b, trace_b)
    return VerifyResult.ok()
