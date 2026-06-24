"""Export certificate class complexity analysis docs."""

from __future__ import annotations

import argparse
import json

from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.evaluator.certificate_class_complexity_analysis import (
    export_certificate_class_complexity_analysis,
)


def main(argv: list[str] | None = None) -> int:
    repo_root = find_repo_root()
    parser = argparse.ArgumentParser(
        description="Export structural certificate complexity analysis (no model calls)",
    )
    parser.add_argument(
        "--json-out",
        default=str(repo_root / "docs/certificate_class_complexity_analysis.json"),
    )
    parser.add_argument(
        "--md-out",
        default=str(repo_root / "docs/certificate_class_complexity_analysis.md"),
    )
    parser.add_argument(
        "--csv-out",
        default=str(repo_root / "docs/certificate_class_complexity_tables.csv"),
    )
    args = parser.parse_args(argv)
    payload = export_certificate_class_complexity_analysis(
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
                "certificate_types": list(payload["certificate_specs"].keys()),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
