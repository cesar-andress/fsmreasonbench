"""Local matrix temperature path and repair tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fsmreasonbench.runners.experiment_cells import mark_cell_running
from fsmreasonbench.runners.experiment_status import scan_experiment_status
from fsmreasonbench.runners.local_matrix_paths import (
    apply_repair_actions,
    infer_temperature_from_artifacts,
    plan_repair_actions,
    scan_misplaced_cells,
)
from fsmreasonbench.runners.track_pilot_models import (
    TrackPilotModelsConfig,
    apply_incremental_safe,
    build_cell_dir,
    infer_matrix_layout,
    run_track_pilot_models,
    temperature_dir_name,
)


def test_build_cell_dir_includes_temp_in_matrix_layout() -> None:
    path = build_cell_dir(
        Path("runs/local_matrix_v1"),
        "llama3.1:8b",
        "C2",
        0.0,
        "R1",
        matrix_layout=True,
    )
    assert path == Path("runs/local_matrix_v1/llama3.1_8b/C2/temp_0/R1")


def test_temperature_dir_name_stable() -> None:
    assert temperature_dir_name(0.0) == "temp_0"
    assert temperature_dir_name(0) == "temp_0"
    assert temperature_dir_name(0.2) == "temp_0.2"
    assert temperature_dir_name(0.7) == "temp_0.7"


def test_infer_matrix_layout_from_out_dir_name() -> None:
    assert infer_matrix_layout("runs/local_matrix_v1") is True
    assert infer_matrix_layout("runs/track_pilot_v1") is False


def test_incremental_safe_writes_to_temp_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Path] = {}

    def fake_batch(*, items, generate, run_dir, model, family, track, temperature, config, item_timeout):
        captured["run_dir"] = run_dir
        summary = {
            "n": 1,
            "extractability_rate": 1.0,
            "verdict_accuracy": 1.0,
            "certificate_valid_rate": 1.0,
            "fully_correct_rate": 1.0,
            "tool_invocation_rate": 0.0,
            "average_tool_calls_per_item": 0.0,
        }
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
        (run_dir / "scores.jsonl").write_text('{"item_id":"x"}\n', encoding="utf-8")

    monkeypatch.setattr(
        "fsmreasonbench.runners.track_pilot_models._run_cell_batch",
        fake_batch,
    )
    monkeypatch.setattr(
        "fsmreasonbench.runners.track_pilot_models._load_family_items",
        lambda _cfg: {"C2": []},
    )
    monkeypatch.setattr("fsmreasonbench.runners.track_pilot_models.time.sleep", lambda _s: None)

    root = tmp_path / "local_matrix_v1"
    config = apply_incremental_safe(
        TrackPilotModelsConfig(
            models=("llama3.1:8b",),
            families=("C2",),
            tracks=("R1",),
            c2_items_path=".",
            f1_items_path=".",
            out_dir=root,
            temperatures=(0.0,),
            matrix_layout=True,
            incremental_safe=True,
            skip_completed=False,
        )
    )
    run_track_pilot_models(config, lambda _m, _t: lambda *_a, **_k: "{}")
    assert captured["run_dir"] == root / "llama3.1_8b" / "C2" / "temp_0" / "R1"


def test_retry_failed_uses_temp_specific_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Path] = {}

    def fake_batch(*, items, generate, run_dir, model, family, track, temperature, config, item_timeout):
        captured["run_dir"] = run_dir
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "summary.json").write_text('{"n":1}', encoding="utf-8")
        (run_dir / "scores.jsonl").write_text('{"item_id":"x"}\n', encoding="utf-8")

    monkeypatch.setattr("fsmreasonbench.runners.track_pilot_models._run_cell_batch", fake_batch)
    monkeypatch.setattr("fsmreasonbench.runners.track_pilot_models._load_family_items", lambda _cfg: {"C2": []})
    monkeypatch.setattr("fsmreasonbench.runners.track_pilot_models.time.sleep", lambda _s: None)

    root = tmp_path / "local_matrix_v1"
    config = TrackPilotModelsConfig(
        models=("llama3.1:8b",),
        families=("C2",),
        tracks=("R1",),
        c2_items_path=".",
        f1_items_path=".",
        out_dir=root,
        temperatures=(0.2,),
        matrix_layout=True,
        retry_failed=True,
        skip_completed=True,
    )
    run_track_pilot_models(config, lambda _m, _t: lambda *_a, **_k: "{}")
    assert captured["run_dir"] == root / "llama3.1_8b" / "C2" / "temp_0.2" / "R1"


def test_partial_resume_uses_temp_specific_path(tmp_path: Path) -> None:
    run_dir = tmp_path / "local_matrix_v1" / "mock" / "C2" / "temp_0" / "R0"
    run_dir.mkdir(parents=True)
    (run_dir / "scores.jsonl").write_text('{"item_id":"item-0"}\n', encoding="utf-8")
    assert infer_temperature_from_artifacts(run_dir) is None
    mark_cell_running(
        run_dir,
        model="mock",
        model_dir="mock",
        family="C2",
        track="R0",
        temperature=0.0,
        item_source="/items.jsonl",
        config_hash="abc",
        max_items=20,
    )
    assert infer_temperature_from_artifacts(run_dir) == 0.0


def test_experiment_status_detects_misplaced_path(tmp_path: Path) -> None:
    root = tmp_path / "local_matrix_v1"
    misplaced = root / "llama3.1_8b" / "C2" / "R1"
    misplaced.mkdir(parents=True)
    mark_cell_running(
        misplaced,
        model="llama3.1:8b",
        model_dir="llama3.1_8b",
        family="C2",
        track="R1",
        temperature=0.0,
        item_source="/items.jsonl",
        config_hash="abc",
        max_items=20,
    )
    (misplaced / "scores.jsonl").write_text('{"item_id":"x"}\n', encoding="utf-8")
    (root / "combined_summary.json").write_text(
        json.dumps({"experiment": "local_matrix", "models": ["llama3.1:8b"]}),
        encoding="utf-8",
    )

    result = scan_experiment_status(
        root,
        models=("llama3.1:8b",),
        families=("C2",),
        tracks=("R1",),
        temperatures=(0.0,),
    )
    assert result.status_counts["missing"] == 1
    assert result.status_counts["misplaced_running"] == 1
    assert result.misplaced_cells[0]["expected_run_dir"].endswith("/temp_0/R1")


def test_experiment_status_detects_missing_expected_path(tmp_path: Path) -> None:
    root = tmp_path / "local_matrix_v1"
    root.mkdir()
    (root / "combined_summary.json").write_text(
        json.dumps({"experiment": "local_matrix", "models": ["mock"]}),
        encoding="utf-8",
    )
    result = scan_experiment_status(
        root,
        models=("mock",),
        families=("C2",),
        tracks=("R1",),
        temperatures=(0.0,),
    )
    assert result.status_counts["missing"] == 1


def test_repair_dry_run_reports_intended_move(tmp_path: Path) -> None:
    root = tmp_path / "local_matrix_v1"
    misplaced = root / "llama3.1_8b" / "C2" / "R1"
    misplaced.mkdir(parents=True)
    mark_cell_running(
        misplaced,
        model="llama3.1:8b",
        model_dir="llama3.1_8b",
        family="C2",
        track="R1",
        temperature=0.0,
        item_source="/items.jsonl",
        config_hash="abc",
        max_items=20,
    )
    (misplaced / "results.jsonl").write_text("{}\n", encoding="utf-8")
    actions = plan_repair_actions(root, models=("llama3.1:8b",), families=("C2",), tracks=("R1",))
    assert actions[0].status == "planned"
    assert actions[0].target_dir == root / "llama3.1_8b" / "C2" / "temp_0" / "R1"
    dry = apply_repair_actions(actions, dry_run=True)
    assert dry[0].status == "planned"
    assert misplaced.exists()


def test_repair_apply_moves_misplaced_outputs_safely(tmp_path: Path) -> None:
    root = tmp_path / "local_matrix_v1"
    misplaced = root / "llama3.1_8b" / "C2" / "R1"
    misplaced.mkdir(parents=True)
    mark_cell_running(
        misplaced,
        model="llama3.1:8b",
        model_dir="llama3.1_8b",
        family="C2",
        track="R1",
        temperature=0.0,
        item_source="/items.jsonl",
        config_hash="abc",
        max_items=20,
    )
    (misplaced / "scores.jsonl").write_text('{"item_id":"x"}\n', encoding="utf-8")
    actions = plan_repair_actions(root, models=("llama3.1:8b",), families=("C2",), tracks=("R1",))
    applied = apply_repair_actions(actions, dry_run=False)
    target = root / "llama3.1_8b" / "C2" / "temp_0" / "R1"
    assert applied[0].status == "applied"
    assert target.exists()
    assert (target / "scores.jsonl").exists()
    assert not misplaced.exists()


def test_repair_refuses_ambiguous_moves(tmp_path: Path) -> None:
    root = tmp_path / "local_matrix_v1"
    misplaced = root / "llama3.1_8b" / "C2" / "R1"
    misplaced.mkdir(parents=True)
    (misplaced / "scores.jsonl").write_text('{"item_id":"x"}\n', encoding="utf-8")
    actions = plan_repair_actions(root, models=("llama3.1:8b",), families=("C2",), tracks=("R1",))
    assert actions[0].status == "ambiguous"
    applied = apply_repair_actions(actions, dry_run=False)
    assert applied[0].status == "ambiguous"
    assert misplaced.exists()


def test_scan_misplaced_cells_finds_legacy_layout(tmp_path: Path) -> None:
    root = tmp_path / "local_matrix_v1"
    legacy = root / "llama3.1_8b" / "C2" / "R1"
    legacy.mkdir(parents=True)
    (legacy / "results.jsonl").write_text("{}\n", encoding="utf-8")
    rows = scan_misplaced_cells(root, models=("llama3.1:8b",), families=("C2",), tracks=("R1",))
    assert len(rows) == 1
    assert rows[0]["extended_status"] == "misplaced_partial"
