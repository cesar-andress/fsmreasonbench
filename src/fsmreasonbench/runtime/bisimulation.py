"""Bisimulation relation construction and verification for F1 equivalence witnesses."""

from __future__ import annotations

from collections import deque

from fsmreasonbench.models.fsm import ExecutableFSM
from fsmreasonbench.runtime.dfa_minimize import (
    _acceptance_pair_differs,
    _dfa_successor,
    _optional_dfa_successor,
    are_equivalent_dfas,
    complete_dfa,
)


def compute_bisimulation_pairs(
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
) -> tuple[tuple[str, str], ...]:
    """
    Build a bisimulation relation for equivalent DFAs.

    For language-equivalent DFAs, the synchronized product reachable from
    (q0_A, q0_B) under paired transitions forms a bisimulation witness.
    """
    if not are_equivalent_dfas(fsm_a, fsm_b):
        raise ValueError("cannot build bisimulation witness for non-equivalent DFAs")

    completed_a = complete_dfa(fsm_a)
    completed_b = complete_dfa(fsm_b)
    start = (completed_a.initial_state, completed_b.initial_state)
    visited: set[tuple[str, str]] = {start}
    queue: deque[tuple[str, str]] = deque([start])
    while queue:
        state_a, state_b = queue.popleft()
        for symbol in completed_a.input_alphabet:
            successor = (
                _dfa_successor(completed_a, state_a, symbol),
                _dfa_successor(completed_b, state_b, symbol),
            )
            if successor not in visited:
                visited.add(successor)
                queue.append(successor)
    return tuple(sorted(visited))


def pairs_from_payload(payload: dict) -> set[tuple[str, str]]:
    raw_pairs = payload.get("pairs")
    if not isinstance(raw_pairs, list) or not raw_pairs:
        raise ValueError("payload.pairs must be a non-empty array")
    relation: set[tuple[str, str]] = set()
    for index, entry in enumerate(raw_pairs):
        if not isinstance(entry, dict):
            raise ValueError(f"payload.pairs[{index}] must be an object")
        state_a = entry.get("state_a")
        state_b = entry.get("state_b")
        if not isinstance(state_a, str) or not state_a:
            raise ValueError(f"payload.pairs[{index}].state_a must be a non-empty string")
        if not isinstance(state_b, str) or not state_b:
            raise ValueError(f"payload.pairs[{index}].state_b must be a non-empty string")
        relation.add((state_a, state_b))
    return relation


def verify_bisimulation_relation(
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
    relation: set[tuple[str, str]],
) -> tuple[bool, tuple[str, ...]]:
    """Check that relation is a bisimulation containing the initial pair."""
    errors: list[str] = []
    completed_a = complete_dfa(fsm_a)
    completed_b = complete_dfa(fsm_b)
    initial = (completed_a.initial_state, completed_b.initial_state)

    if not are_equivalent_dfas(fsm_a, fsm_b):
        errors.append("equivalence check reports non-equivalent DFAs")

    if initial not in relation:
        errors.append("initial state pair missing from bisimulation relation")

    for state_a, state_b in relation:
        if state_a not in completed_a.states:
            errors.append(f"unknown state_a in pair: {state_a!r}")
        if state_b not in completed_b.states:
            errors.append(f"unknown state_b in pair: {state_b!r}")
        if _acceptance_pair_differs(completed_a, completed_b, (state_a, state_b)):
            errors.append(
                f"acceptance mismatch for pair ({state_a!r}, {state_b!r})"
            )
        for symbol in completed_a.input_alphabet:
            succ_a = _optional_dfa_successor(completed_a, state_a, symbol)
            succ_b = _optional_dfa_successor(completed_b, state_b, symbol)
            if succ_a is None or succ_b is None:
                errors.append(
                    "missing transition for "
                    f"({state_a!r},{state_b!r}) on symbol {symbol!r}"
                )
                continue
            if (succ_a, succ_b) not in relation:
                errors.append(
                    "transition inconsistency for "
                    f"({state_a!r},{state_b!r}) on symbol {symbol!r}"
                )

    return (not errors, tuple(errors))
