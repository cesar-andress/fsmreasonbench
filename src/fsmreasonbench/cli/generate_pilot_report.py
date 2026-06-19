"""CLI for generating pilot evaluation Markdown reports."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fsmreasonbench.evaluator.pilot_report import (
    PilotV0FamilyRun,
    write_pilot_report,
    write_pilot_v0_artifacts,
)

DEFAULT_OUT = "runs/pilot_v0/report.md"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a Markdown pilot evaluation report from scoring JSONL files",
    )
    parser.add_argument(
        "--scores",
        action="append",
        help="Scoring records JSONL (repeat for multiple runs)",
    )
    parser.add_argument(
        "--out",
        default=DEFAULT_OUT,
        help=f"Output Markdown path (default: {DEFAULT_OUT})",
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=5,
        help="Max sample failures per stage (default: 5)",
    )
    parser.add_argument(
        "--top-reasons",
        type=int,
        default=10,
        help="Max certificate failure reasons to list (default: 10)",
    )
    parser.add_argument(
        "--pilot-v0",
        action="store_true",
        help="Write combined pilot v0 Markdown + JSON summary",
    )
    parser.add_argument("--model", default="qwen2.5-coder:7b", help="Model name for pilot v0")
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature for pilot v0 metadata",
    )
    parser.add_argument("--c2-scores", help="C2 scores JSONL for pilot v0")
    parser.add_argument("--c2-results", help="C2 results JSONL for pilot v0")
    parser.add_argument("--f1-scores", help="F1 scores JSONL for pilot v0")
    parser.add_argument("--f1-results", help="F1 results JSONL for pilot v0")
    parser.add_argument(
        "--summary-json",
        help="Pilot v0 JSON summary output path (default: sibling of --out)",
    )
    args = parser.parse_args(argv)

    try:
        if args.pilot_v0:
            if not args.c2_scores or not args.c2_results or not args.f1_scores or not args.f1_results:
                parser.error(
                    "--pilot-v0 requires --c2-scores, --c2-results, --f1-scores, and --f1-results"
                )
            summary_path = args.summary_json or str(Path(args.out).with_suffix(".json"))
            report_path, summary_destination = write_pilot_v0_artifacts(
                [
                    PilotV0FamilyRun("C2", args.c2_scores, args.c2_results),
                    PilotV0FamilyRun("F1", args.f1_scores, args.f1_results),
                ],
                args.out,
                summary_path,
                model=args.model,
                temperature=args.temperature,
                sample_limit=args.sample_limit,
                top_reason_limit=args.top_reasons,
            )
            print(f"Wrote pilot v0 report to {Path(report_path)}")
            print(f"Wrote pilot v0 summary to {Path(summary_destination)}")
            return 0

        if not args.scores:
            parser.error("--scores is required unless --pilot-v0 is set")

        destination = write_pilot_report(
            args.scores,
            args.out,
            sample_limit=args.sample_limit,
            top_reason_limit=args.top_reasons,
        )
    except (ValueError, OSError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"Wrote pilot report to {Path(destination)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
