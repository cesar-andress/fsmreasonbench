"""Tests for Ollama temperature diagnostic payloads."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fsmreasonbench.runners.ollama import build_ollama_generate_request_body
from fsmreasonbench.runners.ollama_temperature_diagnostic import run_temperature_diagnostic


def test_build_ollama_generate_request_body_sets_temperature() -> None:
    body = build_ollama_generate_request_body(
        model="mock-model",
        prompt="hello",
        temperature=0.7,
    )
    assert body["model"] == "mock-model"
    assert body["prompt"] == "hello"
    assert body["stream"] is False
    assert body["options"] == {"temperature": 0.7}


@pytest.mark.parametrize(
    ("temperature", "expected"),
    [(0.0, 0.0), (0.2, 0.2), (0.7, 0.7)],
)
def test_payload_temperature_matches_requested(temperature: float, expected: float) -> None:
    body = build_ollama_generate_request_body(
        model="mock-model",
        prompt="probe",
        temperature=temperature,
    )
    assert body["options"]["temperature"] == expected


def test_run_temperature_diagnostic_dry_run_payloads_differ(tmp_path: Path) -> None:
    result = run_temperature_diagnostic(
        model="mock-model",
        temperatures=(0.0, 0.2, 0.7),
        out_dir=tmp_path / "diag",
        dry_run=True,
    )

    assert result.payloads_differ is True
    assert result.payload_temperatures == (0.0, 0.2, 0.7)

    log_records = [
        json.loads(line)
        for line in (tmp_path / "diag" / "diagnostic_log.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(log_records) == 3
    assert {record["raw_request_payload"]["options"]["temperature"] for record in log_records} == {
        0.0,
        0.2,
        0.7,
    }

    summary = json.loads((tmp_path / "diag" / "summary.json").read_text(encoding="utf-8"))
    assert summary["payloads_differ"] is True
    assert summary["payload_temperatures"] == [0.0, 0.2, 0.7]
