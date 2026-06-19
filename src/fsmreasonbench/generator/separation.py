"""Seeded F1 DFA non-equivalence generator."""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass

from fsmreasonbench.items.assembly import BenchmarkItem, assemble_separation_item, self_verify_item
from fsmreasonbench.models.fsm import ExecutableFSM, FSMType, Transition
from fsmreasonbench.oracle.separation import are_equivalent, shortest_distinguishing_trace


@dataclass(frozen=True, slots=True)
class SeparationGeneratorConfig:
    """Generator parameters for F1 DFA non-equivalence items."""

    state_count_a: int = 4
    state_count_b: int = 4
    alphabet_size: int = 3
    transition_density: float = 0.6
    min_distinguishing_trace_length: int = 2
    max_distinguishing_trace_length: int = 12
    max_retries: int = 64

    def __post_init__(self) -> None:
        if self.state_count_a < 2 or self.state_count_b < 2:
            raise ValueError("state counts must be >= 2")
        if self.alphabet_size < 1:
            raise ValueError("alphabet_size must be >= 1")
        if not 0.0 <= self.transition_density <= 1.0:
            raise ValueError("transition_density must be in [0, 1]")
        if self.min_distinguishing_trace_length < 0:
            raise ValueError("min_distinguishing_trace_length must be >= 0")
        if self.max_distinguishing_trace_length < self.min_distinguishing_trace_length:
            raise ValueError(
                "max_distinguishing_trace_length must be >= min_distinguishing_trace_length"
            )
        if self.max_retries < 1:
            raise ValueError("max_retries must be >= 1")


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

    for attempt in range(config.max_retries):
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
            _validate_generated_constraints(item, config)
        except AssertionError:
            continue
        return item

    raise RuntimeError(
        "failed to generate F1 item for "
        f"seed={seed} with distinguishing_trace_length in "
        f"[{config.min_distinguishing_trace_length}, {config.max_distinguishing_trace_length}] "
        f"after {config.max_retries} retries"
    )


def _validate_generated_constraints(
    item: BenchmarkItem,
    config: SeparationGeneratorConfig,
) -> None:
    """Assert generator policy on assembled F1 item."""
    witness = shortest_distinguishing_trace(item.fsm_a, item.fsm_b)
    if witness is None:
        raise AssertionError("non-equivalent pair must have a distinguishing trace")

    trace_length = len(witness.trace)
    recorded = item.difficulty["core"]["distinguishing_trace_length"]
    if trace_length != recorded:
        raise AssertionError(
            f"distinguishing_trace_length metadata mismatch: {recorded} vs {trace_length}"
        )
    if trace_length < config.min_distinguishing_trace_length:
        raise AssertionError(
            f"distinguishing trace shorter than min_distinguishing_trace_length: "
            f"{trace_length} < {config.min_distinguishing_trace_length}"
        )
    if trace_length > config.max_distinguishing_trace_length:
        raise AssertionError(
            f"distinguishing trace longer than max_distinguishing_trace_length: "
            f"{trace_length} > {config.max_distinguishing_trace_length}"
        )
