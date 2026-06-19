"""DFA separation / equivalence oracle."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from fsmreasonbench.models.fsm import ExecutableFSM, FSMType
from fsmreasonbench.runtime.acceptance import accepts_trace


@dataclass(frozen=True, slots=True)
class SeparationResult:
    """Outcome of DFA non-equivalence analysis."""

    equivalent: bool
    distinguishing_trace: tuple[str, ...] | None
    acceptance_a: bool | None
    acceptance_b: bool | None


def are_equivalent(fsm_a: ExecutableFSM, fsm_b: ExecutableFSM) -> bool:
    """Return True iff the two DFAs accept the same language."""
    return check_separation(fsm_a, fsm_b).equivalent


def check_separation(fsm_a: ExecutableFSM, fsm_b: ExecutableFSM) -> SeparationResult:
    """
    Decide equivalence and return the shortest distinguishing trace when possible.

    Both machines must be DFAs over the same alphabet.
    """
    _assert_dfa_pair(fsm_a, fsm_b)
    witness = shortest_distinguishing_trace(fsm_a, fsm_b)
    if witness is None:
        return SeparationResult(
            equivalent=True,
            distinguishing_trace=None,
            acceptance_a=None,
            acceptance_b=None,
        )
    return SeparationResult(
        equivalent=False,
        distinguishing_trace=witness.trace,
        acceptance_a=witness.acceptance_a,
        acceptance_b=witness.acceptance_b,
    )


@dataclass(frozen=True, slots=True)
class DistinguishingTraceWitness:
    trace: tuple[str, ...]
    acceptance_a: bool
    acceptance_b: bool


def shortest_distinguishing_trace(
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
) -> DistinguishingTraceWitness | None:
    """BFS product search for a shortest trace where acceptance differs."""
    _assert_dfa_pair(fsm_a, fsm_b)

    start = (fsm_a.initial_state, fsm_b.initial_state)
    witness = _witness_if_distinguishing(fsm_a, fsm_b, start, ())
    if witness is not None:
        return witness

    queue: deque[tuple[tuple[str, str], tuple[str, ...]]] = deque([(start, ())])
    visited = {start}

    while queue:
        pair, trace = queue.popleft()
        for symbol in fsm_a.input_alphabet:
            next_a = _dfa_step(fsm_a, pair[0], symbol)
            next_b = _dfa_step(fsm_b, pair[1], symbol)
            if next_a is None or next_b is None:
                continue
            successor = (next_a, next_b)
            if successor in visited:
                continue
            visited.add(successor)
            extended = trace + (symbol,)
            witness = _witness_if_distinguishing(fsm_a, fsm_b, successor, extended)
            if witness is not None:
                return witness
            queue.append((successor, extended))
    return None


def _witness_if_distinguishing(
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
    pair: tuple[str, str],
    trace: tuple[str, ...],
) -> DistinguishingTraceWitness | None:
    acceptance_a = pair[0] in fsm_a.accepting_states
    acceptance_b = pair[1] in fsm_b.accepting_states
    if acceptance_a == acceptance_b:
        return None
    return DistinguishingTraceWitness(
        trace=trace,
        acceptance_a=acceptance_a,
        acceptance_b=acceptance_b,
    )


def _dfa_step(fsm: ExecutableFSM, state: str, symbol: str) -> str | None:
    successors = fsm.transitions_from(state, symbol)
    if len(successors) != 1:
        return None
    return successors[0].to_state


def _assert_dfa_pair(fsm_a: ExecutableFSM, fsm_b: ExecutableFSM) -> None:
    if fsm_a.fsm_type != FSMType.DFA or fsm_b.fsm_type != FSMType.DFA:
        raise ValueError("separation oracle supports DFA pairs only")
    if fsm_a.input_alphabet != fsm_b.input_alphabet:
        raise ValueError("DFA alphabets must match for separation oracle")
