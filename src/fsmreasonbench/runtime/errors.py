"""Simulation errors."""

from __future__ import annotations


class SimulationError(Exception):
    """Raised when a trace cannot be executed on an FSM."""

    def __init__(
        self,
        message: str,
        *,
        step_index: int | None = None,
        state: str | None = None,
        symbol: str | None = None,
    ) -> None:
        super().__init__(message)
        self.step_index = step_index
        self.state = state
        self.symbol = symbol
