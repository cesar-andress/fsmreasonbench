"""CLI for validating exploratory cohort snapshots."""

from __future__ import annotations

import argparse
import json
import sys

from fsmreasonbench.cohort.validate import format_validation_report, validate_cohort


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate an exploratory cohort directory (files, checksums, self-verify)",
    )
    parser.add_argument("--cohort-dir", required=True, help="Cohort directory to validate")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON validation report to stdout",
    )
    args = parser.parse_args(argv)

    try:
        report = validate_cohort(args.cohort_dir)
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        print(format_validation_report(report), end="")
    return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
