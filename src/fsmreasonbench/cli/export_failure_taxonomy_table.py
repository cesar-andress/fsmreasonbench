"""CLI to export failure taxonomy LaTeX tables from Markdown reports."""

from __future__ import annotations

import argparse
import sys

from fsmreasonbench.evaluator.failure_taxonomy_export import (
    DEFAULT_LATEX_CAPTION,
    DEFAULT_LATEX_LABEL,
    export_failure_taxonomy_latex,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export a LaTeX failure taxonomy table from a Markdown report",
    )
    parser.add_argument(
        "--report",
        required=True,
        help="Markdown report path (e.g. docs/f1_mixed_failure_taxonomy_report.md)",
    )
    parser.add_argument("--out-tex", required=True, help="Output LaTeX table path")
    parser.add_argument(
        "--caption",
        default=DEFAULT_LATEX_CAPTION,
        help="LaTeX table caption",
    )
    parser.add_argument(
        "--label",
        default=DEFAULT_LATEX_LABEL,
        help="LaTeX table label",
    )
    args = parser.parse_args(argv)

    try:
        out_path = export_failure_taxonomy_latex(
            args.report,
            args.out_tex,
            caption=args.caption,
            label=args.label,
        )
    except (ValueError, OSError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
