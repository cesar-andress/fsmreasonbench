"""Plot local model track-temperature matrix summaries."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fsmreasonbench.evaluator.local_matrix_plots import plot_local_matrix


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Plot local model track-temperature matrix summaries",
    )
    parser.add_argument(
        "--summary",
        default="runs/local_matrix_v1/combined_summary.json",
        help="Path to combined_summary.json",
    )
    parser.add_argument(
        "--out-dir",
        help="Directory for PNG output (default: {summary_parent}/plots)",
    )
    args = parser.parse_args(argv)

    try:
        written = plot_local_matrix(args.summary, args.out_dir)
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    for path in written:
        print(f"Wrote {Path(path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
