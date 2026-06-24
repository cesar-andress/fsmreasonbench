"""Export C2 existential-vs-universal stratified analysis tables."""

from __future__ import annotations

import argparse
import json

from fsmreasonbench.cohort.c2_balanced_n100 import resolve_balanced_c2_cohort
from fsmreasonbench.cohort.expanded_n100 import EXPANDED_COHORT_ROOT
from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.evaluator.c2_existential_universal_stratified_analysis import (
    DEFAULT_LOCAL_MATRIX_ROOT,
    DEFAULT_STUDY_ROOT,
    export_c2_existential_universal_stratified_analysis,
)


def main(argv: list[str] | None = None) -> int:
    repo_root = find_repo_root()
    parser = argparse.ArgumentParser(description="Export C2 stratified analysis JSON/CSV")
    parser.add_argument("--study-root", type=str, default=str(repo_root / DEFAULT_STUDY_ROOT))
    parser.add_argument("--cohort-root", type=str, default=str(repo_root / EXPANDED_COHORT_ROOT))
    parser.add_argument(
        "--local-matrix-root",
        type=str,
        default=str(repo_root / DEFAULT_LOCAL_MATRIX_ROOT),
    )
    parser.add_argument(
        "--json-out",
        type=str,
        default=str(repo_root / "docs/c2_existential_universal_stratified_analysis.json"),
    )
    parser.add_argument(
        "--csv-out",
        type=str,
        default=str(repo_root / "docs/c2_existential_universal_stratified_tables.csv"),
    )
    args = parser.parse_args(argv)

    items_path, _ = resolve_balanced_c2_cohort(args.cohort_root)
    payload = export_c2_existential_universal_stratified_analysis(
        study_root=args.study_root,
        cohort_items_path=items_path,
        local_matrix_root=args.local_matrix_root,
        json_out=args.json_out,
        csv_out=args.csv_out,
    )
    print(json.dumps({"json_out": args.json_out, "csv_out": args.csv_out, **payload}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
