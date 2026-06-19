"""Reachability oracle — builds witnesses using runtime semantics."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from fsmreasonbench.models.fsm import ExecutableFSM, FSMType
from fsmreasonbench.runtime.reachability import reachable_states
from fsmreasonbench.runtime.simulation import simulate


@dataclass(frozen=True, slots=True)
class ReachabilityWitness:
    trace: tuple[str, ...]
    state_sequence: tuple[str, ...]
    branching_choices: tuple[int, ...] | None = None


@dataclass(frozen=True, slots=True)
class UnreachabilityWitness:
    reachable_states: tuple[str, ...]
    target_state: str


def is_reachable(fsm: ExecutableFSM, target_state: str) -> bool:
    return target_state in reachable_states(fsm)


def shortest_reachability_witness(
    fsm: ExecutableFSM,
    target_state: str,
) -> ReachabilityWitness | None:
    if target_state == fsm.initial_state:
        return ReachabilityWitness(trace=(), state_sequence=(fsm.initial_state,))

    parent: dict[str, tuple[str | None, str | None, int | None]] = {
        fsm.initial_state: (None, None, None)
    }
    queue: deque[str] = deque([fsm.initial_state])

    while queue:
        state = queue.popleft()
        for symbol in fsm.input_alphabet:
            successors = fsm.transitions_from(state, symbol)
            for branch_index, transition in enumerate(successors):
                successor = transition.to_state
                if successor in parent:
                    continue
                parent[successor] = (
                    state,
                    symbol,
                    branch_index if fsm.fsm_type != FSMType.DFA else None,
                )
                if successor == target_state:
                    return _reconstruct_witness(fsm, parent, target_state)
                queue.append(successor)
    return None


def unreachability_witness(fsm: ExecutableFSM, target_state: str) -> UnreachabilityWitness:
    reachable = reachable_states(fsm)
    return UnreachabilityWitness(
        reachable_states=tuple(sorted(reachable)),
        target_state=target_state,
    )


def _reconstruct_witness(
    fsm: ExecutableFSM,
    parent: dict[str, tuple[str | None, str | None, int | None]],
    target_state: str,
) -> ReachabilityWitness:
    trace_rev: list[str] = []
    branch_rev: list[int] = []
    state = target_state
    while True:
        prev, symbol, branch = parent[state]
        if prev is None:
            break
        assert symbol is not None
        trace_rev.append(symbol)
        if branch is not None:
            branch_rev.append(branch)
        state = prev
    trace = tuple(reversed(trace_rev))
    branch_choices = tuple(reversed(branch_rev)) if branch_rev else None
    simulation = simulate(fsm, trace, branch_choices=branch_choices)
    return ReachabilityWitness(
        trace=simulation.trace,
        state_sequence=simulation.state_sequence,
        branching_choices=simulation.branching_choices,
    )
