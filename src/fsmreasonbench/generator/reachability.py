"""Seeded reachability benchmark instance generator (C2 vertical slice)."""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass

from fsmreasonbench.models.fsm import ExecutableFSM, FSMType, Transition


@dataclass(frozen=True, slots=True)
class ReachabilityGeneratorConfig:
    """Generator parameters; difficulty controlled by state_count only (Phase 2)."""

    state_count: int = 5
    alphabet_size: int = 3
    transition_density: float = 0.6
    fsm_type: FSMType = FSMType.DFA


def generate_reachability_fsm(
    seed: int,
    config: ReachabilityGeneratorConfig | None = None,
) -> ExecutableFSM:
    """
    Deterministic random FSM from seed.

    Produces a connected-ish automaton with partial transition function allowed.
    """
    config = config or ReachabilityGeneratorConfig()
    if config.state_count < 2:
        raise ValueError("state_count must be >= 2")
    if config.alphabet_size < 1:
        raise ValueError("alphabet_size must be >= 1")
    if not 0.0 <= config.transition_density <= 1.0:
        raise ValueError("transition_density must be in [0, 1]")

    rng = random.Random(seed)
    states = tuple(f"q{index}" for index in range(config.state_count))
    alphabet = tuple(chr(ord("a") + index) for index in range(config.alphabet_size))
    initial_state = states[0]

    transitions: list[Transition] = []
    for state in states:
        for symbol in alphabet:
            if rng.random() <= config.transition_density:
                target = rng.choice(states)
                transitions.append(
                    Transition(from_state=state, input_symbol=symbol, to_state=target)
                )

    # Ensure at least one outgoing edge from initial state for non-degenerate reachability
    if not any(transition.from_state == initial_state for transition in transitions):
        transitions.append(
            Transition(
                from_state=initial_state,
                input_symbol=rng.choice(alphabet),
                to_state=rng.choice(states[1:]),
            )
        )

    accepting = (rng.choice(states),)
    return ExecutableFSM(
        fsm_id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"fsmreasonbench:reachability:{seed}")),
        fsm_type=config.fsm_type,
        states=states,
        initial_state=initial_state,
        input_alphabet=alphabet,
        transitions=tuple(transitions),
        accepting_states=accepting,
        metadata={"generator_seed": seed, "state_count": config.state_count},
    )


def pick_target_state(seed: int, fsm: ExecutableFSM) -> str:
    """Deterministically pick a target state (may be reachable or not)."""
    rng = random.Random(seed + 1)
    return rng.choice(fsm.states)
