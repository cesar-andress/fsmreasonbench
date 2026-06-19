"""Reachability computation (shared semantics layer)."""

from __future__ import annotations

from collections import deque

from fsmreasonbench.models.fsm import ExecutableFSM


def reachable_states(fsm: ExecutableFSM) -> frozenset[str]:
    """Compute all states reachable from the initial state."""
    visited: set[str] = set()
    queue: deque[str] = deque([fsm.initial_state])
    while queue:
        state = queue.popleft()
        if state in visited:
            continue
        visited.add(state)
        for symbol in fsm.input_alphabet:
            for transition in fsm.transitions_from(state, symbol):
                if transition.to_state not in visited:
                    queue.append(transition.to_state)
    return frozenset(visited)
