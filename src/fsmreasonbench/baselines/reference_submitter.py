"""Reference submitter baseline: solve items and emit model-shaped submissions."""

from __future__ import annotations

import json
from typing import Any

from fsmreasonbench.certificates.reachability import build_reachability_certificate
from fsmreasonbench.certificates.separation import (
    build_distinguishing_trace_certificate,
    build_equivalence_witness_certificate,
)
from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.models.fsm import ExecutableFSM
from fsmreasonbench.oracle.reachability import is_reachable
from fsmreasonbench.oracle.separation import are_equivalent

__all__ = [
    "build_reference_submission",
    "run_reference_submitter",
    "serialize_reference_submission",
]


def build_reference_submission(item: BenchmarkItem) -> dict[str, Any]:
    """
    Build a model-shaped submission using evaluatee-visible FSM fields only.

    Does not read ``answer_key.certificate`` or any other gold certificate fields.
    """
    if item.family == "C2":
        return _build_c2_reference_submission(
            item_id=item.item_id,
            fsm=item.fsm,
            target_state=item.question["target_state"],
        )
    if item.family == "F1":
        if item.fsm_b is None:
            raise ValueError("F1 reference submitter requires fsm_b")
        return _build_f1_reference_submission(
            item_id=item.item_id,
            fsm_a=item.fsm_a,
            fsm_b=item.fsm_b,
        )
    raise ValueError(f"unsupported family for reference submitter: {item.family!r}")


def _build_c2_reference_submission(
    *,
    item_id: str,
    fsm: ExecutableFSM,
    target_state: str,
) -> dict[str, Any]:
    verdict = is_reachable(fsm, target_state)
    certificate = build_reachability_certificate(fsm, target_state)
    return {
        "item_id": item_id,
        "verdict": verdict,
        "certificate": certificate,
    }


def _build_f1_reference_submission(
    *,
    item_id: str,
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
) -> dict[str, Any]:
    equivalent = are_equivalent(fsm_a, fsm_b)
    if equivalent:
        certificate = build_equivalence_witness_certificate(fsm_a, fsm_b)
        return {
            "item_id": item_id,
            "verdict": True,
            "certificate": certificate,
        }
    certificate = build_distinguishing_trace_certificate(fsm_a, fsm_b)
    return {
        "item_id": item_id,
        "verdict": False,
        "certificate": certificate,
    }


def serialize_reference_submission(submission: dict[str, Any]) -> str:
    """Serialize submission the way model batch runners store raw responses."""
    return json.dumps(submission, sort_keys=True)


def run_reference_submitter(item: BenchmarkItem) -> str:
    """Return a JSON submission string for the public evaluator parser."""
    return serialize_reference_submission(build_reference_submission(item))
