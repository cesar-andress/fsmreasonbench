"""F2 composition reference baselines."""

from __future__ import annotations

import random
from typing import Any

from fsmreasonbench.certificates.composition import build_projected_trace_witness_certificate
from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.oracle.composition import shortest_violation_witness


def run_oracle_baseline(item: BenchmarkItem) -> dict[str, Any]:
    """Symbolic ceiling: correct verdict and projected trace witness."""
    if item.fsm_b is None:
        raise ValueError("F2 baseline requires fsm_b")
    witness = shortest_violation_witness(item.fsm_a, item.fsm_b, item.question)
    if witness is None:
        raise RuntimeError("oracle baseline requires a violation witness in first F2 slice")
    certificate = build_projected_trace_witness_certificate(item.fsm_a, item.fsm_b, witness)
    return {
        "item_id": item.item_id,
        "verdict": False,
        "certificate": certificate,
    }


def run_random_baseline(item: BenchmarkItem, *, seed: int = 0) -> dict[str, Any]:
    """Random trace witness; structurally typed but usually incorrect."""
    if item.fsm_b is None:
        raise ValueError("F2 baseline requires fsm_b")
    rng = random.Random(seed)
    alphabet = list(item.question["composition_spec"]["synchronized_alphabet"])
    trace_len = rng.randint(0, max(1, len(alphabet)))
    trace = [rng.choice(alphabet) for _ in range(trace_len)]
    states_a = [rng.choice(item.fsm_a.states) for _ in range(trace_len + 1)]
    states_b = [rng.choice(item.fsm_b.states) for _ in range(trace_len + 1)]
    return {
        "item_id": item.item_id,
        "verdict": rng.choice((True, False)),
        "certificate": {
            "certificate_type": "projected_trace_witness",
            "version": "1.0",
            "fsm_ids": [item.fsm_a.fsm_id, item.fsm_b.fsm_id],
            "payload": {
                "component_trace_A": trace,
                "component_trace_B": trace,
                "synchronized_trace": trace,
                "projected_states_A": states_a,
                "projected_states_B": states_b,
                "property_evaluation": {
                    "property_kind": "safety",
                    "satisfied": False,
                    "violation_step_index": trace_len,
                    "product_state_at_violation": f"{states_a[-1]},{states_b[-1]}",
                },
            },
        },
    }
