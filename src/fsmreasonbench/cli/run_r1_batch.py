"""Run R1 track batch evaluation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.runners.r1_step_simulator import run_r1_batch


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run R1 track on an items JSONL cohort")
    parser.add_argument("--items", required=True, help="Path to items.jsonl")
    parser.add_argument(
        "--out-dir",
        default="runs/r1_batch",
        help="Output directory for scores and transcripts",
    )
    parser.add_argument(
        "--repo-root",
        help="Repository root (default: auto-detect)",
    )
    args = parser.parse_args(argv)

    try:
        repo_root = Path(args.repo_root).resolve() if args.repo_root else find_repo_root()
        items_path = Path(args.items)
        if not items_path.is_absolute():
            items_path = (repo_root / items_path).resolve()
        out_dir = Path(args.out_dir)
        if not out_dir.is_absolute():
            out_dir = (repo_root / out_dir).resolve()
        summary = run_r1_batch(items_path, out_dir)
    except (ValueError, OSError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"R1 batch complete: n={summary['n']} fully_correct_rate={summary['fully_correct_rate']}")
    print(f"Wrote outputs to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
