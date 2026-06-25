"""Tests for partial frontier export (incremental R1-only runs)."""

from __future__ import annotations

import json
from pathlib import Path

from fsmreasonbench.evaluator.frontier_tools_analysis import export_frontier_tools_n100_package
from fsmreasonbench.generator.separation import generate_separation_item


def test_export_skips_missing_r2_scores(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    run_root = repo_root / "runs/frontier_gpt_tools_n100_v1"
    r1_dir = run_root / "gpt-5" / "F1" / "temp_0.2" / "R1"
    r1_dir.mkdir(parents=True)

    item = generate_separation_item(42)
    r1_dir.joinpath("scores.jsonl").write_text(
        json.dumps(
            {
                "item_id": item.item_id,
                "extractable": True,
                "verdict_correct": True,
                "certificate_valid": False,
                "fully_correct": False,
                "failure_stage": "certificate_invalid",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    cohort_dir = repo_root / "cohorts/v0.1-expanded-n100/f1-mixed-level3"
    cohort_dir.mkdir(parents=True)
    cohort_dir.joinpath("items.jsonl").write_text(
        json.dumps(item.to_full_dict()) + "\n",
        encoding="utf-8",
    )

    config_dir = repo_root / "configs/frontier"
    config_dir.mkdir(parents=True)
    config_dir.joinpath("frontier_gpt_tools_n100_v1.json").write_text(
        json.dumps(
            {
                "campaign_id": "frontier_gpt_tools_n100_v1",
                "provider": "openai",
                "model": "gpt",
                "families": ["F1"],
                "tracks": ["R1", "R2"],
                "temperatures": [0.2],
                "max_items": 100,
                "out_dir": "runs/frontier_gpt_tools_n100_v1",
            }
        ),
        encoding="utf-8",
    )

    combined = {
        "cell_inventory": [
            {
                "family": "F1",
                "track": "R1",
                "n": 1,
                "extractability_rate": 1.0,
                "verdict_accuracy": 1.0,
                "certificate_valid_rate": 0.0,
                "fully_correct_rate": 0.0,
                "provider_error_count": 0,
                "status": "completed",
                "run_dir": str(r1_dir.relative_to(repo_root)),
            },
            {
                "family": "F1",
                "track": "R2",
                "n": 100,
                "status": "missing",
                "run_dir": str(run_root / "gpt/F1/temp_0.2/R2"),
            },
        ]
    }
    run_root.mkdir(parents=True, exist_ok=True)
    run_root.joinpath("combined_summary.json").write_text(
        json.dumps(combined), encoding="utf-8"
    )

    payload = export_frontier_tools_n100_package(
        repo_root,
        campaign_config_path=config_dir / "frontier_gpt_tools_n100_v1.json",
        json_out=repo_root / "docs/out.json",
    )

    assert payload["tracks_available"] == ["R1"]
    assert payload["partial_run_note"] is not None
    assert payload["paired_track_comparisons"] == []
    assert "R1" in payload["f1_subtype_tables"]["by_track"]
    assert "R2" not in payload["f1_subtype_tables"]["by_track"]
