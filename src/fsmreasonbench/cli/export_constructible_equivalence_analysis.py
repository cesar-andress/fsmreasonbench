"""CLI: export constructible equivalence witness analysis (Experiment A1)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.evaluator.constructible_equivalence_analysis import (
    export_constructible_equivalence_package,
)


def main(argv: list[str] | None = None) -> int:
    repo_root = find_repo_root()
    parser = argparse.ArgumentParser(
        description="Export hash vs bisimulation construct-validity analysis (read-only on frozen runs)",
    )
    parser.add_argument(
        "--paper-tables-dir",
        default=str(repo_root.parent / "paper" / "tables"),
    )
    parser.add_argument(
        "--paper-figures-dir",
        default=str(repo_root.parent / "paper" / "figures"),
    )
    args = parser.parse_args(argv)
    outputs = export_constructible_equivalence_package(
        repo_root,
        paper_tables_dir=Path(args.paper_tables_dir),
        paper_figures_dir=Path(args.paper_figures_dir),
    )
    print(json.dumps(outputs, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
