"""Scientific-path tests for clean_v2 evaluatee leakage and views."""

from __future__ import annotations

import json

from fsmreasonbench.clean_v2.views import (
    build_evaluatee_view,
    build_evaluator_only,
    collect_item_specific_gold_tokens,
)
from fsmreasonbench.evaluator.jsonl import load_items_jsonl


def _eq_item(repo_items_path):
    items = load_items_jsonl(repo_items_path)
    return next(item for item in items if item.answer_key["verdict"] is True)


def test_evaluatee_omits_answer_key_and_equivalent_flag(repo_root):
    item = _eq_item(repo_root / "cohorts/v0.1-expanded-n100/f1-mixed-level3/items.jsonl")
    evaluatee = build_evaluatee_view(item).to_dict()
    blob = json.dumps(evaluatee, sort_keys=True)
    assert "answer_key" not in evaluatee
    assert "equivalent_transform" not in blob
    core = (evaluatee.get("difficulty") or {}).get("core") or {}
    assert "equivalent" not in core
    assert "distinguishing_trace_length" not in core


def test_item_specific_gold_tokens_absent_from_evaluatee(repo_root):
    item = _eq_item(repo_root / "cohorts/v0.1-expanded-n100/f1-mixed-level3/items.jsonl")
    evaluatee_blob = json.dumps(build_evaluatee_view(item).to_dict(), sort_keys=True)
    for token in collect_item_specific_gold_tokens(item):
        assert token not in evaluatee_blob


def test_evaluator_only_retains_gold(repo_root):
    item = _eq_item(repo_root / "cohorts/v0.1-expanded-n100/f1-mixed-level3/items.jsonl")
    evaluator = build_evaluator_only(item)
    assert evaluator.gold_verdict is True
    assert isinstance(evaluator.gold_certificate, dict)
