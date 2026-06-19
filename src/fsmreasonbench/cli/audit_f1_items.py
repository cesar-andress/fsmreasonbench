"""CLI for F1 item difficulty and constructive-generator audit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fsmreasonbench.evaluator.f1_item_audit import write_f1_audit_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit F1 items for gold-trace regularity and constructive-generator "
            "difficulty signals"
        ),
    )
    parser.add_argument(
        "--items",
        required=True,
        help="Path to F1 items JSONL (e.g. capability-surface level batch)",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output JSON audit report path",
    )
    args = parser.parse_args(argv)

    try:
        payload = write_f1_audit_report(args.items, args.out)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    summary = payload["summary"]
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"Wrote audit report to {Path(args.out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
