"""Separation certificate builders (oracle-side)."""

from __future__ import annotations

from typing import Any

from fsmreasonbench.models.fsm import ExecutableFSM
from fsmreasonbench.runtime.dfa_minimize import minimized_dfa_hash
from fsmreasonbench.oracle.separation import (
    DistinguishingTraceWitness,
    check_separation,
    shortest_distinguishing_trace,
)


def build_distinguishing_trace_certificate(
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
    *,
    version: str = "1.0",
) -> dict[str, Any]:
    """Build gold certificate for F1 DFA non-equivalence."""
    witness = shortest_distinguishing_trace(fsm_a, fsm_b)
    if witness is None:
        raise RuntimeError("internal error: cannot build distinguishing trace for equivalent DFAs")
    return _distinguishing_certificate_envelope(fsm_a, fsm_b, witness, version=version)


def build_equivalence_witness_certificate(
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
    *,
    version: str = "1.0",
) -> dict[str, Any]:
    """Build gold certificate for F1 DFA equivalence."""
    return {
        "certificate_type": "equivalence_witness",
        "version": version,
        "fsm_ids": [fsm_a.fsm_id, fsm_b.fsm_id],
        "verdict_supported": True,
        "payload": {
            "equivalent": True,
            "minimized_hash_A": minimized_dfa_hash(fsm_a),
            "minimized_hash_B": minimized_dfa_hash(fsm_b),
        },
    }


def _distinguishing_certificate_envelope(
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
    witness: DistinguishingTraceWitness,
    *,
    version: str,
) -> dict[str, Any]:
    return {
        "certificate_type": "distinguishing_trace",
        "version": version,
        "fsm_ids": [fsm_a.fsm_id, fsm_b.fsm_id],
        "verdict_supported": False,
        "payload": {
            "trace": list(witness.trace),
            "acceptance": {
                "A": witness.acceptance_a,
                "B": witness.acceptance_b,
            },
        },
    }


def separation_oracle_summary(fsm_a: ExecutableFSM, fsm_b: ExecutableFSM) -> dict[str, Any]:
    """Return oracle separation fields for debugging and tests."""
    result = check_separation(fsm_a, fsm_b)
    return {
        "equivalent": result.equivalent,
        "distinguishing_trace": (
            list(result.distinguishing_trace) if result.distinguishing_trace is not None else None
        ),
        "acceptance_A": result.acceptance_a,
        "acceptance_B": result.acceptance_b,
    }
