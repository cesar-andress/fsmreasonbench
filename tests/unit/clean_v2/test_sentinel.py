"""Sentinel campaign smoke test (mock provider only)."""

from __future__ import annotations

from fsmreasonbench.clean_v2.sentinel import run_sentinel_campaign


def test_sentinel_campaign_zero_external_calls(repo_root, tmp_path):
    payload = run_sentinel_campaign(
        cohort_items_path=repo_root / "cohorts/v0.1-expanded-n100/f1-mixed-level3/items.jsonl",
        out_root=tmp_path / "sentinel",
        overwrite=True,
    )
    assert payload["external_model_calls"] == 0
    assert payload["provider"] == "DeterministicMockProvider"
    assert payload["n_scores"] >= 10
    assert payload["summary"]["n_attempted"] == payload["n_scores"]
    assert len(payload["repetition_run_ids"]) == 3
    assert len(set(payload["repetition_run_ids"])) == 3
    for proof in payload["fingerprint_proofs"].values():
        assert proof["ok"] is True
        assert proof["unexpected_differences"] == []
