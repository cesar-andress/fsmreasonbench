"""CLI for failure taxonomy analysis of one scored run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fsmreasonbench.evaluator.failure_taxonomy import (
    analyze_failure_taxonomy,
    format_failure_taxonomy_report,
)
from fsmreasonbench.evaluator.io import dump_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Classify certificate_invalid failures in a scored run into "
            "interpretable taxonomy categories"
        ),
    )
    parser.add_argument("--scores", required=True, help="Scoring records JSONL")
    parser.add_argument("--results", required=True, help="Run results JSONL")
    parser.add_argument("--out", help="Write JSON report to this path")
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Max sample item_ids per taxonomy category (default: 5)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON report to stdout instead of a human-readable summary",
    )
    args = parser.parse_args(argv)

    try:
        payload = analyze_failure_taxonomy(
            args.scores,
            args.results,
            sample_limit=args.limit,
        )
    except (ValueError, OSError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.out:
        dump_json(args.out, payload)

    if args.json or not args.out:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif args.out:
        print(format_failure_taxonomy_report(payload), end="")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
