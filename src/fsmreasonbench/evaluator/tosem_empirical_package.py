"""TOSEM manuscript exports from frozen runs (provider-agnostic, no inference).

Visualization policy (manuscript):
- When a table and a figure repeat the same cell rates, keep the figure only; annotate bars or
  points with frozen rates (and k/n where applicable).
- Same experiment family across models uses the same visual typology and subtype column order
  (F1 ablations: Sep./Eq./All witness validity; C2 ablations: Trace/Unreach./All).
"""

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
from fsmreasonbench.evaluator.local_matrix_bootstrap_export import (
    export_local_matrix_bootstrap_package,
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

LOCAL_MATRIX_BOOTSTRAP_JSON = "docs/local_matrix_n100_t02_bootstrap_summary.json"
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
        "n": cell.get("n", 100),
        "extract": cell.get("extractability_rate"),
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


def _short_gap_model_label(model: str) -> str:
    if model == "Claude Sonnet":
        return "Claude"
    if model == "GPT-4.1":
        return "GPT-4.1"
    return model.split(":")[0]


def _f1_r1_gap_panel_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    order = ["Claude Sonnet", "GPT-4.1"]
    order.extend(
        sorted(
            {
                row["model"]
                for row in rows
                if row["model"] not in {"Claude Sonnet", "GPT-4.1"}
            }
        )
    )
    panel_rows: list[dict[str, Any]] = []
    for model in order:
        cell = _lookup_gap_cell(rows, model, "F1", "R1")
        if cell is not None:
            panel_rows.append(cell)
    return panel_rows


def render_knowing_showing_gap_latex(rows: list[dict[str, Any]]) -> str:
    from fsmreasonbench.evaluator.paper_table_style import (
        FROZEN_TOOL_TRACK_COLUMNS_WITH_GAP,
        frozen_n100_caption,
    )

    tabular_lines = [
        "    \\toprule",
        f"    {FROZEN_TOOL_TRACK_COLUMNS_WITH_GAP} \\\\",
        "    \\midrule",
    ]
    for group_title, group_rows in _group_gap_rows(rows):
        tabular_lines.append(f"    \\multicolumn{{9}}{{l}}{{\\textit{{{group_title}}}}} \\\\")
        for row in group_rows:
            model_display = row["model"]
            if model_display not in {"Claude Sonnet", "GPT-4.1"}:
                model_display = f"\\texttt{{{model_display}}}"
            tabular_lines.append(
                "    "
                + " & ".join(
                    [
                        model_display,
                        str(row["family"]),
                        str(row["track"]),
                        str(row.get("n", 100)),
                        _format_rate(row.get("extract")),
                        _format_rate(row["verdict"]),
                        _format_rate(row["cert"]),
                        _format_rate(row["full"]),
                        _format_rate(row["gap"]),
                    ]
                )
                + " \\\\"
            )
        tabular_lines.append("    \\midrule")
    if tabular_lines[-1].endswith("\\midrule"):
        tabular_lines[-1] = "    \\bottomrule"

    lines = [
        "% Verdict--witness gap: verdict accuracy minus full correctness rate (same cell).",
        "% Generated by export_tosem_empirical_package from frozen combined_summary.json files.",
        "% Verdict denominator = extractable items; Full denominator = n.",
        "\\begin{table*}[tbp]",
        "  \\centering",
        f"  \\caption{{{frozen_n100_caption('verdict--witness gap (Gap $=$ Verdict $-$ Full)')}}}",
        "  \\label{tab:knowing-showing-gap-n100}",
        "  \\setlength{\\tabcolsep}{2.5pt}",
        "  \\begin{tabular}{@{}llllrrrrr@{}}",
        *tabular_lines,
        "  \\end{tabular}",
        "\\end{table*}",
        "",
    ]
    return "\n".join(lines)


def render_failure_stage_latex(rows: list[dict[str, Any]]) -> str:
    lines = [
        "% Failure-stage decomposition (failure_stage_counts). Provider errors = 0 for all frozen cells.",
        "% Generated by export_tosem_empirical_package from frozen combined_summary.json files.",
        "\\begin{table*}[tbp]",
        "  \\centering",
        "  \\caption{Failure-stage counts ($n{=}100$ per cell). "
        "Stage definitions: Section~\\ref{subsec:failure-taxonomy}.}",
        "  \\label{tab:failure-stage-n100}",
        "  \\setlength{\\tabcolsep}{4pt}",
        "  \\begin{tabular*}{\\textwidth}{@{\\extracolsep{\\fill}} l l l r r r r @{}}",
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
    lines.extend(["    \\bottomrule", "  \\end{tabular*}", "\\end{table*}", ""])
    return "\n".join(lines)


def render_frontier_comparison_latex(
    claude_rows: list[dict[str, Any]],
    gpt_rows: list[dict[str, Any]],
) -> str:
    from fsmreasonbench.evaluator.paper_table_style import (
        FROZEN_TOOL_TRACK_COLUMNS,
        frozen_n100_caption,
    )

    lines = [
        "% Unified frontier tool-track comparison (Claude Sonnet 4.5 vs GPT-4.1).",
        "% Generated by export_tosem_empirical_package from frozen combined_summary.json files.",
        "\\begin{table}[t]",
        "  \\centering",
        f"  \\caption{{{frozen_n100_caption('frontier tool-track rates')}}}",
        "  \\label{tab:frontier-tools-comparison-n100}",
        "  \\setlength{\\tabcolsep}{3pt}",
        "  \\begin{tabular}{@{}llllrrrr@{}}",
        "    \\toprule",
        f"    {FROZEN_TOOL_TRACK_COLUMNS} \\\\",
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


F1_ABLATION_SUBTYPE_LABELS = ("Sep. witness", "Eq. witness", "All")
C2_ABLATION_SUBTYPE_LABELS = ("Trace witness", "Unreach. witness", "All")
F1_ABLATION_CERT_KEYS = (
    "distinguishing_trace_cert",
    "equivalence_witness_cert",
    "overall_cert",
)
C2_ABLATION_CERT_KEYS = (
    "trace_witness_cert",
    "unreachability_witness_cert",
    "overall_cert",
)
F1_CLAUDE_CONDITION_LABELS = ["R1", "Oracle+Fmt", "R2A", "R2B", "R2C"]
F1_GPT_CONDITION_LABELS = ["R1", "R2", "R2C"]
C2_CONDITION_LABELS = ["R1", "Oracle+Fmt", "R2A", "R2B", "R2C"]


def _render_ablation_figure_latex(
    *,
    comment_lines: list[str],
    caption: str,
    label: str,
    figure_name: str,
    description: str,
    width: str = "0.82\\linewidth",
) -> str:
    lines = [
        *comment_lines,
        "\\begin{figure}[tbp]",
        "  \\centering",
        f"  \\includegraphics[width={width}]{{figures/{figure_name}}}",
        f"  \\Description{{{description}}}",
        f"  \\caption{{{caption}}}",
        f"  \\label{{{label}}}",
        "\\end{figure}",
        "",
    ]
    return "\n".join(lines)


def _latex_table_with_side_panel(
    *,
    comment_lines: list[str],
    caption: str,
    label: str,
    tabular_body_lines: list[str],
    panel_figure: str,
    table_width: str = "0.52\\linewidth",
    panel_width: str = "0.43\\linewidth",
    panel_vspace: str = "1.15\\baselineskip",
    panel_layout: str = "side",
    panel_below_width: str = "0.68\\linewidth",
) -> str:
    caption_block = [
        f"  \\caption{{{caption}}}",
        f"  \\label{{{label}}}",
        "  \\par\\vspace{0.45\\baselineskip}",
    ]
    tabular_block = [
        "    \\setlength{\\tabcolsep}{2.5pt}",
        "    \\resizebox{\\linewidth}{!}{%",
        "    \\begin{tabular}{@{}lccc@{}}",
        *tabular_body_lines,
        "    \\end{tabular}",
        "    }",
    ]
    if panel_layout == "below":
        lines = [
            *comment_lines,
            "\\begin{table}[tbp]",
            "  \\centering",
            *caption_block,
            "  \\footnotesize",
            *tabular_block,
            "  \\par\\vspace{0.55em}",
            f"  \\includegraphics[width={panel_below_width}]{{figures/{panel_figure}}}",
            "\\end{table}",
            "",
        ]
        return "\n".join(lines)

    lines = [
        *comment_lines,
        "\\begin{table}[tbp]",
        "  \\centering",
        *caption_block,
        f"  \\begin{{minipage}}[t]{{{table_width}}}",
        "    \\vspace{0pt}",
        "    \\centering",
        "    \\footnotesize",
        *tabular_block,
        "  \\end{minipage}\\hspace{0.025\\linewidth}",
        f"  \\begin{{minipage}}[t]{{{panel_width}}}",
        "    \\vspace{0pt}",
        f"    \\vspace{{{panel_vspace}}}",
        "    \\centering",
        f"    \\includegraphics[width=\\linewidth]{{figures/{panel_figure}}}",
        "  \\end{minipage}",
        "\\end{table}",
        "",
    ]
    return "\n".join(lines)


def write_figure_ablation_table_panel(
    *,
    short_condition_labels: list[str],
    subtype_labels: list[str],
    cert_rates: list[list[float]],
    title: str | None = None,
    ylabel: str = "Witness validity",
    output_path: Path,
) -> Path | None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    from fsmreasonbench.evaluator.paper_figure_style import (
        configure_paper_figure_style,
        plot_ablation_subtype_panel,
    )

    configure_paper_figure_style()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    n_conditions = len(short_condition_labels)
    fig_width = 4.35 if n_conditions <= 3 else 5.05
    fig_height = 3.05 if n_conditions <= 3 else 3.35
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    plot_ablation_subtype_panel(
        ax,
        condition_labels=short_condition_labels,
        subtype_labels=subtype_labels,
        cert_rates=cert_rates,
        title=title,
        ylabel=ylabel,
        show_legend=True,
        bar_width=0.22 if n_conditions <= 3 else 0.17,
        annotate_rates=True,
    )
    bottom = 0.34 if n_conditions <= 3 else 0.38
    fig.subplots_adjust(top=0.96, bottom=bottom, left=0.16, right=0.98)
    fig.savefig(output_path, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    return output_path


def render_f1_claude_ablations_latex(
    rows: list[dict[str, Any]],
    *,
    include_panel: bool = True,
) -> str:
    del rows
    if not include_panel:
        return ""
    caption = (
        "F1 \\claude{} witness validity by condition and gold subtype ($n{=}100$)."
    )
    return _render_ablation_figure_latex(
        comment_lines=[
            "% Generated by export_tosem_empirical_package from frozen Claude F1 ablation runs.",
        ],
        caption=caption,
        label="fig:f1-claude-ablations",
        figure_name="figure_f1_claude_ablations_panel.pdf",
        description=(
            "Grouped bar chart of F1 Claude ablation witness-validity rates by condition "
            "and gold subtype (separation, equivalence, all)."
        ),
    )


def render_f1_gpt_ablations_latex(
    rows: list[dict[str, Any]],
    *,
    include_panel: bool = True,
) -> str:
    del rows
    if not include_panel:
        return ""
    caption = (
        "F1 \\gpt{} witness validity by condition and gold subtype ($n{=}100$; R1/R2/R2C)."
    )
    return _render_ablation_figure_latex(
        comment_lines=[
            "% Generated by export_tosem_empirical_package from frozen GPT F1 scores.jsonl files.",
        ],
        caption=caption,
        label="fig:f1-gpt-ablations",
        figure_name="figure_f1_gpt_ablations_panel.pdf",
        description=(
            "Grouped bar chart of F1 GPT-4.1 ablation witness-validity rates by condition "
            "and gold subtype (separation, equivalence, all)."
        ),
    )


def render_c2_claude_ablations_latex(
    rows: list[dict[str, Any]],
    *,
    include_panel: bool = True,
) -> str:
    del rows
    if not include_panel:
        return ""
    caption = (
        "C2 \\claude{} witness validity by condition and gold subtype ($n{=}100$)."
    )
    return _render_ablation_figure_latex(
        comment_lines=[
            "% Generated by export_tosem_empirical_package from frozen C2 ablation runs.",
        ],
        caption=caption,
        label="fig:c2-claude-ablations",
        figure_name="figure_c2_claude_ablations_panel.pdf",
        description=(
            "Grouped bar chart of C2 Claude ablation witness-validity rates by condition "
            "and gold subtype (trace, unreachability, all)."
        ),
        width="0.88\\linewidth",
    )


def _ablation_panel_cert_rates(
    rows: list[dict[str, Any]], keys: tuple[str, str, str]
) -> list[list[float]]:
    return [[float(row[key]) for key in keys] for row in rows]


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
        "  \\caption{Paired McNemar contrasts on identical item IDs.}",
        "  \\label{tab:results-paired-mcnemar}",
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


HEADLINE_GAP_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("C2", "R1"),
    ("C2", "R2"),
    ("F1", "R1"),
    ("F1", "R2"),
)
GPT_GAP_EXTRA_CATEGORIES: tuple[tuple[str, str], ...] = (("F1", "R2C"),)

CLAUDE_ATTRIBUTION_CONDITIONS: tuple[str, ...] = (
    "R1",
    "Oracle+Format",
    "R2A",
    "R2B",
    "R2C",
)
CLAUDE_ATTRIBUTION_LABELS: dict[str, str] = {
    "R1": "R1",
    "Oracle+Format": "Oracle",
    "R2A": "R2A",
    "R2B": "R2B",
    "R2C": "R2C",
}


def _lookup_gap_cell(
    rows: list[dict[str, Any]],
    model: str,
    family: str,
    track: str,
) -> dict[str, Any] | None:
    for row in rows:
        if row["model"] == model and row["family"] == family and row["track"] == track:
            return row
    return None


def _category_labels(categories: Iterable[tuple[str, str]]) -> list[str]:
    return [f"{family}/{track}" for family, track in categories]


def _panel_rates(
    rows: list[dict[str, Any]],
    model: str,
    categories: Iterable[tuple[str, str]],
) -> tuple[list[float | None], list[float | None]]:
    verdict_rates: list[float | None] = []
    full_rates: list[float | None] = []
    for family, track in categories:
        cell = _lookup_gap_cell(rows, model, family, track)
        if cell is None:
            verdict_rates.append(None)
            full_rates.append(None)
        else:
            verdict_rates.append(cell["verdict"])
            full_rates.append(cell["full"])
    return verdict_rates, full_rates


def write_figure_knowing_showing_gap_table_panel(
    gap_rows: list[dict[str, Any]],
    figures_dir: Path,
) -> Path | None:
    """Compact F1/R1 inset for Table~\\ref{tab:knowing-showing-gap-n100}."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    from fsmreasonbench.evaluator.paper_figure_style import (
        VERDICT_BAR_COLOR,
        configure_paper_figure_style,
        plot_verdict_full_by_models,
        style_axes,
    )

    panel_rows = _f1_r1_gap_panel_rows(gap_rows)
    if not panel_rows:
        return None

    configure_paper_figure_style()
    figures_dir.mkdir(parents=True, exist_ok=True)

    labels = [_short_gap_model_label(row["model"]) for row in panel_rows]
    verdict_rates = [float(row["verdict"]) for row in panel_rows]
    full_rates = [float(row["full"]) for row in panel_rows]
    gaps = [float(row["gap"]) for row in panel_rows]

    fig, axes = plt.subplots(
        2,
        1,
        figsize=(4.4, 5.85),
        sharex=False,
        gridspec_kw={"height_ratios": [1.45, 1.0]},
    )
    plot_verdict_full_by_models(
        axes[0],
        model_labels=labels,
        verdict_rates=verdict_rates,
        full_rates=full_rates,
        title=None,
        show_legend=True,
    )

    gap_order = sorted(range(len(gaps)), key=lambda index: gaps[index], reverse=True)
    gap_labels = [labels[index] for index in gap_order]
    gap_values = [gaps[index] for index in gap_order]
    axes[1].barh(
        gap_labels,
        gap_values,
        color=VERDICT_BAR_COLOR,
        edgecolor="0.0",
        linewidth=0.6,
        height=0.62,
    )
    axes[1].set_xlim(0.0, 1.05)
    axes[1].set_xlabel("Gap (Verdict $-$ Full)")
    style_axes(axes[1])

    fig.subplots_adjust(top=0.96, bottom=0.11, left=0.16, right=0.99, hspace=0.38)
    out_path = figures_dir / "figure_knowing_showing_gap_table_panel.pdf"
    fig.savefig(out_path, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)
    return out_path


def write_figure_verdict_witness_gap_comparison(
    gap_rows: list[dict[str, Any]],
    figures_dir: Path,
) -> Path | None:
    """Three-panel verdict vs full comparison: Claude, GPT-4.1, local open-weight."""
    try:
        import matplotlib.pyplot as plt
        from matplotlib.gridspec import GridSpec
    except ImportError:
        return None

    from fsmreasonbench.evaluator.paper_figure_style import (
        configure_paper_figure_style,
        plot_verdict_full_pairs,
    )

    configure_paper_figure_style()
    figures_dir.mkdir(parents=True, exist_ok=True)

    local_models = sorted(
        {row["model"] for row in gap_rows if row["model"] not in {"Claude Sonnet", "GPT-4.1"}}
    )
    headline = list(HEADLINE_GAP_CATEGORIES)
    gpt_categories = headline + list(GPT_GAP_EXTRA_CATEGORIES)

    fig = plt.figure(figsize=(11.2, 4.4))
    gs = GridSpec(1, 3, figure=fig, width_ratios=[1.0, 1.05, 1.25], wspace=0.38)

    ax_claude = fig.add_subplot(gs[0, 0])
    verdict, full = _panel_rates(gap_rows, "Claude Sonnet", headline)
    plot_verdict_full_pairs(
        ax_claude,
        categories=headline,
        verdict_rates=verdict,
        full_rates=full,
        category_labels=_category_labels(headline),
        title="Claude Sonnet 4.5",
    )

    ax_gpt = fig.add_subplot(gs[0, 1])
    verdict, full = _panel_rates(gap_rows, "GPT-4.1", gpt_categories)
    plot_verdict_full_pairs(
        ax_gpt,
        categories=gpt_categories,
        verdict_rates=verdict,
        full_rates=full,
        category_labels=_category_labels(gpt_categories),
        title="GPT-4.1",
    )

    inner = gs[0, 2].subgridspec(2, 2, hspace=0.55, wspace=0.35)
    for index, model in enumerate(local_models[:4]):
        ax = fig.add_subplot(inner[index // 2, index % 2])
        verdict, full = _panel_rates(gap_rows, model, headline)
        short_label = model.split(":")[0].replace("mistral-nemo", "mistral")
        plot_verdict_full_pairs(
            ax,
            categories=headline,
            verdict_rates=verdict,
            full_rates=full,
            category_labels=_category_labels(headline),
            title=short_label,
        )

    handles, labels = ax_claude.get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="lower center",
        ncol=2,
        frameon=False,
        bbox_to_anchor=(0.5, -0.02),
    )
    fig.subplots_adjust(bottom=0.22, top=0.92)
    out_path = figures_dir / "figure_verdict_witness_gap_comparison.pdf"
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return out_path


def write_figure_attribution_fingerprint_comparison(
    repo_root: Path,
    gpt_rows: list[dict[str, Any]],
    figures_dir: Path,
) -> Path | None:
    """Two-panel fingerprint witness validity across attribution conditions."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    from fsmreasonbench.evaluator.paper_figure_style import (
        STAGE_BAR_COLORS,
        configure_paper_figure_style,
        style_axes,
    )

    claude_json = repo_root / "docs/f1_claude_ablation_stratified_analysis.json"
    if not claude_json.is_file():
        return None
    claude_payload = _load_json(claude_json)
    claude_summary = claude_payload.get("stratified_subtype_summary") or {}

    configure_paper_figure_style()
    figures_dir.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(10.2, 3.8), sharey=True)

    claude_labels: list[str] = []
    claude_rates: list[float] = []
    for condition in CLAUDE_ATTRIBUTION_CONDITIONS:
        block = claude_summary.get(condition) or {}
        eq = block.get("equivalence_witness") or {}
        if "cert" not in eq:
            continue
        claude_labels.append(CLAUDE_ATTRIBUTION_LABELS.get(condition, condition))
        claude_rates.append(float(eq["cert"]))

    axes[0].bar(
        claude_labels,
        claude_rates,
        color=STAGE_BAR_COLORS[0],
        edgecolor="0.0",
        linewidth=0.6,
    )
    axes[0].set_title("Claude Sonnet 4.5")
    axes[0].set_ylabel("Fingerprint witness validity ($n{=}51$)")
    axes[0].set_ylim(0.0, 1.05)
    axes[0].tick_params(axis="x", rotation=25)
    style_axes(axes[0])

    gpt_labels = ["R1", "R2", "R2C"]
    gpt_rates = [
        float(next(row for row in gpt_rows if row["condition"] == condition)["equivalence_witness_cert"])
        for condition in GPT_F1_CONDITION_ORDER
    ]
    axes[1].bar(
        gpt_labels,
        gpt_rates,
        color=STAGE_BAR_COLORS[2],
        edgecolor="0.0",
        linewidth=0.6,
    )
    axes[1].set_title("GPT-4.1")
    axes[1].tick_params(axis="x", rotation=0)
    style_axes(axes[1])

    fig.tight_layout()
    out_path = figures_dir / "figure_attribution_fingerprint_comparison.pdf"
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return out_path


def _paper_tables_dir(repo_root: Path) -> Path:
    candidate = repo_root.parent / "paper" / "tables"
    if candidate.is_dir():
        return candidate
    return repo_root / "docs" / "paper_tables"


def _repo_rel(path: Path, repo_root: Path) -> str:
    """Path relative to repository root for portable manifests."""
    resolved = path.resolve()
    root = repo_root.resolve()
    try:
        return str(resolved.relative_to(root))
    except ValueError:
        paper_root = (root.parent / "paper").resolve()
        try:
            return str(Path("..") / "paper" / resolved.relative_to(paper_root))
        except ValueError:
            return str(path)


def export_tosem_empirical_package(
    repo_root: str | Path,
    *,
    paper_tables_dir: str | Path | None = None,
    paper_figures_dir: str | Path | None = None,
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

    from fsmreasonbench.evaluator.tmlr_empirical_package import build_table2, build_table3

    claude_ablation_rows = build_table2(root)
    (tables_dir / "f1_claude_ablations.tex").write_text(
        render_f1_claude_ablations_latex(claude_ablation_rows), encoding="utf-8"
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

    c2_ablation_rows = build_table3(root)
    (tables_dir / "c2_claude_ablations.tex").write_text(
        render_c2_claude_ablations_latex(c2_ablation_rows), encoding="utf-8"
    )

    mcnemar_rows = build_paired_mcnemar_rows(root)
    (tables_dir / "results_paired_mcnemar.tex").write_text(
        render_paired_mcnemar_latex(mcnemar_rows), encoding="utf-8"
    )

    local_bootstrap = export_local_matrix_bootstrap_package(
        root,
        json_out=root / LOCAL_MATRIX_BOOTSTRAP_JSON,
        latex_out=tables_dir / "local_matrix_n100_summary.tex",
    )

    figures_dir = (
        Path(paper_figures_dir)
        if paper_figures_dir is not None
        else root.parent / "paper" / "figures"
    )
    paper_figures: dict[str, str] = {}
    gap_figure = write_figure_verdict_witness_gap_comparison(gap_rows, figures_dir)
    if gap_figure is not None:
        paper_figures["figure_verdict_witness_gap_comparison.pdf"] = _repo_rel(gap_figure, root)
    claude_ablation_panel = write_figure_ablation_table_panel(
        short_condition_labels=F1_CLAUDE_CONDITION_LABELS,
        subtype_labels=list(F1_ABLATION_SUBTYPE_LABELS),
        cert_rates=_ablation_panel_cert_rates(claude_ablation_rows, F1_ABLATION_CERT_KEYS),
        output_path=figures_dir / "figure_f1_claude_ablations_panel.pdf",
    )
    if claude_ablation_panel is not None:
        paper_figures["figure_f1_claude_ablations_panel.pdf"] = _repo_rel(
            claude_ablation_panel, root
        )
    gpt_ablation_panel = write_figure_ablation_table_panel(
        short_condition_labels=F1_GPT_CONDITION_LABELS,
        subtype_labels=list(F1_ABLATION_SUBTYPE_LABELS),
        cert_rates=_ablation_panel_cert_rates(gpt_ablation_rows, F1_ABLATION_CERT_KEYS),
        output_path=figures_dir / "figure_f1_gpt_ablations_panel.pdf",
    )
    if gpt_ablation_panel is not None:
        paper_figures["figure_f1_gpt_ablations_panel.pdf"] = _repo_rel(gpt_ablation_panel, root)
    c2_ablation_panel = write_figure_ablation_table_panel(
        short_condition_labels=C2_CONDITION_LABELS,
        subtype_labels=list(C2_ABLATION_SUBTYPE_LABELS),
        cert_rates=_ablation_panel_cert_rates(c2_ablation_rows, C2_ABLATION_CERT_KEYS),
        output_path=figures_dir / "figure_c2_claude_ablations_panel.pdf",
    )
    if c2_ablation_panel is not None:
        paper_figures["figure_c2_claude_ablations_panel.pdf"] = _repo_rel(
            c2_ablation_panel, root
        )

    manifest = {
        "package_version": "tosem_v1",
        "generated_from": "frozen runs only (no inference)",
        "combined_summaries": FROZEN_COMBINED_SUMMARIES,
        "gpt_f1_condition_runs": GPT_F1_CONDITION_RUNS,
        "paper_tables": {
            name: _repo_rel(tables_dir / name, root)
            for name in (
                "claude_sonnet_tools_n100_summary.tex",
                "gpt_tools_n100_summary.tex",
                "frontier_tools_comparison_n100.tex",
                "knowing_showing_gap_n100.tex",
                "failure_stage_n100.tex",
                "f1_claude_ablations.tex",
                "f1_gpt_ablations.tex",
                "c2_claude_ablations.tex",
                "results_paired_mcnemar.tex",
                "local_matrix_n100_summary.tex",
            )
        },
        "analysis_json": {
            "gpt_tools_summary": "docs/frontier_gpt_tools_n100_v1_summary.json",
            "gpt_uncertainty": GPT_UNCERTAINTY_JSON,
            "gpt_f1_ablation_stratified": "docs/f1_gpt_ablation_stratified_analysis.json",
            "gpt_f1_frontier_subtypes": "docs/f1_gpt_frontier_subtype_stratified_analysis.json",
            "local_matrix_bootstrap": LOCAL_MATRIX_BOOTSTRAP_JSON,
        },
        "local_matrix_export": {
            "cells_exported": len(local_bootstrap["cells"]),
        },
        "gpt_frontier_export": {
            "campaign_id": gpt_payload["campaign_id"],
            "cells_exported": gpt_payload["cells_exported"],
        },
        "paper_figures": paper_figures,
    }
    (package_dir / "package_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest
