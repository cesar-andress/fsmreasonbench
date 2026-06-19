"""Seeded F1 DFA separation generator (equivalent and non-equivalent pairs)."""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass
from typing import Literal

from fsmreasonbench.generator.separation_constructive import (
    construct_separation_decoy_dfa_pair,
    construct_separation_dfa_pair,
)
from fsmreasonbench.generator.separation_equivalent import generate_equivalent_partner
from fsmreasonbench.items.assembly import BenchmarkItem, assemble_separation_item, self_verify_item
from fsmreasonbench.models.fsm import ExecutableFSM, FSMType, Transition
from fsmreasonbench.oracle.separation import are_equivalent, shortest_distinguishing_trace

SeparationGeneratorMode = Literal["constructive", "constructive_decoy", "random"]


def resolve_separation_mode(config: SeparationGeneratorConfig) -> SeparationGeneratorMode:
    """Return effective generator mode (constructive_decoy default when min length >= 3)."""
    if config.mode in ("constructive", "constructive_decoy", "random"):
        return config.mode
    if config.min_distinguishing_trace_length >= 3:
        return "constructive_decoy"
    return "random"


def resolve_target_distinguishing_length(
    seed: int,
    config: SeparationGeneratorConfig,
) -> int:
    """Pick the target distinguishing trace length for constructive generation."""
    if config.target_distinguishing_trace_length is not None:
        target = config.target_distinguishing_trace_length
    elif config.min_distinguishing_trace_length == config.max_distinguishing_trace_length:
        target = config.min_distinguishing_trace_length
    else:
        rng = random.Random(seed)
        target = rng.randint(
            config.min_distinguishing_trace_length,
            config.max_distinguishing_trace_length,
        )

    if not (
        config.min_distinguishing_trace_length
        <= target
        <= config.max_distinguishing_trace_length
    ):
        raise ValueError(
            "target distinguishing trace length "
            f"{target} outside [{config.min_distinguishing_trace_length}, "
            f"{config.max_distinguishing_trace_length}]"
        )
    return target


@dataclass(frozen=True, slots=True)
class SeparationGeneratorConfig:
    """Generator parameters for F1 DFA non-equivalence items."""

    state_count_a: int = 4
    state_count_b: int = 4
    alphabet_size: int = 3
    transition_density: float = 0.6
    mode: SeparationGeneratorMode | None = None
    target_distinguishing_trace_length: int | None = None
    min_distinguishing_trace_length: int = 2
    max_distinguishing_trace_length: int = 12
    max_retries: int = 64
    include_equivalent: bool = False
    equivalent_ratio: float = 0.5

    def __post_init__(self) -> None:
        if self.state_count_a < 2 or self.state_count_b < 2:
            raise ValueError("state counts must be >= 2")
        if self.alphabet_size < 1:
            raise ValueError("alphabet_size must be >= 1")
        if not 0.0 <= self.transition_density <= 1.0:
            raise ValueError("transition_density must be in [0, 1]")
        if self.mode is not None and self.mode not in (
            "constructive",
            "constructive_decoy",
            "random",
        ):
            raise ValueError(
                "mode must be 'constructive', 'constructive_decoy', 'random', or None for auto"
            )
        if self.min_distinguishing_trace_length < 0:
            raise ValueError("min_distinguishing_trace_length must be >= 0")
        if self.max_distinguishing_trace_length < self.min_distinguishing_trace_length:
            raise ValueError(
                "max_distinguishing_trace_length must be >= min_distinguishing_trace_length"
            )
        if self.target_distinguishing_trace_length is not None and not (
            self.min_distinguishing_trace_length
            <= self.target_distinguishing_trace_length
            <= self.max_distinguishing_trace_length
        ):
            raise ValueError(
                "target_distinguishing_trace_length must lie within "
                "[min_distinguishing_trace_length, max_distinguishing_trace_length]"
            )
        if self.max_retries < 1:
            raise ValueError("max_retries must be >= 1")
        if not 0.0 <= self.equivalent_ratio <= 1.0:
            raise ValueError("equivalent_ratio must be in [0, 1]")


def separation_config_for_level(level: int) -> SeparationGeneratorConfig:
    """Capability-surface F1 config with mixed equivalent/non-equivalent pairs."""
    return SeparationGeneratorConfig(
        min_distinguishing_trace_length=level,
        max_distinguishing_trace_length=level,
        target_distinguishing_trace_length=level,
        mode="constructive_decoy" if level >= 3 else None,
        include_equivalent=True,
        equivalent_ratio=0.5,
    )


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
    """Generate a self-verifying F1 separation item (equivalent or non-equivalent)."""
    config = config or SeparationGeneratorConfig()
    if _should_generate_equivalent(seed, config):
        return _generate_equivalent_separation_item(seed, config)
    mode = resolve_separation_mode(config)
    if mode in ("constructive", "constructive_decoy"):
        return _generate_constructive_separation_item(seed, config, mode=mode)
    return _generate_random_separation_item(seed, config)


def _should_generate_equivalent(seed: int, config: SeparationGeneratorConfig) -> bool:
    if not config.include_equivalent or config.equivalent_ratio <= 0.0:
        return False
    if config.equivalent_ratio >= 1.0:
        return True
    rng = random.Random(seed + 7919)
    return rng.random() < config.equivalent_ratio


def _generate_equivalent_separation_item(
    seed: int,
    config: SeparationGeneratorConfig,
) -> BenchmarkItem:
    from fsmreasonbench.runtime.dfa_minimize import complete_dfa

    fsm_a = complete_dfa(
        generate_separation_dfa(
            seed,
            config,
            label="A",
            state_count=config.state_count_a,
        )
    )
    fsm_b = generate_equivalent_partner(fsm_a, seed + 1)
    if not are_equivalent(fsm_a, fsm_b):
        raise RuntimeError(f"equivalent generator produced non-equivalent pair for seed={seed}")
    item = assemble_separation_item(fsm_a, fsm_b, seed=seed)
    self_verify_item(item)
    return item


def _generate_constructive_separation_item(
    seed: int,
    config: SeparationGeneratorConfig,
    *,
    mode: Literal["constructive", "constructive_decoy"],
) -> BenchmarkItem:
    target_k = resolve_target_distinguishing_length(seed, config)
    builder = (
        construct_separation_dfa_pair
        if mode == "constructive"
        else construct_separation_decoy_dfa_pair
    )
    fsm_a, fsm_b = builder(
        seed,
        target_k,
        alphabet_size=config.alphabet_size,
    )
    item = assemble_separation_item(fsm_a, fsm_b, seed=seed)
    self_verify_item(item)
    _validate_generated_constraints(item, config)
    return item


def _generate_random_separation_item(
    seed: int,
    config: SeparationGeneratorConfig,
) -> BenchmarkItem:
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
    """Assert generator policy on assembled non-equivalent F1 item."""
    if item.answer_key["verdict"] is True:
        return
    witness = shortest_distinguishing_trace(item.fsm_a, item.fsm_b)
    if witness is None:
        raise AssertionError("non-equivalent pair must have a distinguishing trace")

    trace_length = len(witness.trace)
    recorded = item.difficulty["core"]["distinguishing_trace_length"]
    if trace_length != recorded:
        raise AssertionError(
            f"distinguishing_trace_length metadata mismatch: {recorded} vs {trace_length}"
        )
    if config.target_distinguishing_trace_length is not None:
        if trace_length != config.target_distinguishing_trace_length:
            raise AssertionError(
                "distinguishing trace length does not match target: "
                f"{trace_length} != {config.target_distinguishing_trace_length}"
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
