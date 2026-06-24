"""Export F1 equivalence_witness verifier audit report."""

from __future__ import annotations

import argparse
import json
import sys

from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.evaluator.f1_equivalence_witness_verifier_audit import (
    export_f1_equivalence_witness_verifier_audit,
)


def main(argv: list[str] | None = None) -> int:
    repo_root = find_repo_root()
    parser = argparse.ArgumentParser(
        description="Export hostile audit report for F1 equivalence_witness verifier",
    )
    parser.add_argument(
        "--markdown-out",
        default=str(repo_root / "docs/f1_equivalence_witness_verifier_audit.md"),
    )
    parser.add_argument(
        "--json-out",
        default=str(repo_root / "docs/f1_equivalence_witness_verifier_audit.json"),
    )
    args = parser.parse_args(argv)

    payload = export_f1_equivalence_witness_verifier_audit(
        markdown_path=args.markdown_out,
        json_path=args.json_out,
    )
    if not payload["summary"]["all_passed"]:
        print("audit checks failed", file=sys.stderr)
        print(json.dumps(payload["summary"], indent=2), file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "markdown": args.markdown_out,
                "json": args.json_out,
                "summary": payload["summary"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
