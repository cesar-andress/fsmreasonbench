"""CLI for generating pilot evaluation Markdown reports."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fsmreasonbench.evaluator.pilot_report import write_pilot_report

DEFAULT_OUT = "runs/pilot_v0/report.md"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a Markdown pilot evaluation report from scoring JSONL files",
    )
    parser.add_argument(
        "--scores",
        action="append",
        required=True,
        help="Scoring records JSONL (repeat for multiple runs)",
    )
    parser.add_argument(
        "--out",
        default=DEFAULT_OUT,
        help=f"Output Markdown path (default: {DEFAULT_OUT})",
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=5,
        help="Max sample failures per stage (default: 5)",
    )
    parser.add_argument(
        "--top-reasons",
        type=int,
        default=10,
        help="Max certificate failure reasons to list (default: 10)",
    )
    args = parser.parse_args(argv)

    try:
        destination = write_pilot_report(
            args.scores,
            args.out,
            sample_limit=args.sample_limit,
            top_reason_limit=args.top_reasons,
        )
    except (ValueError, OSError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"Wrote pilot report to {Path(destination)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
