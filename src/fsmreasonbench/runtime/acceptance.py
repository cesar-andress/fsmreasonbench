"""Trace acceptance helpers."""

from __future__ import annotations

from fsmreasonbench.models.fsm import ExecutableFSM
from fsmreasonbench.runtime.simulation import simulate


def accepts_trace(fsm: ExecutableFSM, trace: list[str] | tuple[str, ...]) -> bool:
    """Return whether ``trace`` ends in an accepting state."""
    result = simulate(fsm, trace)
    return result.state_sequence[-1] in fsm.accepting_states
