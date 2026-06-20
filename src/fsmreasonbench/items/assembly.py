"""Benchmark item assembly for C2 reachability and F1 separation vertical slices."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from fsmreasonbench.certificates.reachability import build_reachability_certificate
from fsmreasonbench.certificates.separation import (
    build_distinguishing_trace_certificate,
    build_equivalence_witness_certificate,
)
from fsmreasonbench.models.fsm import ExecutableFSM
from fsmreasonbench.models.serialization import canonical_json, content_hash, fsm_to_dict
from fsmreasonbench.oracle.reachability import is_reachable, shortest_reachability_witness
from fsmreasonbench.oracle.separation import are_equivalent, shortest_distinguishing_trace
from fsmreasonbench.verifier.reachability import verify_reachability_certificate
from fsmreasonbench.verifier.separation import (
    verify_distinguishing_trace_certificate,
    verify_equivalence_witness_certificate,
)


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
    fsm_b: ExecutableFSM | None = None

    @property
    def fsm_a(self) -> ExecutableFSM:
        return self.fsm

    def to_evaluatee_dict(self) -> dict[str, Any]:
        """Serialize evaluatee-visible fields (no answer key)."""
        data: dict[str, Any] = {
            "item_id": self.item_id,
            "family": self.family,
            "family_tier": self.family_tier,
            "question": self.question,
            "difficulty": self.difficulty,
            "contamination": self.contamination,
        }
        if self.family == "F1":
            if self.fsm_b is None:
                raise ValueError("F1 item requires fsm_b")
            data["fsm_a"] = fsm_to_dict(self.fsm, include_metadata=True)
            data["fsm_b"] = fsm_to_dict(self.fsm_b, include_metadata=True)
        else:
            data["fsm"] = fsm_to_dict(self.fsm, include_metadata=True)
        return data

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
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"fsmreasonbench:item:C2:{seed}:{fsm.fsm_id}:{target_state}",
        )
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


def assemble_separation_item(
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
    *,
    seed: int,
    item_id: str | None = None,
) -> BenchmarkItem:
    """
    Assemble F1 separation item with oracle-produced gold certificate.

    Verdict convention: ``verdict=true`` means equivalent; ``verdict=false`` means not equivalent.
    """
    if are_equivalent(fsm_a, fsm_b):
        return _assemble_equivalent_separation_item(
            fsm_a,
            fsm_b,
            seed=seed,
            item_id=item_id,
        )
    return _assemble_non_equivalent_separation_item(
        fsm_a,
        fsm_b,
        seed=seed,
        item_id=item_id,
    )


def _assemble_non_equivalent_separation_item(
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
    *,
    seed: int,
    item_id: str | None = None,
) -> BenchmarkItem:
    certificate = build_distinguishing_trace_certificate(fsm_a, fsm_b)
    witness = shortest_distinguishing_trace(fsm_a, fsm_b)
    if witness is None:
        raise RuntimeError("internal error: non-equivalent pair without witness")

    question = {
        "family": "F1",
        "prompt_id": "separation.non_equivalence.v1",
        "task": "non_equivalence",
        "fsm_a_id": fsm_a.fsm_id,
        "fsm_b_id": fsm_b.fsm_id,
    }
    fingerprint_input = canonical_json(
        {
            "fsm_a": fsm_to_dict(fsm_a, include_metadata=False),
            "fsm_b": fsm_to_dict(fsm_b, include_metadata=False),
            "question": question,
        }
    )
    public_fingerprint = content_hash({"canonical": fingerprint_input})

    resolved_item_id = item_id or str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"fsmreasonbench:item:F1:{seed}:{fsm_a.fsm_id}:{fsm_b.fsm_id}",
        )
    )

    return BenchmarkItem(
        item_id=resolved_item_id,
        family="F1",
        family_tier="flagship",
        fsm=fsm_a,
        fsm_b=fsm_b,
        question=question,
        answer_key={
            "item_id": resolved_item_id,
            "verdict": False,
            "certificate": certificate,
        },
        difficulty={
            "core": {
                "|Q_A|": fsm_a.state_count,
                "|Q_B|": fsm_b.state_count,
                "alphabet_size": len(fsm_a.input_alphabet),
                "distinguishing_trace_length": len(witness.trace),
                "transition_count_A": len(fsm_a.transitions),
                "transition_count_B": len(fsm_b.transitions),
                "equivalent": False,
            },
            "generator_seed": seed,
        },
        contamination={"public_fingerprint": public_fingerprint},
    )


def _assemble_equivalent_separation_item(
    fsm_a: ExecutableFSM,
    fsm_b: ExecutableFSM,
    *,
    seed: int,
    item_id: str | None = None,
) -> BenchmarkItem:
    certificate = build_equivalence_witness_certificate(fsm_a, fsm_b)

    question = {
        "family": "F1",
        "prompt_id": "separation.equivalence.v1",
        "task": "equivalence",
        "fsm_a_id": fsm_a.fsm_id,
        "fsm_b_id": fsm_b.fsm_id,
    }
    fingerprint_input = canonical_json(
        {
            "fsm_a": fsm_to_dict(fsm_a, include_metadata=False),
            "fsm_b": fsm_to_dict(fsm_b, include_metadata=False),
            "question": question,
        }
    )
    public_fingerprint = content_hash({"canonical": fingerprint_input})

    resolved_item_id = item_id or str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"fsmreasonbench:item:F1:eq:{seed}:{fsm_a.fsm_id}:{fsm_b.fsm_id}",
        )
    )

    return BenchmarkItem(
        item_id=resolved_item_id,
        family="F1",
        family_tier="flagship",
        fsm=fsm_a,
        fsm_b=fsm_b,
        question=question,
        answer_key={
            "item_id": resolved_item_id,
            "verdict": True,
            "certificate": certificate,
        },
        difficulty={
            "core": {
                "|Q_A|": fsm_a.state_count,
                "|Q_B|": fsm_b.state_count,
                "alphabet_size": len(fsm_a.input_alphabet),
                "distinguishing_trace_length": 0,
                "transition_count_A": len(fsm_a.transitions),
                "transition_count_B": len(fsm_b.transitions),
                "equivalent": True,
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
    if item.family == "F1":
        _self_verify_f1_item(item)
        return
    _self_verify_c2_item(item)


def _self_verify_c2_item(item: BenchmarkItem) -> None:
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


def _self_verify_f1_item(item: BenchmarkItem) -> None:
    if item.fsm_b is None:
        raise AssertionError("F1 item missing fsm_b")
    certificate = item.answer_key["certificate"]
    expected_verdict = item.answer_key["verdict"]
    cert_type = certificate["certificate_type"]

    if expected_verdict is True:
        result = verify_equivalence_witness_certificate(item.fsm_a, item.fsm_b, certificate)
        if not result.valid:
            raise AssertionError(f"self-verification failed: {result.errors}")
        if cert_type != "equivalence_witness":
            raise AssertionError(
                f"expected equivalence_witness certificate, got {cert_type!r}"
            )
        if not are_equivalent(item.fsm_a, item.fsm_b):
            raise AssertionError("oracle reports non-equivalent DFAs for equivalence item")
        return

    result = verify_distinguishing_trace_certificate(item.fsm_a, item.fsm_b, certificate)
    if not result.valid:
        raise AssertionError(f"self-verification failed: {result.errors}")
    if cert_type != "distinguishing_trace":
        raise AssertionError(
            f"expected distinguishing_trace certificate, got {cert_type!r}"
        )
    if are_equivalent(item.fsm_a, item.fsm_b):
        raise AssertionError("oracle reports equivalent DFAs for non-equivalence item")
