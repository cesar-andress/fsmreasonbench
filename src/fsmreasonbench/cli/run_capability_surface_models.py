"""Run model capability-surface evaluation across difficulty levels."""

from __future__ import annotations

import argparse
import json
import sys

from fsmreasonbench.evaluator.capability_surface_models import (
    CapabilitySurfaceModelsConfig,
    run_capability_surface_models,
)
from fsmreasonbench.runners.ollama import HttpOllamaClient, OllamaConfig


def _parse_models(raw: str) -> tuple[str, ...]:
    models = tuple(part.strip() for part in raw.split(",") if part.strip())
    if not models:
        raise ValueError("at least one model is required")
    return models


def _parse_families(raw: str) -> tuple[str, ...]:
    families = tuple(part.strip() for part in raw.split(",") if part.strip())
    if not families:
        raise ValueError("at least one family is required")
    for family in families:
        if family not in {"C2", "F1"}:
            raise ValueError(f"unsupported family: {family!r}")
    return families


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run C2/F1 capability-surface sweeps with Ollama models",
    )
    parser.add_argument(
        "--models",
        default="qwen2.5-coder:7b,llama3.1:8b,mistral-nemo:12b,gemma2:9b",
        help="Comma-separated Ollama model names",
    )
    parser.add_argument(
        "--families",
        default="C2,F1",
        help="Comma-separated families (default: C2,F1)",
    )
    parser.add_argument(
        "--levels",
        default="1,2,3,4,5",
        help="Comma-separated difficulty levels (default: 1,2,3,4,5)",
    )
    parser.add_argument(
        "--n-per-level",
        type=int,
        default=20,
        help="Items per family/level (default: 20)",
    )
    parser.add_argument("--seed", type=int, default=1, help="Generator seed (default: 1)")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument(
        "--out-dir",
        default="runs/capability_surface_models",
        help="Output directory (default: runs/capability_surface_models)",
    )
    parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434",
        help="Ollama base URL (default: http://localhost:11434)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run model/level combinations even if summary.json exists",
    )
    args = parser.parse_args(argv)

    if args.n_per_level < 1:
        parser.error("--n-per-level must be >= 1")

    try:
        models = _parse_models(args.models)
        families = _parse_families(args.families)
        levels = tuple(int(part.strip()) for part in args.levels.split(",") if part.strip())
        if not levels or any(level < 1 for level in levels):
            raise ValueError("levels must be positive integers")
    except ValueError as exc:
        parser.error(str(exc))

    config = CapabilitySurfaceModelsConfig(
        models=models,
        out_dir=args.out_dir,
        families=families,
        c2_levels=levels,
        f1_levels=levels,
        n_per_level=args.n_per_level,
        seed=args.seed,
        temperature=args.temperature,
        timeout=args.timeout,
        skip_completed=not args.force,
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
        result = run_capability_surface_models(config, generate_factory)
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "out_dir": str(result.out_dir),
                "models": list(models),
                "families": list(families),
                "levels": list(levels),
                "rows": len(result.rows),
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
