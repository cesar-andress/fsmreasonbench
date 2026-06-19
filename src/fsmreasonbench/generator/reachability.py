"""Seeded reachability benchmark instance generator (C2 vertical slice)."""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass

from fsmreasonbench.items.assembly import BenchmarkItem, assemble_reachability_item, self_verify_item
from fsmreasonbench.models.fsm import ExecutableFSM, FSMType, Transition
from fsmreasonbench.oracle.reachability import shortest_reachability_witness


@dataclass(frozen=True, slots=True)
class ReachabilityGeneratorConfig:
    """Generator parameters for C2 reachability items."""

    state_count: int = 5
    alphabet_size: int = 3
    transition_density: float = 0.6
    fsm_type: FSMType = FSMType.DFA
    min_witness_length: int = 1
    max_witness_length: int = 12
    allow_initial_target: bool = False
    include_negative: bool = True
    max_generation_attempts: int = 64

    def __post_init__(self) -> None:
        if self.state_count < 2:
            raise ValueError("state_count must be >= 2")
        if self.alphabet_size < 1:
            raise ValueError("alphabet_size must be >= 1")
        if not 0.0 <= self.transition_density <= 1.0:
            raise ValueError("transition_density must be in [0, 1]")
        if self.min_witness_length < 0:
            raise ValueError("min_witness_length must be >= 0")
        if self.max_witness_length < self.min_witness_length:
            raise ValueError("max_witness_length must be >= min_witness_length")
        if self.max_generation_attempts < 1:
            raise ValueError("max_generation_attempts must be >= 1")


def generate_reachability_fsm(
    seed: int,
    config: ReachabilityGeneratorConfig | None = None,
) -> ExecutableFSM:
    """Deterministic random FSM from seed."""
    config = config or ReachabilityGeneratorConfig()
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


def classify_reachability_targets(
    fsm: ExecutableFSM,
    config: ReachabilityGeneratorConfig,
) -> tuple[list[str], list[str]]:
    """
    Partition states into positive and negative candidate targets.

    Positive: reachable with witness length in [min, max], respecting allow_initial_target.
    Negative: unreachable from initial state.
    """
    positive: list[str] = []
    negative: list[str] = []

    for state in fsm.states:
        witness = shortest_reachability_witness(fsm, state)
        if witness is None:
            negative.append(state)
            continue

        witness_length = len(witness.trace)
        if state == fsm.initial_state:
            if not config.allow_initial_target or witness_length != 0:
                continue
            positive.append(state)
            continue

        if config.min_witness_length <= witness_length <= config.max_witness_length:
            positive.append(state)

    return positive, negative


def pick_reachability_target(
    seed: int,
    fsm: ExecutableFSM,
    config: ReachabilityGeneratorConfig,
    *,
    force_positive: bool | None = None,
) -> tuple[str, bool]:
    """
    Pick a target state and verdict polarity satisfying generator constraints.

    Returns (target_state, verdict) where verdict True means reachable.
    """
    positive, negative = classify_reachability_targets(fsm, config)
    rng = random.Random(seed + 1)

    want_positive = rng.choice((True, False)) if force_positive is None else force_positive
    if config.include_negative and not want_positive and negative:
        return rng.choice(negative), False
    if positive:
        return rng.choice(positive), True
    if config.include_negative and negative:
        return rng.choice(negative), False

    raise ValueError("no target satisfies reachability generator constraints")


def generate_reachability_item(
    seed: int,
    config: ReachabilityGeneratorConfig | None = None,
    *,
    force_positive: bool | None = None,
) -> BenchmarkItem:
    """
    Generate a self-verifying C2 reachability item.

    Retries FSM generation with perturbed seeds when constraints cannot be met.
    """
    config = config or ReachabilityGeneratorConfig()

    for attempt in range(config.max_generation_attempts):
        fsm_seed = seed if attempt == 0 else seed + attempt * 9973
        fsm = generate_reachability_fsm(fsm_seed, config)
        try:
            target, _verdict = pick_reachability_target(
                seed + attempt,
                fsm,
                config,
                force_positive=force_positive,
            )
        except ValueError:
            continue

        item = assemble_reachability_item(fsm, target, seed=seed + attempt)
        try:
            self_verify_item(item)
            _validate_generated_constraints(item, config)
        except AssertionError:
            continue
        return item

    raise RuntimeError(
        f"failed to generate C2 item for seed={seed} after {config.max_generation_attempts} attempts"
    )


def _validate_generated_constraints(item: BenchmarkItem, config: ReachabilityGeneratorConfig) -> None:
    """Assert generator policy on assembled item."""
    target = item.question["target_state"]
    verdict = item.answer_key["verdict"]
    certificate = item.answer_key["certificate"]

    if verdict:
        witness = certificate["payload"]
        trace = witness["trace"]
        witness_length = len(trace)
        if target == item.fsm.initial_state:
            if not config.allow_initial_target:
                raise AssertionError("initial target not allowed")
            if witness_length != 0:
                raise AssertionError("initial target must have empty witness")
        elif witness_length < config.min_witness_length:
            raise AssertionError("witness shorter than min_witness_length")
        if witness_length > config.max_witness_length:
            raise AssertionError("witness longer than max_witness_length")
    else:
        if certificate["certificate_type"] != "unreachability_witness":
            raise AssertionError("negative item must use unreachability_witness")


def pick_target_state(seed: int, fsm: ExecutableFSM) -> str:
    """Backward-compatible target picker using default generator config."""
    target, _verdict = pick_reachability_target(seed, fsm, ReachabilityGeneratorConfig())
    return target
