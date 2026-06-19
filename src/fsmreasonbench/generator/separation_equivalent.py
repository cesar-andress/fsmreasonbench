"""Behavior-preserving DFA transformations for F1 equivalent pairs."""

from __future__ import annotations

import random
import uuid

from fsmreasonbench.models.fsm import ExecutableFSM, FSMType, Transition


def generate_equivalent_partner(fsm_a: ExecutableFSM, seed: int) -> ExecutableFSM:
    """Build DFA B as a behavior-preserving transformation of A."""
    rng = random.Random(seed)
    transform = rng.choice(("rename", "unreachable", "duplicate_sink"))
    if transform == "rename":
        return _rename_states(fsm_a, seed=seed + 11)
    if transform == "unreachable":
        return _inject_unreachable_states(fsm_a, seed=seed + 23)
    return _duplicate_equivalent_sink(fsm_a, seed=seed + 37)


def _rename_states(fsm_a: ExecutableFSM, *, seed: int) -> ExecutableFSM:
    rng = random.Random(seed)
    prefix = rng.choice(("beta", "prime", "alt"))
    mapping = {state: f"{prefix}_{state}" for state in fsm_a.states}
    transitions = tuple(
        Transition(
            from_state=mapping[transition.from_state],
            input_symbol=transition.input_symbol,
            to_state=mapping[transition.to_state],
        )
        for transition in fsm_a.transitions
    )
    return _clone_with(
        fsm_a,
        seed=seed,
        label="B",
        states=tuple(mapping[state] for state in fsm_a.states),
        initial_state=mapping[fsm_a.initial_state],
        transitions=transitions,
        accepting_states=tuple(mapping[state] for state in fsm_a.accepting_states),
        metadata={
            **fsm_a.metadata,
            "equivalent_transform": "rename",
        },
    )


def _inject_unreachable_states(fsm_a: ExecutableFSM, *, seed: int) -> ExecutableFSM:
    rng = random.Random(seed)
    extra_count = rng.randint(1, 2)
    extra_states = tuple(f"unreach_{index}" for index in range(extra_count))
    states = fsm_a.states + extra_states
    transitions = list(fsm_a.transitions)
    for state in extra_states:
        for symbol in fsm_a.input_alphabet:
            transitions.append(
                Transition(
                    from_state=state,
                    input_symbol=symbol,
                    to_state=rng.choice(extra_states),
                )
            )
    return _clone_with(
        fsm_a,
        seed=seed,
        label="B",
        states=states,
        transitions=tuple(transitions),
        metadata={
            **fsm_a.metadata,
            "equivalent_transform": "unreachable",
        },
    )


def _duplicate_equivalent_sink(fsm_a: ExecutableFSM, *, seed: int) -> ExecutableFSM:
    rng = random.Random(seed)
    sink_state = _pick_sink_state(fsm_a) or fsm_a.initial_state
    duplicate = f"{sink_state}_mirror"
    gate = "gate_mirror"
    states = fsm_a.states + (duplicate, gate)
    transitions = list(fsm_a.transitions)
    for symbol in fsm_a.input_alphabet:
        transitions.append(
            Transition(from_state=duplicate, input_symbol=symbol, to_state=duplicate)
        )
        transitions.append(
            Transition(from_state=gate, input_symbol=symbol, to_state=duplicate)
        )
    accepting = fsm_a.accepting_states
    if sink_state in accepting:
        accepting = accepting + (duplicate,)
    return _clone_with(
        fsm_a,
        seed=seed,
        label="B",
        states=states,
        transitions=tuple(transitions),
        accepting_states=accepting,
        metadata={
            **fsm_a.metadata,
            "equivalent_transform": "duplicate_sink",
        },
    )


def _pick_sink_state(fsm: ExecutableFSM) -> str | None:
    for state in fsm.states:
        outgoing = [transition for transition in fsm.transitions if transition.from_state == state]
        if outgoing and all(transition.to_state == state for transition in outgoing):
            return state
    return None


def _clone_with(
    fsm_a: ExecutableFSM,
    *,
    seed: int,
    label: str,
    states: tuple[str, ...],
    transitions: tuple[Transition, ...],
    initial_state: str | None = None,
    accepting_states: tuple[str, ...] | None = None,
    metadata: dict[str, object],
) -> ExecutableFSM:
    return ExecutableFSM(
        fsm_id=str(
            uuid.uuid5(uuid.NAMESPACE_URL, f"fsmreasonbench:separation:{label}:{seed}")
        ),
        fsm_type=FSMType.DFA,
        states=states,
        initial_state=initial_state or fsm_a.initial_state,
        input_alphabet=fsm_a.input_alphabet,
        transitions=transitions,
        accepting_states=accepting_states if accepting_states is not None else fsm_a.accepting_states,
        metadata=metadata,
    )
