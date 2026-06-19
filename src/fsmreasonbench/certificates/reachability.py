"""Reachability certificate builders (oracle-side, not used by verifier)."""

from __future__ import annotations

from typing import Any

from fsmreasonbench.models.fsm import ExecutableFSM
from fsmreasonbench.oracle.reachability import (
    ReachabilityWitness,
    UnreachabilityWitness,
    is_reachable,
    shortest_reachability_witness,
    unreachability_witness,
)


def build_reachability_certificate(
    fsm: ExecutableFSM,
    target_state: str,
    *,
    version: str = "1.0",
) -> dict[str, Any]:
    """Build gold certificate for C2 reachability question."""
    reachable = is_reachable(fsm, target_state)
    envelope: dict[str, Any] = {
        "certificate_type": "trace_witness" if reachable else "unreachability_witness",
        "version": version,
        "fsm_id": fsm.fsm_id,
        "verdict_supported": reachable,
        "payload": {},
    }
    if reachable:
        witness = shortest_reachability_witness(fsm, target_state)
        if witness is None:
            raise RuntimeError("internal error: is_reachable True but no witness")
        envelope["payload"] = _trace_payload(witness)
    else:
        envelope["payload"] = _unreachability_payload(unreachability_witness(fsm, target_state))
    return envelope


def _trace_payload(witness: ReachabilityWitness) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "trace": list(witness.trace),
        "state_sequence": list(witness.state_sequence),
        "accepting": True,
    }
    if witness.branching_choices is not None:
        payload["branching_choices"] = list(witness.branching_choices)
    return payload


def _unreachability_payload(witness: UnreachabilityWitness) -> dict[str, Any]:
    return {
        "reachable_states": list(witness.reachable_states),
        "target_state": witness.target_state,
    }
