"""R1 single-step FSM simulator."""

from __future__ import annotations

from typing import Any

from fsmreasonbench.models.fsm import ExecutableFSM, FSMType
from fsmreasonbench.tracks.audit import AuditLogBuilder

STEP_SIMULATOR_VERSION = "1.0"


class StepSimulator:
    """
    R1-permitted tool: single transition step on an evaluatee-visible FSM.

    Every call is logged to the audit builder.
    """

    def __init__(self, fsm: ExecutableFSM, *, audit: AuditLogBuilder) -> None:
        self._fsm = fsm
        self._audit = audit

    @property
    def fsm_id(self) -> str:
        return self._fsm.fsm_id

    def step(self, state: str, symbol: str) -> dict[str, Any]:
        if state not in self._fsm.states:
            outputs = {
                "success": False,
                "error": f"unknown state {state!r}",
            }
            self._audit.record_tool(
                "step",
                {
                    "fsm_id": self._fsm.fsm_id,
                    "state": state,
                    "symbol": symbol,
                },
                outputs,
                tool_version=STEP_SIMULATOR_VERSION,
                provenance="r1_step_simulator",
            )
            return outputs

        if symbol not in self._fsm.input_alphabet:
            outputs = {
                "success": False,
                "error": f"symbol {symbol!r} not in alphabet",
            }
            self._audit.record_tool(
                "step",
                {
                    "fsm_id": self._fsm.fsm_id,
                    "state": state,
                    "symbol": symbol,
                },
                outputs,
                tool_version=STEP_SIMULATOR_VERSION,
                provenance="r1_step_simulator",
            )
            return outputs

        successors = self._fsm.transitions_from(state, symbol)
        if not successors:
            outputs = {
                "success": False,
                "error": f"no transition from {state!r} on {symbol!r}",
            }
        elif self._fsm.fsm_type == FSMType.DFA:
            if len(successors) != 1:
                outputs = {
                    "success": False,
                    "error": f"DFA state {state!r} has {len(successors)} successors",
                }
            else:
                outputs = {
                    "success": True,
                    "next_state": successors[0].to_state,
                }
        elif len(successors) == 1:
            outputs = {
                "success": True,
                "next_state": successors[0].to_state,
                "branch_index": 0,
            }
        else:
            outputs = {
                "success": False,
                "error": "NFA multi-successor step requires branch_index (not in R1 v1)",
                "successor_count": len(successors),
            }

        self._audit.record_tool(
            "step",
            {
                "fsm_id": self._fsm.fsm_id,
                "state": state,
                "symbol": symbol,
            },
            outputs,
            tool_version=STEP_SIMULATOR_VERSION,
            provenance="r1_step_simulator",
        )
        return outputs
