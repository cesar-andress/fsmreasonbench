"""Run Ollama batch evaluation under R0/R1/R2 tracks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fsmreasonbench.evaluator.jsonl import load_items_jsonl
from fsmreasonbench.runners.ollama import HttpOllamaClient, OllamaConfig
from fsmreasonbench.runners.ollama_batch import OllamaBatchConfig
from fsmreasonbench.runners.ollama_track_batch import run_ollama_track_batch
from fsmreasonbench.tracks.models import TrackId


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Ollama on a C2/F1 item JSONL batch under track R0/R1/R2",
    )
    parser.add_argument("--model", required=True, help="Ollama model name")
    parser.add_argument(
        "--items",
        required=True,
        help="Input items JSONL (must include answer_key for scoring)",
    )
    parser.add_argument("--out", required=True, help="Output JSONL path for run records")
    parser.add_argument(
        "--out-dir",
        help="Directory for transcripts/scores/summary (default: out path without suffix)",
    )
    parser.add_argument(
        "--track",
        choices=[track.value for track in TrackId],
        default=TrackId.R0.value,
        help="Evaluation track (default: R0)",
    )
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--max-items", type=int, help="Optional cap on items evaluated")
    parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434",
        help="Ollama base URL",
    )
    parser.add_argument("--no-summary", action="store_true")
    args = parser.parse_args(argv)

    if args.max_items is not None and args.max_items < 1:
        parser.error("--max-items must be >= 1")

    try:
        items = load_items_jsonl(args.items)
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if not items:
        print("ERROR: items JSONL is empty", file=sys.stderr)
        return 2

    family = items[0].family
    if family not in {"C2", "F1"}:
        print(f"ERROR: unsupported family={family!r}", file=sys.stderr)
        return 2

    client = HttpOllamaClient(
        OllamaConfig(
            base_url=args.ollama_url,
            model=args.model,
            temperature=args.temperature,
            timeout=args.timeout,
        )
    )
    config = OllamaBatchConfig(
        model=args.model,
        temperature=args.temperature,
        timeout=args.timeout,
        max_items=args.max_items,
    )

    try:
        result = run_ollama_track_batch(
            items,
            client.generate,
            args.out,
            config,
            args.track,
            out_dir=args.out_dir,
            write_summary=not args.no_summary,
        )
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "model": args.model,
                "track": args.track,
                "family": family,
                "out": args.out,
                "out_dir": str(result.out_dir),
                "n": result.summary["n"],
                "fully_correct_rate": result.summary["fully_correct_rate"],
                "extractability_rate": result.summary["extractability_rate"],
                "tool_invocation_rate": result.summary.get("tool_invocation_rate", 0.0),
                "average_tool_calls_per_item": result.summary.get(
                    "average_tool_calls_per_item", 0.0
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
