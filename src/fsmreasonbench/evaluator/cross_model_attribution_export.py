"""Cross-model attribution comparison (Experiment C)."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from fsmreasonbench.evaluator.f1_claude_ablation_stratified_analysis import (
    load_condition_outcomes,
    load_item_metadata,
    paired_bootstrap_difference_ci,
)
from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.evaluator.summary import summarize_scoring_records

EXTENSION_DOCS_DIR = "docs/tosem_extension_experiments_v1"
EXTENSION_TABLE_PREFIX = "extension_"

ATTRIBUTION_CONDITIONS: tuple[str, ...] = (
    "Oracle+Format",
    "R2A",
    "R2B",
    "R2C",
)

CLAUDE_ATTRIBUTION_RUNS: dict[str, str] = {
    "Oracle+Format": "runs/ablations_f1_oracle_verdict_format_control_claude_n100_v1/scores.jsonl",
    "R2A": "runs/ablations_f1_r2_attribution_claude_n100_v1/R2A/scores.jsonl",
    "R2B": "runs/ablations_f1_r2_attribution_claude_n100_v1/R2B/scores.jsonl",
    "R2C": "runs/ablations_f1_r2_attribution_claude_n100_v1/R2C/scores.jsonl",
}

GPT_ATTRIBUTION_RUNS: dict[str, str] = {
    "Oracle+Format": "runs/ablations_f1_oracle_verdict_format_control_gpt_n100_v1/scores.jsonl",
    "R2A": "runs/ablations_f1_r2_attribution_gpt_n100_v1/R2A/scores.jsonl",
    "R2B": "runs/ablations_f1_r2_attribution_gpt_n100_v1/R2B/scores.jsonl",
    "R2C": "runs/ablations_f1_r2_attribution_gpt_n100_v1/R2C/scores.jsonl",
}

FROZEN_GPT_PARTIAL_RUNS: dict[str, str] = {
    "R2C": "runs/ablations_f1_r2c_gpt_n100_v1/R2C/scores.jsonl",
}


def _resolve_run_paths(
    mapping: dict[str, str],
    repo_root: Path,
) -> dict[str, Path | None]:
    resolved: dict[str, Path | None] = {}
    for condition, rel in mapping.items():
        path = repo_root / rel
        resolved[condition] = path if path.exists() else None
    return resolved


def _condition_summary(path: Path) -> dict[str, Any]:
    from fsmreasonbench.evaluator.jsonl import read_jsonl
    from fsmreasonbench.evaluator.models import ScoringRecord

    rows = list(read_jsonl(path))
    scoring = [ScoringRecord.from_dict(row) for row in rows]
    summary = summarize_scoring_records(scoring)
    summary["n_scores"] = len(scoring)
    return summary


def _load_outcomes(path: Path) -> dict[str, Any]:
    return load_condition_outcomes(path)


def build_provider_attribution_summary(
    repo_root: Path,
    *,
    provider: str,
    run_map: dict[str, str],
) -> dict[str, Any]:
    conditions: dict[str, Any] = {}
    for condition, rel in run_map.items():
        path = repo_root / rel
        if not path.exists():
            conditions[condition] = {"status": "pending", "scores_path": str(path)}
            continue
        summary = _condition_summary(path)
        conditions[condition] = {
            "status": "available",
            "scores_path": str(path),
            "certificate_valid_rate": summary.get("certificate_valid_rate"),
            "fully_correct_rate": summary.get("fully_correct_rate"),
            "verdict_accuracy": summary.get("verdict_accuracy"),
            "n": summary.get("n"),
        }
    return {"provider": provider, "conditions": conditions}


def build_cross_model_attribution_report(
    repo_root: Path,
    *,
    cohort_items: str = "cohorts/v0.1-expanded-n100/f1-mixed-level3/items.jsonl",
) -> dict[str, Any]:
    claude = build_provider_attribution_summary(
        repo_root, provider="claude", run_map=CLAUDE_ATTRIBUTION_RUNS
    )
    gpt_full = build_provider_attribution_summary(
        repo_root, provider="gpt", run_map=GPT_ATTRIBUTION_RUNS
    )
    gpt_frozen = build_provider_attribution_summary(
        repo_root, provider="gpt_frozen_partial", run_map=FROZEN_GPT_PARTIAL_RUNS
    )

    paired_rows: list[dict[str, Any]] = []
    metadata_path = repo_root / cohort_items
    metadata = load_item_metadata(metadata_path) if metadata_path.exists() else {}
    for condition in ATTRIBUTION_CONDITIONS:
        claude_path = repo_root / CLAUDE_ATTRIBUTION_RUNS[condition]
        gpt_path = repo_root / GPT_ATTRIBUTION_RUNS[condition]
        if not claude_path.exists() or not gpt_path.exists():
            paired_rows.append(
                {
                    "condition": condition,
                    "status": "pending",
                    "claude_scores": str(claude_path),
                    "gpt_scores": str(gpt_path),
                }
            )
            continue
        claude_out = load_condition_outcomes(claude_path)
        gpt_out = load_condition_outcomes(gpt_path)
        common_ids = sorted(set(claude_out) & set(gpt_out) & set(metadata))
        claude_rates = [
            1.0 if claude_out[i].certificate_valid else 0.0 for i in common_ids
        ]
        gpt_rates = [1.0 if gpt_out[i].certificate_valid else 0.0 for i in common_ids]
        diff = sum(g - c for c, g in zip(claude_rates, gpt_rates)) / len(common_ids)
        ci = paired_bootstrap_difference_ci(claude_rates, gpt_rates)
        paired_rows.append(
            {
                "condition": condition,
                "status": "available",
                "n_paired": len(common_ids),
                "gpt_minus_claude_cert_rate": round(diff, 4),
                "bootstrap_ci": ci,
                "effect_size_cohens_h": _cohens_h(
                    sum(claude_rates) / len(claude_rates),
                    sum(gpt_rates) / len(gpt_rates),
                ),
            }
        )

    return {
        "experiment": "cross_model_attribution_comparison",
        "claude": claude,
        "gpt": gpt_full,
        "gpt_frozen_partial": gpt_frozen,
        "paired_comparisons": paired_rows,
    }


def _cohens_h(p1: float, p2: float) -> float | None:
    try:
        return round(2.0 * math.asin(math.sqrt(p1)) - 2.0 * math.asin(math.sqrt(p2)), 4)
    except ValueError:
        return None


def render_cross_model_attribution_latex(report: dict[str, Any]) -> str:
    lines = [
        "% Generated by export_tosem_extension_experiments (Experiment C).",
        "\\begin{table}[t]",
        "  \\centering",
        "  \\caption{Cross-model F1 attribution comparison (Claude vs GPT-4.1). "
        "Pending cells await new GPT ladder campaigns; frozen R2C remains in partial column.}",
        "  \\label{tab:extension-cross-model-attribution}",
        "  \\begin{tabular}{@{}lcccc@{}}",
        "    \\toprule",
        "    Condition & Claude cert. & GPT cert. & $\\Delta$ (GPT$-$Claude) & Status \\\\",
        "    \\midrule",
    ]
    claude_conds = (report.get("claude") or {}).get("conditions") or {}
    gpt_conds = (report.get("gpt") or {}).get("conditions") or {}
    paired = {row["condition"]: row for row in report.get("paired_comparisons") or []}
    for condition in ATTRIBUTION_CONDITIONS:
        c = claude_conds.get(condition, {})
        g = gpt_conds.get(condition, {})
        c_rate = c.get("certificate_valid_rate")
        g_rate = g.get("certificate_valid_rate")
        c_s = f"{c_rate:.3f}" if c_rate is not None else ""
        g_s = f"{g_rate:.3f}" if g_rate is not None else ""
        p = paired.get(condition, {})
        delta = p.get("gpt_minus_claude_cert_rate")
        d_s = f"{delta:+.3f}" if delta is not None else ""
        status = p.get("status", g.get("status", c.get("status", "pending")))
        lines.append(f"    {condition} & {c_s} & {g_s} & {d_s} & {status} \\\\")
    lines.extend(["    \\bottomrule", "  \\end{tabular}", "\\end{table}"])
    return "\n".join(lines) + "\n"


def _try_cross_model_plot(report: dict[str, Any], out_path: Path) -> bool:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return False

    claude_conds = (report.get("claude") or {}).get("conditions") or {}
    gpt_conds = (report.get("gpt") or {}).get("conditions") or {}
    labels: list[str] = []
    claude_vals: list[float] = []
    gpt_vals: list[float] = []
    for condition in ATTRIBUTION_CONDITIONS:
        c = claude_conds.get(condition, {})
        g = gpt_conds.get(condition, {})
        if c.get("status") != "available" or g.get("status") != "available":
            continue
        c_rate = c.get("certificate_valid_rate")
        g_rate = g.get("certificate_valid_rate")
        if c_rate is None or g_rate is None:
            continue
        labels.append(condition)
        claude_vals.append(float(c_rate))
        gpt_vals.append(float(g_rate))
    if not labels:
        return False

    x = range(len(labels))
    width = 0.35
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar([i - width / 2 for i in x], claude_vals, width, label="Claude")
    ax.bar([i + width / 2 for i in x], gpt_vals, width, label="GPT-4.1")
    ax.set_xticks(list(x), labels, rotation=20, ha="right")
    ax.set_ylabel("Certificate valid rate")
    ax.set_title("Cross-model F1 attribution comparison")
    ax.legend()
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return True


def export_cross_model_attribution_package(
    repo_root: Path,
    *,
    paper_tables_dir: Path | None = None,
    paper_figures_dir: Path | None = None,
) -> dict[str, str]:
    report = build_cross_model_attribution_report(repo_root)
    docs_dir = repo_root / EXTENSION_DOCS_DIR
    docs_dir.mkdir(parents=True, exist_ok=True)

    json_path = docs_dir / "cross_model_attribution_comparison.json"
    dump_json(json_path, report)

    latex = render_cross_model_attribution_latex(report)
    table_name = f"{EXTENSION_TABLE_PREFIX}cross_model_attribution.tex"
    docs_table = docs_dir / table_name
    docs_table.write_text(latex, encoding="utf-8")

    outputs = {
        "cross_model_json": str(json_path),
        "cross_model_table_tex": str(docs_table),
    }
    if paper_tables_dir is not None:
        paper_tables_dir.mkdir(parents=True, exist_ok=True)
        paper_path = paper_tables_dir / table_name
        paper_path.write_text(latex, encoding="utf-8")
        outputs["paper_cross_model_table"] = str(paper_path)

    if paper_figures_dir is None:
        paper_figures_dir = repo_root.parent / "paper" / "figures"
    fig_path = paper_figures_dir / f"{EXTENSION_TABLE_PREFIX}cross_model_attribution.pdf"
    if _try_cross_model_plot(report, fig_path):
        outputs["cross_model_plot"] = str(fig_path)
    return outputs
