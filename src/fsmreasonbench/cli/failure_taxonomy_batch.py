"""CLI for batch failure taxonomy analysis over scored run trees."""

from __future__ import annotations

import argparse
import json
import sys

from fsmreasonbench.evaluator.failure_taxonomy import (
    analyze_failure_taxonomy_batch,
    format_failure_taxonomy_report,
)
from fsmreasonbench.evaluator.io import dump_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Classify certificate_invalid failures across all scored runs under a root directory"
        ),
    )
    parser.add_argument(
        "--root",
        required=True,
        help="Root directory to scan for scores.jsonl/results.jsonl pairs",
    )
    parser.add_argument("--out", required=True, help="Write JSON report to this path")
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Max sample item_ids per taxonomy category (default: 5)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Also print JSON report to stdout",
    )
    args = parser.parse_args(argv)

    try:
        payload = analyze_failure_taxonomy_batch(
            args.root,
            sample_limit=args.limit,
        )
    except (ValueError, OSError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    dump_json(args.out, payload)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(format_failure_taxonomy_report(payload), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
