"""Benchmark item assembly for the C2 reachability vertical slice."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from fsmreasonbench.certificates.reachability import build_reachability_certificate
from fsmreasonbench.models.fsm import ExecutableFSM
from fsmreasonbench.models.serialization import canonical_json, content_hash, fsm_to_dict
from fsmreasonbench.oracle.reachability import is_reachable, shortest_reachability_witness
from fsmreasonbench.verifier.reachability import verify_reachability_certificate


@dataclass(frozen=True, slots=True)
class BenchmarkItem:
    """Fully assembled benchmark item with gold answer and certificate."""

    item_id: str
    family: str
    family_tier: str
    fsm: ExecutableFSM
    question: dict[str, Any]
    answer_key: dict[str, Any]
    difficulty: dict[str, Any]
    contamination: dict[str, Any] = field(default_factory=dict)

    def to_evaluatee_dict(self) -> dict[str, Any]:
        """Serialize evaluatee-visible fields (no answer key)."""
        return {
            "item_id": self.item_id,
            "family": self.family,
            "family_tier": self.family_tier,
            "fsm": fsm_to_dict(self.fsm, include_metadata=True),
            "question": self.question,
            "difficulty": self.difficulty,
            "contamination": self.contamination,
        }

    def to_full_dict(self) -> dict[str, Any]:
        data = self.to_evaluatee_dict()
        data["answer_key"] = self.answer_key
        return data


def assemble_reachability_item(
    fsm: ExecutableFSM,
    target_state: str,
    *,
    seed: int,
    item_id: str | None = None,
) -> BenchmarkItem:
    """Assemble C2 item with oracle-produced gold certificate."""
    reachable = is_reachable(fsm, target_state)
    certificate = build_reachability_certificate(fsm, target_state)
    witness = shortest_reachability_witness(fsm, target_state) if reachable else None
    witness_length = len(witness.trace) if witness else 0

    question = {
        "family": "C2",
        "prompt_id": "reachability.v1",
        "target_state": target_state,
    }
    fingerprint_input = canonical_json(
        {"fsm": fsm_to_dict(fsm, include_metadata=False), "question": question}
    )
    public_fingerprint = content_hash({"canonical": fingerprint_input})

    resolved_item_id = item_id or str(
        uuid.uuid5(uuid.NAMESPACE_URL, f"fsmreasonbench:item:{seed}:{target_state}")
    )

    return BenchmarkItem(
        item_id=resolved_item_id,
        family="C2",
        family_tier="calibration",
        fsm=fsm,
        question=question,
        answer_key={
            "item_id": resolved_item_id,
            "verdict": reachable,
            "certificate": certificate,
        },
        difficulty={
            "core": {
                "|Q|": fsm.state_count,
                "witness_length": witness_length,
            },
            "generator_seed": seed,
        },
        contamination={"public_fingerprint": public_fingerprint},
    )


def self_verify_item(item: BenchmarkItem) -> None:
    """
    Validate item end-to-end: oracle certificate accepted by independent verifier.

    Raises AssertionError on failure.
    """
    target_state = item.question["target_state"]
    certificate = item.answer_key["certificate"]
    expected_verdict = item.answer_key["verdict"]

    result = verify_reachability_certificate(item.fsm, target_state, certificate)
    if not result.valid:
        raise AssertionError(f"self-verification failed: {result.errors}")

    cert_type = certificate["certificate_type"]
    if expected_verdict and cert_type != "trace_witness":
        raise AssertionError(f"expected trace_witness for reachable target, got {cert_type}")
    if not expected_verdict and cert_type != "unreachability_witness":
        raise AssertionError(f"expected unreachability_witness, got {cert_type}")

    actual = is_reachable(item.fsm, target_state)
    if actual != expected_verdict:
        raise AssertionError(f"verdict mismatch: oracle={expected_verdict}, actual={actual}")
