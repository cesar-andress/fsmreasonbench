"""F1 generator difficulty controls and determinism."""

import pytest

from fsmreasonbench.generator.separation import SeparationGeneratorConfig, generate_separation_item
from fsmreasonbench.items.assembly import self_verify_item
from fsmreasonbench.verifier.separation import verify_distinguishing_trace_certificate


def test_generated_trace_respects_min_length() -> None:
    config = SeparationGeneratorConfig(min_distinguishing_trace_length=2, max_retries=128)
    item = generate_separation_item(17, config)
    assert item.difficulty["core"]["distinguishing_trace_length"] >= 2


def test_generated_trace_respects_max_length() -> None:
    config = SeparationGeneratorConfig(
        min_distinguishing_trace_length=1,
        max_distinguishing_trace_length=2,
        max_retries=128,
    )
    item = generate_separation_item(23, config)
    assert item.difficulty["core"]["distinguishing_trace_length"] <= 2


def test_generation_fails_explicitly_when_bounds_unsatisfiable() -> None:
    config = SeparationGeneratorConfig(
        min_distinguishing_trace_length=99,
        max_distinguishing_trace_length=99,
        max_retries=3,
    )
    with pytest.raises(RuntimeError, match="after 3 retries"):
        generate_separation_item(1, config)


def test_seed_determinism_holds() -> None:
    config = SeparationGeneratorConfig(min_distinguishing_trace_length=2)
    first = generate_separation_item(31, config)
    second = generate_separation_item(31, config)
    assert first.to_full_dict() == second.to_full_dict()


def test_invalid_distinguishing_trace_rejected() -> None:
    item = generate_separation_item(
        42,
        SeparationGeneratorConfig(min_distinguishing_trace_length=1),
    )
    certificate = dict(item.answer_key["certificate"])
    certificate["payload"] = dict(certificate["payload"])
    certificate["payload"]["trace"] = ["z"] * 3
    result = verify_distinguishing_trace_certificate(item.fsm_a, item.fsm_b, certificate)
    assert not result.valid


def test_agreeing_acceptance_trace_rejected() -> None:
    item = generate_separation_item(
        42,
        SeparationGeneratorConfig(min_distinguishing_trace_length=1),
    )
    trace = item.answer_key["certificate"]["payload"]["trace"]
    from fsmreasonbench.runtime.acceptance import accepts_trace

    acceptance_a = accepts_trace(item.fsm_a, trace)
    acceptance_b = accepts_trace(item.fsm_b, trace)
    assert acceptance_a != acceptance_b
    certificate = {
        "certificate_type": "distinguishing_trace",
        "version": "1.0",
        "fsm_ids": [item.fsm_a.fsm_id, item.fsm_b.fsm_id],
        "payload": {
            "trace": trace,
            "acceptance": {"A": acceptance_a, "B": acceptance_a},
        },
    }
    result = verify_distinguishing_trace_certificate(item.fsm_a, item.fsm_b, certificate)
    assert not result.valid
    assert any("distinguish" in error or "mismatch" in error for error in result.errors)


def test_smoke_min_length_one_allowed() -> None:
    item = generate_separation_item(
        42,
        SeparationGeneratorConfig(min_distinguishing_trace_length=1),
    )
    self_verify_item(item)
