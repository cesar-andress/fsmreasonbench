"""Multi-model track pilot runner tests with fake Ollama client."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fsmreasonbench.cli.run_track_pilot_models import main as run_track_pilot_models_main
from fsmreasonbench.generator.reachability import generate_reachability_item
from fsmreasonbench.generator.separation import (
    SeparationGeneratorConfig,
    generate_separation_item,
)
from fsmreasonbench.runners.track_pilot_models import (
    TrackPilotModelsConfig,
    build_delegation_rows,
    build_track_row,
    cell_dir,
    is_cell_complete,
    run_track_pilot_models,
)
from fsmreasonbench.tracks.models import TrackId


def _make_fake_generate(c2_item, f1_item, track: TrackId):
    def fake_generate(
        prompt: str,
        *,
        model: str,
        temperature: float,
        timeout: float,
    ) -> str:
        _ = (model, temperature, timeout)
        item = f1_item if "equivalent" in prompt.lower() else c2_item
        if track == TrackId.R0:
            return json.dumps(
                {
                    "item_id": item.item_id,
                    "verdict": item.answer_key["verdict"],
                    "certificate": item.answer_key["certificate"],
                }
            )
        if "final_submission" in prompt.lower() or "tool result" in prompt.lower():
            return json.dumps(
                {
                    "phase": "final_submission",
                    "submission": {
                        "item_id": item.item_id,
                        "verdict": item.answer_key["verdict"],
                        "certificate": item.answer_key["certificate"],
                    },
                }
            )
        if track == TrackId.R1:
            return json.dumps(
                {
                    "phase": "tool_plan",
                    "tool_calls": [
                        {
                            "call_id": "1",
                            "tool": "step",
                            "inputs": {
                                "fsm_id": item.fsm.fsm_id,
                                "state": item.fsm.initial_state,
                                "symbol": item.fsm.input_alphabet[0],
                            },
                        }
                    ],
                }
            )
        if item.family == "F1":
            return json.dumps(
                {
                    "phase": "tool_plan",
                    "tool_calls": [
                        {
                            "call_id": "1",
                            "tool": "solver.distinguishing_certificate",
                            "inputs": {
                                "fsm_id_a": item.fsm.fsm_id,
                                "fsm_id_b": item.fsm_b.fsm_id,
                            },
                        }
                    ],
                }
            )
        return json.dumps(
            {
                "phase": "tool_plan",
                "tool_calls": [
                    {
                        "call_id": "1",
                        "tool": "solver.reachability_certificate",
                        "inputs": {
                            "fsm_id": item.fsm.fsm_id,
                            "target_state": item.question["target_state"],
                        },
                    }
                ],
            }
        )

    return fake_generate


def _make_factory(c2_item, f1_item):
    def generate_factory(model: str, temperature: float):
        _ = (model, temperature)

        def fake_generate(
            prompt: str,
            *,
            model: str,
            temperature: float,
            timeout: float,
        ) -> str:
            lowered = prompt.lower()
            if "final_submission" in lowered or "tool result" in lowered:
                track = TrackId.R2 if "solver" in lowered else TrackId.R1
            elif "solver." in lowered or "registered solver" in lowered:
                track = TrackId.R2
            elif "tool_plan" in lowered or '"step"' in lowered:
                track = TrackId.R1
            else:
                track = TrackId.R0
            return _make_fake_generate(c2_item, f1_item, track)(
                prompt,
                model=model,
                temperature=temperature,
                timeout=timeout,
            )

        return fake_generate

    return generate_factory


def _write_items_jsonl(path: Path, items) -> None:
    path.write_text(
        "\n".join(json.dumps(item.to_full_dict(), sort_keys=True) for item in items) + "\n",
        encoding="utf-8",
    )


@pytest.fixture
def pilot_items(tmp_path: Path):
    c2_item = generate_reachability_item(42)
    f1_item = generate_separation_item(
        43,
        SeparationGeneratorConfig(min_distinguishing_trace_length=1),
    )
    c2_items_path = tmp_path / "c2_items.jsonl"
    f1_items_path = tmp_path / "f1_items.jsonl"
    _write_items_jsonl(c2_items_path, [c2_item])
    _write_items_jsonl(f1_items_path, [f1_item])
    return c2_items_path, f1_items_path, c2_item, f1_item


def test_runner_creates_expected_directory_layout(tmp_path: Path, pilot_items) -> None:
    c2_items_path, f1_items_path, c2_item, f1_item = pilot_items
    out_dir = tmp_path / "track_pilot"
    result = run_track_pilot_models(
        TrackPilotModelsConfig(
            models=("mock-a",),
            families=("C2", "F1"),
            tracks=("R0", "R1"),
            c2_items_path=c2_items_path,
            f1_items_path=f1_items_path,
            out_dir=out_dir,
            max_items=1,
        ),
        _make_factory(c2_item, f1_item),
    )

    assert len(result.track_rows) == 4
    for family in ("C2", "F1"):
        for track in ("R0", "R1"):
            run_dir = cell_dir(out_dir, "mock-a", family, track, temperature=0.0)
            assert (run_dir / "results.jsonl").exists()
            assert (run_dir / "scores.jsonl").exists()
            assert (run_dir / "summary.json").exists()
            assert (run_dir / "transcripts").is_dir()

    assert (out_dir / "combined_summary.json").exists()
    assert (out_dir / "combined_summary.csv").exists()
    assert (out_dir / "report.md").exists()


def test_skip_completed_cells(tmp_path: Path, pilot_items) -> None:
    c2_items_path, f1_items_path, c2_item, f1_item = pilot_items
    invocations = {"count": 0}

    def generate_factory(model: str, temperature: float):
        _ = temperature
        base = _make_fake_generate(c2_item, f1_item, TrackId.R0)

        def counting_generate(
            prompt: str,
            *,
            model: str,
            temperature: float,
            timeout: float,
        ) -> str:
            invocations["count"] += 1
            return base(prompt, model=model, temperature=temperature, timeout=timeout)

        return counting_generate

    config = TrackPilotModelsConfig(
        models=("mock-a",),
        families=("C2",),
        tracks=("R0",),
        c2_items_path=c2_items_path,
        f1_items_path=f1_items_path,
        out_dir=tmp_path / "skip_test",
        max_items=1,
        skip_completed=True,
    )
    run_track_pilot_models(config, generate_factory)
    first_count = invocations["count"]
    assert first_count > 0
    run_track_pilot_models(config, generate_factory)
    assert invocations["count"] == first_count


def test_force_reruns_completed_cells(tmp_path: Path, pilot_items) -> None:
    c2_items_path, f1_items_path, c2_item, f1_item = pilot_items
    invocations = {"count": 0}

    def generate_factory(model: str, temperature: float):
        _ = temperature
        base = _make_fake_generate(c2_item, f1_item, TrackId.R0)

        def counting_generate(
            prompt: str,
            *,
            model: str,
            temperature: float,
            timeout: float,
        ) -> str:
            invocations["count"] += 1
            return base(prompt, model=model, temperature=temperature, timeout=timeout)

        return counting_generate

    config = TrackPilotModelsConfig(
        models=("mock-a",),
        families=("C2",),
        tracks=("R0",),
        c2_items_path=c2_items_path,
        f1_items_path=f1_items_path,
        out_dir=tmp_path / "force_test",
        max_items=1,
        skip_completed=True,
    )
    run_track_pilot_models(config, generate_factory)
    first_count = invocations["count"]
    config_force = TrackPilotModelsConfig(
        models=config.models,
        families=config.families,
        tracks=config.tracks,
        c2_items_path=config.c2_items_path,
        f1_items_path=config.f1_items_path,
        out_dir=config.out_dir,
        max_items=config.max_items,
        skip_completed=False,
    )
    run_track_pilot_models(config_force, generate_factory)
    assert invocations["count"] > first_count


def test_failed_cell_recorded_not_fatal(tmp_path: Path, pilot_items) -> None:
    c2_items_path, f1_items_path, c2_item, f1_item = pilot_items

    def generate_factory(model: str, temperature: float):
        _ = temperature
        def fake_generate(
            prompt: str,
            *,
            model: str,
            temperature: float,
            timeout: float,
        ) -> str:
            if model == "bad-model":
                raise RuntimeError("simulated ollama failure")
            return _make_fake_generate(c2_item, f1_item, TrackId.R0)(
                prompt,
                model=model,
                temperature=temperature,
                timeout=timeout,
            )

        return fake_generate

    result = run_track_pilot_models(
        TrackPilotModelsConfig(
            models=("bad-model", "good-model"),
            families=("C2",),
            tracks=("R0",),
            c2_items_path=c2_items_path,
            f1_items_path=f1_items_path,
            out_dir=tmp_path / "fail_test",
            max_items=1,
        ),
        generate_factory,
    )

    assert len(result.failed_cells) == 1
    assert result.failed_cells[0]["model"] == "bad-model"
    good_rows = [
        row
        for row in result.track_rows
        if row["model"] == "good-model" and row.get("status") == "completed"
    ]
    assert len(good_rows) == 1
    assert good_rows[0]["fully_correct_rate"] == 1.0


def test_combined_summary_contains_required_fields(tmp_path: Path, pilot_items) -> None:
    c2_items_path, f1_items_path, c2_item, f1_item = pilot_items

    out_dir = tmp_path / "summary_fields"
    run_track_pilot_models(
        TrackPilotModelsConfig(
            models=("mock-a",),
            families=("C2",),
            tracks=("R0", "R1", "R2"),
            c2_items_path=c2_items_path,
            f1_items_path=f1_items_path,
            out_dir=out_dir,
            max_items=1,
        ),
        _make_factory(c2_item, f1_item),
    )
    payload = json.loads((out_dir / "combined_summary.json").read_text(encoding="utf-8"))
    row = payload["track_rows"][0]
    for field in (
        "model",
        "family",
        "track",
        "n",
        "extractability_rate",
        "verdict_accuracy",
        "certificate_valid_rate",
        "fully_correct_rate",
        "tool_invocation_rate",
        "average_tool_calls_per_item",
        "failure_stage_counts",
        "track_failure_counts",
    ):
        assert field in row, field
    assert payload["delegation_rows"]


def test_delegation_gaps_computed_correctly() -> None:
    rows = [
        build_track_row(
            {
                "n": 2,
                "verdict_accuracy": 0.0,
                "certificate_valid_rate": 0.0,
                "fully_correct_rate": 0.0,
                "extractability_rate": 1.0,
                "failure_stage_counts": {},
                "track_failure_counts": {},
            },
            model="mock",
            family="C2",
            track="R0",
            temperature=0.0,
            cohort_id="test",
            run_dir=Path("."),
        ),
        build_track_row(
            {
                "n": 2,
                "verdict_accuracy": 0.5,
                "certificate_valid_rate": 0.5,
                "fully_correct_rate": 0.5,
                "extractability_rate": 1.0,
                "failure_stage_counts": {},
                "track_failure_counts": {},
            },
            model="mock",
            family="C2",
            track="R1",
            temperature=0.0,
            cohort_id="test",
            run_dir=Path("."),
        ),
        build_track_row(
            {
                "n": 2,
                "verdict_accuracy": 1.0,
                "certificate_valid_rate": 1.0,
                "fully_correct_rate": 1.0,
                "extractability_rate": 1.0,
                "failure_stage_counts": {},
                "track_failure_counts": {},
            },
            model="mock",
            family="C2",
            track="R2",
            temperature=0.0,
            cohort_id="test",
            run_dir=Path("."),
        ),
    ]
    delegation = build_delegation_rows(rows)[0]
    assert delegation["delta_R1_minus_R0_verdict_accuracy"] == pytest.approx(0.5)
    assert delegation["delta_R2_minus_R0_fully_correct_rate"] == pytest.approx(1.0)
    assert delegation["delta_R2_minus_R1_fully_correct_rate"] == pytest.approx(0.5)


def test_report_includes_track_comparison_tables(tmp_path: Path, pilot_items) -> None:
    c2_items_path, f1_items_path, c2_item, f1_item = pilot_items

    out_dir = tmp_path / "report_test"
    run_track_pilot_models(
        TrackPilotModelsConfig(
            models=("mock-a",),
            families=("C2",),
            tracks=("R0", "R1", "R2"),
            c2_items_path=c2_items_path,
            f1_items_path=f1_items_path,
            out_dir=out_dir,
            max_items=1,
        ),
        _make_factory(c2_item, f1_item),
    )
    report = (out_dir / "report.md").read_text(encoding="utf-8")
    assert "## Overview" in report
    assert "## C2 — per-track metrics" in report
    assert "## C2 — delegation gaps by temperature" in report
    assert "## C2 — failure movement" in report
    assert "## Interpretation" in report
    assert "exploratory" in report.lower()


def test_is_cell_complete_detects_summary(tmp_path: Path) -> None:
    run_dir = tmp_path / "cell"
    run_dir.mkdir()
    assert not is_cell_complete(run_dir)
    (run_dir / "summary.json").write_text("{}", encoding="utf-8")
    assert is_cell_complete(run_dir)


def test_cli_with_mocked_client(
    tmp_path: Path,
    pilot_items,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    c2_items_path, f1_items_path, c2_item, f1_item = pilot_items

    class FakeClient:
        def generate(
            self,
            prompt: str,
            *,
            model: str,
            temperature: float,
            timeout: float,
        ) -> str:
            return _make_fake_generate(c2_item, f1_item, TrackId.R0)(
                prompt,
                model=model,
                temperature=temperature,
                timeout=timeout,
            )

    monkeypatch.setattr(
        "fsmreasonbench.cli.run_track_pilot_models.HttpOllamaClient",
        lambda config: FakeClient(),
    )

    out_dir = tmp_path / "cli_pilot"
    assert (
        run_track_pilot_models_main(
            [
                "--models",
                "mock-model",
                "--families",
                "C2",
                "--tracks",
                "R0",
                "--c2-items",
                str(c2_items_path),
                "--f1-items",
                str(f1_items_path),
                "--max-items",
                "1",
                "--out-dir",
                str(out_dir),
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["cells_completed"] == 1
