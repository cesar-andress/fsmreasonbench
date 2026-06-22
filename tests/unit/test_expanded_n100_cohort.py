"""Expanded n=100 exploratory cohort workflow tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fsmreasonbench.cohort.expanded_n100 import (
    C2_BATCH_SEED,
    DEFAULT_ITEM_COUNT,
    F1_SEED_START,
    assert_disjoint_from_reference,
    build_expanded_cohorts,
    generate_c2_expanded_items,
    generate_f1_expanded_items,
    resolve_cohort_bundle,
)
from fsmreasonbench.cohort.validate import validate_cohort
from fsmreasonbench.dev.doc_consistency import find_repo_root


@pytest.fixture(scope="module")
def repo_root() -> Path:
    return find_repo_root()


def test_generate_c2_expanded_items_count_and_unique_ids() -> None:
    items = generate_c2_expanded_items(100)
    assert len(items) == 100
    assert len({item.item_id for item in items}) == 100
    seeds = [item.difficulty["generator_seed"] for item in items]
    assert seeds[0] == C2_BATCH_SEED + 0 * 100_003
    assert len(set(seeds)) == 100


def test_generate_f1_expanded_items_count_and_unique_seeds() -> None:
    items = generate_f1_expanded_items(100)
    assert len(items) == 100
    seeds = [item.difficulty["generator_seed"] for item in items]
    assert seeds[0] == F1_SEED_START
    assert seeds[-1] == F1_SEED_START + 99
    assert len(set(seeds)) == 100


def test_expanded_items_disjoint_from_v01_exploratory(repo_root: Path) -> None:
    reference = repo_root / "cohorts/v0.1-exploratory"
    c2_items = generate_c2_expanded_items(100)
    f1_items = generate_f1_expanded_items(100)
    assert_disjoint_from_reference(
        c2_items,
        reference / "c2-reachability-level3/items.jsonl",
        label="C2 expanded",
    )
    assert_disjoint_from_reference(
        f1_items,
        reference / "f1-mixed-level3/items.jsonl",
        label="F1 expanded",
    )


def test_build_expanded_cohorts_freeze_validate(tmp_path: Path, repo_root: Path) -> None:
    cohort_root = tmp_path / "expanded"
    reference_root = repo_root / "cohorts/v0.1-exploratory"
    result = build_expanded_cohorts(
        repo_root,
        item_count=100,
        cohort_root=cohort_root,
        reference_root=reference_root,
        validate=True,
    )

    assert result["item_count"] == 100
    c2_dir = cohort_root / "c2-reachability-level3"
    f1_dir = cohort_root / "f1-mixed-level3"
    assert (c2_dir / "items.jsonl").is_file()
    assert (f1_dir / "items.jsonl").is_file()

    c2_manifest = json.loads((c2_dir / "manifest.json").read_text(encoding="utf-8"))
    f1_manifest = json.loads((f1_dir / "manifest.json").read_text(encoding="utf-8"))
    assert c2_manifest["item_count"] == 100
    assert f1_manifest["item_count"] == 100
    assert c2_manifest["generation_parameters"]["batch_seed"] == C2_BATCH_SEED
    assert f1_manifest["generation_parameters"]["seed_start"] == F1_SEED_START
    assert len(c2_manifest["items"]) == DEFAULT_ITEM_COUNT

    assert validate_cohort(c2_dir).valid
    assert validate_cohort(f1_dir).valid

    c2_items, f1_items, c2_id, f1_id = resolve_cohort_bundle(cohort_root)
    assert c2_items.is_file()
    assert f1_items.is_file()
    assert c2_id.endswith("expanded-n100")
    assert f1_id.endswith("expanded-n100")
