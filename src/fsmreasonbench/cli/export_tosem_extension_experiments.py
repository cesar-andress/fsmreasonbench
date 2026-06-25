"""CLI: export TOSEM extension experiment artifacts (read-only)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.evaluator.tosem_extension_exports import export_tosem_extension_experiments


def main(argv: list[str] | None = None) -> int:
    repo_root = find_repo_root()
    parser = argparse.ArgumentParser(
        description=(
            "Export extension experiment LaTeX/JSON (replicates, cross-model attribution). "
            "Does not overwrite frozen TOSEM tables."
        ),
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

    manifest = export_tosem_extension_experiments(
        repo_root,
        paper_tables_dir=Path(args.paper_tables_dir),
        paper_figures_dir=Path(args.paper_figures_dir),
    )
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
