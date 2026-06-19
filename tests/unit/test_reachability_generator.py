"""Tests for reachability generator difficulty controls."""

import pytest

from fsmreasonbench.certificates.reachability import build_reachability_certificate
from fsmreasonbench.generator.reachability import (
    ReachabilityGeneratorConfig,
    classify_reachability_targets,
    generate_reachability_item,
    pick_reachability_target,
)
from fsmreasonbench.items.assembly import self_verify_item
from fsmreasonbench.models.fsm import ExecutableFSM, FSMType, Transition
from fsmreasonbench.verifier.reachability import verify_reachability_certificate


def test_positive_items_respect_min_witness_length() -> None:
    config = ReachabilityGeneratorConfig(
        state_count=6,
        min_witness_length=2,
        max_witness_length=8,
        include_negative=False,
    )
    for seed in range(20):
        item = generate_reachability_item(seed, config, force_positive=True)
        self_verify_item(item)
        assert item.answer_key["verdict"] is True
        assert len(item.answer_key["certificate"]["payload"]["trace"]) >= 2


def test_empty_trace_only_when_allow_initial_target() -> None:
    fsm = ExecutableFSM(
        fsm_id="550e8400-e29b-41d4-a716-446655440034",
        fsm_type=FSMType.DFA,
        states=("q0", "q1"),
        initial_state="q0",
        input_alphabet=("a",),
        transitions=(Transition("q0", "a", "q0"),),
        accepting_states=("q0",),
    )
    config = ReachabilityGeneratorConfig(
        min_witness_length=0,
        allow_initial_target=True,
        include_negative=False,
    )
    target, verdict = pick_reachability_target(1, fsm, config, force_positive=True)
    assert verdict is True
    assert target == "q0"
    item = generate_reachability_item(500, config, force_positive=True)
    if item.answer_key["verdict"] and item.question["target_state"] == item.fsm.initial_state:
        assert item.answer_key["certificate"]["payload"]["trace"] == []

    strict = ReachabilityGeneratorConfig(
        state_count=5,
        min_witness_length=1,
        allow_initial_target=False,
        include_negative=False,
    )
    for seed in range(30):
        item = generate_reachability_item(seed, strict, force_positive=True)
        assert item.question["target_state"] != item.fsm.initial_state
        assert len(item.answer_key["certificate"]["payload"]["trace"]) >= 1


def test_negative_items_verify_correctly() -> None:
    config = ReachabilityGeneratorConfig(state_count=6, include_negative=True)
    seen_negative = False
    for seed in range(40):
        item = generate_reachability_item(seed, config, force_positive=False)
        self_verify_item(item)
        if not item.answer_key["verdict"]:
            seen_negative = True
            assert item.answer_key["certificate"]["certificate_type"] == "unreachability_witness"
            assert (
                item.question["target_state"]
                not in item.answer_key["certificate"]["payload"]["reachable_states"]
            )
    assert seen_negative, "expected at least one negative item in sample"


def test_invalid_positive_witness_is_rejected() -> None:
    fsm = ExecutableFSM(
        fsm_id="550e8400-e29b-41d4-a716-446655440030",
        fsm_type=FSMType.DFA,
        states=("q0", "q1"),
        initial_state="q0",
        input_alphabet=("a",),
        transitions=(Transition("q0", "a", "q1"),),
        accepting_states=("q1",),
    )
    certificate = build_reachability_certificate(fsm, "q1")
    certificate["payload"]["trace"] = []
    certificate["payload"]["state_sequence"] = ["q0", "q1"]
    result = verify_reachability_certificate(fsm, "q1", certificate)
    assert not result.valid


def test_invalid_negative_certificate_is_rejected() -> None:
    fsm = ExecutableFSM(
        fsm_id="550e8400-e29b-41d4-a716-446655440031",
        fsm_type=FSMType.DFA,
        states=("q0", "q1", "q2"),
        initial_state="q0",
        input_alphabet=("a",),
        transitions=(Transition("q0", "a", "q1"),),
        accepting_states=("q1",),
    )
    certificate = build_reachability_certificate(fsm, "q2")
    assert certificate["certificate_type"] == "unreachability_witness"
    certificate["payload"]["reachable_states"] = ["q0"]
    result = verify_reachability_certificate(fsm, "q2", certificate)
    assert not result.valid
    assert any("missing reachable states" in error for error in result.errors)


def test_classify_targets_excludes_initial_by_default() -> None:
    fsm = ExecutableFSM(
        fsm_id="550e8400-e29b-41d4-a716-446655440032",
        fsm_type=FSMType.DFA,
        states=("q0", "q1"),
        initial_state="q0",
        input_alphabet=("a",),
        transitions=(Transition("q0", "a", "q1"),),
        accepting_states=("q1",),
    )
    config = ReachabilityGeneratorConfig(min_witness_length=1, allow_initial_target=False)
    positive, negative = classify_reachability_targets(fsm, config)
    assert "q0" not in positive
    assert "q1" in positive


def test_pick_target_raises_when_no_candidate() -> None:
    fsm = ExecutableFSM(
        fsm_id="550e8400-e29b-41d4-a716-446655440033",
        fsm_type=FSMType.DFA,
        states=("q0", "q1"),
        initial_state="q0",
        input_alphabet=("a",),
        transitions=(Transition("q0", "a", "q1"),),
        accepting_states=("q1",),
    )
    config = ReachabilityGeneratorConfig(
        min_witness_length=99,
        max_witness_length=99,
        include_negative=False,
        allow_initial_target=False,
    )
    with pytest.raises(ValueError):
        pick_reachability_target(1, fsm, config, force_positive=True)
