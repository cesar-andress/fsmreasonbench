"""Seeded F1 DFA non-equivalence generator."""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass

from fsmreasonbench.items.assembly import BenchmarkItem, assemble_separation_item, self_verify_item
from fsmreasonbench.models.fsm import ExecutableFSM, FSMType, Transition
from fsmreasonbench.oracle.separation import are_equivalent


@dataclass(frozen=True, slots=True)
class SeparationGeneratorConfig:
    """Generator parameters for F1 DFA non-equivalence items."""

    state_count_a: int = 4
    state_count_b: int = 4
    alphabet_size: int = 3
    transition_density: float = 0.6
    max_generation_attempts: int = 64

    def __post_init__(self) -> None:
        if self.state_count_a < 2 or self.state_count_b < 2:
            raise ValueError("state counts must be >= 2")
        if self.alphabet_size < 1:
            raise ValueError("alphabet_size must be >= 1")
        if not 0.0 <= self.transition_density <= 1.0:
            raise ValueError("transition_density must be in [0, 1]")
        if self.max_generation_attempts < 1:
            raise ValueError("max_generation_attempts must be >= 1")


def generate_separation_dfa(
    seed: int,
    config: SeparationGeneratorConfig,
    *,
    label: str,
    state_count: int,
) -> ExecutableFSM:
    """Deterministic random DFA for F1 generation."""
    rng = random.Random(seed)
    states = tuple(f"q{index}" for index in range(state_count))
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
        fsm_id=str(
            uuid.uuid5(uuid.NAMESPACE_URL, f"fsmreasonbench:separation:{label}:{seed}")
        ),
        fsm_type=FSMType.DFA,
        states=states,
        initial_state=initial_state,
        input_alphabet=alphabet,
        transitions=tuple(transitions),
        accepting_states=accepting,
        metadata={
            "generator_seed": seed,
            "state_count": state_count,
            "label": label,
        },
    )


def generate_separation_item(
    seed: int,
    config: SeparationGeneratorConfig | None = None,
) -> BenchmarkItem:
    """Generate a self-verifying F1 non-equivalence item."""
    config = config or SeparationGeneratorConfig()

    for attempt in range(config.max_generation_attempts):
        attempt_seed = seed if attempt == 0 else seed + attempt * 9973
        fsm_a = generate_separation_dfa(
            attempt_seed,
            config,
            label="A",
            state_count=config.state_count_a,
        )
        fsm_b = generate_separation_dfa(
            attempt_seed + 1,
            config,
            label="B",
            state_count=config.state_count_b,
        )
        if are_equivalent(fsm_a, fsm_b):
            continue

        item = assemble_separation_item(fsm_a, fsm_b, seed=attempt_seed)
        try:
            self_verify_item(item)
        except AssertionError:
            continue
        return item

    raise RuntimeError(
        f"failed to generate F1 item for seed={seed} after {config.max_generation_attempts} attempts"
    )
