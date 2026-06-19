"""Plot capability-surface model evaluation curves."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fsmreasonbench.evaluator.capability_surface_plots import plot_capability_surface


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Plot model capability-surface summaries",
    )
    parser.add_argument(
        "--summary",
        default="runs/capability_surface_models/combined_summary.json",
        help="Path to combined_summary.json",
    )
    parser.add_argument(
        "--out-dir",
        help="Directory for PNG output (default: summary parent directory)",
    )
    args = parser.parse_args(argv)

    try:
        written = plot_capability_surface(args.summary, args.out_dir)
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    for path in written:
        print(f"Wrote {Path(path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
