"""Export TOSEM extension experiment tables/figures (Experiment E; read-only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fsmreasonbench.evaluator.cross_model_attribution_export import (
    export_cross_model_attribution_package,
)
from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.evaluator.replicate_stability_export import (
    EXTENSION_DOCS_DIR,
    export_replicate_stability_package,
    export_run_stability_comparison_package,
)
from fsmreasonbench.experiments.replicate_studies import replicate_study_root

PACKAGE_DIR = EXTENSION_DOCS_DIR

DEFAULT_REPLICATE_STUDIES: dict[str, str] = {
    "claude_frontier": "runs/frontier_claude_sonnet_tools_n100_v2_replicates",
    "gpt_frontier": "runs/frontier_gpt_tools_n100_v1_replicates",
}


def export_tosem_extension_experiments(
    repo_root: Path,
    *,
    paper_tables_dir: Path | None = None,
    paper_figures_dir: Path | None = None,
    replicate_studies: dict[str, str] | None = None,
) -> dict[str, Any]:
    if paper_tables_dir is None:
        paper_tables_dir = repo_root.parent / "paper" / "tables"
    if paper_figures_dir is None:
        paper_figures_dir = repo_root.parent / "paper" / "figures"

    manifest: dict[str, Any] = {
        "package_version": "tosem_extension_v1",
        "generated_from": "extension experiment outputs only (does not overwrite frozen tables)",
        "replicate_exports": {},
        "cross_model_attribution": {},
        "run_stability_comparison": {},
        "paper_tables": {},
        "paper_figures": {},
        "pending_studies": [],
    }

    studies = replicate_studies or DEFAULT_REPLICATE_STUDIES
    for label, rel_root in studies.items():
        study_root = repo_root / rel_root
        agg = study_root / "aggregate_replicates.json"
        if not agg.exists():
            manifest["pending_studies"].append(
                {
                    "label": label,
                    "study_root": str(study_root),
                    "reason": "aggregate_replicates.json not found (campaign not run yet)",
                }
            )
            continue
        aggregate = json.loads(agg.read_text(encoding="utf-8"))
        campaign_id = str(aggregate.get("campaign_id", label))
        paths = export_replicate_stability_package(
            repo_root,
            study_root=study_root,
            campaign_id=campaign_id,
            paper_tables_dir=paper_tables_dir,
            paper_figures_dir=paper_figures_dir,
        )
        manifest["replicate_exports"][label] = paths
        for key, path in paths.items():
            if "paper" in key or path.endswith(".tex") or path.endswith(".pdf"):
                target = "paper_tables" if path.endswith(".tex") else "paper_figures"
                manifest[target][Path(path).name] = path

    cross_paths = export_cross_model_attribution_package(
        repo_root,
        paper_tables_dir=paper_tables_dir,
        paper_figures_dir=paper_figures_dir,
    )
    manifest["cross_model_attribution"] = cross_paths
    if "paper_cross_model_table" in cross_paths:
        manifest["paper_tables"][Path(cross_paths["paper_cross_model_table"]).name] = cross_paths[
            "paper_cross_model_table"
        ]
    if "cross_model_plot" in cross_paths:
        manifest["paper_figures"][Path(cross_paths["cross_model_plot"]).name] = cross_paths[
            "cross_model_plot"
        ]

    claude_study = repo_root / studies["claude_frontier"]
    gpt_study = repo_root / studies["gpt_frontier"]
    stability_cmp = export_run_stability_comparison_package(
        repo_root,
        claude_study_root=claude_study,
        gpt_study_root=gpt_study,
        paper_tables_dir=paper_tables_dir,
    )
    manifest["run_stability_comparison"] = stability_cmp
    if "paper_stability_vs_cross_model_table" in stability_cmp:
        manifest["paper_tables"][
            Path(stability_cmp["paper_stability_vs_cross_model_table"]).name
        ] = stability_cmp["paper_stability_vs_cross_model_table"]

    package_dir = repo_root / PACKAGE_DIR
    package_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = package_dir / "extension_manifest.json"
    dump_json(manifest_path, manifest)
    manifest["manifest_path"] = str(manifest_path)
    return manifest
