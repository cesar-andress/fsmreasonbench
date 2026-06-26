"""TMLR-ready empirical package export (tables, figures, uncertainty, narrative)."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.evaluator.bootstrap import DEFAULT_BOOTSTRAP_ALPHA, DEFAULT_BOOTSTRAP_RESAMPLES
from fsmreasonbench.evaluator.clopper_pearson import proportion_ci_with_boundary_fallback
from fsmreasonbench.evaluator.c2_existential_universal_stratified_analysis import (
    load_c2_item_metadata,
    load_condition_outcomes,
)
from fsmreasonbench.evaluator.certificate_class_complexity_analysis import (
    CERTIFICATE_TYPES,
    build_comparative_matrix,
    run_certificate_class_complexity_analysis,
)
from fsmreasonbench.evaluator.f1_claude_ablation_stratified_analysis import (
    ItemOutcome,
    exact_mcnemar_p_value,
    load_item_metadata,
    paired_bootstrap_difference_ci,
)

PACKAGE_VERSION = "v1"
PACKAGE_DIR = f"docs/tmlr_empirical_package_{PACKAGE_VERSION}"

F1_CONDITIONS = ("R1", "Oracle+Format", "R2A", "R2B", "R2C")
F1_CONDITION_LABELS = {
    "R1": "R1",
    "Oracle+Format": "Oracle+Format",
    "R2A": "R2A verify-only",
    "R2B": "R2B repair-only",
    "R2C": "R2C generator-assisted",
}
C2_CONDITIONS = F1_CONDITIONS

SOURCE_ARTIFACTS = {
    "local_matrix": "runs/local_matrix_n100_t02_v2",
    "frontier_claude": "runs/frontier_claude_sonnet_tools_n100_v2",
    "f1_oracle_ablation": "runs/ablations_f1_oracle_verdict_format_control_claude_n100_v1",
    "f1_r2_attribution": "runs/ablations_f1_r2_attribution_claude_n100_v1",
    "c2_ablation": "runs/ablations_c2_existential_universal_claude_n100_v1",
    "docs_f1_audit": "docs/f1_equivalence_witness_verifier_audit.json",
    "docs_f1_claude_stratified": "docs/f1_claude_ablation_stratified_analysis.json",
    "docs_f1_local_stratified": "docs/f1_local_matrix_subtype_stratified_analysis.json",
    "docs_c2_stratified": "docs/c2_existential_universal_stratified_analysis.json",
    "docs_complexity": "docs/certificate_class_complexity_analysis.json",
}

EXCLUDED_RUNS = [
    "Invalid Claude credit-exhaustion / infrastructure-failure cells (excluded from conclusions).",
    "Invalid Gemini quota-failure runs (excluded from conclusions).",
    "Contaminated legacy frontier run frontier_claude_sonnet_full_n100_v1 (never used).",
    "Smoke-test duplicate score rows in C2 ablation were deduplicated to n=100 unique item_ids.",
]

F1_CERTIFICATE_TYPES = ("distinguishing_trace", "equivalence_witness")
C2_CERTIFICATE_TYPES = ("trace_witness", "unreachability_witness")

FRONTIER_COHORTS = {
    "F1": "cohorts/v0.1-expanded-n100/f1-mixed-level3/items.jsonl",
    "C2": "cohorts/v0.1-expanded-n100/c2-reachability-level3/items.jsonl",
}

FRONTIER_R1_RUNS: dict[str, dict[str, str]] = {
    "claude": {
        "F1": (
            "runs/frontier_claude_sonnet_tools_n100_v2/"
            "claude-sonnet-4-5-20250929/F1/temp_0.2/R1/scores.jsonl"
        ),
        "C2": (
            "runs/frontier_claude_sonnet_tools_n100_v2/"
            "claude-sonnet-4-5-20250929/C2/temp_0.2/R1/scores.jsonl"
        ),
    },
    "gpt": {
        "F1": "runs/frontier_gpt_tools_n100_v1/gpt-4.1/F1/temp_0.2/R1/scores.jsonl",
        "C2": "runs/frontier_gpt_tools_n100_v1/gpt-4.1/C2/temp_0.2/R1/scores.jsonl",
    },
}

FIGURE1_LABEL_LAYOUT: dict[str, dict[str, Any]] = {
    "trace_witness": {
        "label": "trace witness",
        "text_xy": (3.5, 0.76),
        "ha": "center",
    },
    "distinguishing_trace": {
        "label": "distinguishing trace",
        "text_xy": (4.5, 0.58),
        "ha": "center",
    },
    "unreachability_witness": {
        "label": "unreachability witness",
        "text_xy": (6.2, 0.84),
        "ha": "left",
    },
    "equivalence_witness": {
        "label": "equivalence witness",
        "text_xy": (9.5, 0.28),
        "ha": "center",
    },
}

FIGURE1_XLIM = (3.1, 10.2)
FIGURE1_YLIM = (-0.05, 1.08)


@dataclass(frozen=True, slots=True)
class RateWithCI:
    rate: float
    n: int
    successes: int
    ci_low: float
    ci_high: float
    note: str = ""


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = quantile * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def bootstrap_rate_ci(
    values: list[bool],
    *,
    n_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    seed: int = 4242,
    alpha: float = DEFAULT_BOOTSTRAP_ALPHA,
) -> RateWithCI:
    import random

    if not values:
        return RateWithCI(0.0, 0, 0, 0.0, 0.0, note="empty")
    successes = sum(1 for value in values if value)
    rate = successes / len(values)
    rng = random.Random(seed)
    size = len(values)
    samples: list[float] = []
    for _ in range(n_resamples):
        idx = [rng.randrange(size) for _ in range(size)]
        sample = [values[i] for i in idx]
        samples.append(sum(sample) / len(sample))
    low_q = alpha / 2.0
    high_q = 1.0 - alpha / 2.0
    bootstrap_lo = round(_percentile(samples, low_q), 4)
    bootstrap_hi = round(_percentile(samples, high_q), 4)
    ci_lo, ci_hi = proportion_ci_with_boundary_fallback(
        successes,
        len(values),
        bootstrap_lo,
        bootstrap_hi,
        alpha=alpha,
    )
    return RateWithCI(
        rate=round(rate, 4),
        n=len(values),
        successes=successes,
        ci_low=round(ci_lo, 4),
        ci_high=round(ci_hi, 4),
    )


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rate_fmt(value: float, ci_low: float | None = None, ci_high: float | None = None) -> str:
    if ci_low is not None and ci_high is not None:
        return f"{value:.3f} [{ci_low:.3f}, {ci_high:.3f}]"
    return f"{value:.3f}"


def _pair_fmt(cert: float, full: float) -> str:
    return f"{cert:.3f} / {full:.3f}"


def build_table1(repo_root: Path) -> list[dict[str, Any]]:
    complexity = _load_json(repo_root / SOURCE_ARTIFACTS["docs_complexity"])
    c2_json = _load_json(repo_root / SOURCE_ARTIFACTS["docs_c2_stratified"])
    matrix = {row["certificate_type"]: row for row in complexity["comparative_matrix"]}
    specs = complexity["certificate_specs"]
    claude_rates = dict(complexity.get("claude_r1_certificate_valid_rate_by_type", {}))
    for row in c2_json["tables"]["table2_by_certificate_subtype"]:
        if row["condition"] == "R1":
            claude_rates[row["certificate_type"]] = row["cert"]
    rows: list[dict[str, Any]] = []
    for cert_type in CERTIFICATE_TYPES:
        row = matrix[cert_type]
        rate = claude_rates.get(cert_type, 0.0)
        rows.append(
            {
                "certificate_type": cert_type,
                "family": specs[cert_type]["family"],
                "required_fields": row["required_fields"],
                "canonical_hashing": row["requires_canonical_hashing"],
                "multiple_valid_forms": row["multiple_valid_forms"],
                "complexity_score": row["estimated_complexity_score"],
                "Claude_R1_cert": round(rate, 3),
            }
        )
    return rows


def _cert_rate_for_type(
    outcomes: dict[str, ItemOutcome],
    metadata: dict[str, Any],
    cert_type: str,
) -> float:
    filtered = _filter_outcomes_by_cert_type(outcomes, metadata, cert_type)
    if not filtered:
        raise ValueError(f"no items for certificate_type={cert_type!r}")
    successes = sum(1 for outcome in filtered.values() if outcome.certificate_valid)
    return round(successes / len(filtered), 3)


def build_frontier_r1_cert_rates_by_type(repo_root: Path, provider: str) -> dict[str, float]:
    """R1 certificate-valid rates by witness class from frozen frontier tool runs."""
    if provider not in FRONTIER_R1_RUNS:
        raise ValueError(f"unsupported provider {provider!r}; expected claude or gpt")
    runs = FRONTIER_R1_RUNS[provider]
    rates: dict[str, float] = {}

    f1_scores = repo_root / runs["F1"]
    f1_cohort = repo_root / FRONTIER_COHORTS["F1"]
    f1_outcomes = load_condition_outcomes(f1_scores)
    f1_meta = load_item_metadata(f1_cohort)
    for cert_type in F1_CERTIFICATE_TYPES:
        rates[cert_type] = _cert_rate_for_type(f1_outcomes, f1_meta, cert_type)

    c2_scores = repo_root / runs["C2"]
    c2_cohort = repo_root / FRONTIER_COHORTS["C2"]
    c2_outcomes = load_condition_outcomes(c2_scores)
    c2_meta = load_c2_item_metadata(c2_cohort)
    for cert_type in C2_CERTIFICATE_TYPES:
        rates[cert_type] = _cert_rate_for_type(c2_outcomes, c2_meta, cert_type)

    return rates


def build_table1_frontier_comparison(repo_root: Path) -> list[dict[str, Any]]:
    """Table 1 rows with Claude and GPT R1 rates from matching frontier tool campaigns."""
    table1 = build_table1(repo_root)
    claude_rates = build_frontier_r1_cert_rates_by_type(repo_root, "claude")
    gpt_rates = build_frontier_r1_cert_rates_by_type(repo_root, "gpt")
    rows: list[dict[str, Any]] = []
    for row in table1:
        cert_type = row["certificate_type"]
        updated = dict(row)
        updated["Claude_R1_cert"] = claude_rates[cert_type]
        updated["GPT_R1_cert"] = gpt_rates[cert_type]
        rows.append(updated)
    return rows


def _f1_subtype_lookup(f1_json: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    for row in f1_json["tables"]["by_certificate_type"]:
        lookup[(row["Condition"], row["certificate_type"])] = row
    overall = {row["Condition"]: row for row in f1_json["tables"]["overall"]}
    lookup.update({(cond, "__overall__"): overall[cond] for cond in overall})
    return lookup


def build_table2(repo_root: Path) -> list[dict[str, Any]]:
    f1_json = _load_json(repo_root / SOURCE_ARTIFACTS["docs_f1_claude_stratified"])
    lookup = _f1_subtype_lookup(f1_json)
    rows: list[dict[str, Any]] = []
    for condition in F1_CONDITIONS:
        dist = lookup[(condition, "distinguishing_trace")]
        eq = lookup[(condition, "equivalence_witness")]
        overall = lookup[(condition, "__overall__")]
        rows.append(
            {
                "condition": F1_CONDITION_LABELS[condition],
                "distinguishing_trace_cert": dist["cert"],
                "distinguishing_trace_full": dist["full"],
                "equivalence_witness_cert": eq["cert"],
                "equivalence_witness_full": eq["full"],
                "overall_cert": overall["cert"],
                "overall_full": overall["full"],
            }
        )
    return rows


def build_table3(repo_root: Path) -> list[dict[str, Any]]:
    c2_json = _load_json(repo_root / SOURCE_ARTIFACTS["docs_c2_stratified"])
    by_cond: dict[str, dict[str, dict[str, Any]]] = {}
    for row in c2_json["tables"]["table2_by_certificate_subtype"]:
        by_cond.setdefault(row["condition"], {})[row["certificate_type"]] = row
    overall = {row["condition"]: row for row in c2_json["tables"]["table1_overall_by_condition"]}
    rows: list[dict[str, Any]] = []
    for condition in C2_CONDITIONS:
        trace = by_cond[condition]["trace_witness"]
        unreach = by_cond[condition]["unreachability_witness"]
        ov = overall[condition]
        rows.append(
            {
                "condition": F1_CONDITION_LABELS[condition],
                "trace_witness_cert": trace["cert"],
                "trace_witness_full": trace["full"],
                "unreachability_witness_cert": unreach["cert"],
                "unreachability_witness_full": unreach["full"],
                "overall_cert": ov["cert"],
                "overall_full": ov["full"],
            }
        )
    return rows


def build_table4(repo_root: Path) -> list[dict[str, Any]]:
    local_json = _load_json(repo_root / SOURCE_ARTIFACTS["docs_f1_local_stratified"])
    by_cell: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    for row in local_json["tables"]["by_certificate_type"]:
        by_cell.setdefault((row["model"], row["track"]), {})[row["certificate_type"]] = row
    overall = {
        (row["model"], row["track"]): row for row in local_json["tables"]["overall"]
    }
    rows: list[dict[str, Any]] = []
    for (model, track), sub in sorted(by_cell.items()):
        dist = sub["distinguishing_trace"]
        eq = sub["equivalence_witness"]
        ov = overall[(model, track)]
        rows.append(
            {
                "model": model,
                "track": track,
                "distinguishing_trace_full": dist["full"],
                "equivalence_witness_full": eq["full"],
                "overall_full": ov["full"],
                "extract": ov["extract"],
                "verdict": ov["verdict"],
            }
        )
    return rows


def build_appendix_table(repo_root: Path) -> dict[str, Any]:
    audit = _load_json(repo_root / SOURCE_ARTIFACTS["docs_f1_audit"])
    complexity = run_certificate_class_complexity_analysis(repo_root)
    checks_pass = sum(1 for c in audit["checks"] if c["passed"])
    checks_total = len(audit["checks"])
    return {
        "verifier_audit": {
            "checks_passed": checks_pass,
            "checks_total": checks_total,
            "single_canonical_witness_form": audit["acceptance_conditions"][
                "single_canonical_witness_form"
            ],
            "paper_validity_sentence": audit.get("paper_validity_sentence", ""),
        },
        "failure_taxonomy_pooled": complexity["failure_taxonomy"]["pooled_by_certificate_type"],
    }


def _filter_outcomes_by_cert_type(
    outcomes: dict[str, ItemOutcome],
    metadata: dict[str, Any],
    cert_type: str,
) -> dict[str, ItemOutcome]:
    filtered: dict[str, ItemOutcome] = {}
    for item_id, outcome in outcomes.items():
        meta = metadata[item_id]
        gold_type = getattr(meta, "gold_certificate_type", None)
        if gold_type is None and isinstance(meta, dict):
            gold_type = meta.get("gold_certificate_type")
        if gold_type == cert_type:
            filtered[item_id] = outcome
    return filtered


def compute_uncertainty(repo_root: Path) -> dict[str, Any]:
    f1_scores = (
        repo_root
        / SOURCE_ARTIFACTS["frontier_claude"]
        / "claude-sonnet-4-5-20250929/F1/temp_0.2/R1/scores.jsonl"
    )
    f1_cohort = repo_root / "cohorts/v0.1-expanded-n100/f1-mixed-level3/items.jsonl"
    f1_meta = load_item_metadata(f1_cohort)
    f1_r1 = load_condition_outcomes(f1_scores)

    c2_scores = repo_root / SOURCE_ARTIFACTS["c2_ablation"] / "R1/scores.jsonl"
    c2_cohort = (
        repo_root / "cohorts/v0.1-expanded-n100/c2-reachability-balanced-n100/items.jsonl"
    )
    c2_meta = load_c2_item_metadata(c2_cohort)
    c2_r1 = load_condition_outcomes(c2_scores)

    f1_json = _load_json(repo_root / SOURCE_ARTIFACTS["docs_f1_claude_stratified"])
    paired_rows = f1_json["tables"].get("paired_comparisons", [])

    dist_outcomes = _filter_outcomes_by_cert_type(f1_r1, f1_meta, "distinguishing_trace")
    eq_outcomes = _filter_outcomes_by_cert_type(f1_r1, f1_meta, "equivalence_witness")
    dist_cert = [o.certificate_valid for o in dist_outcomes.values()]
    eq_cert = [o.certificate_valid for o in eq_outcomes.values()]

    trace_outcomes = _filter_outcomes_by_cert_type(c2_r1, c2_meta, "trace_witness")
    unreach_outcomes = _filter_outcomes_by_cert_type(c2_r1, c2_meta, "unreachability_witness")

    def _paired_mcnemar_cert(
        first: dict[str, ItemOutcome],
        second: dict[str, ItemOutcome],
        label: str,
    ) -> dict[str, Any]:
        shared = sorted(set(first) & set(second))
        first_only = second_only = 0
        first_vals: list[bool] = []
        second_vals: list[bool] = []
        for item_id in shared:
            a = first[item_id].certificate_valid
            b = second[item_id].certificate_valid
            first_vals.append(a)
            second_vals.append(b)
            if a and not b:
                first_only += 1
            elif b and not a:
                second_only += 1
        return {
            "comparison": label,
            "paired_items": len(shared),
            "first_cert_rate": asdict(bootstrap_rate_ci(first_vals, seed=5101)),
            "second_cert_rate": asdict(bootstrap_rate_ci(second_vals, seed=5102)),
            "cert_diff_first_minus_second": paired_bootstrap_difference_ci(
                first_vals, second_vals, seed=5103
            ),
            "mcnemar_first_only": first_only,
            "mcnemar_second_only": second_only,
            "mcnemar_p_value": exact_mcnemar_p_value(first_only, second_only),
            "test_type": "paired_mcnemar_on_same_item_ids",
        }

    f1_r2a = load_condition_outcomes(
        repo_root / SOURCE_ARTIFACTS["f1_r2_attribution"] / "R2A/scores.jsonl"
    )
    f1_r2b = load_condition_outcomes(
        repo_root / SOURCE_ARTIFACTS["f1_r2_attribution"] / "R2B/scores.jsonl"
    )
    f1_r2c = load_condition_outcomes(
        repo_root / SOURCE_ARTIFACTS["f1_r2_attribution"] / "R2C/scores.jsonl"
    )

    local_json = _load_json(repo_root / SOURCE_ARTIFACTS["docs_f1_local_stratified"])
    local_gaps: list[dict[str, Any]] = []
    for row in local_json["tables"]["by_certificate_type"]:
        if row["track"] != "R1":
            continue
        if row["certificate_type"] != "distinguishing_trace":
            continue
        eq_row = next(
            r
            for r in local_json["tables"]["by_certificate_type"]
            if r["model"] == row["model"]
            and r["track"] == row["track"]
            and r["certificate_type"] == "equivalence_witness"
        )
        local_gaps.append(
            {
                "model": row["model"],
                "track": row["track"],
                "distinguishing_trace_full": row["full"],
                "equivalence_witness_full": eq_row["full"],
                "gap_dist_minus_eq": round(row["full"] - eq_row["full"], 3),
                "note": (
                    "Descriptive subtype gap on disjoint item subsets (49 dist + 51 eq); "
                    "not a paired same-item test."
                ),
            }
        )

    return {
        "bootstrap_settings": {
            "n_resamples": DEFAULT_BOOTSTRAP_RESAMPLES,
            "alpha": DEFAULT_BOOTSTRAP_ALPHA,
            "method": "percentile_bootstrap",
        },
        "f1_r1_subtype_comparison": {
            "note": (
                "distinguishing_trace (n=49) and equivalence_witness (n=51) are disjoint item "
                "subsets; rates are reported with independent bootstrap CIs (descriptive)."
            ),
            "distinguishing_trace_cert": asdict(bootstrap_rate_ci(dist_cert, seed=5001)),
            "equivalence_witness_cert": asdict(bootstrap_rate_ci(eq_cert, seed=5002)),
            "descriptive_gap_dist_minus_eq": round(
                bootstrap_rate_ci(dist_cert).rate - bootstrap_rate_ci(eq_cert).rate, 4
            ),
        },
        "c2_r1_subtype_comparison": {
            "note": (
                "trace_witness and unreachability_witness are disjoint balanced subsets (50+50); "
                "independent bootstrap CIs (descriptive)."
            ),
            "trace_witness_cert": asdict(
                bootstrap_rate_ci(
                    [o.certificate_valid for o in trace_outcomes.values()], seed=5201
                )
            ),
            "unreachability_witness_cert": asdict(
                bootstrap_rate_ci(
                    [o.certificate_valid for o in unreach_outcomes.values()], seed=5202
                )
            ),
        },
        "paired_condition_comparisons": [
            _paired_mcnemar_cert(f1_r1, f1_r2c, "F1 R1 vs R2C (overall, n=100)"),
            _paired_mcnemar_cert(f1_r2a, f1_r2c, "F1 R2A vs R2C (overall, n=100)"),
            _paired_mcnemar_cert(f1_r2b, f1_r2c, "F1 R2B vs R2C (overall, n=100)"),
            _paired_mcnemar_cert(
                _filter_outcomes_by_cert_type(f1_r1, f1_meta, "equivalence_witness"),
                _filter_outcomes_by_cert_type(f1_r2c, f1_meta, "equivalence_witness"),
                "F1 eq-witness R1 vs R2C (n=51 paired items)",
            ),
        ],
        "paired_comparisons_from_f1_stratified_export": paired_rows,
        "local_f1_r1_subtype_gaps_descriptive": local_gaps,
    }


def _dataclass_to_json(obj: Any) -> Any:
    if hasattr(obj, "__dict__") and hasattr(obj, "rate"):
        return obj.__dict__
    if isinstance(obj, dict):
        return {k: _dataclass_to_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_dataclass_to_json(v) for v in obj]
    return obj


def _markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(lines)


def _latex_escape(text: str) -> str:
    return (
        text.replace("\\", "\\textbackslash{}")
        .replace("_", "\\_")
        .replace("%", "\\%")
        .replace("&", "\\&")
    )


def _latex_table(
    caption: str,
    label: str,
    headers: list[str],
    rows: list[list[Any]],
    col_spec: str | None = None,
) -> str:
    spec = col_spec or ("l" * len(headers))
    lines = [
        "\\begin{table}[t]",
        "\\centering",
        f"\\caption{{{caption}}}",
        f"\\label{{{label}}}",
        f"\\begin{{tabular}}{{{spec}}}",
        "\\toprule",
        " & ".join(_latex_escape(str(h)) for h in headers) + " \\\\",
        "\\midrule",
    ]
    for row in rows:
        lines.append(" & ".join(_latex_escape(str(cell)) for cell in row) + " \\\\")
    lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table}"])
    return "\n".join(lines)


def write_tables(
    out_dir: Path,
    *,
    table1: list[dict[str, Any]],
    table2: list[dict[str, Any]],
    table3: list[dict[str, Any]],
    table4: list[dict[str, Any]],
    appendix: dict[str, Any],
) -> None:
    tables_dir = out_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    t1_headers = [
        "certificate_type",
        "family",
        "required_fields",
        "canonical_hashing",
        "multiple_valid_forms",
        "complexity_score",
        "Claude_R1_cert",
    ]
    t1_rows = [[row[h] for h in t1_headers] for row in table1]
    (tables_dir / "table1_certificate_complexity.md").write_text(
        "# Table 1: Certificate class complexity and Claude R1 success\n\n"
        + _markdown_table(t1_headers, t1_rows),
        encoding="utf-8",
    )
    (tables_dir / "table1_certificate_complexity.tex").write_text(
        _latex_table(
            "Certificate class complexity and Claude R1 certificate success.",
            "tab:cert-complexity",
            t1_headers,
            t1_rows,
            "llrrrrr",
        ),
        encoding="utf-8",
    )

    t2_headers = [
        "condition",
        "dist_cert/full",
        "eq_cert/full",
        "overall_cert/full",
    ]
    t2_rows = [
        [
            row["condition"],
            _pair_fmt(row["distinguishing_trace_cert"], row["distinguishing_trace_full"]),
            _pair_fmt(row["equivalence_witness_cert"], row["equivalence_witness_full"]),
            _pair_fmt(row["overall_cert"], row["overall_full"]),
        ]
        for row in table2
    ]
    (tables_dir / "table2_f1_claude_ablations.md").write_text(
        "# Table 2: F1 Claude ablations by condition and subtype\n\n"
        + _markdown_table(t2_headers, t2_rows),
        encoding="utf-8",
    )
    (tables_dir / "table2_f1_claude_ablations.tex").write_text(
        _latex_table(
            "F1 Claude ablations by condition and certificate subtype (cert/full rates).",
            "tab:f1-ablations",
            t2_headers,
            t2_rows,
            "lccc",
        ),
        encoding="utf-8",
    )

    t3_headers = ["condition", "trace_cert/full", "unreach_cert/full", "overall_cert/full"]
    t3_rows = [
        [
            row["condition"],
            _pair_fmt(row["trace_witness_cert"], row["trace_witness_full"]),
            _pair_fmt(row["unreachability_witness_cert"], row["unreachability_witness_full"]),
            _pair_fmt(row["overall_cert"], row["overall_full"]),
        ]
        for row in table3
    ]
    (tables_dir / "table3_c2_claude_ablations.md").write_text(
        "# Table 3: C2 Claude ablations by condition and subtype\n\n"
        + _markdown_table(t3_headers, t3_rows),
        encoding="utf-8",
    )
    (tables_dir / "table3_c2_claude_ablations.tex").write_text(
        _latex_table(
            "C2 Claude ablations by condition and certificate subtype (cert/full rates).",
            "tab:c2-ablations",
            t3_headers,
            t3_rows,
            "lccc",
        ),
        encoding="utf-8",
    )

    t4_headers = [
        "model",
        "track",
        "dist_full",
        "eq_full",
        "overall_full",
        "extract",
        "verdict",
    ]
    t4_rows = [
        [
            row["model"],
            row["track"],
            f"{row['distinguishing_trace_full']:.3f}",
            f"{row['equivalence_witness_full']:.3f}",
            f"{row['overall_full']:.3f}",
            f"{row['extract']:.3f}",
            f"{row['verdict']:.3f}",
        ]
        for row in table4
    ]
    (tables_dir / "table4_local_f1_matrix.md").write_text(
        "# Table 4: Local F1 matrix subtype results\n\n" + _markdown_table(t4_headers, t4_rows),
        encoding="utf-8",
    )
    (tables_dir / "table4_local_f1_matrix.tex").write_text(
        _latex_table(
            "Local open-weight F1 matrix by model, track, and certificate subtype.",
            "tab:local-f1",
            t4_headers,
            t4_rows,
            "llrrrrr",
        ),
        encoding="utf-8",
    )

    appendix_lines = [
        "# Appendix Table: Verifier audit and failure taxonomy",
        "",
        "## equivalence_witness verifier audit",
        "",
        f"- Checks passed: {appendix['verifier_audit']['checks_passed']}/"
        f"{appendix['verifier_audit']['checks_total']}",
        f"- Single canonical witness form: "
        f"{appendix['verifier_audit']['single_canonical_witness_form']}",
        "",
        f"> {appendix['verifier_audit']['paper_validity_sentence']}",
        "",
        "## Pooled failure taxonomy (frozen Claude runs)",
        "",
    ]
    for cert_type, pooled in appendix["failure_taxonomy_pooled"].items():
        appendix_lines.append(f"### {cert_type}")
        svf = pooled.get("semantic_vs_formatting", {})
        appendix_lines.append(
            f"- Semantic: {svf.get('semantic', 0)}; formatting: {svf.get('formatting', 0)}"
        )
        for entry in pooled.get("top_failure_categories", [])[:4]:
            appendix_lines.append(
                f"- `{entry['category']}`: {entry['count']} ({entry['percentage']:.1%})"
            )
        appendix_lines.append("")
    (tables_dir / "appendix_verifier_failure_taxonomy.md").write_text(
        "\n".join(appendix_lines),
        encoding="utf-8",
    )
    (tables_dir / "appendix_verifier_failure_taxonomy.tex").write_text(
        "\\section*{Appendix: Verifier audit and failure taxonomy}\n\n"
        + "\n".join(
            line.replace("#", "")
            for line in appendix_lines
            if line and not line.startswith("|")
        ),
        encoding="utf-8",
    )


def _configure_complexity_figure_style() -> None:
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "text.color": "black",
            "axes.labelcolor": "black",
            "xtick.color": "black",
            "ytick.color": "black",
        }
    )


def _plot_complexity_vs_cert_panel(
    ax: Any,
    rows: list[dict[str, Any]],
    *,
    cert_rate_key: str,
    ylabel: str,
    title: str | None = None,
    annotate: bool = True,
) -> None:
    for row in rows:
        if row.get(cert_rate_key) is None:
            continue
        cert_type = row["certificate_type"]
        x = row["complexity_score"]
        y = row[cert_rate_key]
        ax.scatter(x, y, s=120, c="black", edgecolors="0.35", linewidths=0.6, zorder=3)
        if not annotate:
            continue
        layout = FIGURE1_LABEL_LAYOUT.get(
            cert_type,
            {
                "label": cert_type.replace("_", " "),
                "text_xy": (x + 0.35, y + 0.08),
                "ha": "left",
            },
        )
        ax.annotate(
            layout["label"],
            xy=(x, y),
            xytext=layout["text_xy"],
            textcoords="data",
            fontsize=9,
            ha=layout["ha"],
            va="center",
            arrowprops={
                "arrowstyle": "-",
                "color": "0.45",
                "lw": 0.8,
                "shrinkA": 6,
                "shrinkB": 4,
            },
            bbox={
                "boxstyle": "round,pad=0.25",
                "fc": "white",
                "ec": "0.85",
                "alpha": 0.92,
            },
            zorder=4,
        )
    ax.set_xlabel("Structural complexity score")
    ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)
    ax.set_xlim(*FIGURE1_XLIM)
    ax.set_ylim(*FIGURE1_YLIM)
    ax.grid(True, alpha=0.3, color="0.85")


def write_figure1_complexity_vs_success(
    figures_dir: Path,
    table1: list[dict[str, Any]],
) -> tuple[Path, Path]:
    import matplotlib.pyplot as plt

    _configure_complexity_figure_style()
    figures_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    _plot_complexity_vs_cert_panel(
        ax,
        table1,
        cert_rate_key="Claude_R1_cert",
        ylabel="Claude R1 certificate\nvalid rate",
        title="Certificate complexity vs Claude R1 success",
    )
    fig.subplots_adjust(top=0.90, bottom=0.13, left=0.17, right=0.98)
    png_path = figures_dir / "figure1_complexity_vs_success.png"
    pdf_path = figures_dir / "figure1_complexity_vs_success.pdf"
    fig.savefig(png_path, dpi=200)
    fig.savefig(pdf_path)
    plt.close(fig)
    return png_path, pdf_path


def write_figure_certificate_complexity_frontier_comparison(
    figures_dir: Path,
    table1: list[dict[str, Any]],
) -> tuple[Path, Path]:
    import matplotlib.pyplot as plt

    _configure_complexity_figure_style()
    figures_dir.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.8), sharex=True, sharey=True)
    _plot_complexity_vs_cert_panel(
        axes[0],
        table1,
        cert_rate_key="Claude_R1_cert",
        ylabel="R1 witness\nvalidity",
        title="Claude Sonnet 4.5 R1",
    )
    _plot_complexity_vs_cert_panel(
        axes[1],
        table1,
        cert_rate_key="GPT_R1_cert",
        ylabel="R1 witness\nvalidity",
        title="GPT-4.1 R1",
    )
    axes[0].set_ylabel("R1 witness\nvalidity")
    axes[1].set_ylabel("")
    fig.subplots_adjust(top=0.88, bottom=0.16, left=0.10, right=0.98, wspace=0.22)
    png_path = figures_dir / "figure_certificate_complexity_frontier_comparison.png"
    pdf_path = figures_dir / "figure_certificate_complexity_frontier_comparison.pdf"
    fig.savefig(png_path, dpi=200)
    fig.savefig(pdf_path)
    plt.close(fig)
    return png_path, pdf_path


def write_certificate_complexity_figures(
    repo_root: Path,
    out_dir: Path,
    *,
    model: str = "both",
    paper_figures_dir: Path | None = None,
) -> list[str]:
    """Export certificate-complexity scatter figure(s) from frozen summaries."""
    if model not in {"claude", "gpt", "both"}:
        raise ValueError(f"unsupported model {model!r}; expected claude, gpt, or both")

    figures_dir = out_dir / "figures"
    written: list[str] = []

    if model in {"claude", "both"}:
        table1_claude = build_table1(repo_root)
        write_figure1_complexity_vs_success(figures_dir, table1_claude)
        written.extend(
            [
                "figures/figure1_complexity_vs_success.png",
                "figures/figure1_complexity_vs_success.pdf",
            ]
        )

    if model in {"gpt", "both"}:
        table1_frontier = build_table1_frontier_comparison(repo_root)
        if model == "gpt":
            import matplotlib.pyplot as plt

            _configure_complexity_figure_style()
            fig, ax = plt.subplots(figsize=(7.2, 5.0))
            _plot_complexity_vs_cert_panel(
                ax,
                table1_frontier,
                cert_rate_key="GPT_R1_cert",
                ylabel="GPT-4.1 R1 witness\nvalidity",
                title="Witness complexity vs GPT-4.1 R1 validity",
            )
            fig.subplots_adjust(top=0.90, bottom=0.13, left=0.17, right=0.98)
            stem = "figure_certificate_complexity_gpt_r1"
            fig.savefig(figures_dir / f"{stem}.png", dpi=200)
            fig.savefig(figures_dir / f"{stem}.pdf")
            plt.close(fig)
            written.extend([f"figures/{stem}.png", f"figures/{stem}.pdf"])
        if model == "both":
            write_figure_certificate_complexity_frontier_comparison(figures_dir, table1_frontier)
            written.extend(
                [
                    "figures/figure_certificate_complexity_frontier_comparison.png",
                    "figures/figure_certificate_complexity_frontier_comparison.pdf",
                ]
            )

    if paper_figures_dir is not None:
        paper_figures_dir.mkdir(parents=True, exist_ok=True)
        for relative in written:
            source = out_dir / relative
            if source.is_file():
                target = paper_figures_dir / source.name
                target.write_bytes(source.read_bytes())

    return written


def write_figures(
    out_dir: Path,
    *,
    table1: list[dict[str, Any]],
    table2: list[dict[str, Any]],
    table3: list[dict[str, Any]],
    table4: list[dict[str, Any]],
) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    figures_dir = out_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    write_figure1_complexity_vs_success(figures_dir, table1)

    # Figure 2: F1 slopegraph
    conds = [row["condition"] for row in table2]
    x = np.arange(len(conds))
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.plot(x, [r["distinguishing_trace_cert"] for r in table2], "o-", label="distinguishing_trace cert")
    ax.plot(x, [r["equivalence_witness_cert"] for r in table2], "o-", label="equivalence_witness cert")
    ax.set_xticks(x, conds, rotation=20, ha="right")
    ax.set_ylabel("certificate_valid_rate")
    ax.set_title("F1 Claude ablation: certificate rate by subtype")
    ax.set_ylim(-0.05, 1.05)
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(figures_dir / "figure2_f1_ablation_slopegraph.png", dpi=200)
    fig.savefig(figures_dir / "figure2_f1_ablation_slopegraph.pdf")
    plt.close(fig)

    # Figure 3: C2 slopegraph
    conds3 = [row["condition"] for row in table3]
    x3 = np.arange(len(conds3))
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.plot(x3, [r["trace_witness_cert"] for r in table3], "o-", label="trace_witness cert")
    ax.plot(
        x3,
        [r["unreachability_witness_cert"] for r in table3],
        "o-",
        label="unreachability_witness cert",
    )
    ax.set_xticks(x3, conds3, rotation=20, ha="right")
    ax.set_ylabel("certificate_valid_rate")
    ax.set_title("C2 Claude ablation: certificate rate by subtype")
    ax.set_ylim(-0.05, 1.05)
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(figures_dir / "figure3_c2_ablation_slopegraph.png", dpi=200)
    fig.savefig(figures_dir / "figure3_c2_ablation_slopegraph.pdf")
    plt.close(fig)

    # Figure 4: local F1 heatmap (two panels)
    models = sorted({row["model"] for row in table4})
    tracks = ["R0", "R1", "R2"]
    dist_matrix = np.zeros((len(models), len(tracks)))
    eq_matrix = np.zeros((len(models), len(tracks)))
    lookup = {(r["model"], r["track"]): r for r in table4}
    for i, model in enumerate(models):
        for j, track in enumerate(tracks):
            row = lookup[(model, track)]
            dist_matrix[i, j] = row["distinguishing_trace_full"]
            eq_matrix[i, j] = row["equivalence_witness_full"]

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5), sharey=True)
    for ax, matrix, title in (
        (axes[0], dist_matrix, "distinguishing_trace full"),
        (axes[1], eq_matrix, "equivalence_witness full"),
    ):
        im = ax.imshow(matrix, vmin=0, vmax=1, cmap="viridis", aspect="auto")
        ax.set_xticks(range(len(tracks)), tracks)
        ax.set_yticks(range(len(models)), models)
        ax.set_title(title)
        for i in range(len(models)):
            for j in range(len(tracks)):
                ax.text(j, i, f"{matrix[i, j]:.2f}", ha="center", va="center", color="white")
    fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.85, label="fully_correct_rate")
    fig.suptitle("Local F1 subtype heatmap (open-weight models, n=100, T=0.2)")
    fig.tight_layout()
    fig.savefig(figures_dir / "figure4_local_f1_heatmap.png", dpi=200)
    fig.savefig(figures_dir / "figure4_local_f1_heatmap.pdf")
    plt.close(fig)


def write_uncertainty_docs(out_dir: Path, uncertainty: dict[str, Any]) -> None:
    unc_dir = out_dir / "uncertainty"
    unc_dir.mkdir(parents=True, exist_ok=True)
    serializable = _dataclass_to_json(uncertainty)
    (unc_dir / "bootstrap_mcnemar_summary.json").write_text(
        json.dumps(serializable, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    lines = [
        "# Uncertainty summary (bootstrap 95% CI + paired tests)",
        "",
        "## F1 R1 subtype rates (descriptive; disjoint item subsets)",
        "",
    ]
    f1 = uncertainty["f1_r1_subtype_comparison"]
    lines.append(f"- Note: {f1['note']}")
    for key in ("distinguishing_trace_cert", "equivalence_witness_cert"):
        row = f1[key]
        lines.append(
            f"- **{key}**: {_rate_fmt(row['rate'], row['ci_low'], row['ci_high'])} "
            f"(k={row['successes']}/{row['n']})"
        )
    lines.extend(["", "## C2 R1 subtype rates (descriptive)", ""])
    c2 = uncertainty["c2_r1_subtype_comparison"]
    lines.append(f"- Note: {c2['note']}")
    for key in ("trace_witness_cert", "unreachability_witness_cert"):
        row = c2[key]
        lines.append(
            f"- **{key}**: {_rate_fmt(row['rate'], row['ci_low'], row['ci_high'])} "
            f"(k={row['successes']}/{row['n']})"
        )
    lines.extend(["", "## Paired condition comparisons (same item IDs)", ""])
    for row in uncertainty["paired_condition_comparisons"]:
        lines.append(f"### {row['comparison']}")
        lines.append(f"- McNemar p-value: {row['mcnemar_p_value']}")
        diff = row["cert_diff_first_minus_second"]
        lines.append(
            f"- Cert rate diff CI: {diff['point_diff']:+.3f} "
            f"[{diff['ci_low']:+.3f}, {diff['ci_high']:+.3f}]"
        )
        lines.append("")
    (unc_dir / "bootstrap_mcnemar_summary.md").write_text("\n".join(lines), encoding="utf-8")


def write_readme(out_dir: Path, repo_root: Path) -> None:
    readme = f"""# TMLR Empirical Package {PACKAGE_VERSION}

Frozen empirical artifacts for the FSMReasonBench paper submission.

## Final thesis

Knowing the verdict is not enough: LLMs can construct replay-style FSM certificates, but fail sharply on **canonical hash-based certificates** that require verifier-identical symbolic synthesis.

## No new model calls

This package is generated entirely from frozen runs and existing analysis exports. **No API calls were made during package generation.**

## Frozen run policy

- Do **not** modify directories under `runs/` referenced below.
- Do **not** overwrite prior docs under `docs/` outside this package directory.
- Regenerate only into `docs/tmlr_empirical_package_v1/`.

## Source artifacts

| Artifact | Path |
|----------|------|
| Local matrix | `{SOURCE_ARTIFACTS['local_matrix']}` |
| Claude frontier tools | `{SOURCE_ARTIFACTS['frontier_claude']}` |
| F1 oracle ablation | `{SOURCE_ARTIFACTS['f1_oracle_ablation']}` |
| F1 R2 attribution | `{SOURCE_ARTIFACTS['f1_r2_attribution']}` |
| C2 existential/universal ablation | `{SOURCE_ARTIFACTS['c2_ablation']}` |
| F1 verifier audit | `{SOURCE_ARTIFACTS['docs_f1_audit']}` |
| F1 Claude stratified | `{SOURCE_ARTIFACTS['docs_f1_claude_stratified']}` |
| F1 local stratified | `{SOURCE_ARTIFACTS['docs_f1_local_stratified']}` |
| C2 stratified | `{SOURCE_ARTIFACTS['docs_c2_stratified']}` |
| Certificate complexity | `{SOURCE_ARTIFACTS['docs_complexity']}` |

## Excluded from scientific conclusions

"""
    for item in EXCLUDED_RUNS:
        readme += f"- {item}\n"

    readme += """
## Key claims (supported)

1. Claude R1 achieves ~0.94 `distinguishing_trace` cert but **0.00** `equivalence_witness` cert on F1 (n=100).
2. Oracle verdict + format control does **not** restore eq-witness (remains 0.00); R2A/R2B add ~0.02–0.03 overall, not ~0.50.
3. R2C / frozen R2 (~0.99) closes eq-witness via `solver.equivalence_certificate` (same hash builder as verifier).
4. C2 shows **no F1-like collapse**: trace_witness ~0.96, unreachability_witness ~1.00 under Claude R1.
5. Structural analysis: only `equivalence_witness` requires canonical `minimized_dfa_hash` (complexity 9.5/10).

## Non-claims

- We do **not** claim a general existential-vs-universal certification asymmetry (C2 refutes this for Claude).
- We do **not** claim the verifier is buggy (16/16 hostile audit checks pass).
- We do **not** claim oracle verdict alone enables certificate construction.
- Hash mismatch on eq-witness does **not** prove model refuted equivalence when semantic check passes.

## Tables and figures

| Output | Source |
|--------|--------|
| Table 1 | `docs/certificate_class_complexity_analysis.json` + Claude R1 frozen scores |
| Table 2 | `docs/f1_claude_ablation_stratified_analysis.json` |
| Table 3 | `docs/c2_existential_universal_stratified_analysis.json` |
| Table 4 | `docs/f1_local_matrix_subtype_stratified_analysis.json` |
| Appendix | `docs/f1_equivalence_witness_verifier_audit.json` + complexity failure taxonomy |
| Figure 1 | Table 1 |
| Figure 2 | Table 2 |
| Figure 3 | Table 3 |
| Figure 4 | Table 4 |
| Uncertainty | Item-level scores from frozen runs (see `uncertainty/`) |

## Regenerate

```bash
cd {repo_root.name}
PYTHONPATH=src python -m fsmreasonbench.cli.export_tmlr_empirical_package
```

Requires `matplotlib` (`pip install -e '.[plot]'`).
"""
    (out_dir / "README.md").write_text(readme, encoding="utf-8")


def write_narrative_memo(out_dir: Path) -> None:
    memo = """# Narrative memo (TMLR empirical package)

## Final paper thesis

LLMs can answer FSM verdict questions and emit **replay-checkable witnesses** (traces, acceptance labels, reachability paths, reachable sets), but fail sharply when the benchmark requires **verifier-identical canonical hash witnesses** (`minimized_dfa_hash`) for DFA equivalence. Knowing the oracle verdict and schema is insufficient; only generator-assisted tool tracks supply the canonical synthesis.

## What we stopped claiming

- A general **existential-vs-universal** certification asymmetry (C2 balanced ablation shows both C2 subtypes ~96–100% for Claude R1).
- That the universal side of F1 (`equivalence_witness`) fails because quantification is inherently harder than producing a trace.
- That verify-only or repair-only tool ablations explain the R1→R2 jump (they add ~2–3 points; R2C adds ~50).

## Three strongest empirical results

1. **F1 subtype split under Claude R1:** distinguishing_trace cert ≈ 0.94 vs equivalence_witness cert = 0.00 (same model, same track, same cohort).
2. **R2C attribution:** eq-witness jumps from 0.00 → ~0.98 only when `solver.equivalence_certificate` is allowed — matching frozen R2.
3. **C2 negative control:** no eq-witness-style collapse; unreachability_witness ≥ trace_witness for Claude — ruling out a simple universal-quantifier story.

## Three strongest controls

1. **Oracle + format ablation:** fixed gold verdict + worked examples; eq-witness remains 0.00.
2. **R2A/R2B ablation:** verify-only / repair-only tools; eq-witness remains 0.00.
3. **Verifier hostile audit:** 16/16 checks pass; hash strictness is contractual, not accidental bug.

## Main limitation

The benchmark's eq-witness contract accepts **only** hash-based witnesses (no partition/bijection alternatives). Claude's R1 failure is partly **witness-format** failure under a strict contract, even when semantic equivalence is correct (verdict accuracy 1.0, failures labeled `equivalence_hash_mismatch`).

## Abstract (proposed one sentence)

FSMReasonBench shows that frontier LLMs construct replay-valid FSM certificates for separation and reachability, yet collapse on equivalence items requiring verifier-identical minimized DFA hashes unless given solver certificate generators—indicating a sharp gap between verdict prediction and canonical symbolic synthesis, not a generic existential/universal asymmetry.

## Main figure

**Figure 1** (complexity score vs Claude R1 certificate rate): `equivalence_witness` is the isolated low outlier at complexity 9.5 with cert 0.00.

## Most dangerous reviewer attack

"The eq-witness task is unfair: you test hash memorization, not reasoning; the model knows they're equivalent (verdict 100%) so the benchmark measures an arbitrary canonical format."

## Supported rebuttal

The audit documents an independent semantic check (`are_equivalent_dfas`) **plus** a deliberate single canonical witness contract; hash mismatch is labeled witness-construction failure, not refutation. Controls show replay-style certificates succeed under the same model and prompts, and R2C succeeds by calling the **same** hash builder the verifier uses — the gap is **synthesis of the contracted witness**, not verdict ability or JSON formatting. C2 further shows exact-set and replay witnesses are not universally hard for Claude, isolating **canonical hashing** as the distinctive barrier.
"""
    (out_dir / "narrative_memo.md").write_text(memo, encoding="utf-8")


def export_tmlr_empirical_package(
    repo_root: str | Path | None = None,
    *,
    model: str = "both",
    paper_figures_dir: str | Path | None = None,
) -> dict[str, Any]:
    repo_root = Path(repo_root) if repo_root is not None else find_repo_root()
    out_dir = repo_root / PACKAGE_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    paper_dir = Path(paper_figures_dir) if paper_figures_dir is not None else repo_root.parent / "paper" / "figures"

    table1 = build_table1(repo_root)
    table2 = build_table2(repo_root)
    table3 = build_table3(repo_root)
    table4 = build_table4(repo_root)
    appendix = build_appendix_table(repo_root)
    uncertainty = compute_uncertainty(repo_root)

    write_tables(
        out_dir,
        table1=table1,
        table2=table2,
        table3=table3,
        table4=table4,
        appendix=appendix,
    )
    write_figures(
        out_dir,
        table1=table1,
        table2=table2,
        table3=table3,
        table4=table4,
    )
    complexity_figures = write_certificate_complexity_figures(
        repo_root,
        out_dir,
        model=model,
        paper_figures_dir=paper_dir,
    )
    write_uncertainty_docs(out_dir, uncertainty)
    write_readme(out_dir, repo_root)
    write_narrative_memo(out_dir)

    manifest = {
        "package_version": PACKAGE_VERSION,
        "output_dir": str(out_dir),
        "source_artifacts": SOURCE_ARTIFACTS,
        "excluded_runs": EXCLUDED_RUNS,
        "tables": {
            "table1": table1,
            "table2": table2,
            "table3": table3,
            "table4": table4,
            "appendix": appendix,
            "table1_frontier_comparison": build_table1_frontier_comparison(repo_root),
        },
        "uncertainty": _dataclass_to_json(uncertainty),
        "figures": [
            "figures/figure1_complexity_vs_success.png",
            "figures/figure1_complexity_vs_success.pdf",
            "figures/figure2_f1_ablation_slopegraph.png",
            "figures/figure2_f1_ablation_slopegraph.pdf",
            "figures/figure3_c2_ablation_slopegraph.png",
            "figures/figure3_c2_ablation_slopegraph.pdf",
            "figures/figure4_local_f1_heatmap.png",
            "figures/figure4_local_f1_heatmap.pdf",
            *complexity_figures,
        ],
    }
    (out_dir / "package_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return manifest
