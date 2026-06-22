"""Diagnostic runner to verify Ollama temperature propagation."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from fsmreasonbench.runners.ollama import (
    HttpOllamaClient,
    OllamaConfig,
    build_ollama_generate_request_body,
)

DEFAULT_DIAGNOSTIC_PROMPT = "Reply with exactly one word: alpha"
DEFAULT_DIAGNOSTIC_TEMPERATURES = (0.0, 0.2, 0.7)


@dataclass(frozen=True, slots=True)
class TemperatureDiagnosticRecord:
    model: str
    temperature: float
    raw_request_payload: dict[str, Any]
    dry_run: bool
    response_preview: str | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class TemperatureDiagnosticResult:
    out_dir: Path
    records: tuple[TemperatureDiagnosticRecord, ...]
    payloads_differ: bool
    payload_temperatures: tuple[float, ...]


def _make_generate_factory(
    *,
    base_url: str,
    model: str,
    temperature: float,
    timeout: float,
):
    """Mirror ``run_track_pilot_models`` client wiring."""

    client = HttpOllamaClient(
        OllamaConfig(
            base_url=base_url,
            model=model,
            temperature=temperature,
            timeout=timeout,
        )
    )
    return client.generate


def run_temperature_diagnostic(
    *,
    model: str,
    temperatures: tuple[float, ...] = DEFAULT_DIAGNOSTIC_TEMPERATURES,
    prompt: str = DEFAULT_DIAGNOSTIC_PROMPT,
    base_url: str = "http://localhost:11434",
    timeout: float = 60.0,
    out_dir: Path,
    dry_run: bool = False,
) -> TemperatureDiagnosticResult:
    """Run one generate attempt per temperature and log request payloads."""
    out_dir.mkdir(parents=True, exist_ok=True)
    records: list[TemperatureDiagnosticRecord] = []

    for temperature in temperatures:
        raw_request_payload = build_ollama_generate_request_body(
            model=model,
            prompt=prompt,
            temperature=temperature,
        )
        response_preview: str | None = None
        error: str | None = None

        if not dry_run:
            generate = _make_generate_factory(
                base_url=base_url,
                model=model,
                temperature=temperature,
                timeout=timeout,
            )
            try:
                response = generate(
                    prompt,
                    model=model,
                    temperature=temperature,
                    timeout=timeout,
                )
                response_preview = response[:200]
            except RuntimeError as exc:
                error = str(exc)

        records.append(
            TemperatureDiagnosticRecord(
                model=model,
                temperature=temperature,
                raw_request_payload=raw_request_payload,
                dry_run=dry_run,
                response_preview=response_preview,
                error=error,
            )
        )

    payload_temperatures = tuple(
        record.raw_request_payload["options"]["temperature"] for record in records
    )
    payloads_differ = len(set(payload_temperatures)) == len(payload_temperatures)

    log_path = out_dir / "diagnostic_log.jsonl"
    log_path.write_text(
        "\n".join(json.dumps(asdict(record), sort_keys=True) for record in records) + "\n",
        encoding="utf-8",
    )

    summary = {
        "model": model,
        "temperatures_requested": list(temperatures),
        "payload_temperatures": list(payload_temperatures),
        "payloads_differ": payloads_differ,
        "dry_run": dry_run,
        "prompt": prompt,
        "base_url": base_url,
        "diagnostic_log": str(log_path),
        "records": [asdict(record) for record in records],
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return TemperatureDiagnosticResult(
        out_dir=out_dir,
        records=tuple(records),
        payloads_differ=payloads_differ,
        payload_temperatures=payload_temperatures,
    )
