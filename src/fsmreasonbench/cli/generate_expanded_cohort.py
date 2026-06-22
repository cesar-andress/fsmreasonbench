"""Generate and freeze v0.1-expanded-n100 exploratory cohorts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fsmreasonbench.cohort.expanded_n100 import (
    DEFAULT_ITEM_COUNT,
    build_expanded_cohorts,
    resolve_expanded_cohort_paths,
)
from fsmreasonbench.dev.doc_consistency import find_repo_root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate and freeze C2/F1 expanded exploratory cohorts "
            "(100 items each by default) under cohorts/v0.1-expanded-n100/"
        ),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root (default: auto-detect)",
    )
    parser.add_argument(
        "--cohort-root",
        type=Path,
        default=None,
        help="Output cohort bundle root (default: <repo-root>/cohorts/v0.1-expanded-n100)",
    )
    parser.add_argument(
        "--reference-root",
        type=Path,
        default=None,
        help="Reference cohort root for item_id disjointness checks (default: v0.1-exploratory)",
    )
    parser.add_argument(
        "--item-count",
        type=int,
        default=DEFAULT_ITEM_COUNT,
        help=f"Items per family (default: {DEFAULT_ITEM_COUNT})",
    )
    parser.add_argument(
        "--skip-validate",
        action="store_true",
        help="Skip validate_cohort after freeze",
    )
    args = parser.parse_args(argv)

    repo_root = args.repo_root or find_repo_root()
    if args.item_count < 1:
        parser.error("--item-count must be >= 1")

    try:
        result = build_expanded_cohorts(
            repo_root,
            item_count=args.item_count,
            cohort_root=args.cohort_root,
            reference_root=args.reference_root,
            validate=not args.skip_validate,
        )
    except (ValueError, OSError, AssertionError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    paths = resolve_expanded_cohort_paths(repo_root, cohort_root=args.cohort_root)
    print(
        json.dumps(
            {
                "cohort_root": result["cohort_root"],
                "item_count": result["item_count"],
                "c2_cohort_id": result["c2"]["cohort_id"],
                "f1_cohort_id": result["f1"]["cohort_id"],
                "c2_fingerprint": result["c2"]["cohort_fingerprint"],
                "f1_fingerprint": result["f1"]["cohort_fingerprint"],
                "c2_items": str(paths.c2_items),
                "f1_items": str(paths.f1_items),
                "validated": not args.skip_validate,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
