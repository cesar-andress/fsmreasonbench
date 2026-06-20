"""CLI for publication readiness reporting."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.reporting.publication_readiness import (
    build_publication_readiness_report,
    write_publication_readiness_report,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a read-only Markdown report summarizing publication and release "
            "readiness for the FSMReasonBench artifact."
        ),
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output Markdown report path (e.g. docs/publication_readiness.md)",
    )
    parser.add_argument(
        "--repo-root",
        help="Repository root (default: auto-detect from cwd)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print structured JSON report to stdout after writing Markdown",
    )
    args = parser.parse_args(argv)

    try:
        repo_root = find_repo_root() if args.repo_root is None else Path(args.repo_root).resolve()
        if not repo_root.is_dir():
            raise FileNotFoundError(f"repository root not found: {repo_root}")
        report = write_publication_readiness_report(repo_root, args.out)
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        print(f"Wrote {Path(args.out).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
