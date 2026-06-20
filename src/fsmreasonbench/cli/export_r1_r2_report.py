"""Export R1/R2 track comparison report."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.evaluator.r1_r2_report import export_r1_r2_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate R0/R1/R2 reference tracks and export delegation-gap report",
    )
    parser.add_argument("--repo-root", help="Repository root (default: auto-detect)")
    parser.add_argument(
        "--out-json",
        default="docs/r1_r2_summary.json",
        help="Output JSON summary path",
    )
    parser.add_argument(
        "--out-csv",
        default="docs/r1_r2_summary.csv",
        help="Output CSV summary path",
    )
    parser.add_argument(
        "--out-md",
        default="docs/r1_r2_report.md",
        help="Output Markdown report path",
    )
    parser.add_argument(
        "--no-strict",
        action="store_true",
        help="Do not fail when reference track metrics are below 1.0",
    )
    args = parser.parse_args(argv)

    try:
        repo_root = Path(args.repo_root).resolve() if args.repo_root else find_repo_root()
        written = export_r1_r2_report(
            repo_root,
            out_json=args.out_json,
            out_csv=args.out_csv,
            out_md=args.out_md,
            strict=not args.no_strict,
        )
    except (ValueError, OSError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    for kind, path in written.items():
        print(f"Wrote {kind} to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
