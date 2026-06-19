"""CLI for documentation consistency checks."""

from __future__ import annotations

import argparse
import sys

from pathlib import Path

from fsmreasonbench.dev.doc_consistency import (
    check_documentation,
    find_repo_root,
    format_report,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Check documentation consistency: CLI modules exist, referenced files "
            "exist, and implemented family names (C2/F1) are consistent."
        ),
    )
    parser.add_argument(
        "--repo-root",
        help="Repository root (default: auto-detect from cwd)",
    )
    parser.add_argument(
        "--extra-doc",
        action="append",
        default=[],
        help="Additional markdown file to include (repeatable)",
    )
    args = parser.parse_args(argv)

    try:
        repo_root = (
            find_repo_root()
            if args.repo_root is None
            else find_repo_root(Path(args.repo_root))
        )
        report = check_documentation(
            repo_root,
            extra_paths=tuple(args.extra_doc),
        )
    except (FileNotFoundError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(format_report(report))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
