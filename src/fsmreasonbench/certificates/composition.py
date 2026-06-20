"""F2 composition certificate builders (oracle-side)."""

from __future__ import annotations

from typing import Any

from fsmreasonbench.models.fsm import ExecutableFSM
from fsmreasonbench.runtime.composition import ProjectedTraceWitness


def build_projected_trace_witness_certificate(
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
    witness: ProjectedTraceWitness,
    *,
    version: str = "1.0",
) -> dict[str, Any]:
    """Build gold counterexample certificate without materialized product tables."""
    return {
        "certificate_type": "projected_trace_witness",
        "version": version,
        "fsm_ids": [fsm_a.fsm_id, fsm_b.fsm_id],
        "verdict_supported": False,
        "payload": {
            "component_trace_A": list(witness.component_trace_a),
            "component_trace_B": list(witness.component_trace_b),
            "synchronized_trace": list(witness.synchronized_trace),
            "projected_states_A": list(witness.projected_states_a),
            "projected_states_B": list(witness.projected_states_b),
            "property_evaluation": {
                "property_kind": "safety",
                "satisfied": False,
                "violation_step_index": witness.violation_step_index,
                "product_state_at_violation": witness.product_state_at_violation,
            },
        },
    }
