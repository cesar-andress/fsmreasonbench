"""Model capability-surface evaluation tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fsmreasonbench.cli.plot_capability_surface import main as plot_capability_surface_main
from fsmreasonbench.cli.run_capability_surface_models import main as run_capability_surface_models_main
from fsmreasonbench.evaluator.capability_surface_models import (
    CapabilitySurfaceModelsConfig,
    render_capability_surface_models_report,
    run_capability_surface_models,
)
from fsmreasonbench.evaluator.capability_surface_plots import plot_capability_surface
from fsmreasonbench.generator.reachability import generate_reachability_item
from fsmreasonbench.generator.separation import (
    SeparationGeneratorConfig,
    generate_separation_item,
)


def _submission_for_item(item) -> dict[str, object]:
    return {
        "item_id": item.item_id,
        "verdict": item.answer_key["verdict"],
        "certificate": item.answer_key["certificate"],
    }


def test_run_capability_surface_models_with_mocked_generate(tmp_path: Path) -> None:
    def generate_factory(model: str):
        def fake_generate(
            prompt: str,
            *,
            model: str,
            temperature: float,
            timeout: float,
        ) -> str:
            if "equivalent" in prompt.lower():
                item = generate_separation_item(
                    99,
                    SeparationGeneratorConfig(min_distinguishing_trace_length=1),
                )
            else:
                item = generate_reachability_item(98)
            return json.dumps(_submission_for_item(item))

        return fake_generate

    result = run_capability_surface_models(
        CapabilitySurfaceModelsConfig(
            models=("mock-a", "mock-b"),
            out_dir=tmp_path / "surface_models",
            families=("C2", "F1"),
            c2_levels=(1, 2),
            f1_levels=(1, 2),
            n_per_level=2,
            seed=5,
        ),
        generate_factory,
    )

    assert len(result.rows) == 2 * 2 * 2  # families × levels × models
    root = result.out_dir
    assert (root / "combined_summary.json").exists()
    assert (root / "combined_summary.csv").exists()
    assert (root / "report.md").exists()
    assert (root / "C2" / "min_witness_length_1" / "mock-a" / "scores.jsonl").exists()

    payload = json.loads((root / "combined_summary.json").read_text(encoding="utf-8"))
    row = payload["rows"][0]
    assert {"family", "difficulty_level", "model", "fully_correct_rate"} <= row.keys()


def test_render_capability_surface_models_report() -> None:
    rows = [
        {
            "family": "C2",
            "difficulty_level": 1,
            "model": "mock-a",
            "fully_correct_rate": 0.5,
            "verdict_accuracy": 0.6,
            "certificate_valid_rate": 0.4,
            "extractability_rate": 1.0,
        },
        {
            "family": "C2",
            "difficulty_level": 2,
            "model": "mock-a",
            "fully_correct_rate": 0.2,
            "verdict_accuracy": 0.3,
            "certificate_valid_rate": 0.2,
            "extractability_rate": 1.0,
        },
    ]
    report = render_capability_surface_models_report(rows)
    assert "# Model Capability Surface Report" in report
    assert "Fully correct rate" in report
    assert "`mock-a`" in report


def test_plot_capability_surface_writes_pngs(tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    summary_path = tmp_path / "combined_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "family": "C2",
                        "difficulty_level": 1,
                        "model": "mock-a",
                        "fully_correct_rate": 0.5,
                        "verdict_accuracy": 0.6,
                        "certificate_valid_rate": 0.4,
                        "extractability_rate": 1.0,
                    },
                    {
                        "family": "C2",
                        "difficulty_level": 2,
                        "model": "mock-a",
                        "fully_correct_rate": 0.2,
                        "verdict_accuracy": 0.3,
                        "certificate_valid_rate": 0.2,
                        "extractability_rate": 1.0,
                    },
                    {
                        "family": "F1",
                        "difficulty_level": 1,
                        "model": "mock-a",
                        "fully_correct_rate": 0.1,
                        "verdict_accuracy": 1.0,
                        "certificate_valid_rate": 0.1,
                        "extractability_rate": 1.0,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    written = plot_capability_surface(summary_path, tmp_path / "plots")
    names = {path.name for path in written}
    assert "fully_correct_vs_difficulty.png" in names
    assert "verdict_vs_difficulty.png" in names
    assert all(path.exists() for path in written)


def test_cli_run_capability_surface_models(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class FakeClient:
        def generate(
            self,
            prompt: str,
            *,
            model: str,
            temperature: float,
            timeout: float,
        ) -> str:
            return "NOT VALID JSON"

    monkeypatch.setattr(
        "fsmreasonbench.cli.run_capability_surface_models.HttpOllamaClient",
        lambda config: FakeClient(),
    )

    out_dir = tmp_path / "cli_surface_models"
    assert (
        run_capability_surface_models_main(
            [
                "--models",
                "mock-model",
                "--families",
                "C2",
                "--levels",
                "1",
                "--n-per-level",
                "1",
                "--seed",
                "3",
                "--out-dir",
                str(out_dir),
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["rows"] == 1
    assert (out_dir / "combined_summary.json").exists()


def test_cli_plot_capability_surface(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pytest.importorskip("matplotlib")
    summary_path = tmp_path / "combined_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "family": "C2",
                        "difficulty_level": 1,
                        "model": "mock-a",
                        "fully_correct_rate": 0.5,
                        "verdict_accuracy": 0.6,
                        "certificate_valid_rate": 0.4,
                        "extractability_rate": 1.0,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    plot_dir = tmp_path / "plots"
    assert (
        plot_capability_surface_main(
            [
                "--summary",
                str(summary_path),
                "--out-dir",
                str(plot_dir),
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert "fully_correct_vs_difficulty.png" in output
    assert (plot_dir / "fully_correct_vs_difficulty.png").exists()
