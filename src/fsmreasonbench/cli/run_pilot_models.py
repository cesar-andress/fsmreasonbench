"""Run C2/F1 pilot batches across multiple Ollama models."""

from __future__ import annotations

import argparse
import json
import sys

from fsmreasonbench.runners.ollama import HttpOllamaClient, OllamaConfig
from fsmreasonbench.runners.pilot_models import PilotModelsConfig, run_pilot_models


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run C2/F1 pilot batches across multiple Ollama models",
    )
    parser.add_argument(
        "--models",
        required=True,
        help="Comma-separated Ollama model names",
    )
    parser.add_argument("--c2-items", required=True, help="C2 items JSONL")
    parser.add_argument("--f1-items", required=True, help="F1 items JSONL")
    parser.add_argument(
        "--max-items",
        type=int,
        default=20,
        help="Max items per family (default: 20)",
    )
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument(
        "--out-dir",
        default="runs/pilot_v1",
        help="Output directory (default: runs/pilot_v1)",
    )
    parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434",
        help="Ollama base URL (default: http://localhost:11434)",
    )
    args = parser.parse_args(argv)

    models = tuple(model.strip() for model in args.models.split(",") if model.strip())
    if not models:
        parser.error("--models must contain at least one model name")
    if args.max_items < 1:
        parser.error("--max-items must be >= 1")

    config = PilotModelsConfig(
        models=models,
        c2_items_path=args.c2_items,
        f1_items_path=args.f1_items,
        out_dir=args.out_dir,
        max_items=args.max_items,
        temperature=args.temperature,
        timeout=args.timeout,
    )

    def generate_factory(model: str):
        client = HttpOllamaClient(
            OllamaConfig(
                base_url=args.ollama_url,
                model=model,
                temperature=args.temperature,
                timeout=args.timeout,
            )
        )
        return client.generate

    try:
        result = run_pilot_models(config, generate_factory)
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "out_dir": str(result.out_dir),
                "models": list(models),
                "runs": len(result.rows),
                "combined_summary": str(result.out_dir / "combined_summary.json"),
                "report": str(result.out_dir / "report.md"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
