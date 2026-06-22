"""Export extractability / metric-denominator audit for a local matrix run."""

from __future__ import annotations

import argparse
from pathlib import Path

from fsmreasonbench.evaluator.extractability_audit import (
    audit_matrix_scores,
    render_extractability_audit_markdown,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit extractability denominators for matrix experiment cells",
    )
    parser.add_argument(
        "--root",
        default="runs/local_matrix_v1",
        help="Matrix experiment root (default: runs/local_matrix_v1)",
    )
    parser.add_argument(
        "--out",
        default="docs/extractability_audit.md",
        help="Markdown output path (default: docs/extractability_audit.md)",
    )
    parser.add_argument(
        "--expected-items",
        type=int,
        default=20,
        help="Expected items per cell for partial-cell notes (default: 20)",
    )
    args = parser.parse_args(argv)

    root = Path(args.root)
    if not root.is_dir():
        parser.error(f"--root is not a directory: {root}")

    audits = audit_matrix_scores(root)
    if not audits:
        parser.error(f"no matrix scores.jsonl files found under {root}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        render_extractability_audit_markdown(
            audits,
            root=root,
            expected_items_per_cell=args.expected_items,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {out_path} ({len(audits)} cells)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
