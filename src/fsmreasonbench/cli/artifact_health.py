"""CLI for artifact health checks."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fsmreasonbench.dev.artifact_health import (
    build_artifact_health_report,
    format_artifact_health_report,
)
from fsmreasonbench.dev.doc_consistency import find_repo_root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Print FSMReasonBench artifact health: package version, families, "
            "schemas, example self-verification, and suggested pytest command."
        ),
    )
    parser.add_argument(
        "--repo-root",
        help="Repository root (default: auto-detect from cwd)",
    )
    args = parser.parse_args(argv)

    try:
        repo_root = (
            find_repo_root()
            if args.repo_root is None
            else find_repo_root(Path(args.repo_root))
        )
        report = build_artifact_health_report(repo_root)
    except (FileNotFoundError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(format_artifact_health_report(report))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
