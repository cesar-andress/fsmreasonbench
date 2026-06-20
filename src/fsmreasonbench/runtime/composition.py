"""Synchronous composition runtime (internal product reasoning)."""

from __future__ import annotations

from dataclasses import dataclass

from fsmreasonbench.models.fsm import ExecutableFSM, FSMType
from fsmreasonbench.runtime.errors import SimulationError
from fsmreasonbench.runtime.simulation import simulate


@dataclass(frozen=True, slots=True)
class ProductState:
    """Pair state in a synchronous product."""

    state_a: str
    state_b: str

    def encode(self) -> str:
        return f"{self.state_a},{self.state_b}"


@dataclass(frozen=True, slots=True)
class ProjectedTraceWitness:
    """Counterexample trace with component projections."""

    synchronized_trace: tuple[str, ...]
    component_trace_a: tuple[str, ...]
    component_trace_b: tuple[str, ...]
    projected_states_a: tuple[str, ...]
    projected_states_b: tuple[str, ...]
    violation_step_index: int
    product_state_at_violation: str


def synchronized_alphabet(
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
    *,
    override: tuple[str, ...] | list[str] | None = None,
) -> tuple[str, ...]:
    if override is not None:
        return tuple(override)
    shared = [symbol for symbol in fsm_a.input_alphabet if symbol in fsm_b.input_alphabet]
    return tuple(shared)


def initial_product_state(fsm_a: ExecutableFSM, fsm_b: ExecutableFSM) -> ProductState:
    return ProductState(fsm_a.initial_state, fsm_b.initial_state)


def product_successor(
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
    state: ProductState,
    symbol: str,
) -> ProductState | None:
    succ_a = fsm_a.transitions_from(state.state_a, symbol)
    succ_b = fsm_b.transitions_from(state.state_b, symbol)
    if not succ_a or not succ_b:
        return None
    if fsm_a.fsm_type == FSMType.DFA and len(succ_a) != 1:
        return None
    if fsm_b.fsm_type == FSMType.DFA and len(succ_b) != 1:
        return None
    return ProductState(succ_a[0].to_state, succ_b[0].to_state)


def replay_projected_traces(
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
    *,
    component_trace_a: list[str] | tuple[str, ...],
    component_trace_b: list[str] | tuple[str, ...],
    synchronized_trace: list[str] | tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    trace_a = tuple(component_trace_a)
    trace_b = tuple(component_trace_b)
    sync = tuple(synchronized_trace)
    if trace_a != sync or trace_b != sync:
        raise SimulationError("component traces must match synchronized_trace in v1 sync product")
    sim_a = simulate(fsm_a, trace_a)
    sim_b = simulate(fsm_b, trace_b)
    return sim_a.state_sequence, sim_b.state_sequence


def product_state_sequence(
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
    synchronized_trace: list[str] | tuple[str, ...],
) -> tuple[str, ...]:
    current = initial_product_state(fsm_a, fsm_b)
    sequence = [current.encode()]
    for symbol in synchronized_trace:
        nxt = product_successor(fsm_a, fsm_b, current, symbol)
        if nxt is None:
            raise SimulationError(
                f"invalid synchronous step from {current.encode()!r} on {symbol!r}"
            )
        current = nxt
        sequence.append(current.encode())
    return tuple(sequence)


def shortest_safety_violation_witness(
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
    *,
    safe_product_states: set[str],
    sync_alphabet: tuple[str, ...] | None = None,
    max_depth: int = 24,
) -> ProjectedTraceWitness | None:
    """
    BFS for a shortest synchronous trace reaching an unsafe product state.

    Returns None when no violation exists within ``max_depth``.
    """
    alphabet = sync_alphabet or synchronized_alphabet(fsm_a, fsm_b)
    if not alphabet:
        return None

    start = initial_product_state(fsm_a, fsm_b)
    if start.encode() not in safe_product_states:
        return ProjectedTraceWitness(
            synchronized_trace=(),
            component_trace_a=(),
            component_trace_b=(),
            projected_states_a=(fsm_a.initial_state,),
            projected_states_b=(fsm_b.initial_state,),
            violation_step_index=0,
            product_state_at_violation=start.encode(),
        )

    queue: list[tuple[ProductState, tuple[str, ...]]] = [(start, ())]
    best_depth: dict[str, int] = {start.encode(): 0}

    while queue:
        state, trace = queue.pop(0)
        if len(trace) >= max_depth:
            continue
        for symbol in alphabet:
            nxt = product_successor(fsm_a, fsm_b, state, symbol)
            if nxt is None:
                continue
            new_trace = trace + (symbol,)
            encoded = nxt.encode()
            if encoded not in safe_product_states:
                sim_a = simulate(fsm_a, new_trace)
                sim_b = simulate(fsm_b, new_trace)
                return ProjectedTraceWitness(
                    synchronized_trace=new_trace,
                    component_trace_a=new_trace,
                    component_trace_b=new_trace,
                    projected_states_a=sim_a.state_sequence,
                    projected_states_b=sim_b.state_sequence,
                    violation_step_index=len(new_trace),
                    product_state_at_violation=encoded,
                )
            depth = len(new_trace)
            prior = best_depth.get(encoded)
            if prior is not None and prior <= depth:
                continue
            best_depth[encoded] = depth
            queue.append((nxt, new_trace))
    return None
