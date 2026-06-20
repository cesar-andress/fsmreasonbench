"""F2 composition oracle (internal product allowed)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fsmreasonbench.models.fsm import ExecutableFSM
from fsmreasonbench.runtime.composition import (
    ProductState,
    ProjectedTraceWitness,
    initial_product_state,
    shortest_safety_violation_witness,
    synchronized_alphabet,
)


@dataclass(frozen=True, slots=True)
class SafetyPropertySpec:
    kind: str
    safe_product_states: frozenset[str]
    synchronized_alphabet: tuple[str, ...]


def parse_safety_property(
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
    question: dict[str, Any],
) -> SafetyPropertySpec:
    prop = question["property"]
    if prop["kind"] != "safety":
        raise ValueError(f"unsupported property kind for first F2 slice: {prop['kind']!r}")
    composition = question["composition_spec"]
    sync = tuple(composition.get("synchronized_alphabet") or synchronized_alphabet(fsm_a, fsm_b))
    invariant = prop["invariant"]
    if invariant["type"] != "state_set":
        raise ValueError("first F2 slice supports state_set safety invariants only")
    safe = frozenset(invariant["satisfying_states"])
    return SafetyPropertySpec(
        kind="safety",
        safe_product_states=safe,
        synchronized_alphabet=sync,
    )


def property_holds(
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
    question: dict[str, Any],
) -> bool:
    """True when the safety property holds on all reachable product states explored."""
    spec = parse_safety_property(fsm_a, fsm_b, question)
    witness = shortest_safety_violation_witness(
        fsm_a,
        fsm_b,
        safe_product_states=set(spec.safe_product_states),
        sync_alphabet=spec.synchronized_alphabet,
    )
    return witness is None


def shortest_violation_witness(
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
    question: dict[str, Any],
) -> ProjectedTraceWitness | None:
    spec = parse_safety_property(fsm_a, fsm_b, question)
    return shortest_safety_violation_witness(
        fsm_a,
        fsm_b,
        safe_product_states=set(spec.safe_product_states),
        sync_alphabet=spec.synchronized_alphabet,
    )


def all_product_states(fsm_a: ExecutableFSM, fsm_b: ExecutableFSM) -> list[str]:
    return [
        ProductState(a, b).encode()
        for a in fsm_a.states
        for b in fsm_b.states
    ]
