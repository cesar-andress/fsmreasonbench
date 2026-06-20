"""CLI to export publication-ready capability-surface PDF figures."""

from __future__ import annotations

import argparse
import sys

from fsmreasonbench.evaluator.capability_surface_figure_export import (
    export_capability_surface_figure,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Export LaTeX-ready capability-surface PDF figures from summary CSV "
            "and paired Markdown reports"
        ),
    )
    parser.add_argument(
        "--summary-csv",
        required=True,
        help="Aggregate summary CSV (validates model list)",
    )
    parser.add_argument(
        "--report-md",
        help="Markdown report with per-level tables (default: inferred from CSV name)",
    )
    parser.add_argument(
        "--summary-json",
        help="Optional combined_summary.json for bootstrap confidence bands",
    )
    parser.add_argument(
        "--family",
        required=True,
        choices=["C2", "F1"],
        help="Task family to plot",
    )
    parser.add_argument("--out", required=True, help="Output PDF path")
    parser.add_argument("--title", help="Optional plot title")
    args = parser.parse_args(argv)

    try:
        out_path = export_capability_surface_figure(
            args.summary_csv,
            args.out,
            family=args.family,
            report_md=args.report_md,
            summary_json=args.summary_json,
            title=args.title,
        )
    except (ValueError, OSError, FileNotFoundError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
