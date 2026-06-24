"""Export equivalence hash mismatch decomposition docs."""

from __future__ import annotations

import argparse
import json

from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.evaluator.equivalence_hash_mismatch_decomposition import (
    export_equivalence_hash_mismatch_decomposition,
)


def main(argv: list[str] | None = None) -> int:
    repo_root = find_repo_root()
    parser = argparse.ArgumentParser(
        description="Decompose F1 equivalence_witness hash mismatches (no model calls)",
    )
    parser.add_argument(
        "--json-out",
        default=str(repo_root / "docs/equivalence_hash_mismatch_decomposition.json"),
    )
    parser.add_argument(
        "--md-out",
        default=str(repo_root / "docs/equivalence_hash_mismatch_decomposition.md"),
    )
    parser.add_argument(
        "--csv-out",
        default=str(repo_root / "docs/equivalence_hash_mismatch_decomposition_tables.csv"),
    )
    args = parser.parse_args(argv)
    payload = export_equivalence_hash_mismatch_decomposition(
        repo_root,
        json_out=args.json_out,
        md_out=args.md_out,
        csv_out=args.csv_out,
    )
    print(
        json.dumps(
            {
                "json_out": args.json_out,
                "md_out": args.md_out,
                "csv_out": args.csv_out,
                "R1_failures": payload["coverage"][0]["eq_witness_failures"],
                "Oracle_failures": payload["coverage"][1]["eq_witness_failures"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
