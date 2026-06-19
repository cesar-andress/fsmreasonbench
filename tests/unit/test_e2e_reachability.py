"""End-to-end: generator → oracle → certificate → verifier."""

from fsmreasonbench.generator.reachability import (
    ReachabilityGeneratorConfig,
    generate_reachability_item,
)
from fsmreasonbench.items.assembly import self_verify_item
from fsmreasonbench.models.serialization import fsm_from_dict, fsm_to_dict
from fsmreasonbench.verifier.reachability import verify_reachability_certificate


def test_generator_deterministic() -> None:
    config = ReachabilityGeneratorConfig(state_count=4, include_negative=False)
    first = generate_reachability_item(123, config, force_positive=True)
    second = generate_reachability_item(123, config, force_positive=True)
    assert first.to_full_dict() == second.to_full_dict()


def test_self_verifying_item_multiple_seeds() -> None:
    config = ReachabilityGeneratorConfig(state_count=5)
    for seed in range(10):
        item = generate_reachability_item(seed, config)
        self_verify_item(item)


def test_evaluatee_roundtrip_preserves_verification() -> None:
    item = generate_reachability_item(99, ReachabilityGeneratorConfig(state_count=6))
    self_verify_item(item)

    evaluatee = item.to_evaluatee_dict()
    restored_fsm = fsm_from_dict(evaluatee["fsm"])
    certificate = item.answer_key["certificate"]
    result = verify_reachability_certificate(
        restored_fsm,
        evaluatee["question"]["target_state"],
        certificate,
    )
    assert result.valid, result.errors


def test_item_difficulty_records_state_count() -> None:
    item = generate_reachability_item(7, ReachabilityGeneratorConfig(state_count=3))
    assert item.difficulty["core"]["|Q|"] == 3
    assert item.difficulty["core"]["|Q|"] == item.fsm.state_count
