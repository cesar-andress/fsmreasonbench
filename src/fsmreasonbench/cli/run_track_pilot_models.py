"""Run multi-model R0/R1/R2 track pilot on frozen exploratory cohorts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.runners.ollama import HttpOllamaClient, OllamaConfig
from fsmreasonbench.runners.track_pilot_models import (
    DEFAULT_C2_ITEMS,
    DEFAULT_F1_ITEMS,
    TrackPilotModelsConfig,
    parse_temperatures,
    run_track_pilot_models,
)
from fsmreasonbench.tracks.models import TrackId


def _parse_csv(raw: str) -> tuple[str, ...]:
    values = tuple(part.strip() for part in raw.split(",") if part.strip())
    if not values:
        raise ValueError("expected at least one value")
    return values


def main(argv: list[str] | None = None) -> int:
    repo_root = find_repo_root()
    parser = argparse.ArgumentParser(
        description="Run R0/R1/R2 track pilot across multiple Ollama models and families",
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
        "--tracks",
        default="R0,R1,R2",
        help="Comma-separated tracks (default: R0,R1,R2)",
    )
    parser.add_argument(
        "--c2-items",
        default=str(repo_root / DEFAULT_C2_ITEMS),
        help=f"C2 items JSONL (default: {DEFAULT_C2_ITEMS})",
    )
    parser.add_argument(
        "--f1-items",
        default=str(repo_root / DEFAULT_F1_ITEMS),
        help=f"F1 items JSONL (default: {DEFAULT_F1_ITEMS})",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=20,
        help="Max items per cell (default: 20)",
    )
    parser.add_argument(
        "--temperatures",
        help="Comma-separated sampling temperatures (e.g. 0,0.2,0.7)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Single temperature when --temperatures is not set (default: 0.0)",
    )
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument(
        "--out-dir",
        default="runs/track_pilot_v1",
        help="Output directory (default: runs/track_pilot_v1)",
    )
    parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434",
        help="Ollama base URL (default: http://localhost:11434)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run cells even when summary.json exists",
    )
    args = parser.parse_args(argv)

    if args.max_items < 1:
        parser.error("--max-items must be >= 1")

    try:
        models = _parse_csv(args.models)
        families = _parse_csv(args.families)
        tracks = _parse_csv(args.tracks)
        temperatures = (
            parse_temperatures(args.temperatures)
            if args.temperatures
            else (args.temperature,)
        )
        for family in families:
            if family not in {"C2", "F1"}:
                raise ValueError(f"unsupported family: {family!r}")
        for track in tracks:
            TrackId(track)
    except ValueError as exc:
        parser.error(str(exc))

    config = TrackPilotModelsConfig(
        models=models,
        families=families,
        tracks=tracks,
        c2_items_path=Path(args.c2_items),
        f1_items_path=Path(args.f1_items),
        out_dir=args.out_dir,
        max_items=args.max_items,
        temperatures=temperatures,
        timeout=args.timeout,
        skip_completed=not args.force,
    )

    def generate_factory(model: str, temperature: float):
        client = HttpOllamaClient(
            OllamaConfig(
                base_url=args.ollama_url,
                model=model,
                temperature=temperature,
                timeout=args.timeout,
            )
        )
        return client.generate

    try:
        result = run_track_pilot_models(config, generate_factory)
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    completed = sum(1 for row in result.track_rows if row.get("status") == "completed")
    print(
        json.dumps(
            {
                "out_dir": str(result.out_dir),
                "models": list(models),
                "families": list(families),
                "tracks": list(tracks),
                "temperatures": list(temperatures),
                "cells_completed": completed,
                "cells_failed": len(result.failed_cells),
                "combined_summary": str(result.out_dir / "combined_summary.json"),
                "report": str(result.out_dir / "report.md"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if not result.failed_cells else 1


if __name__ == "__main__":
    raise SystemExit(main())
