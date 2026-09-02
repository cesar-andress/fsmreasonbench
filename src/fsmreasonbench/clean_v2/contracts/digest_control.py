"""Digest/hash infeasibility-control contract (not a primary feasible arm)."""

from __future__ import annotations

from typing import Any

from fsmreasonbench.models.fsm import ExecutableFSM
from fsmreasonbench.verifier.result import VerifyResult
from fsmreasonbench.verifier.separation import verify_equivalence_witness_certificate

CONTRACT_ROLE = "infeasibility_control"


def verify_digest_control_contract(
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
    certificate: dict[str, Any],
) -> VerifyResult:
    """Reuse existing hash witness verifier; marked experimentally as control-only."""
    return verify_equivalence_witness_certificate(fsm_a, fsm_b, certificate)
