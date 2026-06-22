"""CLI to verify Ollama receives distinct temperature values."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fsmreasonbench.runners.ollama_temperature_diagnostic import (
    DEFAULT_DIAGNOSTIC_PROMPT,
    run_temperature_diagnostic,
)
from fsmreasonbench.runners.track_pilot_models import parse_temperatures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Log Ollama generate payloads for multiple temperatures",
    )
    parser.add_argument(
        "--model",
        default="qwen2.5-coder:7b",
        help="Ollama model name (default: qwen2.5-coder:7b)",
    )
    parser.add_argument(
        "--temperatures",
        default="0,0.2,0.7",
        help="Comma-separated temperatures to probe (default: 0,0.2,0.7)",
    )
    parser.add_argument(
        "--prompt",
        default=DEFAULT_DIAGNOSTIC_PROMPT,
        help="Prompt sent to Ollama for each temperature probe",
    )
    parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434",
        help="Ollama base URL (default: http://localhost:11434)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Per-request timeout in seconds (default: 60)",
    )
    parser.add_argument(
        "--out-dir",
        default="runs/ollama_temperature_diagnostic",
        help="Output directory for diagnostic_log.jsonl and summary.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only log request payloads without calling Ollama",
    )
    args = parser.parse_args(argv)

    try:
        temperatures = parse_temperatures(args.temperatures)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    result = run_temperature_diagnostic(
        model=args.model,
        temperatures=temperatures,
        prompt=args.prompt,
        base_url=args.ollama_url,
        timeout=args.timeout,
        out_dir=Path(args.out_dir),
        dry_run=args.dry_run,
    )

    for record in result.records:
        payload_temp = record.raw_request_payload["options"]["temperature"]
        print(
            f"T={record.temperature:g} -> payload options.temperature={payload_temp:g} "
            f"model={record.model!r}"
        )
        print(json.dumps(record.raw_request_payload, indent=2, sort_keys=True))
        if record.error:
            print(f"  ERROR: {record.error}", file=sys.stderr)
        elif record.response_preview is not None:
            preview = record.response_preview.replace("\n", "\\n")
            print(f"  response_preview: {preview!r}")

    print(
        json.dumps(
            {
                "out_dir": str(result.out_dir),
                "payloads_differ": result.payloads_differ,
                "payload_temperatures": list(result.payload_temperatures),
                "dry_run": args.dry_run,
            },
            indent=2,
            sort_keys=True,
        )
    )

    if not result.payloads_differ:
        print(
            "ERROR: payload temperatures are not all distinct; "
            "temperature is not propagating correctly",
            file=sys.stderr,
        )
        return 1

    if any(record.error for record in result.records):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
