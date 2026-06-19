"""Tests for reference oracle: simulation and reachability."""

import pytest

from fsmreasonbench.models.fsm import ExecutableFSM, FSMType, Transition
from fsmreasonbench.oracle.simulation import SimulationError
from fsmreasonbench.oracle.reachability import (
    is_reachable,
    reachable_states,
    shortest_reachability_witness,
    unreachability_witness,
)
from fsmreasonbench.oracle.simulation import simulate


def _line_dfa() -> ExecutableFSM:
    return ExecutableFSM(
        fsm_id="550e8400-e29b-41d4-a716-446655440010",
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


def _nfa_fork() -> ExecutableFSM:
    return ExecutableFSM(
        fsm_id="550e8400-e29b-41d4-a716-446655440011",
        fsm_type=FSMType.NFA,
        states=("q0", "q1", "q2"),
        initial_state="q0",
        input_alphabet=("a",),
        transitions=(
            Transition("q0", "a", "q1"),
            Transition("q0", "a", "q2"),
        ),
        accepting_states=("q2",),
    )


def test_simulate_dfa_trace() -> None:
    fsm = _line_dfa()
    result = simulate(fsm, ("a", "b"))
    assert result.state_sequence == ("q0", "q1", "q2")


def test_simulate_undefined_transition_raises() -> None:
    fsm = _line_dfa()
    with pytest.raises(SimulationError):
        simulate(fsm, ("b",))


def test_nfa_requires_branch_choices() -> None:
    fsm = _nfa_fork()
    with pytest.raises(SimulationError, match="branch_choices"):
        simulate(fsm, ("a",))


def test_nfa_simulation_with_branch_choice() -> None:
    fsm = _nfa_fork()
    result = simulate(fsm, ("a",), branch_choices=(1,))
    assert result.state_sequence == ("q0", "q2")


def test_reachability_and_shortest_path() -> None:
    fsm = _line_dfa()
    assert is_reachable(fsm, "q2")
    witness = shortest_reachability_witness(fsm, "q2")
    assert witness is not None
    assert witness.trace == ("a", "b")
    assert witness.state_sequence == ("q0", "q1", "q2")
    assert reachable_states(fsm) == frozenset({"q0", "q1", "q2"})


def test_unreachable_target() -> None:
    fsm = ExecutableFSM(
        fsm_id="550e8400-e29b-41d4-a716-446655440012",
        fsm_type=FSMType.DFA,
        states=("q0", "q1", "q2"),
        initial_state="q0",
        input_alphabet=("a",),
        transitions=(Transition("q0", "a", "q1"),),
        accepting_states=("q1",),
    )
    assert not is_reachable(fsm, "q2")
    assert shortest_reachability_witness(fsm, "q2") is None
    witness = unreachability_witness(fsm, "q2")
    assert "q2" not in witness.reachable_states
    assert witness.reachable_states == ("q0", "q1")
