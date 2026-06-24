"""Ollama batch runner tests with mocked client."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fsmreasonbench.cli.run_ollama_batch import main as run_ollama_batch_main
from fsmreasonbench.evaluator.jsonl import load_items_jsonl, read_jsonl
from fsmreasonbench.generator.reachability import generate_reachability_item
from fsmreasonbench.generator.separation import (
    SeparationGeneratorConfig,
    generate_separation_item,
)
from fsmreasonbench.runners.ollama_batch import OllamaBatchConfig, run_ollama_batch
from fsmreasonbench.runners.prompts import render_prompt
from fsmreasonbench.runners.response_extract import extract_submission_payload


def _write_items_jsonl(path: Path, items) -> None:
    path.write_text(
        "\n".join(json.dumps(item.to_full_dict(), sort_keys=True) for item in items) + "\n",
        encoding="utf-8",
    )


def test_render_c2_prompt_contains_target() -> None:
    item = generate_reachability_item(42)
    prompt = render_prompt(item)
    assert item.question["target_state"] in prompt
    assert "trace_witness" in prompt


def test_render_f1_prompt_contains_equivalence_question() -> None:
    item = generate_separation_item(
        42,
        SeparationGeneratorConfig(min_distinguishing_trace_length=1),
    )
    prompt = render_prompt(item)
    assert "equivalent" in prompt.lower()
    assert "distinguishing_trace" in prompt


def test_extract_submission_from_json_fence() -> None:
    payload = {
        "item_id": "abc",
        "verdict": False,
        "certificate": {"certificate_type": "distinguishing_trace", "payload": {}},
    }
    raw = "Here is my answer:\n```json\n" + json.dumps(payload) + "\n```"
    extracted = extract_submission_payload(raw)
    assert extracted == payload


def test_run_ollama_batch_with_mocked_client(tmp_path: Path) -> None:
    item = generate_reachability_item(42)
    submission = {
        "item_id": item.item_id,
        "verdict": item.answer_key["verdict"],
        "certificate": item.answer_key["certificate"],
    }

    def fake_generate(
        prompt: str,
        *,
        model: str,
        temperature: float,
        timeout: float,
    ) -> str:
        assert model == "mock-model"
        assert "reachability" in prompt.lower() or "reachable" in prompt.lower()
        return json.dumps(submission)

    out_path = tmp_path / "results.jsonl"
    result = run_ollama_batch(
        [item],
        fake_generate,
        out_path,
        OllamaBatchConfig(model="mock-model"),
        out_dir=tmp_path / "run",
    )
    assert result.summary["fully_correct_rate"] == 1.0
    records = read_jsonl(tmp_path / "run" / "results.jsonl")
    assert len(records) == 1
    assert records[0]["scoring_record"]["fully_correct"] is True
    assert (tmp_path / "run" / "transcripts" / f"{item.item_id}.json").exists()
    assert (tmp_path / "run" / "scores.jsonl").exists()
    assert (tmp_path / "run" / "summary.json").exists()


def test_run_ollama_batch_f1_with_mocked_client(tmp_path: Path) -> None:
    item = generate_separation_item(
        42,
        SeparationGeneratorConfig(min_distinguishing_trace_length=1),
    )
    submission = {
        "item_id": item.item_id,
        "verdict": item.answer_key["verdict"],
        "certificate": item.answer_key["certificate"],
    }

    def fake_generate(
        prompt: str,
        *,
        model: str,
        temperature: float,
        timeout: float,
    ) -> str:
        return json.dumps(submission)

    result = run_ollama_batch(
        [item],
        fake_generate,
        tmp_path / "f1_results.jsonl",
        OllamaBatchConfig(model="mock-model"),
        out_dir=tmp_path / "f1_run",
    )
    assert result.summary["family"] == "F1"
    assert result.summary["fully_correct_rate"] == 1.0


def test_run_ollama_batch_respects_max_items(tmp_path: Path) -> None:
    items = [generate_reachability_item(seed) for seed in (1, 2, 3)]

    def fake_generate(
        prompt: str,
        *,
        model: str,
        temperature: float,
        timeout: float,
    ) -> str:
        return "NOT VALID"

    run_ollama_batch(
        items,
        fake_generate,
        tmp_path / "limited.jsonl",
        OllamaBatchConfig(model="mock-model", max_items=2),
        out_dir=tmp_path / "limited",
    )
    assert len(read_jsonl(tmp_path / "limited" / "results.jsonl")) == 2


def test_cli_with_mocked_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    item = generate_reachability_item(7)
    items_path = tmp_path / "items.jsonl"
    _write_items_jsonl(items_path, [item])

    submission = {
        "item_id": item.item_id,
        "verdict": item.answer_key["verdict"],
        "certificate": item.answer_key["certificate"],
    }

    class FakeClient:
        def generate(
            self,
            prompt: str,
            *,
            model: str,
            temperature: float,
            timeout: float,
        ) -> str:
            return json.dumps(submission)

    monkeypatch.setattr(
        "fsmreasonbench.cli.run_ollama_batch.HttpOllamaClient",
        lambda config: FakeClient(),
    )

    out_path = tmp_path / "cli_results.jsonl"
    assert (
        run_ollama_batch_main(
            [
                "--model",
                "mock-model",
                "--items",
                str(items_path),
                "--out",
                str(out_path),
                "--out-dir",
                str(tmp_path / "cli_run"),
            ]
        )
        == 0
    )
    loaded = load_items_jsonl(items_path)
    assert len(loaded) == 1
    records = read_jsonl(tmp_path / "cli_run" / "results.jsonl")
    assert records[0]["scoring_record"]["fully_correct"] is True
