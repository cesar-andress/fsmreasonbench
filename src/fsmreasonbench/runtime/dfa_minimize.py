"""DFA minimization and canonical hashing (shared by oracle and verifier)."""

from __future__ import annotations

from collections import deque
from itertools import product

from fsmreasonbench.models.fsm import ExecutableFSM, FSMType, Transition
from fsmreasonbench.models.serialization import content_hash


def minimized_dfa_hash(fsm: ExecutableFSM) -> str:
    """Return a canonical hash of the DFA language (complete, reachable core)."""
    completed = complete_dfa(fsm)
    reachable = _reachable_states(completed, completed.initial_state)
    core = _restrict_to_states(completed, reachable)
    alphabet = core.input_alphabet
    max_length = min(len(core.states), 12)
    bits: list[bool] = []
    for length in range(max_length + 1):
        for trace in product(alphabet, repeat=length):
            bits.append(_accepts(core, trace))

    return content_hash(
        {
            "input_alphabet": list(alphabet),
            "language_bits": bits,
        }
    )



def _accepts(fsm: ExecutableFSM, trace: tuple[str, ...]) -> bool:
    state = fsm.initial_state
    for symbol in trace:
        state = _dfa_successor(fsm, state, symbol)
    return state in fsm.accepting_states


def _restrict_to_states(fsm: ExecutableFSM, states: set[str]) -> ExecutableFSM:
    active = tuple(state for state in fsm.states if state in states)
    transitions = tuple(
        transition
        for transition in fsm.transitions
        if transition.from_state in states and transition.to_state in states
    )
    accepting = tuple(state for state in fsm.accepting_states if state in states)
    return ExecutableFSM(
        fsm_id=fsm.fsm_id,
        fsm_type=FSMType.DFA,
        states=active,
        initial_state=fsm.initial_state,
        input_alphabet=fsm.input_alphabet,
        transitions=transitions,
        accepting_states=accepting,
        metadata=dict(fsm.metadata),
    )


def minimize_dfa(fsm: ExecutableFSM) -> ExecutableFSM:
    """Minimize a DFA up to language equivalence (reachable states only)."""
    if fsm.fsm_type != FSMType.DFA:
        raise ValueError("minimize_dfa supports DFA only")

    completed = complete_dfa(fsm)
    reachable = _reachable_states(completed, completed.initial_state)
    active = tuple(state for state in completed.states if state in reachable)
    if not active:
        raise ValueError("DFA has no reachable states")

    accepting = {state for state in active if state in completed.accepting_states}
    non_accepting = set(active) - accepting
    groups: list[set[str]] = []
    if non_accepting:
        groups.append(non_accepting)
    if accepting:
        groups.append(accepting)

    changed = True
    while changed:
        changed = False
        next_groups: list[set[str]] = []
        for group in groups:
            split = _split_group(completed, group, groups)
            if len(split) > 1:
                changed = True
            next_groups.extend(split)
        groups = next_groups

    state_group = {state: index for index, group in enumerate(groups) for state in group}
    alphabet = completed.input_alphabet
    initial_group = state_group[completed.initial_state]
    accepting_groups = tuple(
        sorted({state_group[state] for state in accepting})
    )

    canonical_states = tuple(f"m{index}" for index in range(len(groups)))
    transitions: list[Transition] = []
    for group_index, group in enumerate(groups):
        representative = min(group, key=str)
        from_state = canonical_states[group_index]
        for symbol in alphabet:
            target_group = state_group[_dfa_successor(completed, representative, symbol)]
            transitions.append(
                Transition(
                    from_state=from_state,
                    input_symbol=symbol,
                    to_state=canonical_states[target_group],
                )
            )

    return ExecutableFSM(
        fsm_id=f"minimized:{fsm.fsm_id}",
        fsm_type=FSMType.DFA,
        states=canonical_states,
        initial_state=canonical_states[initial_group],
        input_alphabet=alphabet,
        transitions=tuple(transitions),
        accepting_states=tuple(canonical_states[index] for index in accepting_groups),
        metadata={"source_fsm_id": fsm.fsm_id},
    )


def complete_dfa(fsm: ExecutableFSM) -> ExecutableFSM:
    """Add an implicit trap state so the transition function is total."""
    if fsm.fsm_type != FSMType.DFA:
        raise ValueError("complete_dfa supports DFA only")

    trap = "__trap__"
    states = tuple(dict.fromkeys((*fsm.states, trap)))
    transitions = list(fsm.transitions)
    for state in states:
        for symbol in fsm.input_alphabet:
            if not fsm.transitions_from(state, symbol):
                transitions.append(
                    Transition(from_state=state, input_symbol=symbol, to_state=trap)
                )
    accepting = tuple(state for state in fsm.accepting_states if state != trap)
    return ExecutableFSM(
        fsm_id=fsm.fsm_id,
        fsm_type=FSMType.DFA,
        states=states,
        initial_state=fsm.initial_state,
        input_alphabet=fsm.input_alphabet,
        transitions=tuple(transitions),
        accepting_states=accepting,
        metadata=dict(fsm.metadata),
    )


def are_equivalent_dfas(fsm_a: ExecutableFSM, fsm_b: ExecutableFSM) -> bool:
    """Return True iff two DFAs accept the same language."""
    if fsm_a.fsm_type != FSMType.DFA or fsm_b.fsm_type != FSMType.DFA:
        raise ValueError("equivalence check requires DFA inputs")
    if fsm_a.input_alphabet != fsm_b.input_alphabet:
        raise ValueError("DFA alphabets must match")

    start = (fsm_a.initial_state, fsm_b.initial_state)
    if _acceptance_pair_differs(fsm_a, fsm_b, start):
        return False

    queue: deque[tuple[str, str]] = deque([start])
    visited = {start}
    while queue:
        pair = queue.popleft()
        for symbol in fsm_a.input_alphabet:
            next_a = _optional_dfa_successor(fsm_a, pair[0], symbol)
            next_b = _optional_dfa_successor(fsm_b, pair[1], symbol)
            if next_a is None or next_b is None:
                continue
            successor = (next_a, next_b)
            if successor in visited:
                continue
            visited.add(successor)
            if _acceptance_pair_differs(fsm_a, fsm_b, successor):
                return False
            queue.append(successor)
    return True


def _split_group(
    fsm: ExecutableFSM,
    group: set[str],
    groups: list[set[str]],
) -> list[set[str]]:
    if len(group) <= 1:
        return [group]
    group_lookup = {state: index for index, group_states in enumerate(groups) for state in group_states}
    buckets: dict[tuple[int, ...], set[str]] = {}
    for state in group:
        signature = tuple(
            group_lookup[_dfa_successor(fsm, state, symbol)] for symbol in fsm.input_alphabet
        )
        buckets.setdefault(signature, set()).add(state)
    return list(buckets.values())


def _acceptance_pair_differs(
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
    pair: tuple[str, str],
) -> bool:
    return (pair[0] in fsm_a.accepting_states) != (pair[1] in fsm_b.accepting_states)


def _reachable_states(fsm: ExecutableFSM, initial_state: str) -> set[str]:
    seen = {initial_state}
    queue: deque[str] = deque([initial_state])
    while queue:
        state = queue.popleft()
        for symbol in fsm.input_alphabet:
            successor = _dfa_successor(fsm, state, symbol)
            if successor not in seen:
                seen.add(successor)
                queue.append(successor)
    return seen


def _optional_dfa_successor(fsm: ExecutableFSM, state: str, symbol: str) -> str | None:
    transitions = fsm.transitions_from(state, symbol)
    if len(transitions) != 1:
        return None
    return transitions[0].to_state


def _dfa_successor(fsm: ExecutableFSM, state: str, symbol: str) -> str:
    successor = _optional_dfa_successor(fsm, state, symbol)
    if successor is None:
        raise ValueError(f"DFA missing transition for ({state!r}, {symbol!r})")
    return successor
