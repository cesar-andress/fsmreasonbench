"""Export paper-ready capability-surface reports from combined summaries."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fsmreasonbench.evaluator.capability_surface_report_export import (
    export_capability_surface_report,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Export Markdown and LaTeX reports from a capability-surface "
            "combined_summary.json or combined_summary.csv"
        ),
    )
    parser.add_argument(
        "--summary",
        required=True,
        help="Path to combined_summary.json or combined_summary.csv",
    )
    parser.add_argument(
        "--out-md",
        help="Output Markdown report path",
    )
    parser.add_argument(
        "--out-tex",
        help="Output LaTeX table path",
    )
    parser.add_argument(
        "--out-csv",
        help="Optional aggregated CSV export (family × model means)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if expected family/level/model cells are missing",
    )
    args = parser.parse_args(argv)

    if not args.out_md and not args.out_tex and not args.out_csv:
        parser.error("at least one of --out-md, --out-tex, or --out-csv is required")

    try:
        written = export_capability_surface_report(
            args.summary,
            out_md=args.out_md,
            out_tex=args.out_tex,
            out_csv=args.out_csv,
            strict=args.strict,
        )
    except (ValueError, OSError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    for kind, path in written.items():
        print(f"Wrote {kind} to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
