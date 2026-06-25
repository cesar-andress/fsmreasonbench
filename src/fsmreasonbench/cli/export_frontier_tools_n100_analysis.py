"""Export frontier tool-track n=100 analysis package (summary, subtypes, uncertainty)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.evaluator.frontier_tools_analysis import export_frontier_tools_n100_package


def _default_paper_tables_path(repo_root: Path, filename: str) -> Path:
    paper_tables = repo_root.parent / "paper" / "tables" / filename
    if paper_tables.parent.exists():
        return paper_tables
    return repo_root / "docs" / filename


def main(argv: list[str] | None = None) -> int:
    repo_root = find_repo_root()
    parser = argparse.ArgumentParser(
        description="Export frontier tools n=100 analysis package from a campaign manifest",
    )
    parser.add_argument(
        "--config",
        default="configs/frontier/frontier_gpt_tools_n100_v1.json",
        help="Campaign manifest JSON path relative to repo root",
    )
    parser.add_argument(
        "--json-out",
        default="docs/frontier_gpt_tools_n100_v1_summary.json",
    )
    parser.add_argument(
        "--latex-out",
        default=str(_default_paper_tables_path(repo_root, "gpt_tools_n100_summary.tex")),
    )
    parser.add_argument(
        "--markdown-out",
        default="docs/frontier_gpt_tools_n100_v1_summary.md",
    )
    parser.add_argument(
        "--subtype-json-out",
        default="docs/f1_gpt_frontier_subtype_stratified_analysis.json",
    )
    parser.add_argument(
        "--uncertainty-json-out",
        default="docs/frontier_gpt_tools_n100_v1_uncertainty.json",
    )
    parser.add_argument("--model-label", help="Human-readable model label for LaTeX caption")
    parser.add_argument("--table-label", help="LaTeX \\label{...} for summary table")
    args = parser.parse_args(argv)

    payload = export_frontier_tools_n100_package(
        repo_root,
        campaign_config_path=repo_root / args.config,
        json_out=repo_root / args.json_out,
        latex_out=repo_root / args.latex_out,
        markdown_out=repo_root / args.markdown_out,
        subtype_json_out=repo_root / args.subtype_json_out,
        uncertainty_json_out=repo_root / args.uncertainty_json_out,
        model_label=args.model_label,
        table_label=args.table_label,
    )
    print(json.dumps({"campaign_id": payload["campaign_id"], "outputs": args.json_out}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
