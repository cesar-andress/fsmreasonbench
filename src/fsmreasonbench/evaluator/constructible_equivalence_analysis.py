"""Construct-validity analysis: hash vs bisimulation vs distinguishing witnesses."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fsmreasonbench.evaluator.f1_claude_ablation_stratified_analysis import (
    load_item_metadata,
)
from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.evaluator.models import ScoringRecord
from fsmreasonbench.evaluator.summary import summarize_scoring_records

EXTENSION_TABLE_PREFIX = "extension_"
DOCS_DIR = "docs/a1_constructible_equivalence_v1"

FROZEN_HASH_PATHS: dict[str, dict[str, str]] = {
    "claude": {
        "R1": "runs/frontier_claude_sonnet_tools_n100_v2/claude-sonnet-4-5-20250929/F1/temp_0.2/R1/scores.jsonl",
        "R2C": "runs/ablations_f1_r2_attribution_claude_n100_v1/R2C/scores.jsonl",
    },
    "gpt": {
        "R1": "runs/frontier_gpt_tools_n100_v1/gpt-4.1/F1/temp_0.2/R1/scores.jsonl",
        "R2C": "runs/ablations_f1_r2c_gpt_n100_v1/R2C/scores.jsonl",
    },
}

CONSTRUCTIBLE_PATHS: dict[str, dict[str, str]] = {
    "claude": {
        "R1": "runs/f1_constructible_equivalence_claude_n100_v1/R1/scores.jsonl",
        "R2C": "runs/f1_constructible_equivalence_claude_n100_v1/R2C/scores.jsonl",
    },
    "gpt": {
        "R1": "runs/f1_constructible_equivalence_gpt_n100_v1/R1/scores.jsonl",
        "R2C": "runs/f1_constructible_equivalence_gpt_n100_v1/R2C/scores.jsonl",
    },
}


def _load_scoring(path: Path) -> list[ScoringRecord]:
    from fsmreasonbench.evaluator.jsonl import read_jsonl

    rows = list(read_jsonl(path))
    return [ScoringRecord.from_dict(row) for row in rows]


def _subset_summary(
    path: Path,
    metadata: dict[str, Any],
    *,
    cert_type: str,
) -> dict[str, Any] | None:
    if not path.exists():
        return {"status": "pending", "scores_path": str(path)}
    records = _load_scoring(path)
    filtered = [
        row
        for row in records
        if metadata.get(row.item_id)
        and metadata[row.item_id].gold_certificate_type == cert_type
    ]
    if not filtered:
        return {"status": "empty", "scores_path": str(path), "n": 0}
    summary = summarize_scoring_records(filtered)
    summary["status"] = "available"
    summary["scores_path"] = str(path)
    summary["n"] = len(filtered)
    return summary


def build_constructible_equivalence_analysis(repo_root: Path) -> dict[str, Any]:
    cohort = repo_root / "cohorts/v0.1-expanded-n100/f1-mixed-level3/items.jsonl"
    metadata = load_item_metadata(cohort)

    rows: list[dict[str, Any]] = []
    for provider in ("claude", "gpt"):
        for track in ("R1", "R2C"):
            hash_summary = _subset_summary(
                repo_root / FROZEN_HASH_PATHS[provider][track],
                metadata,
                cert_type="equivalence_witness",
            )
            dist_summary = _subset_summary(
                repo_root / FROZEN_HASH_PATHS[provider]["R1"],
                metadata,
                cert_type="distinguishing_trace",
            ) if track == "R1" else None
            construct_summary = _subset_summary(
                repo_root / CONSTRUCTIBLE_PATHS[provider][track],
                metadata,
                cert_type="equivalence_witness",
            )
            rows.append(
                {
                    "provider": provider,
                    "track": track,
                    "hash_equivalence_witness": hash_summary,
                    "constructible_bisimulation_witness": construct_summary,
                    "distinguishing_trace_r1_baseline": dist_summary,
                }
            )

    return {
        "experiment": "constructible_equivalence_witness_analysis",
        "subset": {
            "equivalence_witness_items": sum(
                1 for meta in metadata.values() if meta.gold_certificate_type == "equivalence_witness"
            ),
            "distinguishing_trace_items": sum(
                1
                for meta in metadata.values()
                if meta.gold_certificate_type == "distinguishing_trace"
            ),
        },
        "research_questions": _research_answers(rows),
        "rows": rows,
    }


def _research_answers(rows: list[dict[str, Any]]) -> dict[str, str]:
    def _rate(cell: dict[str, Any] | None, key: str = "certificate_valid_rate") -> str:
        if not cell or cell.get("status") != "available":
            return "pending"
        val = cell.get(key)
        return f"{val:.3f}" if isinstance(val, (int, float)) else "n/a"

    claude_r1_hash = next(r for r in rows if r["provider"] == "claude" and r["track"] == "R1")
    claude_r1_construct = claude_r1_hash["constructible_bisimulation_witness"]
    claude_r1_dist = claude_r1_hash["distinguishing_trace_r1_baseline"]

    return {
        "q1_hash_only_failure": (
            "Compare hash_equivalence_witness cert rate (~0 on R1) vs bisimulation_witness "
            f"on the same eq subset (constructible R1 cert={_rate(claude_r1_construct)}). "
            "A large gap supports the construct-validity critique that hash emission—not "
            "equivalence reasoning—drives the headline collapse."
        ),
        "q2_structural_witness_without_hash": (
            f"Constructible R1 cert={_rate(claude_r1_construct)} (Claude) indicates whether "
            "models can emit replay-checkable state-pair relations without hash arithmetic."
        ),
        "q3_r2c_benefit_after_hash_removal": (
            "Compare constructible R2C vs R1 and vs frozen hash R2C once campaigns complete; "
            "persistent R2C uplift with bisimulation_certificate indicates tool-assisted "
            "synthesis benefit beyond hash formatting."
        ),
        "q4_distinguishing_baseline": (
            f"Frozen distinguishing_trace R1 cert={_rate(claude_r1_dist)} on non-eq items "
            "provides a replay-checkable contrast class unaffected by hash requirements."
        ),
    }


def render_constructible_equivalence_latex(report: dict[str, Any]) -> str:
    lines = [
        "% Generated by export_constructible_equivalence_analysis (Experiment A1).",
        "\\begin{table}[t]",
        "  \\centering",
        "  \\caption{F1 equivalence subset: hash vs constructible bisimulation witnesses "
        "(pending cells await manual campaigns).}",
        "  \\label{tab:extension-constructible-equivalence}",
        "  \\footnotesize",
        "  \\begin{tabular}{@{}lllrrr@{}}",
        "    \\toprule",
        "    Provider & Track & Witness & $n$ & Cert. valid & Fully correct \\\\",
        "    \\midrule",
    ]
    for row in report.get("rows", []):
        for label, cell_key in (
            ("hash", "hash_equivalence_witness"),
            ("bisimulation", "constructible_bisimulation_witness"),
        ):
            cell = row.get(cell_key) or {}
            if cell.get("status") != "available":
                lines.append(
                    f"    {row['provider']} & {row['track']} & {label} & --- & --- & pending \\\\"
                )
                continue
            lines.append(
                f"    {row['provider']} & {row['track']} & {label} & {cell.get('n')} & "
                f"{cell.get('certificate_valid_rate', 0):.3f} & "
                f"{cell.get('fully_correct_rate', 0):.3f} \\\\"
            )
    lines.extend(["    \\bottomrule", "  \\end{tabular}", "\\end{table}"])
    return "\n".join(lines) + "\n"


def export_constructible_equivalence_package(
    repo_root: Path,
    *,
    paper_tables_dir: Path | None = None,
    paper_figures_dir: Path | None = None,
) -> dict[str, str]:
    report = build_constructible_equivalence_analysis(repo_root)
    docs_dir = repo_root / DOCS_DIR
    docs_dir.mkdir(parents=True, exist_ok=True)
    json_path = docs_dir / "constructible_equivalence_analysis.json"
    dump_json(json_path, report)
    latex = render_constructible_equivalence_latex(report)
    table_name = f"{EXTENSION_TABLE_PREFIX}constructible_equivalence_witness.tex"
    docs_table = docs_dir / table_name
    docs_table.write_text(latex, encoding="utf-8")
    outputs = {
        "analysis_json": str(json_path),
        "analysis_table_tex": str(docs_table),
    }
    if paper_tables_dir is not None:
        paper_tables_dir.mkdir(parents=True, exist_ok=True)
        paper_table = paper_tables_dir / table_name
        paper_table.write_text(latex, encoding="utf-8")
        outputs["paper_table"] = str(paper_table)

    if _try_figure(report, paper_figures_dir or repo_root.parent / "paper" / "figures"):
        outputs["paper_figure"] = str(
            (paper_figures_dir or repo_root.parent / "paper" / "figures")
            / f"{EXTENSION_TABLE_PREFIX}constructible_equivalence_comparison.pdf"
        )
    return outputs


def _try_figure(report: dict[str, Any], figures_dir: Path) -> bool:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return False

    labels: list[str] = []
    hash_rates: list[float] = []
    bisim_rates: list[float] = []
    for row in report.get("rows", []):
        h = row.get("hash_equivalence_witness") or {}
        b = row.get("constructible_bisimulation_witness") or {}
        if h.get("status") != "available" and b.get("status") != "available":
            continue
        labels.append(f"{row['provider']}-{row['track']}")
        hash_rates.append(float(h.get("certificate_valid_rate") or 0.0))
        bisim_rates.append(float(b.get("certificate_valid_rate") or 0.0))
    if not labels:
        return False

    x = range(len(labels))
    width = 0.35
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar([i - width / 2 for i in x], hash_rates, width, label="hash witness (frozen)")
    ax.bar([i + width / 2 for i in x], bisim_rates, width, label="bisimulation (A1)")
    ax.set_xticks(list(x), labels, rotation=20, ha="right")
    ax.set_ylabel("Certificate valid rate (eq subset)")
    ax.set_ylim(0, 1.05)
    ax.legend()
    fig.tight_layout()
    figures_dir.mkdir(parents=True, exist_ok=True)
    out_path = figures_dir / f"{EXTENSION_TABLE_PREFIX}constructible_equivalence_comparison.pdf"
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return True
