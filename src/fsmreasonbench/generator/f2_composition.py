"""Seeded F2 non-materialized composition generator (first vertical slice)."""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass

from fsmreasonbench.generator.reachability import ReachabilityGeneratorConfig, generate_reachability_fsm
from fsmreasonbench.items.assembly import BenchmarkItem, assemble_composition_item, self_verify_item
from fsmreasonbench.oracle.composition import all_product_states, shortest_violation_witness
from fsmreasonbench.runtime.composition import synchronized_alphabet


@dataclass(frozen=True, slots=True)
class CompositionGeneratorConfig:
    """Generator parameters for F2 composition items."""

    state_count_a: int = 3
    state_count_b: int = 3
    alphabet_size: int = 2
    transition_density: float = 0.75
    min_violation_trace_length: int = 1
    max_violation_trace_length: int = 6
    max_generation_attempts: int = 64
    counterexample_only: bool = True

    def __post_init__(self) -> None:
        if self.state_count_a < 2 or self.state_count_b < 2:
            raise ValueError("state counts must be >= 2")
        if self.alphabet_size < 1:
            raise ValueError("alphabet_size must be >= 1")
        if not 0.0 <= self.transition_density <= 1.0:
            raise ValueError("transition_density must be in [0, 1]")
        if self.min_violation_trace_length < 0:
            raise ValueError("min_violation_trace_length must be >= 0")
        if self.max_violation_trace_length < self.min_violation_trace_length:
            raise ValueError("max_violation_trace_length must be >= min_violation_trace_length")
        if self.max_generation_attempts < 1:
            raise ValueError("max_generation_attempts must be >= 1")


def generate_component_fsm(seed: int, config: CompositionGeneratorConfig, *, label: str) -> object:
    reach_cfg = ReachabilityGeneratorConfig(
        state_count=config.state_count_a if label == "A" else config.state_count_b,
        alphabet_size=config.alphabet_size,
        transition_density=config.transition_density,
        min_witness_length=0,
        max_witness_length=config.max_violation_trace_length,
        include_negative=False,
        max_generation_attempts=config.max_generation_attempts,
    )
    fsm = generate_reachability_fsm(seed, reach_cfg)
    return fsm


def generate_composition_item(
    seed: int,
    config: CompositionGeneratorConfig | None = None,
) -> BenchmarkItem:
    """
    Generate a self-verifying F2 counterexample item.

    First slice: ``counterexample_only=True`` emits only ``verdict=false`` items with
    ``projected_trace_witness`` certificates.
    """
    config = config or CompositionGeneratorConfig()
    rng = random.Random(seed)

    for attempt in range(config.max_generation_attempts):
        attempt_seed = seed + attempt * 9973
        fsm_a = generate_component_fsm(attempt_seed, config, label="A")
        fsm_b = generate_component_fsm(attempt_seed + 1, config, label="B")
        sync = synchronized_alphabet(fsm_a, fsm_b)
        if not sync:
            continue

        products = all_product_states(fsm_a, fsm_b)
        if len(products) < 2:
            continue
        forbidden = rng.choice(products)
        safe = set(products) - {forbidden}

        question = {
            "family": "F2",
            "prompt_id": "composition.safety.v1",
            "fsm_a_id": fsm_a.fsm_id,
            "fsm_b_id": fsm_b.fsm_id,
            "secondary_fsm_id": fsm_b.fsm_id,
            "composition_spec": {
                "operator": "synchronous_product",
                "version": "1.0",
                "synchronized_alphabet": list(sync),
            },
            "property": {
                "kind": "safety",
                "invariant": {
                    "type": "state_set",
                    "satisfying_states": sorted(safe),
                },
            },
        }

        witness = shortest_violation_witness(fsm_a, fsm_b, question)
        if witness is None:
            continue
        trace_len = len(witness.synchronized_trace)
        if not (
            config.min_violation_trace_length
            <= trace_len
            <= config.max_violation_trace_length
        ):
            continue

        item = assemble_composition_item(
            fsm_a,
            fsm_b,
            question=question,
            witness=witness,
            seed=attempt_seed,
        )
        self_verify_item(item)
        return item

    raise RuntimeError(
        f"failed to generate F2 composition item for seed={seed} "
        f"after {config.max_generation_attempts} attempts"
    )
