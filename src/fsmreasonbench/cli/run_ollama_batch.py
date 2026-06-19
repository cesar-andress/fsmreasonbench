"""Run a local Ollama model on a C2/F1 item JSONL batch."""

from __future__ import annotations

import argparse
import json
import sys

from fsmreasonbench.evaluator.jsonl import load_items_jsonl
from fsmreasonbench.runners.ollama import HttpOllamaClient, OllamaConfig
from fsmreasonbench.runners.ollama_batch import OllamaBatchConfig, run_ollama_batch


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Ollama on a C2/F1 item JSONL batch")
    parser.add_argument("--model", required=True, help="Ollama model name")
    parser.add_argument(
        "--items",
        required=True,
        help="Input items JSONL (must include answer_key for scoring)",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output JSONL path for run records",
    )
    parser.add_argument(
        "--out-dir",
        help="Directory for transcripts/scores/summary (default: out path without suffix)",
    )
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument(
        "--max-items",
        type=int,
        help="Optional cap on number of items to evaluate",
    )
    parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434",
        help="Ollama base URL (default: http://localhost:11434)",
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Do not write summary.json",
    )
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
    if any(item.family != family for item in items):
        print("ERROR: mixed families in items JSONL", file=sys.stderr)
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
        result = run_ollama_batch(
            items,
            client.generate,
            args.out,
            config,
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
                "family": family,
                "out": args.out,
                "out_dir": str(result.out_dir),
                "n": result.summary["n"],
                "fully_correct_rate": result.summary["fully_correct_rate"],
                "extractability_rate": result.summary["extractability_rate"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
