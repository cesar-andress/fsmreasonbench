"""CLI: export F1 bisimulation_witness hostile verifier audit."""

from __future__ import annotations

import argparse
import json

from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.evaluator.f1_bisimulation_witness_verifier_audit import (
    export_f1_bisimulation_witness_verifier_audit,
)


def main(argv: list[str] | None = None) -> int:
    repo_root = find_repo_root()
    parser = argparse.ArgumentParser(description="Export bisimulation_witness verifier audit")
    parser.add_argument(
        "--json-out",
        default=str(repo_root / "docs/f1_bisimulation_witness_verifier_audit.json"),
    )
    parser.add_argument(
        "--markdown-out",
        default=str(repo_root / "docs/f1_bisimulation_witness_verifier_audit.md"),
    )
    args = parser.parse_args(argv)
    payload = export_f1_bisimulation_witness_verifier_audit(
        markdown_path=args.markdown_out,
        json_path=args.json_out,
    )
    print(json.dumps(payload["summary"], indent=2))
    return 0 if payload["summary"]["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
