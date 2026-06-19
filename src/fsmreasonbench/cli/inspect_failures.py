"""CLI for inspecting failure modes in scored runs."""

from __future__ import annotations

import argparse
import json
import sys

from fsmreasonbench.evaluator.inspect_failures import format_inspection_report, inspect_failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect failure stages and representative examples in scored runs",
    )
    parser.add_argument("--scores", required=True, help="Scoring records JSONL")
    parser.add_argument(
        "--results",
        required=True,
        help="Run results JSONL (e.g. Ollama batch output)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Max samples per failure stage (default: 5)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of a human-readable report",
    )
    args = parser.parse_args(argv)

    try:
        payload = inspect_failures(
            args.scores,
            args.results,
            limit=args.limit,
        )
    except (ValueError, OSError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(format_inspection_report(payload), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
