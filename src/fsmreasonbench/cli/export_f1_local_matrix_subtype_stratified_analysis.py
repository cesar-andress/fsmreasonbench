"""Export F1 subtype-stratified analysis for the local model matrix."""

from __future__ import annotations

import argparse
import json
import sys

from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.evaluator.f1_local_matrix_subtype_stratified_analysis import (
    DEFAULT_LOCAL_MATRIX_ROOT,
    export_f1_local_matrix_subtype_stratified_analysis,
)


def main(argv: list[str] | None = None) -> int:
    repo_root = find_repo_root()
    parser = argparse.ArgumentParser(
        description="Export F1 subtype-stratified analysis for local_matrix runs",
    )
    parser.add_argument(
        "--matrix-root",
        type=str,
        default=str(repo_root / DEFAULT_LOCAL_MATRIX_ROOT),
    )
    parser.add_argument(
        "--cohort-items",
        type=str,
        default=str(repo_root / "cohorts/v0.1-expanded-n100/f1-mixed-level3/items.jsonl"),
    )
    parser.add_argument(
        "--markdown-out",
        type=str,
        default=str(repo_root / "docs/f1_local_matrix_subtype_stratified_analysis.md"),
    )
    parser.add_argument(
        "--json-out",
        type=str,
        default=str(repo_root / "docs/f1_local_matrix_subtype_stratified_analysis.json"),
    )
    parser.add_argument(
        "--csv-out",
        type=str,
        default=str(repo_root / "docs/f1_local_matrix_subtype_stratified_tables.csv"),
    )
    args = parser.parse_args(argv)

    payload = export_f1_local_matrix_subtype_stratified_analysis(
        repo_root,
        markdown_path=args.markdown_out,
        json_path=args.json_out,
        csv_path=args.csv_out,
        matrix_root=args.matrix_root,
        cohort_items_path=args.cohort_items,
    )
    print(
        json.dumps(
            {
                "markdown": args.markdown_out,
                "json": args.json_out,
                "csv": args.csv_out,
                "cells_discovered": payload["cells_discovered"],
                "models": payload["models"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
