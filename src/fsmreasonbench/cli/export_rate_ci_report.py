"""Export bootstrap confidence intervals from existing score files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.evaluator.rate_ci_report import export_rate_ci_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compute bootstrap confidence intervals from existing scores.jsonl run trees"
        ),
    )
    parser.add_argument(
        "--root",
        action="append",
        dest="roots",
        help="Score root directory (repeatable)",
    )
    parser.add_argument(
        "--repo-root",
        help="Repository root used to resolve default score roots (default: auto-detect)",
    )
    parser.add_argument(
        "--out-json",
        default="docs/rate_ci_summary.json",
        help="Output JSON summary path",
    )
    parser.add_argument(
        "--out-csv",
        default="docs/rate_ci_summary.csv",
        help="Output CSV summary path",
    )
    parser.add_argument(
        "--out-md",
        default="docs/rate_ci_report.md",
        help="Output Markdown report path",
    )
    parser.add_argument(
        "--bootstrap-resamples",
        type=int,
        default=1000,
        help="Number of bootstrap resamples (default: 1000)",
    )
    parser.add_argument(
        "--bootstrap-seed",
        type=int,
        default=4242,
        help="Bootstrap RNG seed (default: 4242)",
    )
    args = parser.parse_args(argv)

    try:
        repo_root = (
            Path(args.repo_root).resolve()
            if args.repo_root
            else find_repo_root()
        )
        roots = args.roots or [
            str(repo_root / "runs/capability_surface_models"),
            str(repo_root / "runs/capability_surface_models_f1_mixed"),
            str(repo_root / "runs/pilot_v1"),
        ]
        written = export_rate_ci_report(
            roots,
            out_json=args.out_json,
            out_csv=args.out_csv,
            out_md=args.out_md,
            n_resamples=args.bootstrap_resamples,
            seed=args.bootstrap_seed,
        )
    except (ValueError, OSError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    for kind, path in written.items():
        print(f"Wrote {kind} to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
