"""Unit tests for replicate study aggregation (Experiment A)."""

from __future__ import annotations

import json
from pathlib import Path

from fsmreasonbench.experiments.replicate_studies import (
    build_aggregate_replicates,
    list_pending_replicates,
    replicate_dir_name,
    replicate_study_root,
    write_aggregate_replicates,
)


def _write_combined(study_root: Path, replicate_id: int, fully_correct: float) -> None:
    rep_dir = study_root / replicate_dir_name(replicate_id)
    rep_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "track_rows": [
            {
                "model_dir": "claude-sonnet-4-5-20250929",
                "family": "F1",
                "track": "R2",
                "temperature": 0.2,
                "extractability_rate": 0.9,
                "verdict_accuracy": 0.8,
                "certificate_valid_rate": 0.7,
                "fully_correct_rate": fully_correct,
                "extended_status": "completed",
                "run_dir": str(rep_dir / "cell"),
            }
        ]
    }
    (rep_dir / "combined_summary.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def test_replicate_study_root_suffix() -> None:
    assert replicate_study_root("runs/frontier_claude_sonnet_tools_n100_v2").name.endswith(
        "_replicates"
    )
    assert replicate_study_root("runs/foo_replicates").name == "foo_replicates"


def test_aggregate_replicates_stats(tmp_path: Path) -> None:
    study_root = tmp_path / "study_replicates"
    _write_combined(study_root, 1, 0.40)
    _write_combined(study_root, 2, 0.44)
    _write_combined(study_root, 3, 0.48)
    payload = build_aggregate_replicates(
        study_root,
        campaign_id="test_campaign",
        provider="anthropic",
        model="claude-sonnet-4-5-20250929",
        bootstrap_resamples=200,
        bootstrap_seed=1,
    )
    assert payload["replicate_count"] == 3
    cell = payload["cells"][0]
    stats = cell["metrics"]["fully_correct_rate"]
    assert stats["mean"] == 0.44
    assert stats["min"] == 0.4
    assert stats["max"] == 0.48
    assert stats["n_replicates"] == 3
    assert stats["bootstrap_ci_low"] is not None
    assert stats["coefficient_of_variation"] is not None
    out = write_aggregate_replicates(study_root, payload)
    assert out.exists()


def test_list_pending_replicates(tmp_path: Path) -> None:
    study_root = tmp_path / "pending_replicates"
    _write_combined(study_root, 1, 0.5)
    pending = list_pending_replicates(study_root, 3)
    assert pending == [2, 3]
