"""Oracle separation / distinguishing trace tests."""

from fsmreasonbench.models.fsm import FSMType, Transition
from fsmreasonbench.models.serialization import fsm_from_dict, fsm_to_dict
from fsmreasonbench.oracle.separation import (
    are_equivalent,
    check_separation,
    shortest_distinguishing_trace,
)


def _dfa(
    *,
    fsm_id: str,
    states: tuple[str, ...],
    initial: str,
    alphabet: tuple[str, ...],
    transitions: tuple[tuple[str, str, str], ...],
    accepting: tuple[str, ...],
):
    from fsmreasonbench.models.fsm import ExecutableFSM

    return ExecutableFSM(
        fsm_id=fsm_id,
        fsm_type=FSMType.DFA,
        states=states,
        initial_state=initial,
        input_alphabet=alphabet,
        transitions=tuple(
            Transition(from_state=src, input_symbol=symbol, to_state=dst)
            for src, symbol, dst in transitions
        ),
        accepting_states=accepting,
    )


def test_oracle_finds_distinguishing_trace() -> None:
    alphabet = ("a", "b")
    fsm_a = _dfa(
        fsm_id="00000000-0000-4000-8000-000000000001",
        states=("q0", "q1"),
        initial="q0",
        alphabet=alphabet,
        transitions=(("q0", "a", "q1"), ("q0", "b", "q0"), ("q1", "a", "q1"), ("q1", "b", "q1")),
        accepting=("q1",),
    )
    fsm_b = _dfa(
        fsm_id="00000000-0000-4000-8000-000000000002",
        states=("p0", "p1"),
        initial="p0",
        alphabet=alphabet,
        transitions=(("p0", "a", "p0"), ("p0", "b", "p1"), ("p1", "a", "p1"), ("p1", "b", "p1")),
        accepting=("p1",),
    )
    result = check_separation(fsm_a, fsm_b)
    assert result.equivalent is False
    assert result.distinguishing_trace is not None
    assert result.acceptance_a != result.acceptance_b

    witness = shortest_distinguishing_trace(fsm_a, fsm_b)
    assert witness is not None
    assert witness.trace == ("a",)


def test_oracle_reports_equivalent_pair() -> None:
    fsm_a = _dfa(
        fsm_id="00000000-0000-4000-8000-000000000011",
        states=("q0",),
        initial="q0",
        alphabet=("a",),
        transitions=(("q0", "a", "q0"),),
        accepting=("q0",),
    )
    fsm_b = _dfa(
        fsm_id="00000000-0000-4000-8000-000000000012",
        states=("p0",),
        initial="p0",
        alphabet=("a",),
        transitions=(("p0", "a", "p0"),),
        accepting=("p0",),
    )
    assert are_equivalent(fsm_a, fsm_b)
    assert shortest_distinguishing_trace(fsm_a, fsm_b) is None


def test_oracle_roundtrip_through_serialization() -> None:
    from fsmreasonbench.generator.separation import generate_separation_item

    item = generate_separation_item(42)
    loaded_a = fsm_from_dict(fsm_to_dict(item.fsm_a))
    loaded_b = fsm_from_dict(fsm_to_dict(item.fsm_b))
    witness = shortest_distinguishing_trace(loaded_a, loaded_b)
    assert witness is not None
