"""Trace simulation — re-export from runtime."""

from fsmreasonbench.runtime.errors import SimulationError
from fsmreasonbench.runtime.simulation import SimulationResult, simulate


def accepts_trace(fsm, trace):  # type: ignore[no-untyped-def]
    """Return True if trace is fully defined on the FSM (NFA: any branch)."""
    from fsmreasonbench.models.fsm import FSMType

    trace_tuple = tuple(trace)
    if not trace_tuple:
        return True

    if fsm.fsm_type == FSMType.DFA:
        try:
            simulate(fsm, trace_tuple)
            return True
        except SimulationError:
            return False

    def dfs(state: str, index: int) -> bool:
        if index == len(trace_tuple):
            return True
        symbol = trace_tuple[index]
        for transition in fsm.transitions_from(state, symbol):
            if dfs(transition.to_state, index + 1):
                return True
        return False

    return dfs(fsm.initial_state, 0)


__all__ = ["SimulationError", "SimulationResult", "accepts_trace", "simulate"]
