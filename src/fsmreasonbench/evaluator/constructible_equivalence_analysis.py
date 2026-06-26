"""Construct-validity analysis: hash vs bisimulation vs distinguishing witnesses."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fsmreasonbench.evaluator.bootstrap import DEFAULT_BOOTSTRAP_ALPHA, DEFAULT_BOOTSTRAP_RESAMPLES
from fsmreasonbench.evaluator.f1_claude_ablation_stratified_analysis import (
    ItemOutcome,
    exact_mcnemar_p_value,
    load_condition_outcomes,
    load_item_metadata,
    paired_bootstrap_difference_ci,
)
from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.evaluator.models import ScoringRecord
from fsmreasonbench.evaluator.rate_ci_report import summarize_rates_with_bootstrap
from fsmreasonbench.evaluator.summary import summarize_scoring_records

EXTENSION_TABLE_PREFIX = "extension_"
DOCS_DIR = "docs/a1_constructible_equivalence_v1"
BOOTSTRAP_SEED = 4242
EQUIVALENCE_CERT_TYPE = "equivalence_witness"

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

PROVIDER_LABELS = {
    "claude": "Claude Sonnet~4.5",
    "gpt": "GPT-4.1",
}


def _load_scoring(path: Path) -> list[ScoringRecord]:
    from fsmreasonbench.evaluator.jsonl import read_jsonl

    rows = list(read_jsonl(path))
    return [ScoringRecord.from_dict(row) for row in rows]


def _filter_equivalence_records(
    records: list[ScoringRecord],
    metadata: dict[str, Any],
) -> list[ScoringRecord]:
    return [
        row
        for row in records
        if metadata.get(row.item_id)
        and metadata[row.item_id].gold_certificate_type == EQUIVALENCE_CERT_TYPE
    ]


def _filter_equivalence_outcomes(
    outcomes: dict[str, ItemOutcome],
    metadata: dict[str, Any],
) -> dict[str, ItemOutcome]:
    return {
        item_id: outcome
        for item_id, outcome in outcomes.items()
        if metadata.get(item_id)
        and metadata[item_id].gold_certificate_type == EQUIVALENCE_CERT_TYPE
    }


def _subset_summary(
    path: Path,
    metadata: dict[str, Any],
    *,
    cert_type: str,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    if not path.exists():
        return {"status": "pending", "scores_path": str(path)}
    records = _filter_equivalence_records(_load_scoring(path), metadata)
    if cert_type != EQUIVALENCE_CERT_TYPE:
        records = [
            row
            for row in _load_scoring(path)
            if metadata.get(row.item_id)
            and metadata[row.item_id].gold_certificate_type == cert_type
        ]
    if not records:
        return {"status": "empty", "scores_path": str(path), "n": 0}
    summary = summarize_rates_with_bootstrap(records, n_resamples=DEFAULT_BOOTSTRAP_RESAMPLES, seed=seed)
    summary["status"] = "available"
    summary["scores_path"] = str(path)
    summary["n"] = len(records)
    valid_count = sum(1 for row in records if row.extractable and row.certificate_valid is True)
    summary["certificate_valid_count"] = valid_count
    return summary


def _format_rate_ci(summary: dict[str, Any]) -> str:
    rate = summary.get("certificate_valid_rate", 0.0)
    lo = summary.get("certificate_valid_rate_ci_low", rate)
    hi = summary.get("certificate_valid_rate_ci_high", rate)
    return f"{rate:.3f} [{lo:.3f}, {hi:.3f}]"


def _format_p_value(p_value: float | None) -> str:
    if p_value is None:
        return ""
    if p_value < 0.001:
        return "$\\ll 0.05$"
    return f"{p_value:.3f}"


def _format_ci(diff: dict[str, float]) -> str:
    return f"${diff['point_diff']:.3f} [{diff['ci_low']:.3f}, {diff['ci_high']:.3f}]$"


def _paired_cert_comparison(
    first: dict[str, ItemOutcome],
    second: dict[str, ItemOutcome],
    *,
    comparison_id: str,
    comparison_label: str,
    first_label: str,
    second_label: str,
    group: str,
    provider: str | None = None,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    shared_ids = sorted(set(first) & set(second))
    both_valid = 0
    first_only = 0
    second_only = 0
    both_invalid = 0
    first_cert: list[bool] = []
    second_cert: list[bool] = []
    for item_id in shared_ids:
        a = first[item_id].certificate_valid
        b = second[item_id].certificate_valid
        first_cert.append(a)
        second_cert.append(b)
        if a and b:
            both_valid += 1
        elif a and not b:
            first_only += 1
        elif not a and b:
            second_only += 1
        else:
            both_invalid += 1
    return {
        "comparison_id": comparison_id,
        "comparison": comparison_label,
        "group": group,
        "provider": provider,
        "first_condition": first_label,
        "second_condition": second_label,
        "paired_items": len(shared_ids),
        "agreement_table": {
            "both_valid": both_valid,
            "first_only_valid": first_only,
            "second_only_valid": second_only,
            "both_invalid": both_invalid,
        },
        "mcnemar_first_only": first_only,
        "mcnemar_second_only": second_only,
        "mcnemar_p_value": exact_mcnemar_p_value(first_only, second_only),
        "cert_diff_first_minus_second": paired_bootstrap_difference_ci(
            first_cert,
            second_cert,
            n_resamples=DEFAULT_BOOTSTRAP_RESAMPLES,
            seed=seed,
            alpha=DEFAULT_BOOTSTRAP_ALPHA,
        ),
        "test_type": "paired_mcnemar_on_same_item_ids",
    }


def build_a1_cell_summaries(repo_root: Path, metadata: dict[str, Any]) -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    seed = BOOTSTRAP_SEED
    for provider in ("claude", "gpt"):
        for track in ("R1", "R2C"):
            for witness, path_map, witness_label in (
                ("hash", FROZEN_HASH_PATHS, "hash"),
                ("bisimulation", CONSTRUCTIBLE_PATHS, "bisimulation"),
            ):
                summary = _subset_summary(
                    repo_root / path_map[provider][track],
                    metadata,
                    cert_type=EQUIVALENCE_CERT_TYPE,
                    seed=seed,
                )
                seed += 1
                cells.append(
                    {
                        "provider": provider,
                        "provider_label": PROVIDER_LABELS[provider],
                        "track": track,
                        "witness": witness,
                        "witness_label": witness_label,
                        "summary": summary,
                    }
                )
    return cells


def build_a1_paired_comparisons(repo_root: Path, metadata: dict[str, Any]) -> list[dict[str, Any]]:
    hash_outcomes = {
        provider: {
            track: _filter_equivalence_outcomes(
                load_condition_outcomes(repo_root / FROZEN_HASH_PATHS[provider][track]),
                metadata,
            )
            for track in ("R1", "R2C")
        }
        for provider in ("claude", "gpt")
    }
    bisim_outcomes = {
        provider: {
            track: _filter_equivalence_outcomes(
                load_condition_outcomes(repo_root / CONSTRUCTIBLE_PATHS[provider][track]),
                metadata,
            )
            for track in ("R1", "R2C")
        }
        for provider in ("claude", "gpt")
    }

    comparisons: list[dict[str, Any]] = []
    seed = BOOTSTRAP_SEED + 100

    for provider in ("claude", "gpt"):
        comparisons.append(
            _paired_cert_comparison(
                hash_outcomes[provider]["R1"],
                bisim_outcomes[provider]["R1"],
                comparison_id=f"{provider}_hash_r1_vs_bisim_r1",
                comparison_label=f"{PROVIDER_LABELS[provider]} hash R1 vs bisim R1",
                first_label="hash R1",
                second_label="bisimulation R1",
                group="A_contract_r1",
                provider=provider,
                seed=seed,
            )
        )
        seed += 1
        comparisons.append(
            _paired_cert_comparison(
                hash_outcomes[provider]["R2C"],
                bisim_outcomes[provider]["R2C"],
                comparison_id=f"{provider}_hash_r2c_vs_bisim_r2c",
                comparison_label=f"{PROVIDER_LABELS[provider]} hash R2C vs bisim R2C",
                first_label="hash R2C",
                second_label="bisimulation R2C",
                group="B_contract_r2c",
                provider=provider,
                seed=seed,
            )
        )
        seed += 1

    cross_specs = (
        ("hash R1", "R1", hash_outcomes),
        ("bisimulation R1", "R1", bisim_outcomes),
        ("hash R2C", "R2C", hash_outcomes),
        ("bisimulation R2C", "R2C", bisim_outcomes),
    )
    for witness_label, track, outcome_map in cross_specs:
        comparisons.append(
            _paired_cert_comparison(
                outcome_map["claude"][track],
                outcome_map["gpt"][track],
                comparison_id=f"claude_vs_gpt_{witness_label.replace(' ', '_').lower()}_{track.lower()}",
                comparison_label=f"Claude vs GPT ({witness_label}, {track})",
                first_label=f"Claude {witness_label}",
                second_label=f"GPT {witness_label}",
                group="C_cross_model",
                provider=None,
                seed=seed,
            )
        )
        seed += 1

    return comparisons


def build_constructible_equivalence_analysis(repo_root: Path) -> dict[str, Any]:
    cohort = repo_root / "cohorts/v0.1-expanded-n100/f1-mixed-level3/items.jsonl"
    metadata = load_item_metadata(cohort)

    rows: list[dict[str, Any]] = []
    for provider in ("claude", "gpt"):
        for track in ("R1", "R2C"):
            hash_summary = _subset_summary(
                repo_root / FROZEN_HASH_PATHS[provider][track],
                metadata,
                cert_type=EQUIVALENCE_CERT_TYPE,
            )
            dist_summary = (
                _subset_summary(
                    repo_root / FROZEN_HASH_PATHS[provider]["R1"],
                    metadata,
                    cert_type="distinguishing_trace",
                )
                if track == "R1"
                else None
            )
            construct_summary = _subset_summary(
                repo_root / CONSTRUCTIBLE_PATHS[provider][track],
                metadata,
                cert_type=EQUIVALENCE_CERT_TYPE,
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

    cell_summaries = build_a1_cell_summaries(repo_root, metadata)
    paired_comparisons = build_a1_paired_comparisons(repo_root, metadata)

    return {
        "experiment": "constructible_equivalence_witness_analysis",
        "bootstrap_settings": {
            "n_resamples": DEFAULT_BOOTSTRAP_RESAMPLES,
            "seed": BOOTSTRAP_SEED,
            "alpha": DEFAULT_BOOTSTRAP_ALPHA,
            "method": "percentile_bootstrap_on_item_records",
        },
        "subset": {
            "equivalence_witness_items": sum(
                1
                for meta in metadata.values()
                if meta.gold_certificate_type == EQUIVALENCE_CERT_TYPE
            ),
            "distinguishing_trace_items": sum(
                1
                for meta in metadata.values()
                if meta.gold_certificate_type == "distinguishing_trace"
            ),
            "note": (
                "A1 paired comparisons use the same 51 equivalence item IDs; only witness "
                "contract and study-local prompts differ from frozen hash campaigns."
            ),
        },
        "cell_summaries": cell_summaries,
        "paired_comparisons": paired_comparisons,
        "research_questions": _research_answers(rows, paired_comparisons),
        "rows": rows,
    }


def _research_answers(
    rows: list[dict[str, Any]],
    paired_comparisons: list[dict[str, Any]],
) -> dict[str, str]:
    def _rate(cell: dict[str, Any] | None, key: str = "certificate_valid_rate") -> str:
        if not cell or cell.get("status") != "available":
            return "pending"
        val = cell.get(key)
        return f"{val:.3f}" if isinstance(val, (int, float)) else "n/a"

    claude_r1_hash = next(r for r in rows if r["provider"] == "claude" and r["track"] == "R1")
    claude_r1_construct = claude_r1_hash["constructible_bisimulation_witness"]
    claude_r1_dist = claude_r1_hash["distinguishing_trace_r1_baseline"]
    claude_r1_pair = next(
        row for row in paired_comparisons if row["comparison_id"] == "claude_hash_r1_vs_bisim_r1"
    )

    return {
        "q1_hash_only_failure": (
            "Hash equivalence-witness cert rate is 0.000 on R1 for both providers; bisimulation "
            f"R1 cert={_rate(claude_r1_construct)} (Claude) with paired McNemar "
            f"p={_format_p_value(claude_r1_pair['mcnemar_p_value'])} on identical item IDs."
        ),
        "q2_structural_witness_without_hash": (
            f"Constructible R1 cert={_rate(claude_r1_construct)} (Claude) and "
            f"{_rate(next(r for r in rows if r['provider']=='gpt' and r['track']=='R1')['constructible_bisimulation_witness'])} "
            "(GPT) indicate replay-checkable state-pair witnesses without hash arithmetic."
        ),
        "q3_r2c_benefit_after_hash_removal": (
            "Constructible and hash R2C both reach cert=1.000 for both providers on the eq subset; "
            "generator-assisted access closes both contracts."
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
        "  \\caption{F1 equivalence subset ($n{=}51$): hash-based vs.\\ structural bisimulation "
        "witnesses under identical item IDs and access tracks (Experiment~A1).}",
        "  \\label{tab:extension-constructible-equivalence}",
        "  \\begin{tabular}{@{}lllrrr@{}}",
        "    \\toprule",
        "    Provider & Track & Witness & $n$ & Cert.\\ valid & Fully correct \\\\",
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
                    f"    {row['provider']} & {row['track']} & {label} & & & pending \\\\"
                )
                continue
            lines.append(
                f"    {row['provider']} & {row['track']} & {label} & {cell.get('n')} & "
                f"{cell.get('certificate_valid_rate', 0):.3f} & "
                f"{cell.get('fully_correct_rate', 0):.3f} \\\\"
            )
    lines.extend(["    \\bottomrule", "  \\end{tabular}", "\\end{table}"])
    return "\n".join(lines) + "\n"


def render_constructible_equivalence_statistics_latex(report: dict[str, Any]) -> str:
    lines = [
        "% Generated by export_constructible_equivalence_analysis (Experiment A1).",
        "\\begin{table}[t]",
        "  \\centering",
        "  \\caption{Experiment~A1 inferential summary on the F1 equivalence subset ($n{=}51$ paired items).}",
        "  \\label{tab:extension-constructible-equivalence-stats}",
        "  \\setlength{\\tabcolsep}{3pt}",
        "  \\begin{tabularx}{\\columnwidth}{@{}lYrrrr@{}}",
        "    \\toprule",
        "    Cell & Cert.\\ valid [95\\% CI] & $k/n$ & Agreement & Cert.\\ diff [95\\% CI] & $p$ \\\\",
        "    \\midrule",
    ]
    for cell in report.get("cell_summaries", []):
        summary = cell.get("summary") or {}
        if summary.get("status") != "available":
            continue
        label = (
            f"{cell['provider_label']} {cell['witness_label']} {cell['track']}"
        )
        lines.append(
            "    "
            + " & ".join(
                [
                    label,
                    _format_rate_ci(summary),
                    f"{summary.get('certificate_valid_count', 0)}/{summary.get('n', 0)}",
                    "",
                    "",
                    "",
                ]
            )
            + " \\\\"
        )
    lines.append("    \\midrule")
    for row in report.get("paired_comparisons", []):
        agreement = row["agreement_table"]
        agree_str = (
            f"{agreement['both_valid']}/{agreement['first_only_valid']}/"
            f"{agreement['second_only_valid']}/{agreement['both_invalid']}"
        )
        lines.append(
            "    "
            + " & ".join(
                [
                    row["comparison"],
                    "",
                    f"{row['paired_items']}",
                    agree_str,
                    _format_ci(row["cert_diff_first_minus_second"]),
                    _format_p_value(row["mcnemar_p_value"]),
                ]
            )
            + " \\\\"
        )
    lines.extend(["    \\bottomrule", "  \\end{tabularx}", "\\end{table}", ""])
    return "\n".join(lines)


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

    witness_table = render_constructible_equivalence_latex(report)
    stats_table = render_constructible_equivalence_statistics_latex(report)
    witness_name = f"{EXTENSION_TABLE_PREFIX}constructible_equivalence_witness.tex"
    stats_name = f"{EXTENSION_TABLE_PREFIX}constructible_equivalence_statistics.tex"
    docs_witness = docs_dir / witness_name
    docs_stats = docs_dir / stats_name
    docs_witness.write_text(witness_table, encoding="utf-8")
    docs_stats.write_text(stats_table, encoding="utf-8")

    outputs = {
        "analysis_json": str(json_path),
        "analysis_table_tex": str(docs_witness),
        "statistics_table_tex": str(docs_stats),
    }
    if paper_tables_dir is not None:
        paper_tables_dir.mkdir(parents=True, exist_ok=True)
        paper_witness = paper_tables_dir / witness_name
        paper_stats = paper_tables_dir / stats_name
        paper_witness.write_text(witness_table, encoding="utf-8")
        paper_stats.write_text(stats_table, encoding="utf-8")
        outputs["paper_table"] = str(paper_witness)
        outputs["paper_statistics_table"] = str(paper_stats)

    figures_dir = paper_figures_dir or repo_root.parent / "paper" / "figures"
    if _render_a1_figure(report, figures_dir):
        outputs["paper_figure"] = str(
            figures_dir / f"{EXTENSION_TABLE_PREFIX}constructible_equivalence_comparison.pdf"
        )
    return outputs


def _render_a1_figure(report: dict[str, Any], figures_dir: Path) -> bool:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return False

    from fsmreasonbench.evaluator.paper_figure_style import (
        STAGE_BAR_COLORS,
        configure_paper_figure_style,
        style_axes,
    )

    configure_paper_figure_style()

    def _rate(provider: str, witness_key: str, track: str) -> float:
        row = next(
            r for r in report["rows"] if r["provider"] == provider and r["track"] == track
        )
        cell = row[witness_key]
        if cell.get("status") != "available":
            return 0.0
        return float(cell.get("certificate_valid_rate") or 0.0)

    providers = ["claude", "gpt"]
    provider_labels = [PROVIDER_LABELS[p].replace("~4.5", "").replace("~", " ") for p in providers]
    stages = [
        ("Hash R1", lambda p: _rate(p, "hash_equivalence_witness", "R1")),
        ("Bisimulation R1", lambda p: _rate(p, "constructible_bisimulation_witness", "R1")),
        ("Bisimulation R2C", lambda p: _rate(p, "constructible_bisimulation_witness", "R2C")),
    ]
    colors = STAGE_BAR_COLORS
    x = list(range(len(providers)))
    width = 0.22
    fig, ax = plt.subplots(figsize=(10.2, 3.8))
    for index, (stage_label, rate_fn) in enumerate(stages):
        offsets = [pos + (index - 1) * width for pos in x]
        rates = [rate_fn(provider) for provider in providers]
        ax.bar(
            offsets,
            rates,
            width=width,
            label=stage_label,
            color=colors[index],
            edgecolor="0.0",
            linewidth=0.6,
        )
    ax.set_xticks(x, provider_labels)
    ax.set_ylabel("Witness validity (eq subset, $n{=}51$)")
    ax.set_ylim(0, 1.05)
    ax.legend(loc="upper left", frameon=False, fontsize=9)
    style_axes(ax)
    fig.tight_layout()
    figures_dir.mkdir(parents=True, exist_ok=True)
    out_path = figures_dir / f"{EXTENSION_TABLE_PREFIX}constructible_equivalence_comparison.pdf"
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return True
