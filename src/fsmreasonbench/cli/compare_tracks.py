"""Compare R0/R1/R2 LLM track evaluation runs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.evaluator.track_comparison import export_track_comparison


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare R0, R1, and R2 LLM track run directories",
    )
    parser.add_argument("--r0-dir", required=True, help="R0 run output directory")
    parser.add_argument("--r1-dir", required=True, help="R1 run output directory")
    parser.add_argument("--r2-dir", required=True, help="R2 run output directory")
    parser.add_argument(
        "--out-json",
        default="docs/track_comparison_summary.json",
        help="Output JSON summary",
    )
    parser.add_argument(
        "--out-csv",
        default="docs/track_comparison_summary.csv",
        help="Output CSV summary",
    )
    parser.add_argument(
        "--out-md",
        default="docs/track_comparison_report.md",
        help="Output Markdown report",
    )
    parser.add_argument("--repo-root", help="Repository root (default: auto-detect)")
    args = parser.parse_args(argv)

    try:
        repo_root = Path(args.repo_root).resolve() if args.repo_root else find_repo_root()

        def resolve(path: str) -> Path:
            candidate = Path(path)
            return candidate if candidate.is_absolute() else (repo_root / candidate).resolve()

        written = export_track_comparison(
            r0_dir=resolve(args.r0_dir),
            r1_dir=resolve(args.r1_dir),
            r2_dir=resolve(args.r2_dir),
            out_json=resolve(args.out_json),
            out_csv=resolve(args.out_csv),
            out_md=resolve(args.out_md),
        )
    except (ValueError, OSError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    for kind, path in written.items():
        print(f"Wrote {kind} to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
