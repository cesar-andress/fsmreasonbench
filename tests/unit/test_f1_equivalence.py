"""F1 equivalent-pair generation, verification, and mixed-batch scoring."""

from __future__ import annotations

import pytest

from fsmreasonbench.baselines.f1 import run_oracle_baseline, run_random_baseline
from fsmreasonbench.evaluator.scorer_f1 import score_f1_item
from fsmreasonbench.generator.separation import (
    SeparationGeneratorConfig,
    generate_separation_item,
)
from fsmreasonbench.items.assembly import self_verify_item
from fsmreasonbench.oracle.separation import are_equivalent
from fsmreasonbench.verifier.separation import verify_equivalence_witness_certificate


MIXED_CONFIG = SeparationGeneratorConfig(
    min_distinguishing_trace_length=2,
    max_distinguishing_trace_length=2,
    include_equivalent=True,
    equivalent_ratio=0.5,
    mode="random",
)


def test_equivalent_pair_generated_and_verified() -> None:
    item = generate_separation_item(
        101,
        SeparationGeneratorConfig(
            include_equivalent=True,
            equivalent_ratio=1.0,
            mode="random",
        ),
    )
    assert item.answer_key["verdict"] is True
    assert item.answer_key["certificate"]["certificate_type"] == "equivalence_witness"
    assert item.difficulty["core"]["equivalent"] is True
    assert are_equivalent(item.fsm_a, item.fsm_b)
    self_verify_item(item)
    result = verify_equivalence_witness_certificate(
        item.fsm_a,
        item.fsm_b,
        item.answer_key["certificate"],
    )
    assert result.valid


def test_non_equivalent_pair_still_verified() -> None:
    item = generate_separation_item(
        102,
        SeparationGeneratorConfig(
            include_equivalent=False,
            min_distinguishing_trace_length=2,
        ),
    )
    assert item.answer_key["verdict"] is False
    assert item.answer_key["certificate"]["certificate_type"] == "distinguishing_trace"
    assert not are_equivalent(item.fsm_a, item.fsm_b)
    self_verify_item(item)


def test_mixed_batch_has_both_verdicts() -> None:
    items = [generate_separation_item(seed, MIXED_CONFIG) for seed in range(40)]
    verdicts = {item.answer_key["verdict"] for item in items}
    assert True in verdicts
    assert False in verdicts


def test_oracle_baseline_fully_correct_on_mixed_batch() -> None:
    items = [generate_separation_item(seed, MIXED_CONFIG) for seed in range(20)]
    for item in items:
        record = score_f1_item(item, run_oracle_baseline(item))
        assert record.fully_correct is True, item.item_id


def test_always_false_verdict_not_fully_accurate_on_mixed_batch() -> None:
    items = [generate_separation_item(seed, MIXED_CONFIG) for seed in range(40)]
    records = []
    for item in items:
        submission = run_oracle_baseline(item)
        submission["verdict"] = False
        records.append(score_f1_item(item, submission))
    verdict_correct = [record.verdict_correct for record in records if record.verdict_correct is not None]
    assert verdict_correct
    assert sum(1 for value in verdict_correct if value) < len(verdict_correct)
    assert sum(record.fully_correct for record in records) < len(records)


def test_random_baseline_not_fully_correct_on_mixed_batch() -> None:
    items = [generate_separation_item(seed, MIXED_CONFIG) for seed in range(30)]
    records = [score_f1_item(item, run_random_baseline(item, seed=seed)) for seed, item in enumerate(items)]
    assert sum(record.fully_correct for record in records) < len(records)


@pytest.mark.parametrize("seed", range(5))
def test_equivalent_generator_is_deterministic(seed: int) -> None:
    config = SeparationGeneratorConfig(include_equivalent=True, equivalent_ratio=1.0, mode="random")
    first = generate_separation_item(seed, config)
    second = generate_separation_item(seed, config)
    assert first.to_full_dict() == second.to_full_dict()
