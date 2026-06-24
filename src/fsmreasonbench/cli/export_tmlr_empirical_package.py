"""Export TMLR empirical package (tables, figures, uncertainty, narrative)."""

from __future__ import annotations

import argparse
import json

from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.evaluator.tmlr_empirical_package import (
    PACKAGE_DIR,
    export_tmlr_empirical_package,
)


def main(argv: list[str] | None = None) -> int:
    repo_root = find_repo_root()
    parser = argparse.ArgumentParser(
        description="Export TMLR-ready empirical package from frozen runs (no model calls)",
    )
    parser.add_argument(
        "--out-dir",
        default=str(repo_root / PACKAGE_DIR),
        help=f"Output directory (default: {PACKAGE_DIR})",
    )
    args = parser.parse_args(argv)

    manifest = export_tmlr_empirical_package(repo_root)
    print(
        json.dumps(
            {
                "output_dir": args.out_dir,
                "package_version": manifest["package_version"],
                "figures": len(manifest["figures"]),
                "tables": list(manifest["tables"].keys()),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
