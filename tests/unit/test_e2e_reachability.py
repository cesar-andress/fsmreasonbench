"""End-to-end: generator → oracle → certificate → verifier."""

from fsmreasonbench.generator.reachability import (
    ReachabilityGeneratorConfig,
    generate_reachability_fsm,
    pick_target_state,
)
from fsmreasonbench.items.assembly import assemble_reachability_item, self_verify_item
from fsmreasonbench.models.serialization import fsm_from_dict, fsm_to_dict
from fsmreasonbench.verifier.reachability import verify_reachability_certificate


def test_generator_deterministic() -> None:
    config = ReachabilityGeneratorConfig(state_count=4)
    first = generate_reachability_fsm(123, config)
    second = generate_reachability_fsm(123, config)
    assert first == second


def test_self_verifying_item_multiple_seeds() -> None:
    for seed in range(10):
        fsm = generate_reachability_fsm(seed, ReachabilityGeneratorConfig(state_count=5))
        target = pick_target_state(seed, fsm)
        item = assemble_reachability_item(fsm, target, seed=seed)
        self_verify_item(item)


def test_evaluatee_roundtrip_preserves_verification() -> None:
    fsm = generate_reachability_fsm(99, ReachabilityGeneratorConfig(state_count=6))
    target = pick_target_state(99, fsm)
    item = assemble_reachability_item(fsm, target, seed=99)
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
    fsm = generate_reachability_fsm(7, ReachabilityGeneratorConfig(state_count=3))
    item = assemble_reachability_item(fsm, pick_target_state(7, fsm), seed=7)
    assert item.difficulty["core"]["|Q|"] == 3
    assert item.difficulty["core"]["|Q|"] == fsm.state_count
