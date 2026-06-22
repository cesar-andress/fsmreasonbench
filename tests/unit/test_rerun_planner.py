"""Tests for local matrix rerun planner."""

from __future__ import annotations

import json
from pathlib import Path

from fsmreasonbench.runners.pilot_models import model_dir_name
from fsmreasonbench.runners.rerun_planner import (
    MANDATORY_MAX_EXTRACTABLE,
    build_rerun_plan,
    build_track_pilot_command,
    group_rerun_cells,
    scan_matrix_integrity,
    write_rerun_plan_artifacts,
    MatrixCellRef,
)


def _write_scores(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def _score_row(
    *,
    item_id: str,
    family: str = "C2",
    extractable: bool,
    parse_errors: list[str] | None = None,
) -> dict:
    return {
        "item_id": item_id,
        "family": family,
        "extractable": extractable,
        "failure_stage": "not_extractable" if not extractable else "verdict_wrong",
        "parse_errors": parse_errors or [],
        "verdict_correct": True if extractable else None,
        "certificate_valid": False if extractable else None,
        "fully_correct": False,
    }


def test_group_rerun_cells_merges_tracks_and_temperatures() -> None:
    cells = (
        MatrixCellRef("llama3.1:8b", "C2", 0.2, "R1"),
        MatrixCellRef("llama3.1:8b", "C2", 0.2, "R2"),
        MatrixCellRef("llama3.1:8b", "C2", 0.7, "R1"),
        MatrixCellRef("llama3.1:8b", "C2", 0.7, "R2"),
    )
    groups = group_rerun_cells(cells, tier="mandatory")
    assert len(groups) == 1
    group = groups[0]
    assert group.tracks == ("R1", "R2")
    assert group.temperatures == (0.2, 0.7)
    assert len(group.cells) == 4


def test_scan_matrix_integrity_classifies_missing_and_partial(tmp_path: Path) -> None:
    model = "llama3.1:8b"
    model_dir = model_dir_name(model)
    partial_dir = tmp_path / model_dir / "C2" / "temp_0.2" / "R1"
    _write_scores(
        partial_dir / "scores.jsonl",
        [_score_row(item_id=f"i{i}", extractable=i == 0) for i in range(4)],
    )
    safe_dir = tmp_path / model_dir / "C2" / "temp_0" / "R0"
    _write_scores(
        safe_dir / "scores.jsonl",
        [_score_row(item_id=f"s{i}", extractable=True) for i in range(20)],
    )

    snapshots = scan_matrix_integrity(
        tmp_path,
        models=(model,),
        families=("C2",),
        tracks=("R0", "R1"),
        temperatures=(0.0, 0.2),
        max_items=20,
    )
    by_key = {(s.ref.track, s.ref.temperature): s for s in snapshots}
    assert by_key[("R1", 0.2)].tier == "partial"
    assert by_key[("R0", 0.0)].tier == "safe"
    assert by_key[("R1", 0.0)].tier == "missing"


def test_build_rerun_plan_mandatory_and_recommended(tmp_path: Path) -> None:
    model = "mistral-nemo:12b"
    model_dir = model_dir_name(model)

    mandatory_dir = tmp_path / model_dir / "C2" / "temp_0.2" / "R1"
    _write_scores(
        mandatory_dir / "scores.jsonl",
        [
            _score_row(
                item_id=f"m{i}",
                extractable=False,
                parse_errors=["ollama request failed: Connection refused"],
            )
            for i in range(20)
        ],
    )

    recommended_dir = tmp_path / model_dir / "F1" / "temp_0" / "R2"
    _write_scores(
        recommended_dir / "scores.jsonl",
        [_score_row(item_id=f"r{i}", family="F1", extractable=i < 8) for i in range(20)],
    )

    partial_dir = tmp_path / model_dir / "C2" / "temp_0" / "R1"
    _write_scores(
        partial_dir / "scores.jsonl",
        [_score_row(item_id=f"p{i}", extractable=False) for i in range(4)],
    )

    plan = build_rerun_plan(
        tmp_path,
        models=(model,),
        families=("C2", "F1"),
        tracks=("R0", "R1", "R2"),
        temperatures=(0.0, 0.2),
        max_items=20,
    )

    mandatory_cells = {
        (ref.model, ref.family, ref.temperature, ref.track)
        for group in plan.mandatory_groups
        for ref in group.cells
    }
    assert ("mistral-nemo:12b", "C2", 0.2, "R1") in mandatory_cells
    assert ("mistral-nemo:12b", "C2", 0.0, "R1") in mandatory_cells

    recommended_cells = {
        (ref.model, ref.family, ref.temperature, ref.track)
        for group in plan.recommended_groups
        for ref in group.cells
    }
    assert ("mistral-nemo:12b", "F1", 0.0, "R2") in mandatory_cells
    assert ("mistral-nemo:12b", "F1", 0.0, "R2") not in recommended_cells


def test_build_track_pilot_command_includes_flags(tmp_path: Path) -> None:
    command = build_track_pilot_command(
        models=("qwen2.5-coder:7b",),
        families=("C2",),
        tracks=("R1", "R2"),
        temperatures=(0.0, 0.2),
        out_dir=tmp_path,
        max_items=20,
        timeout=900.0,
        incremental_safe=True,
    )
    assert "--retry-failed" in command
    assert "--incremental-safe" in command
    assert "--tracks R1,R2" in command.replace("\\", "")
    assert "0,0.2" in command.replace("\\", "").replace("\n", " ")


def test_write_rerun_plan_artifacts(tmp_path: Path) -> None:
    model = "gemma2:9b"
    model_dir = model_dir_name(model)
    _write_scores(
        tmp_path / model_dir / "C2" / "temp_0" / "R0" / "scores.jsonl",
        [_score_row(item_id=f"x{i}", extractable=False) for i in range(MANDATORY_MAX_EXTRACTABLE - 1)],
    )

    plan = build_rerun_plan(
        tmp_path,
        models=(model,),
        families=("C2",),
        tracks=("R0",),
        temperatures=(0.0,),
        max_items=MANDATORY_MAX_EXTRACTABLE - 1,
    )
    out_dir = tmp_path / "rerun_plans"
    paths = write_rerun_plan_artifacts(
        plan,
        out_dir,
        timeout=120.0,
        incremental_safe=True,
    )
    assert Path(paths["mandatory_sh"]).exists()
    assert Path(paths["recommended_sh"]).exists()
    assert Path(paths["plan_json"]).exists()
    payload = json.loads(Path(paths["plan_json"]).read_text(encoding="utf-8"))
    assert payload["tier_counts"]["unsafe"] == 1
