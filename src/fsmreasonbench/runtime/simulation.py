"""Trace simulation over executable FSMs."""

from __future__ import annotations

from dataclasses import dataclass

from fsmreasonbench.models.fsm import ExecutableFSM, FSMType
from fsmreasonbench.runtime.errors import SimulationError


@dataclass(frozen=True, slots=True)
class SimulationResult:
    """Successful simulation outcome."""

    trace: tuple[str, ...]
    state_sequence: tuple[str, ...]
    branching_choices: tuple[int, ...] | None = None


def simulate(
    fsm: ExecutableFSM,
    trace: list[str] | tuple[str, ...],
    *,
    branch_choices: list[int] | tuple[int, ...] | None = None,
) -> SimulationResult:
    """Execute trace on FSM."""
    trace_tuple = tuple(trace)
    if not trace_tuple:
        return SimulationResult(trace=(), state_sequence=(fsm.initial_state,))

    state_sequence = [fsm.initial_state]
    choices: list[int] = []
    current = fsm.initial_state

    for index, symbol in enumerate(trace_tuple):
        successors = fsm.transitions_from(current, symbol)
        if not successors:
            raise SimulationError(
                f"no transition from {current!r} on {symbol!r}",
                step_index=index,
                state=current,
                symbol=symbol,
            )
        if fsm.fsm_type == FSMType.DFA:
            if len(successors) != 1:
                raise SimulationError(
                    f"DFA state {current!r} has {len(successors)} successors on {symbol!r}",
                    step_index=index,
                    state=current,
                    symbol=symbol,
                )
            next_state = successors[0].to_state
        else:
            if branch_choices is None:
                raise SimulationError(
                    f"NFA requires branch_choices at step {index}",
                    step_index=index,
                    state=current,
                    symbol=symbol,
                )
            choice = branch_choices[index]
            if choice < 0 or choice >= len(successors):
                raise SimulationError(
                    f"invalid branch choice {choice} at step {index}",
                    step_index=index,
                    state=current,
                    symbol=symbol,
                )
            choices.append(choice)
            next_state = successors[choice].to_state
        state_sequence.append(next_state)
        current = next_state

    return SimulationResult(
        trace=trace_tuple,
        state_sequence=tuple(state_sequence),
        branching_choices=tuple(choices) if choices else None,
    )
