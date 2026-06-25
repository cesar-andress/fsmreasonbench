"""Export TOSEM manuscript tables from frozen runs (Claude + GPT + local matrix)."""

from __future__ import annotations

import argparse
import json

from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.evaluator.tosem_empirical_package import (
    PACKAGE_DIR,
    export_tosem_empirical_package,
)


def main(argv: list[str] | None = None) -> int:
    repo_root = find_repo_root()
    parser = argparse.ArgumentParser(
        description=(
            "Export TOSEM-ready LaTeX tables and JSON summaries from frozen runs "
            "(no model API calls)"
        ),
    )
    parser.add_argument(
        "--paper-tables-dir",
        default=str(repo_root.parent / "paper" / "tables"),
        help="Directory for generated LaTeX tables",
    )
    args = parser.parse_args(argv)

    manifest = export_tosem_empirical_package(
        repo_root,
        paper_tables_dir=args.paper_tables_dir,
    )
    print(
        json.dumps(
            {
                "package_dir": str(repo_root / PACKAGE_DIR),
                "paper_tables": list(manifest["paper_tables"].keys()),
                "gpt_cells_exported": manifest["gpt_frontier_export"]["cells_exported"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
