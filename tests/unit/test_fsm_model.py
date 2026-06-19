"""Tests for FSM model and serialization."""

import pytest

from fsmreasonbench.models.fsm import ExecutableFSM, FSMType, Transition
from fsmreasonbench.models.serialization import (
    canonical_json,
    content_hash,
    fsm_content_hash,
    fsm_from_dict,
    fsm_to_dict,
)


def _sample_dfa() -> ExecutableFSM:
    return ExecutableFSM(
        fsm_id="550e8400-e29b-41d4-a716-446655440000",
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


def test_fsm_roundtrip_serialization() -> None:
    fsm = _sample_dfa()
    restored = fsm_from_dict(fsm_to_dict(fsm))
    assert restored == fsm


def test_canonical_hash_stable() -> None:
    fsm = _sample_dfa()
    first = fsm_content_hash(fsm)
    second = fsm_content_hash(fsm_from_dict(fsm_to_dict(fsm)))
    assert first == second
    assert len(first) == 64


def test_canonical_json_sorted_keys() -> None:
    payload = {"b": 1, "a": 2}
    assert canonical_json(payload) == '{"a":2,"b":1}'
    assert content_hash(payload) == content_hash({"a": 2, "b": 1})


def test_dfa_rejects_nondeterministic_transitions() -> None:
    with pytest.raises(ValueError, match="multiple transitions"):
        ExecutableFSM(
            fsm_id="550e8400-e29b-41d4-a716-446655440001",
            fsm_type=FSMType.DFA,
            states=("q0", "q1"),
            initial_state="q0",
            input_alphabet=("a",),
            transitions=(
                Transition("q0", "a", "q0"),
                Transition("q0", "a", "q1"),
            ),
        )
