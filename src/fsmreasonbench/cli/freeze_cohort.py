"""CLI for freezing exploratory cohort snapshots."""

from __future__ import annotations

import argparse
import json
import sys

from fsmreasonbench.cohort.freeze import freeze_cohort


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Freeze an exploratory cohort snapshot with manifest, checksums, and README "
            "(non-final; no Zenodo DOI)"
        ),
    )
    parser.add_argument("--items", required=True, help="Source items JSONL path")
    parser.add_argument(
        "--cohort-id",
        required=True,
        help="Exploratory cohort identifier (e.g. f1-mixed-level3-v0.1-exploratory)",
    )
    parser.add_argument("--out-dir", required=True, help="Output cohort directory")
    parser.add_argument(
        "--generator-notes",
        help="Optional free-text generator notes stored in manifest.json",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print manifest JSON to stdout",
    )
    args = parser.parse_args(argv)

    try:
        manifest = freeze_cohort(
            args.items,
            args.cohort_id,
            args.out_dir,
            generator_notes=args.generator_notes,
        )
    except (ValueError, OSError, AssertionError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(manifest, indent=2, sort_keys=True))
    else:
        print(
            json.dumps(
                {
                    "cohort_id": manifest["cohort_id"],
                    "out_dir": args.out_dir,
                    "item_count": manifest["item_count"],
                    "cohort_fingerprint": manifest["cohort_fingerprint"],
                },
                indent=2,
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
