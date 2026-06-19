"""F1 separation reference baselines."""

from __future__ import annotations

import random
from typing import Any

from fsmreasonbench.certificates.separation import (
    build_distinguishing_trace_certificate,
    build_equivalence_witness_certificate,
)
from fsmreasonbench.items.assembly import BenchmarkItem


def run_oracle_baseline(item: BenchmarkItem) -> dict[str, Any]:
    """Symbolic ceiling: correct equivalence verdict and matching certificate."""
    if item.fsm_b is None:
        raise ValueError("F1 baseline requires fsm_b")
    expected_verdict = item.answer_key["verdict"]
    if expected_verdict is True:
        certificate = build_equivalence_witness_certificate(item.fsm_a, item.fsm_b)
        return {
            "item_id": item.item_id,
            "verdict": True,
            "certificate": certificate,
        }
    certificate = build_distinguishing_trace_certificate(item.fsm_a, item.fsm_b)
    return {
        "item_id": item.item_id,
        "verdict": False,
        "certificate": certificate,
    }


def run_random_baseline(item: BenchmarkItem, *, seed: int = 0) -> dict[str, Any]:
    """Random trace and acceptance; structurally valid but usually incorrect."""
    if item.fsm_b is None:
        raise ValueError("F1 baseline requires fsm_b")
    rng = random.Random(seed)
    verdict = rng.choice((True, False))
    if verdict:
        return {
            "item_id": item.item_id,
            "verdict": True,
            "certificate": {
                "certificate_type": "equivalence_witness",
                "version": "1.0",
                "fsm_ids": [item.fsm_a.fsm_id, item.fsm_b.fsm_id],
                "payload": {
                    "equivalent": True,
                    "minimized_hash_A": rng.choice(("deadbeef", "cafebabe")),
                    "minimized_hash_B": rng.choice(("deadbeef", "cafebabe")),
                },
            },
        }

    alphabet = list(item.fsm_a.input_alphabet)
    trace_len = rng.randint(0, max(1, len(alphabet)))
    trace = [rng.choice(alphabet) for _ in range(trace_len)]
    acceptance_a = rng.choice((True, False))
    acceptance_b = rng.choice((True, False))
    return {
        "item_id": item.item_id,
        "verdict": False,
        "certificate": {
            "certificate_type": "distinguishing_trace",
            "version": "1.0",
            "fsm_ids": [item.fsm_a.fsm_id, item.fsm_b.fsm_id],
            "payload": {
                "trace": trace,
                "acceptance": {"A": acceptance_a, "B": acceptance_b},
            },
        },
    }
