"""Executable FSM data model."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FSMType(str, Enum):
    DFA = "DFA"
    NFA = "NFA"
    MEALY = "MEALY"


@dataclass(frozen=True, slots=True)
class Transition:
    """Single transition edge."""

    from_state: str
    input_symbol: str
    to_state: str
    output: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "from": self.from_state,
            "input": self.input_symbol,
            "to": self.to_state,
        }
        if self.output is not None:
            data["output"] = self.output
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Transition:
        return cls(
            from_state=data["from"],
            input_symbol=data["input"],
            to_state=data["to"],
            output=data.get("output"),
        )


@dataclass(frozen=True, slots=True)
class ExecutableFSM:
    """Canonical executable finite-state machine (DFA or NFA)."""

    fsm_id: str
    fsm_type: FSMType
    states: tuple[str, ...]
    initial_state: str
    input_alphabet: tuple[str, ...]
    transitions: tuple[Transition, ...]
    accepting_states: tuple[str, ...] = ()
    output_alphabet: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        state_set = set(self.states)
        if self.initial_state not in state_set:
            raise ValueError(f"initial_state {self.initial_state!r} not in states")
        alpha_set = set(self.input_alphabet)
        for transition in self.transitions:
            if transition.from_state not in state_set:
                raise ValueError(f"transition from unknown state {transition.from_state!r}")
            if transition.to_state not in state_set:
                raise ValueError(f"transition to unknown state {transition.to_state!r}")
            if transition.input_symbol not in alpha_set:
                raise ValueError(f"transition input {transition.input_symbol!r} not in alphabet")
        for accepting in self.accepting_states:
            if accepting not in state_set:
                raise ValueError(f"accepting state {accepting!r} not in states")
        if self.fsm_type == FSMType.DFA:
            seen: set[tuple[str, str]] = set()
            for transition in self.transitions:
                key = (transition.from_state, transition.input_symbol)
                if key in seen:
                    raise ValueError(
                        f"DFA has multiple transitions for {key}; use NFA for nondeterminism"
                    )
                seen.add(key)

    @property
    def state_count(self) -> int:
        return len(self.states)

    def transitions_from(self, state: str, symbol: str) -> tuple[Transition, ...]:
        return tuple(
            transition
            for transition in self.transitions
            if transition.from_state == state and transition.input_symbol == symbol
        )
