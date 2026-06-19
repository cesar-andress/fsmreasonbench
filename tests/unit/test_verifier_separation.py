"""F1 separation verifier tests."""

from fsmreasonbench.generator.separation import SeparationGeneratorConfig, generate_separation_item
from fsmreasonbench.verifier.separation import (
    verify_distinguishing_trace_certificate,
    verify_equivalence_witness_certificate,
)


def test_verifier_accepts_gold_distinguishing_trace() -> None:
    item = generate_separation_item(7)
    result = verify_distinguishing_trace_certificate(
        item.fsm_a,
        item.fsm_b,
        item.answer_key["certificate"],
    )
    assert result.valid


def test_verifier_accepts_gold_equivalence_witness() -> None:
    item = generate_separation_item(
        21,
        SeparationGeneratorConfig(include_equivalent=True, equivalent_ratio=1.0, mode="random"),
    )
    result = verify_equivalence_witness_certificate(
        item.fsm_a,
        item.fsm_b,
        item.answer_key["certificate"],
    )
    assert result.valid


def test_verifier_rejects_agreeing_acceptance() -> None:
    item = generate_separation_item(9)
    certificate = {
        "certificate_type": "distinguishing_trace",
        "version": "1.0",
        "fsm_ids": [item.fsm_a.fsm_id, item.fsm_b.fsm_id],
        "payload": {
            "trace": [],
            "acceptance": {"A": False, "B": False},
        },
    }
    result = verify_distinguishing_trace_certificate(
        item.fsm_a,
        item.fsm_b,
        certificate,
    )
    assert not result.valid
    assert any("distinguish" in error for error in result.errors)
