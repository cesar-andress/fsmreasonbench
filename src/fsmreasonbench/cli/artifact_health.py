"""CLI for artifact health checks."""

from __future__ import annotations

import argparse
import json
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
            "Check FSMReasonBench artifact health: package import, required schemas, "
            "example self-verification, and core CLI imports."
        ),
    )
    parser.add_argument(
        "--repo-root",
        help="Repository root (default: auto-detect from cwd)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON report",
    )
    args = parser.parse_args(argv)

    try:
        if args.repo_root is None:
            repo_root = find_repo_root()
        else:
            repo_root = Path(args.repo_root).resolve()
            if not repo_root.is_dir():
                raise FileNotFoundError(f"repository root not found: {repo_root}")
        report = build_artifact_health_report(repo_root)
    except (FileNotFoundError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        print(format_artifact_health_report(report))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
