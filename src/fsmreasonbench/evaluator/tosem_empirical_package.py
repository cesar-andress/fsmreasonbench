"""TOSEM manuscript exports from frozen runs (provider-agnostic, no inference)."""

from __future__ import annotations

import json
import math
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable

from fsmreasonbench.evaluator.f1_claude_ablation_stratified_analysis import (
    exact_mcnemar_p_value,
    load_condition_outcomes,
    load_item_metadata,
    paired_bootstrap_difference_ci,
)
from fsmreasonbench.evaluator.frontier_tools_analysis import (
    build_summary_table_rows,
    export_frontier_tools_n100_package,
    render_frontier_tools_latex_table,
)

PACKAGE_DIR = "docs/tosem_empirical_package_v1"

FROZEN_COMBINED_SUMMARIES: dict[str, str] = {
    "local_matrix": "runs/local_matrix_n100_t02_v2/combined_summary.json",
    "claude_tools": "runs/frontier_claude_sonnet_tools_n100_v2/combined_summary.json",
    "gpt_tools": "runs/frontier_gpt_tools_n100_v1/combined_summary.json",
    "gpt_r2c": "runs/ablations_f1_r2c_gpt_n100_v1/combined_summary.json",
}

GPT_F1_CONDITION_RUNS: dict[str, str] = {
    "R1": "runs/frontier_gpt_tools_n100_v1/gpt-4.1/F1/temp_0.2/R1/scores.jsonl",
    "R2": "runs/frontier_gpt_tools_n100_v1/gpt-4.1/F1/temp_0.2/R2/scores.jsonl",
    "R2C": "runs/ablations_f1_r2c_gpt_n100_v1/R2C/scores.jsonl",
}

GPT_F1_CONDITION_ORDER: tuple[str, ...] = ("R1", "R2", "R2C")

CLAUDE_MCNEMAR_JSON = "docs/tmlr_empirical_package_v1/uncertainty/bootstrap_mcnemar_summary.json"
GPT_UNCERTAINTY_JSON = "docs/frontier_gpt_tools_n100_v1_uncertainty.json"

DEFAULT_COHORT_ITEMS = "cohorts/v0.1-expanded-n100/f1-mixed-level3/items.jsonl"
GPT_CAMPAIGN_CONFIG = "configs/frontier/frontier_gpt_tools_n100_v1.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _format_rate(value: float | None, *, decimals: int = 3) -> str:
    if value is None:
        return "—"
    return f"{value:.{decimals}f}"


def _pair_fmt(cert: float, full: float) -> str:
    return f"{cert:.3f} / {full:.3f}"


def _gap(verdict: float | None, full: float | None) -> float | None:
    if verdict is None or full is None:
        return None
    return round(verdict - full, 3)


def _cells_from_combined(path: Path) -> list[dict[str, Any]]:
    payload = _load_json(path)
    if "cell_inventory" in payload:
        return list(payload["cell_inventory"])
    if "track_rows" in payload:
        rows = []
        for row in payload["track_rows"]:
            normalized = dict(row)
            track = str(row.get("track", ""))
            if track.startswith("R2C"):
                normalized["track"] = "R2C"
            rows.append(normalized)
        return rows
    return []


def _gap_row(model: str, cell: dict[str, Any]) -> dict[str, Any]:
    verdict = cell.get("verdict_accuracy")
    cert = cell.get("certificate_valid_rate")
    full = cell.get("fully_correct_rate")
    return {
        "model": model,
        "family": cell["family"],
        "track": cell["track"],
        "verdict": verdict,
        "cert": cert,
        "full": full,
        "gap": _gap(verdict, full),
    }


def _failure_row(model: str, cell: dict[str, Any]) -> dict[str, Any]:
    counts = cell.get("failure_stage_counts") or {}
    return {
        "model": model,
        "family": cell["family"],
        "track": cell["track"],
        "not_extractable": counts.get("not_extractable", 0),
        "verdict_wrong": counts.get("verdict_wrong", 0),
        "certificate_invalid": counts.get("certificate_invalid", 0),
        "correct": counts.get("correct", 0),
    }


def build_knowing_showing_gap_rows(repo_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    local_cells = _cells_from_combined(repo_root / FROZEN_COMBINED_SUMMARIES["local_matrix"])
    for cell in sorted(local_cells, key=lambda c: (c.get("model", ""), c["family"], c["track"])):
        rows.append(_gap_row(str(cell["model"]), cell))
    for cell in _cells_from_combined(repo_root / FROZEN_COMBINED_SUMMARIES["claude_tools"]):
        rows.append(_gap_row("Claude Sonnet", cell))
    for cell in _cells_from_combined(repo_root / FROZEN_COMBINED_SUMMARIES["gpt_tools"]):
        rows.append(_gap_row("GPT-4.1", cell))
    for cell in _cells_from_combined(repo_root / FROZEN_COMBINED_SUMMARIES["gpt_r2c"]):
        rows.append(_gap_row("GPT-4.1", cell))
    return rows


def build_failure_stage_rows(repo_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cell in sorted(
        _cells_from_combined(repo_root / FROZEN_COMBINED_SUMMARIES["local_matrix"]),
        key=lambda c: (c.get("model", ""), c["family"], c["track"]),
    ):
        rows.append(_failure_row(str(cell["model"]), cell))
    for cell in _cells_from_combined(repo_root / FROZEN_COMBINED_SUMMARIES["claude_tools"]):
        rows.append(_failure_row("Claude Sonnet", cell))
    for cell in _cells_from_combined(repo_root / FROZEN_COMBINED_SUMMARIES["gpt_tools"]):
        rows.append(_failure_row("GPT-4.1", cell))
    for cell in _cells_from_combined(repo_root / FROZEN_COMBINED_SUMMARIES["gpt_r2c"]):
        rows.append(_failure_row("GPT-4.1", cell))
    return rows


def _group_gap_rows(rows: list[dict[str, Any]]) -> list[tuple[str, list[dict[str, Any]]]]:
    groups: list[tuple[str, list[dict[str, Any]]]] = []
    local: list[dict[str, Any]] = []
    claude: list[dict[str, Any]] = []
    gpt: list[dict[str, Any]] = []
    for row in rows:
        model = row["model"]
        if model == "Claude Sonnet":
            claude.append(row)
        elif model == "GPT-4.1":
            gpt.append(row)
        else:
            local.append(row)
    if local:
        groups.append(("Local open-weight (Ollama)", local))
    if claude:
        groups.append(("Frontier tools (Claude Sonnet)", claude))
    if gpt:
        groups.append(("Frontier tools (GPT-4.1)", gpt))
    return groups


def render_knowing_showing_gap_latex(rows: list[dict[str, Any]]) -> str:
    lines = [
        "% Verdict--witness gap: verdict accuracy minus full correctness rate (same cell).",
        "% Generated by export_tosem_empirical_package from frozen combined_summary.json files.",
        "% Verdict denominator = extractable items; Full denominator = n.",
        "\\begin{table*}[t]",
        "  \\centering",
        "  \\caption{Verdict--witness gap on frozen $n{=}100$ cells.",
        "    Gap $=$ Verdict $-$ Full (both as reported rates).",
        "    Large gaps under tool execution indicate correct boolean verdicts without end-to-end certification.}",
        "  \\label{tab:knowing-showing-gap-n100}",
        "  \\small",
        "  \\begin{tabular}{@{}lllrrrr@{}}",
        "    \\toprule",
        "    Model & Fam. & Track & Verdict & Cert. & Full & Gap \\\\",
        "    \\midrule",
    ]
    for group_title, group_rows in _group_gap_rows(rows):
        lines.append(f"    \\multicolumn{{7}}{{l}}{{\\textit{{{group_title}}}}} \\\\")
        for row in group_rows:
            model_display = row["model"]
            if model_display not in {"Claude Sonnet", "GPT-4.1"}:
                model_display = f"\\texttt{{{model_display}}}"
            lines.append(
                "    "
                + " & ".join(
                    [
                        model_display,
                        str(row["family"]),
                        str(row["track"]),
                        _format_rate(row["verdict"]),
                        _format_rate(row["cert"]),
                        _format_rate(row["full"]),
                        _format_rate(row["gap"]),
                    ]
                )
                + " \\\\"
            )
        lines.append("    \\midrule")
    if lines[-1].endswith("\\midrule"):
        lines[-1] = "    \\bottomrule"
    lines.extend(["  \\end{tabular}", "\\end{table*}", ""])
    return "\n".join(lines)


def render_failure_stage_latex(rows: list[dict[str, Any]]) -> str:
    lines = [
        "% Failure-stage decomposition (failure_stage_counts). Provider errors = 0 for all frozen cells.",
        "% Generated by export_tosem_empirical_package from frozen combined_summary.json files.",
        "\\begin{table*}[t]",
        "  \\centering",
        "  \\caption{Failure-stage decomposition on frozen $n{=}100$ cells (counts sum to $n{=}100$ per cell).",
        "    \\texttt{not\\_extractable}: model output parse failures;",
        "    \\texttt{verdict\\_wrong}: extractable but wrong boolean verdict;",
        "    \\texttt{certificate\\_invalid}: correct verdict but verifier rejects certificate;",
        "    \\texttt{correct}: fully correct.}",
        "  \\label{tab:failure-stage-n100}",
        "  \\scriptsize",
        "  \\begin{tabular}{@{}lllrrrr@{}}",
        "    \\toprule",
        "    Model & Fam. & Track & Not Ext. & Verdict Wrong & Cert.\\ Invalid & Correct \\\\",
        "    \\midrule",
    ]
    sections: list[tuple[str, list[dict[str, Any]]]] = [
        ("local", [r for r in rows if r["model"] not in {"Claude Sonnet", "GPT-4.1"}]),
        ("claude", [r for r in rows if r["model"] == "Claude Sonnet"]),
        ("gpt", [r for r in rows if r["model"] == "GPT-4.1"]),
    ]
    for index, (_, section_rows) in enumerate(sections):
        for row in section_rows:
            model_display = row["model"]
            if model_display not in {"Claude Sonnet", "GPT-4.1"}:
                model_display = f"\\texttt{{{model_display}}}"
            lines.append(
                "    "
                + " & ".join(
                    [
                        model_display,
                        str(row["family"]),
                        str(row["track"]),
                        str(row["not_extractable"]),
                        str(row["verdict_wrong"]),
                        str(row["certificate_invalid"]),
                        str(row["correct"]),
                    ]
                )
                + " \\\\"
            )
        if index < len(sections) - 1 and section_rows:
            lines.append("    \\midrule")
    lines.extend(["    \\bottomrule", "  \\end{tabular}", "\\end{table*}", ""])
    return "\n".join(lines)


def render_frontier_comparison_latex(
    claude_rows: list[dict[str, Any]],
    gpt_rows: list[dict[str, Any]],
) -> str:
    lines = [
        "% Unified frontier tool-track comparison (Claude Sonnet 4.5 vs GPT-4.1).",
        "% Generated by export_tosem_empirical_package from frozen combined_summary.json files.",
        "\\begin{table}[t]",
        "  \\centering",
        "  \\caption{Frontier tool-track comparison on frozen $n{=}100$ cells ($T{=}0.2$).",
        "    Verdict and certificate rates condition on extractable submissions; full correctness uses all $n{=}100$ items.}",
        "  \\label{tab:frontier-tools-comparison-n100}",
        "  \\footnotesize",
        "  \\setlength{\\tabcolsep}{3pt}",
        "  \\begin{tabular}{@{}llllrrrr@{}}",
        "    \\toprule",
        "    Model & Fam. & Track & $n$ & Extract. & Verdict & Cert. & Full \\\\",
        "    \\midrule",
    ]
    for model_label, rows in (("Claude Sonnet 4.5", claude_rows), ("GPT-4.1", gpt_rows)):
        for row in rows:
            lines.append(
                "    "
                + " & ".join(
                    [
                        model_label,
                        str(row["family"]),
                        str(row["track"]),
                        str(row["n"]),
                        _format_rate(row["extractability_rate"]),
                        _format_rate(row["verdict_accuracy"]),
                        _format_rate(row["certificate_valid_rate"]),
                        _format_rate(row["fully_correct_rate"]),
                    ]
                )
                + " \\\\"
            )
        lines.append("    \\midrule")
    if lines[-1].endswith("\\midrule"):
        lines[-1] = "    \\bottomrule"
    lines.extend(["  \\end{tabular}", "\\end{table}", ""])
    return "\n".join(lines)


def _rate(values: Iterable[bool]) -> float:
    values = list(values)
    if not values:
        return 0.0
    return sum(1 for value in values if value) / len(values)


def build_f1_gpt_ablation_rows(
    repo_root: Path,
    *,
    cohort_items_path: Path | None = None,
) -> list[dict[str, Any]]:
    metadata = load_item_metadata(cohort_items_path or repo_root / DEFAULT_COHORT_ITEMS)
    rows: list[dict[str, Any]] = []
    for condition in GPT_F1_CONDITION_ORDER:
        scores_path = repo_root / GPT_F1_CONDITION_RUNS[condition]
        outcomes = load_condition_outcomes(scores_path)
        by_type: dict[str, list[ItemOutcome]] = {
            "equivalence_witness": [],
            "distinguishing_trace": [],
        }
        all_outcomes: list[ItemOutcome] = []
        for item_id, meta in metadata.items():
            if item_id not in outcomes:
                continue
            outcome = outcomes[item_id]
            all_outcomes.append(outcome)
            by_type[meta.gold_certificate_type].append(outcome)
        rows.append(
            {
                "condition": condition,
                "distinguishing_trace_cert": _rate(
                    row.certificate_valid for row in by_type["distinguishing_trace"]
                ),
                "distinguishing_trace_full": _rate(
                    row.fully_correct for row in by_type["distinguishing_trace"]
                ),
                "equivalence_witness_cert": _rate(
                    row.certificate_valid for row in by_type["equivalence_witness"]
                ),
                "equivalence_witness_full": _rate(
                    row.fully_correct for row in by_type["equivalence_witness"]
                ),
                "overall_cert": _rate(row.certificate_valid for row in all_outcomes),
                "overall_full": _rate(row.fully_correct for row in all_outcomes),
            }
        )
    return rows


def render_f1_gpt_ablations_latex(rows: list[dict[str, Any]]) -> str:
    condition_labels = {
        "R1": "R1 (tool planning)",
        "R2": "R2 (full execution)",
        "R2C": "R2C (generator-assisted)",
    }
    lines = [
        "% Generated by export_tosem_empirical_package from frozen GPT F1 scores.jsonl files.",
        "\\begin{table}[t]",
        "\\centering",
        "\\caption{F1 GPT-4.1 ablations by condition and certificate subtype "
        "(certificate/full rates; frozen $n{=}100$). "
        "Oracle+Format, R2A, and R2B are not in the GPT freeze.}",
        "\\label{tab:f1-gpt-ablations}",
        "\\footnotesize",
        "\\setlength{\\tabcolsep}{3pt}",
        "\\begin{tabular}{@{}lccc@{}}",
        "\\toprule",
        "Condition & dist.\\ cert/full & eq.\\ cert/full & all cert/full \\\\",
        "\\midrule",
    ]
    for row in rows:
        label = condition_labels.get(row["condition"], row["condition"])
        lines.append(
            "    "
            + " & ".join(
                [
                    label,
                    _pair_fmt(row["distinguishing_trace_cert"], row["distinguishing_trace_full"]),
                    _pair_fmt(row["equivalence_witness_cert"], row["equivalence_witness_full"]),
                    _pair_fmt(row["overall_cert"], row["overall_full"]),
                ]
            )
            + " \\\\"
        )
    lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table}", ""])
    return "\n".join(lines)


def _format_p_value(p_value: float | None) -> str:
    if p_value is None:
        return "—"
    if p_value < 0.001:
        return "$\\ll 0.05$"
    return f"{p_value:.3f}"


def _format_ci(diff: dict[str, float]) -> str:
    return f"${diff['point_diff']:.3f} [{diff['ci_low']:.3f}, {diff['ci_high']:.3f}]$"


def build_paired_mcnemar_rows(repo_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    claude_payload = _load_json(repo_root / CLAUDE_MCNEMAR_JSON)
    claude_labels = {
        "F1 R1 vs R2C (overall, n=100)": "F1 R1 vs R2C",
        "F1 R2A vs R2C (overall, n=100)": "F1 R2A vs R2C",
        "F1 R2B vs R2C (overall, n=100)": "F1 R2B vs R2C",
        "F1 eq-witness R1 vs R2C (n=51 paired items)": (
            "F1 eq-witness R1 vs R2C (n=51 paired items)"
        ),
    }
    by_comparison = {
        str(item["comparison"]): item
        for item in claude_payload.get("paired_condition_comparisons", [])
    }
    for source_label, display_label in claude_labels.items():
        item = by_comparison.get(source_label)
        if item is None:
            continue
        rows.append(
            {
                "model": "Claude Sonnet 4.5",
                "comparison": display_label,
                "cert_diff": item["cert_diff_first_minus_second"],
                "p_value": item["mcnemar_p_value"],
            }
        )

    gpt_payload = _load_json(repo_root / GPT_UNCERTAINTY_JSON)
    for item in gpt_payload.get("paired_track_comparisons", []):
        if item.get("metric") != "certificate_valid":
            continue
        comparison = str(item["comparison"])
        if comparison.startswith("F1 R1 vs R2"):
            label = "F1 R1 vs R2"
        elif comparison.startswith("C2 R1 vs R2"):
            label = "C2 R1 vs R2"
        else:
            continue
        rows.append(
            {
                "model": "GPT-4.1",
                "comparison": label,
                "cert_diff": item["diff_first_minus_second"],
                "p_value": item["mcnemar_p_value"],
            }
        )

    first = load_condition_outcomes(repo_root / GPT_F1_CONDITION_RUNS["R2"])
    second = load_condition_outcomes(repo_root / GPT_F1_CONDITION_RUNS["R2C"])
    shared = sorted(set(first) & set(second))
    first_cert = [first[item_id].certificate_valid for item_id in shared]
    second_cert = [second[item_id].certificate_valid for item_id in shared]
    first_only = sum(1 for a, b in zip(first_cert, second_cert) if a and not b)
    second_only = sum(1 for a, b in zip(first_cert, second_cert) if b and not a)
    rows.append(
        {
            "model": "GPT-4.1",
            "comparison": "F1 R2 vs R2C",
            "cert_diff": paired_bootstrap_difference_ci(first_cert, second_cert, seed=6201),
            "p_value": exact_mcnemar_p_value(first_only, second_only),
        }
    )
    return rows


def render_paired_mcnemar_latex(rows: list[dict[str, Any]]) -> str:
    lines = [
        "% Source: docs/tmlr_empirical_package_v1/uncertainty/bootstrap_mcnemar_summary.json",
        "%         docs/frontier_gpt_tools_n100_v1_uncertainty.json",
        "%         export_tosem_empirical_package (GPT F1 R2 vs R2C paired export)",
        "\\begin{table}[t]",
        "  \\centering",
        "  \\caption{Paired McNemar comparisons on identical item IDs (frozen exports).",
        "    Cert.\\ rate diff is first condition minus second; negative values indicate gains under the second condition.}",
        "  \\label{tab:results-paired-mcnemar}",
        "  \\scriptsize",
        "  \\setlength{\\tabcolsep}{2pt}",
        "  \\begin{tabularx}{\\columnwidth}{@{}llXr@{}}",
        "    \\toprule",
        "    Model & Comparison & Cert.\\ rate diff [95\\% CI] & $p$ \\\\",
        "    \\midrule",
    ]
    for row in rows:
        lines.append(
            "    "
            + " & ".join(
                [
                    row["model"],
                    row["comparison"],
                    _format_ci(row["cert_diff"]),
                    _format_p_value(row["p_value"]),
                ]
            )
            + " \\\\"
        )
    lines.extend(["    \\bottomrule", "  \\end{tabularx}", "\\end{table}", ""])
    return "\n".join(lines)


def _paper_tables_dir(repo_root: Path) -> Path:
    candidate = repo_root.parent / "paper" / "tables"
    if candidate.is_dir():
        return candidate
    return repo_root / "docs" / "paper_tables"


def export_tosem_empirical_package(
    repo_root: str | Path,
    *,
    paper_tables_dir: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root)
    tables_dir = Path(paper_tables_dir) if paper_tables_dir is not None else _paper_tables_dir(root)
    package_dir = root / PACKAGE_DIR
    package_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    gpt_payload = export_frontier_tools_n100_package(
        root,
        campaign_config_path=root / GPT_CAMPAIGN_CONFIG,
        json_out=root / "docs/frontier_gpt_tools_n100_v1_summary.json",
        latex_out=tables_dir / "gpt_tools_n100_summary.tex",
        markdown_out=root / "docs/frontier_gpt_tools_n100_v1_summary.md",
        subtype_json_out=root / "docs/f1_gpt_frontier_subtype_stratified_analysis.json",
        uncertainty_json_out=root / GPT_UNCERTAINTY_JSON,
        model_label="GPT-4.1",
        table_label="tab:frontier-gpt-tools-n100-v1-summary",
    )

    claude_summary = _load_json(root / FROZEN_COMBINED_SUMMARIES["claude_tools"])
    claude_rows = build_summary_table_rows(claude_summary)
    claude_latex = render_frontier_tools_latex_table(
        campaign_id="runs/frontier_claude_sonnet_tools_n100_v2",
        model_label="Claude Sonnet~4.5",
        rows=claude_rows,
        table_label="tab:claude-sonnet-tools-n100-summary",
        tracks_caption="tracks R1/R2 only",
    )
    claude_latex = claude_latex.replace(
        "Source: runs/frontier_claude_sonnet_tools_n100_v2.",
        "Zero provider/infrastructure failures across all four cells.",
    )
    (tables_dir / "claude_sonnet_tools_n100_summary.tex").write_text(claude_latex, encoding="utf-8")

    gpt_tool_rows = gpt_payload["summary_rows"]
    frontier_comparison = render_frontier_comparison_latex(claude_rows, gpt_tool_rows)
    (tables_dir / "frontier_tools_comparison_n100.tex").write_text(
        frontier_comparison, encoding="utf-8"
    )

    gap_rows = build_knowing_showing_gap_rows(root)
    (tables_dir / "knowing_showing_gap_n100.tex").write_text(
        render_knowing_showing_gap_latex(gap_rows), encoding="utf-8"
    )

    failure_rows = build_failure_stage_rows(root)
    (tables_dir / "failure_stage_n100.tex").write_text(
        render_failure_stage_latex(failure_rows), encoding="utf-8"
    )

    gpt_ablation_rows = build_f1_gpt_ablation_rows(root)
    gpt_ablation_json = {
        "provider": "openai",
        "model": "gpt-4.1",
        "conditions": GPT_F1_CONDITION_ORDER,
        "condition_runs": GPT_F1_CONDITION_RUNS,
        "rows": gpt_ablation_rows,
        "note": "Partial GPT attribution ladder: R1/R2 from frontier tools campaign; R2C from ablation export.",
    }
    (root / "docs/f1_gpt_ablation_stratified_analysis.json").write_text(
        json.dumps(gpt_ablation_json, indent=2) + "\n", encoding="utf-8"
    )
    (tables_dir / "f1_gpt_ablations.tex").write_text(
        render_f1_gpt_ablations_latex(gpt_ablation_rows), encoding="utf-8"
    )

    mcnemar_rows = build_paired_mcnemar_rows(root)
    (tables_dir / "results_paired_mcnemar.tex").write_text(
        render_paired_mcnemar_latex(mcnemar_rows), encoding="utf-8"
    )

    manifest = {
        "package_version": "tosem_v1",
        "generated_from": "frozen runs only (no inference)",
        "combined_summaries": FROZEN_COMBINED_SUMMARIES,
        "gpt_f1_condition_runs": GPT_F1_CONDITION_RUNS,
        "paper_tables": {
            "claude_sonnet_tools_n100_summary.tex": str(tables_dir / "claude_sonnet_tools_n100_summary.tex"),
            "gpt_tools_n100_summary.tex": str(tables_dir / "gpt_tools_n100_summary.tex"),
            "frontier_tools_comparison_n100.tex": str(tables_dir / "frontier_tools_comparison_n100.tex"),
            "knowing_showing_gap_n100.tex": str(tables_dir / "knowing_showing_gap_n100.tex"),
            "failure_stage_n100.tex": str(tables_dir / "failure_stage_n100.tex"),
            "f1_gpt_ablations.tex": str(tables_dir / "f1_gpt_ablations.tex"),
            "results_paired_mcnemar.tex": str(tables_dir / "results_paired_mcnemar.tex"),
        },
        "analysis_json": {
            "gpt_tools_summary": "docs/frontier_gpt_tools_n100_v1_summary.json",
            "gpt_uncertainty": GPT_UNCERTAINTY_JSON,
            "gpt_f1_ablation_stratified": "docs/f1_gpt_ablation_stratified_analysis.json",
            "gpt_f1_frontier_subtypes": "docs/f1_gpt_frontier_subtype_stratified_analysis.json",
        },
        "gpt_frontier_export": {
            "campaign_id": gpt_payload["campaign_id"],
            "cells_exported": gpt_payload["cells_exported"],
        },
    }
    (package_dir / "package_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest
