"""F2 composition vertical slice tests."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from fsmreasonbench.cli.generate_batch import main as generate_batch_main
from fsmreasonbench.cohort.freeze import freeze_cohort
from fsmreasonbench.cohort.validate import validate_cohort
from fsmreasonbench.evaluator.batch import (
    assert_unique_item_ids,
    evaluate_baseline_on_items,
    generate_f2_batch,
)
from fsmreasonbench.evaluator.io import item_from_dict, load_item
from fsmreasonbench.evaluator.jsonl import load_items_jsonl
from fsmreasonbench.generator.f2_composition import CompositionGeneratorConfig, generate_composition_item
from fsmreasonbench.items.assembly import self_verify_item
from fsmreasonbench.baselines.f2 import run_oracle_baseline
from fsmreasonbench.evaluator.scorer import score_item
from fsmreasonbench.verifier.composition import verify_projected_trace_witness_certificate


def test_f2_generated_items_self_verify() -> None:
    config = CompositionGeneratorConfig(max_generation_attempts=128)
    for seed in range(5):
        item = generate_composition_item(seed, config)
        self_verify_item(item)


def test_f2_oracle_baseline_fully_correct() -> None:
    items = generate_f2_batch(8, seed=4202, config=CompositionGeneratorConfig(max_generation_attempts=128))
    records = evaluate_baseline_on_items("oracle", items)
    assert all(record.fully_correct for record in records)


def test_f2_invalid_projected_trace_rejected() -> None:
    item = generate_composition_item(11, CompositionGeneratorConfig(max_generation_attempts=128))
    certificate = copy.deepcopy(item.answer_key["certificate"])
    certificate["payload"]["projected_states_A"][1] = "INVALID"
    result = verify_projected_trace_witness_certificate(
        item.fsm_a,
        item.fsm_b,
        item.question,
        certificate,
    )
    assert not result.valid


def test_f2_synchronization_mismatch_rejected() -> None:
    item = generate_composition_item(12, CompositionGeneratorConfig(max_generation_attempts=128))
    certificate = copy.deepcopy(item.answer_key["certificate"])
    certificate["payload"]["component_trace_B"] = list(
        certificate["payload"]["synchronized_trace"]
    ) + ["z"]
    result = verify_projected_trace_witness_certificate(
        item.fsm_a,
        item.fsm_b,
        item.question,
        certificate,
    )
    assert not result.valid


def test_f2_property_mismatch_rejected() -> None:
    item = generate_composition_item(13, CompositionGeneratorConfig(max_generation_attempts=128))
    certificate = copy.deepcopy(item.answer_key["certificate"])
    certificate["payload"]["property_evaluation"]["product_state_at_violation"] = "q0,q0"
    result = verify_projected_trace_witness_certificate(
        item.fsm_a,
        item.fsm_b,
        item.question,
        certificate,
    )
    assert not result.valid


def test_f2_materialization_forbidden_key_rejected() -> None:
    item = generate_composition_item(14, CompositionGeneratorConfig(max_generation_attempts=128))
    certificate = copy.deepcopy(item.answer_key["certificate"])
    certificate["payload"]["product_states"] = ["q0,p0"]
    result = verify_projected_trace_witness_certificate(
        item.fsm_a,
        item.fsm_b,
        item.question,
        certificate,
    )
    assert not result.valid


def test_f2_duplicate_ids_cannot_occur_in_batch() -> None:
    items = generate_f2_batch(10, seed=99, config=CompositionGeneratorConfig(max_generation_attempts=128))
    assert_unique_item_ids(items)


def test_f2_batch_generation_deterministic() -> None:
    config = CompositionGeneratorConfig(max_generation_attempts=128)
    first = generate_f2_batch(6, seed=4202, config=config)
    second = generate_f2_batch(6, seed=4202, config=config)
    assert [item.item_id for item in first] == [item.item_id for item in second]


def test_f2_freeze_and_validate(tmp_path: Path) -> None:
    items = generate_f2_batch(5, seed=7, config=CompositionGeneratorConfig(max_generation_attempts=128))
    source = tmp_path / "f2_items.jsonl"
    source.write_text(
        "\n".join(json.dumps(item.to_full_dict(), sort_keys=True) for item in items) + "\n",
        encoding="utf-8",
    )
    cohort_dir = tmp_path / "f2-cohort"
    freeze_cohort(
        source,
        "f2-smoke-v0.1-exploratory",
        cohort_dir,
    )
    report = validate_cohort(cohort_dir)
    assert report.valid, report.errors


def test_f2_generate_batch_cli(tmp_path: Path) -> None:
    out = tmp_path / "f2_items.jsonl"
    assert (
        generate_batch_main(
            ["--family", "F2", "--n", "4", "--seed", "4202", "--out", str(out)]
        )
        == 0
    )
    items = load_items_jsonl(out)
    assert len(items) == 4
    assert all(item.family == "F2" for item in items)


def test_f2_scorer_routes_correctly() -> None:
    item = generate_composition_item(4202, CompositionGeneratorConfig(max_generation_attempts=128))
    submission = run_oracle_baseline(item)
    record = score_item(item, json.dumps(submission))
    assert record.fully_correct
    assert record.failure_stage == "correct"


def test_f2_example_item_parseable_and_replayable() -> None:
    example_path = Path("examples/F2/item_composition_seed4202.json")
    item = load_item(example_path)
    self_verify_item(item)
    roundtrip = item_from_dict(item.to_full_dict())
    assert roundtrip.item_id == item.item_id
