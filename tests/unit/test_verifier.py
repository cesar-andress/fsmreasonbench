"""Tests for reachability certificate verifier."""

from fsmreasonbench.certificates.reachability import build_reachability_certificate
from fsmreasonbench.models.fsm import ExecutableFSM, FSMType, Transition
from fsmreasonbench.verifier.reachability import verify_reachability_certificate


def _line_dfa() -> ExecutableFSM:
    return ExecutableFSM(
        fsm_id="550e8400-e29b-41d4-a716-446655440020",
        fsm_type=FSMType.DFA,
        states=("q0", "q1", "q2"),
        initial_state="q0",
        input_alphabet=("a", "b"),
        transitions=(
            Transition("q0", "a", "q1"),
            Transition("q1", "b", "q2"),
        ),
        accepting_states=("q2",),
    )


def test_verifier_accepts_oracle_certificate_reachable() -> None:
    fsm = _line_dfa()
    certificate = build_reachability_certificate(fsm, "q2")
    result = verify_reachability_certificate(fsm, "q2", certificate)
    assert result.valid, result.errors


def test_verifier_accepts_oracle_certificate_unreachable() -> None:
    fsm = ExecutableFSM(
        fsm_id="550e8400-e29b-41d4-a716-446655440021",
        fsm_type=FSMType.DFA,
        states=("q0", "q1", "q2"),
        initial_state="q0",
        input_alphabet=("a",),
        transitions=(Transition("q0", "a", "q1"),),
        accepting_states=("q1",),
    )
    certificate = build_reachability_certificate(fsm, "q2")
    result = verify_reachability_certificate(fsm, "q2", certificate)
    assert result.valid, result.errors
    assert certificate["certificate_type"] == "unreachability_witness"


def test_verifier_rejects_invalid_state_sequence() -> None:
    fsm = _line_dfa()
    certificate = build_reachability_certificate(fsm, "q2")
    certificate["payload"]["state_sequence"] = ["q0", "q0", "q2"]
    result = verify_reachability_certificate(fsm, "q2", certificate)
    assert not result.valid
    assert any("does not match replay" in error for error in result.errors)


def test_verifier_rejects_incomplete_reachable_set() -> None:
    fsm = ExecutableFSM(
        fsm_id="550e8400-e29b-41d4-a716-446655440022",
        fsm_type=FSMType.DFA,
        states=("q0", "q1", "q2"),
        initial_state="q0",
        input_alphabet=("a",),
        transitions=(Transition("q0", "a", "q1"),),
        accepting_states=("q1",),
    )
    certificate = build_reachability_certificate(fsm, "q2")
    assert certificate["certificate_type"] == "unreachability_witness"
    certificate["payload"]["reachable_states"] = ["q0"]
    result = verify_reachability_certificate(fsm, "q2", certificate)
    assert not result.valid


def test_verifier_rejects_wrong_target_in_trace() -> None:
    fsm = _line_dfa()
    certificate = build_reachability_certificate(fsm, "q2")
    result = verify_reachability_certificate(fsm, "q1", certificate)
    assert not result.valid
