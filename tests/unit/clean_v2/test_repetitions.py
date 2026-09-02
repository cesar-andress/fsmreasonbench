"""Repetition identity and no-overwrite tests."""

from __future__ import annotations

import pytest

from fsmreasonbench.clean_v2.artifacts import run_id_for
from fsmreasonbench.clean_v2.fingerprint import base_condition
from fsmreasonbench.clean_v2.runner import run_clean_item
from fsmreasonbench.clean_v2.sentinel.mock_provider import DeterministicMockProvider, build_generate_fn
from fsmreasonbench.evaluator.jsonl import load_items_jsonl


def _eq_item(repo_root):
    items = load_items_jsonl(repo_root / "cohorts/v0.1-expanded-n100/f1-mixed-level3/items.jsonl")
    return next(item for item in items if item.answer_key["verdict"] is True)


def test_repetition_run_ids_differ(repo_root):
    item = _eq_item(repo_root)
    ids = [
        run_id_for(
            base_condition(repetition_index=rep),
            item_id=item.item_id,
            item_manifest_fingerprint="mani",
        )
        for rep in (1, 2, 3)
    ]
    assert len(set(ids)) == 3


def test_no_overwrite_by_default(repo_root, tmp_path):
    item = _eq_item(repo_root)
    provider = DeterministicMockProvider(items_by_id={item.item_id: item})
    generate = build_generate_fn(provider)
    condition = base_condition(repetition_index=1)
    run_clean_item(
        item,
        condition,
        generate,
        item_manifest_fingerprint="mani",
        out_dir=tmp_path,
        overwrite=False,
    )
    with pytest.raises(FileExistsError):
        run_clean_item(
            item,
            condition,
            generate,
            item_manifest_fingerprint="mani",
            out_dir=tmp_path,
            overwrite=False,
        )
