"""Export comparative analysis markdown for local matrix n=100 follow-up."""

from __future__ import annotations

import argparse
from pathlib import Path

from fsmreasonbench.evaluator.local_matrix_analysis import (
    build_analysis_payload,
    render_local_matrix_analysis_markdown,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate local matrix follow-up analysis (n=100 T=0.2 vs n=20 pilot)",
    )
    parser.add_argument(
        "--follow-root",
        default="runs/local_matrix_n100_t02_v2",
        help="Follow-up experiment root (default: runs/local_matrix_n100_t02_v2)",
    )
    parser.add_argument(
        "--pilot-root",
        default="runs/local_matrix_v1",
        help="Pilot experiment root for n=20 baseline (default: runs/local_matrix_v1)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        help="Temperature to compare against pilot (default: 0.2)",
    )
    parser.add_argument(
        "--expected-n",
        type=int,
        default=100,
        help="Configured items per cell for safety tiers (default: 100)",
    )
    parser.add_argument(
        "--extractability-audit",
        default="docs/extractability_audit_n100_t02.md",
        help="Path to extractability audit markdown",
    )
    parser.add_argument(
        "--out",
        default="docs/local_matrix_n100_t02_analysis.md",
        help="Analysis output path",
    )
    args = parser.parse_args(argv)

    follow_root = Path(args.follow_root)
    if not follow_root.is_dir():
        parser.error(f"--follow-root is not a directory: {follow_root}")

    payload = build_analysis_payload(
        follow_root=follow_root,
        pilot_root=args.pilot_root,
        temperature=args.temperature,
        expected_n=args.expected_n,
    )

    markdown = render_local_matrix_analysis_markdown(
        follow_root=follow_root,
        follow_summary=payload["follow_summary"],
        follow_cells=payload["follow_cells"],
        follow_delegation=payload["follow_delegation"],
        pilot_summary=payload["pilot_summary"],
        pilot_cells=payload["pilot_cells"],
        pilot_delegation=payload["pilot_delegation"],
        extractability_audit_path=args.extractability_audit,
        plots_dir=follow_root / "plots",
        report_path=follow_root / "report.md",
        temperature=args.temperature,
        expected_n=args.expected_n,
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(markdown, encoding="utf-8")

    completed = sum(1 for cell in payload["follow_cells"] if cell.status == "completed")
    print(f"Wrote {out_path} ({completed}/{len(payload['follow_cells'])} cells completed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
