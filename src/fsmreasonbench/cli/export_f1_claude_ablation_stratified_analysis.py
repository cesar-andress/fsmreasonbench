"""Export item-level stratified analysis for Claude F1 runs and ablations."""

from __future__ import annotations

import argparse
import json
import sys

from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.evaluator.bootstrap import DEFAULT_BOOTSTRAP_RESAMPLES
from fsmreasonbench.evaluator.f1_claude_ablation_stratified_analysis import (
    export_f1_claude_ablation_stratified_analysis,
)


def main(argv: list[str] | None = None) -> int:
    repo_root = find_repo_root()
    parser = argparse.ArgumentParser(
        description=(
            "Export item-level stratified analysis for frozen Claude F1 runs and ablations"
        ),
    )
    parser.add_argument(
        "--markdown-out",
        type=str,
        default=str(repo_root / "docs/f1_claude_ablation_stratified_analysis.md"),
    )
    parser.add_argument(
        "--json-out",
        type=str,
        default=str(repo_root / "docs/f1_claude_ablation_stratified_analysis.json"),
    )
    parser.add_argument(
        "--csv-out",
        type=str,
        default=str(repo_root / "docs/f1_claude_ablation_stratified_tables.csv"),
    )
    parser.add_argument(
        "--cohort-items",
        type=str,
        default=str(repo_root / "cohorts/v0.1-expanded-n100/f1-mixed-level3/items.jsonl"),
    )
    parser.add_argument(
        "--bootstrap-resamples",
        type=int,
        default=DEFAULT_BOOTSTRAP_RESAMPLES,
    )
    parser.add_argument("--bootstrap-seed", type=int, default=4242)
    args = parser.parse_args(argv)

    payload = export_f1_claude_ablation_stratified_analysis(
        repo_root,
        markdown_path=args.markdown_out,
        json_path=args.json_out,
        csv_path=args.csv_out,
        cohort_items_path=args.cohort_items,
        n_resamples=args.bootstrap_resamples,
        seed=args.bootstrap_seed,
    )
    print(
        json.dumps(
            {
                "markdown": args.markdown_out,
                "json": args.json_out,
                "csv": args.csv_out,
                "conditions": payload["conditions"],
                "item_id_alignment": payload["item_id_alignment"]["per_condition"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
