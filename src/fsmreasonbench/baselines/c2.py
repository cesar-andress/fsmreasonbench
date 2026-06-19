"""C2 reachability reference baselines."""

from __future__ import annotations

import random
from typing import Any

from fsmreasonbench.certificates.reachability import build_reachability_certificate
from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.oracle.reachability import is_reachable


def run_oracle_baseline(item: BenchmarkItem) -> dict[str, Any]:
    """
    Symbolic ceiling: correct verdict and verifier-valid certificate from oracle.
    """
    target_state = item.question["target_state"]
    certificate = build_reachability_certificate(item.fsm, target_state)
    return {
        "item_id": item.item_id,
        "verdict": is_reachable(item.fsm, target_state),
        "certificate": certificate,
    }


def run_random_baseline(item: BenchmarkItem, *, seed: int = 0) -> dict[str, Any]:
    """
    Random verdict with structurally valid but usually incorrect certificate.

    Deterministic under ``seed``.
    """
    rng = random.Random(seed)
    target_state = item.question["target_state"]
    verdict = rng.choice((True, False))

    if verdict:
        alphabet = list(item.fsm.input_alphabet)
        trace_len = rng.randint(0, max(1, len(alphabet)))
        trace = [rng.choice(alphabet) for _ in range(trace_len)]
        state_sequence = [
            rng.choice(list(item.fsm.states)) for _ in range(trace_len + 1)
        ]
        certificate: dict[str, Any] = {
            "certificate_type": "trace_witness",
            "version": "1.0",
            "payload": {
                "trace": trace,
                "state_sequence": state_sequence,
                "accepting": True,
            },
        }
    else:
        states = list(item.fsm.states)
        subset_size = rng.randint(0, len(states))
        reachable_states = sorted(rng.sample(states, subset_size))
        certificate = {
            "certificate_type": "unreachability_witness",
            "version": "1.0",
            "payload": {
                "reachable_states": reachable_states,
                "target_state": target_state,
            },
        }

    return {
        "item_id": item.item_id,
        "verdict": verdict,
        "certificate": certificate,
    }


def run_invalid_baseline(item: BenchmarkItem) -> str:
    """Malformed response for extractability-gate testing."""
    return f"NOT VALID JSON {{ item_id: {item.item_id}, verdict: maybe }}"
