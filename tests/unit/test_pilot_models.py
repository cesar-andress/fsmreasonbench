"""Multi-model pilot runner tests with mocked Ollama client."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fsmreasonbench.cli.run_pilot_models import main as run_pilot_models_main
from fsmreasonbench.evaluator.jsonl import read_jsonl
from fsmreasonbench.generator.reachability import generate_reachability_item
from fsmreasonbench.generator.separation import (
    SeparationGeneratorConfig,
    generate_separation_item,
)
from fsmreasonbench.runners.pilot_models import (
    PilotModelsConfig,
    model_dir_name,
    render_pilot_models_report,
    run_pilot_models,
)


def _write_items_jsonl(path: Path, items) -> None:
    path.write_text(
        "\n".join(json.dumps(item.to_full_dict(), sort_keys=True) for item in items) + "\n",
        encoding="utf-8",
    )


def test_model_dir_name_sanitizes_colons() -> None:
    assert model_dir_name("qwen2.5-coder:7b") == "qwen2.5-coder_7b"


def test_run_pilot_models_writes_per_model_family_outputs(tmp_path: Path) -> None:
    c2_item = generate_reachability_item(42)
    f1_item = generate_separation_item(
        43,
        SeparationGeneratorConfig(min_distinguishing_trace_length=1),
    )
    c2_items_path = tmp_path / "c2_items.jsonl"
    f1_items_path = tmp_path / "f1_items.jsonl"
    _write_items_jsonl(c2_items_path, [c2_item])
    _write_items_jsonl(f1_items_path, [f1_item])

    c2_submission = {
        "item_id": c2_item.item_id,
        "verdict": c2_item.answer_key["verdict"],
        "certificate": c2_item.answer_key["certificate"],
    }
    f1_submission = {
        "item_id": f1_item.item_id,
        "verdict": f1_item.answer_key["verdict"],
        "certificate": f1_item.answer_key["certificate"],
    }

    def generate_factory(model: str):
        def fake_generate(
            prompt: str,
            *,
            model: str,
            temperature: float,
            timeout: float,
        ) -> str:
            assert model in {"mock-a", "mock-b"}
            if "equivalent" in prompt.lower():
                return json.dumps(f1_submission)
            return json.dumps(c2_submission)

        return fake_generate

    out_dir = tmp_path / "pilot_v1"
    result = run_pilot_models(
        PilotModelsConfig(
            models=("mock-a", "mock-b"),
            c2_items_path=c2_items_path,
            f1_items_path=f1_items_path,
            out_dir=out_dir,
            max_items=1,
        ),
        generate_factory,
    )

    assert len(result.rows) == 4
    for model in ("mock-a", "mock-b"):
        model_dir = model_dir_name(model)
        for family in ("C2", "F1"):
            run_dir = out_dir / model_dir / family
            assert (run_dir / "scores.jsonl").exists()
            assert (run_dir / "results.jsonl").exists()
            assert (run_dir / "transcripts").is_dir()
            assert (run_dir / "summary.json").exists()

    assert (out_dir / "combined_summary.json").exists()
    assert (out_dir / "combined_summary.csv").exists()
    assert (out_dir / "report.md").exists()

    c2_rows = [row for row in result.rows if row["family"] == "C2"]
    assert all(row["fully_correct_rate"] == 1.0 for row in c2_rows)
    report = (out_dir / "report.md").read_text(encoding="utf-8")
    assert "## C2 comparison" in report
    assert "## F1 comparison" in report
    assert "`mock-a`" in report


def test_render_pilot_models_report_includes_failure_stage_table() -> None:
    rows = [
        {
            "model": "mock-a",
            "family": "C2",
            "n": 2,
            "extractability_rate": 1.0,
            "verdict_accuracy": 0.5,
            "certificate_valid_rate": 0.5,
            "fully_correct_rate": 0.5,
            "failure_stage_counts": {
                "not_extractable": 0,
                "verdict_wrong": 1,
                "certificate_invalid": 0,
                "correct": 1,
            },
        }
    ]
    report = render_pilot_models_report(rows)
    assert "failure stage counts" in report
    assert "verdict_wrong" in report


def test_cli_run_pilot_models_with_mocked_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    c2_item = generate_reachability_item(7)
    f1_item = generate_separation_item(
        8,
        SeparationGeneratorConfig(min_distinguishing_trace_length=1),
    )
    c2_items_path = tmp_path / "c2_items.jsonl"
    f1_items_path = tmp_path / "f1_items.jsonl"
    _write_items_jsonl(c2_items_path, [c2_item])
    _write_items_jsonl(f1_items_path, [f1_item])

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
        "fsmreasonbench.cli.run_pilot_models.HttpOllamaClient",
        lambda config: FakeClient(),
    )

    out_dir = tmp_path / "cli_pilot"
    assert (
        run_pilot_models_main(
            [
                "--models",
                "mock-model",
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
    assert payload["runs"] == 2
    combined = json.loads((out_dir / "combined_summary.json").read_text(encoding="utf-8"))
    assert len(combined["rows"]) == 2
    scores = read_jsonl(out_dir / model_dir_name("mock-model") / "C2" / "scores.jsonl")
    assert scores[0]["failure_stage"] == "not_extractable"
