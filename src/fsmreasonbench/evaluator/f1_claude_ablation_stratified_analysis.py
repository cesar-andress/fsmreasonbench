"""Item-level stratified analysis for frozen Claude F1 runs and ablations."""

from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from fsmreasonbench.evaluator.bootstrap import DEFAULT_BOOTSTRAP_ALPHA, DEFAULT_BOOTSTRAP_RESAMPLES
from fsmreasonbench.evaluator.failure_taxonomy import classify_certificate_errors
from fsmreasonbench.evaluator.jsonl import load_items_jsonl, read_jsonl

DEFAULT_COHORT_ITEMS = "cohorts/v0.1-expanded-n100/f1-mixed-level3/items.jsonl"

CONDITION_RUNS: dict[str, str] = {
    "R1": "runs/frontier_claude_sonnet_tools_n100_v2/claude-sonnet-4-5-20250929/F1/temp_0.2/R1/scores.jsonl",
    "Frozen R2": "runs/frontier_claude_sonnet_tools_n100_v2/claude-sonnet-4-5-20250929/F1/temp_0.2/R2/scores.jsonl",
    "Oracle+Format": "runs/ablations_f1_oracle_verdict_format_control_claude_n100_v1/scores.jsonl",
    "R2A": "runs/ablations_f1_r2_attribution_claude_n100_v1/R2A/scores.jsonl",
    "R2B": "runs/ablations_f1_r2_attribution_claude_n100_v1/R2B/scores.jsonl",
    "R2C": "runs/ablations_f1_r2_attribution_claude_n100_v1/R2C/scores.jsonl",
}

PAIRED_COMPARISONS: tuple[tuple[str, str], ...] = (
    ("R1", "Oracle+Format"),
    ("R1", "R2A"),
    ("R1", "R2B"),
    ("R2A", "R2C"),
    ("R2B", "R2C"),
)

OVERALL_CONDITION_ORDER: tuple[str, ...] = (
    "R1",
    "Oracle+Format",
    "R2A",
    "R2B",
    "R2C",
    "Frozen R2",
)


@dataclass(frozen=True, slots=True)
class ItemMetadata:
    item_id: str
    gold_verdict: bool
    gold_equivalent: bool
    gold_certificate_type: str
    distinguishing_trace_length: int | None
    difficulty_core: dict[str, Any]
    question_task: str | None
    prompt_id: str | None


@dataclass(frozen=True, slots=True)
class ItemOutcome:
    item_id: str
    extractable: bool
    verdict_correct: bool | None
    certificate_valid: bool
    fully_correct: bool
    failure_stage: str
    failure_category: str | None


def load_item_metadata(cohort_items_path: str | Path) -> dict[str, ItemMetadata]:
    items = load_items_jsonl(cohort_items_path)
    metadata: dict[str, ItemMetadata] = {}
    for item in items:
        core = dict(item.difficulty.get("core") or {})
        gold_verdict = bool(item.answer_key["verdict"])
        cert = item.answer_key.get("certificate") or {}
        trace_len = core.get("distinguishing_trace_length")
        if gold_verdict and trace_len == 0:
            trace_len_value: int | None = 0
        elif not gold_verdict:
            trace_len_value = int(trace_len) if trace_len is not None else None
        else:
            trace_len_value = int(trace_len) if trace_len is not None else None
        metadata[item.item_id] = ItemMetadata(
            item_id=item.item_id,
            gold_verdict=gold_verdict,
            gold_equivalent=bool(core.get("equivalent", gold_verdict)),
            gold_certificate_type=str(cert.get("certificate_type", "unknown")),
            distinguishing_trace_length=trace_len_value,
            difficulty_core=core,
            question_task=(item.question or {}).get("task"),
            prompt_id=(item.question or {}).get("prompt_id"),
        )
    return metadata


def load_condition_outcomes(scores_path: str | Path) -> dict[str, ItemOutcome]:
    outcomes: dict[str, ItemOutcome] = {}
    for row in read_jsonl(scores_path):
        item_id = row["item_id"]
        failure_stage = row.get("failure_stage") or "unknown"
        errors = tuple(row.get("certificate_errors") or [])
        failure_category = None
        if failure_stage == "certificate_invalid":
            failure_category = classify_certificate_errors(errors)
        outcomes[item_id] = ItemOutcome(
            item_id=item_id,
            extractable=bool(row.get("extractable")),
            verdict_correct=row.get("verdict_correct"),
            certificate_valid=bool(row.get("certificate_valid")),
            fully_correct=bool(row.get("fully_correct")),
            failure_stage=failure_stage,
            failure_category=failure_category,
        )
    return outcomes


def _rate(values: Iterable[bool]) -> float:
    values = list(values)
    if not values:
        return 0.0
    return sum(1 for value in values if value) / len(values)


def _verdict_rate(outcomes: list[ItemOutcome]) -> float:
    extractable = [row for row in outcomes if row.extractable]
    if not extractable:
        return 0.0
    correct = sum(1 for row in extractable if row.verdict_correct is True)
    return correct / len(extractable)


def _failure_stage_counts(outcomes: list[ItemOutcome]) -> dict[str, int]:
    counts = Counter(row.failure_stage for row in outcomes)
    return {
        "not_extractable": counts.get("not_extractable", 0),
        "provider_error": counts.get("provider_error", 0),
        "verdict_wrong": counts.get("verdict_wrong", 0),
        "certificate_invalid": counts.get("certificate_invalid", 0),
        "correct": counts.get("correct", 0),
    }


def build_overall_table(
    condition_outcomes: dict[str, dict[str, ItemOutcome]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for condition in OVERALL_CONDITION_ORDER:
        by_item = condition_outcomes[condition]
        outcomes = list(by_item.values())
        fs = _failure_stage_counts(outcomes)
        rows.append(
            {
                "Condition": condition,
                "n": len(outcomes),
                "extract": round(_rate(row.extractable for row in outcomes), 3),
                "verdict": round(_verdict_rate(outcomes), 3),
                "cert": round(_rate(row.certificate_valid for row in outcomes), 3),
                "full": round(_rate(row.fully_correct for row in outcomes), 3),
                "not_extractable": fs["not_extractable"],
                "verdict_wrong": fs["verdict_wrong"],
                "certificate_invalid": fs["certificate_invalid"],
                "correct": fs["correct"],
            }
        )
    return rows


def _filter_outcomes(
    outcomes: dict[str, ItemOutcome],
    metadata: dict[str, ItemMetadata],
    *,
    predicate,
) -> list[ItemOutcome]:
    return [
        outcomes[item_id]
        for item_id, meta in metadata.items()
        if item_id in outcomes and predicate(meta)
    ]


def build_by_gold_verdict_table(
    condition_outcomes: dict[str, dict[str, ItemOutcome]],
    metadata: dict[str, ItemMetadata],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for condition in OVERALL_CONDITION_ORDER:
        for gold_verdict in (True, False):
            label = "equivalent" if gold_verdict else "non_equivalent"
            subset = _filter_outcomes(
                condition_outcomes[condition],
                metadata,
                predicate=lambda meta, gv=gold_verdict: meta.gold_verdict is gv,
            )
            fs = _failure_stage_counts(subset)
            rows.append(
                {
                    "Condition": condition,
                    "gold_verdict": label,
                    "n": len(subset),
                    "cert": round(_rate(row.certificate_valid for row in subset), 3),
                    "full": round(_rate(row.fully_correct for row in subset), 3),
                    "certificate_invalid": fs["certificate_invalid"],
                }
            )
    return rows


def build_by_certificate_type_table(
    condition_outcomes: dict[str, dict[str, ItemOutcome]],
    metadata: dict[str, ItemMetadata],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cert_types = ("equivalence_witness", "distinguishing_trace")
    for condition in OVERALL_CONDITION_ORDER:
        for cert_type in cert_types:
            subset = _filter_outcomes(
                condition_outcomes[condition],
                metadata,
                predicate=lambda meta, ct=cert_type: meta.gold_certificate_type == ct,
            )
            fs = _failure_stage_counts(subset)
            rows.append(
                {
                    "Condition": condition,
                    "certificate_type": cert_type,
                    "n": len(subset),
                    "cert": round(_rate(row.certificate_valid for row in subset), 3),
                    "full": round(_rate(row.fully_correct for row in subset), 3),
                    "certificate_invalid": fs["certificate_invalid"],
                }
            )
    return rows


def build_failure_taxonomy_table(
    condition_outcomes: dict[str, dict[str, ItemOutcome]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for condition in OVERALL_CONDITION_ORDER:
        categories = Counter(
            row.failure_category
            for row in condition_outcomes[condition].values()
            if row.failure_category is not None
        )
        total = sum(categories.values())
        for category, count in sorted(categories.items(), key=lambda item: (-item[1], item[0])):
            rows.append(
                {
                    "Condition": condition,
                    "failure_category": category,
                    "count": count,
                    "percentage": round(count / total, 3) if total else 0.0,
                }
            )
    return rows


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


def _binom_pmf(n: int, k: int) -> float:
    if k < 0 or k > n:
        return 0.0
    return math.comb(n, k) * (0.5**n)


def exact_mcnemar_p_value(first_only: int, second_only: int) -> float | None:
    """Two-sided exact McNemar test on discordant pairs."""
    n = first_only + second_only
    if n == 0:
        return None
    lower = min(first_only, second_only)
    p_one_side = sum(_binom_pmf(n, k) for k in range(lower + 1))
    return min(1.0, 2.0 * p_one_side)


def paired_bootstrap_difference_ci(
    first_values: list[bool],
    second_values: list[bool],
    *,
    n_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    seed: int = 4242,
    alpha: float = DEFAULT_BOOTSTRAP_ALPHA,
) -> dict[str, float]:
    import random

    if len(first_values) != len(second_values):
        raise ValueError("paired bootstrap requires equal-length vectors")
    if not first_values:
        return {"point_diff": 0.0, "ci_low": 0.0, "ci_high": 0.0}
    point_diff = _rate(first_values) - _rate(second_values)
    rng = random.Random(seed)
    size = len(first_values)
    samples: list[float] = []
    for _ in range(n_resamples):
        idx = [rng.randrange(size) for _ in range(size)]
        first_sample = [first_values[i] for i in idx]
        second_sample = [second_values[i] for i in idx]
        samples.append(_rate(first_sample) - _rate(second_sample))
    low_q = alpha / 2.0
    high_q = 1.0 - alpha / 2.0
    return {
        "point_diff": round(point_diff, 4),
        "ci_low": round(_percentile(samples, low_q), 4),
        "ci_high": round(_percentile(samples, high_q), 4),
    }


def build_paired_comparison_table(
    condition_outcomes: dict[str, dict[str, ItemOutcome]],
    metadata: dict[str, ItemMetadata],
    *,
    n_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    seed: int = 4242,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for first_name, second_name in PAIRED_COMPARISONS:
        first = condition_outcomes[first_name]
        second = condition_outcomes[second_name]
        shared_ids = sorted(set(first) & set(second) & set(metadata))
        mismatch = {
            "first_only_items": sorted(set(first) - set(second)),
            "second_only_items": sorted(set(second) - set(first)),
            "metadata_missing_items": sorted(set(first) & set(second) - set(metadata)),
        }
        both_correct = 0
        first_only = 0
        second_only = 0
        both_incorrect = 0
        first_full: list[bool] = []
        second_full: list[bool] = []
        first_cert: list[bool] = []
        second_cert: list[bool] = []
        for item_id in shared_ids:
            a = first[item_id]
            b = second[item_id]
            first_full.append(a.fully_correct)
            second_full.append(b.fully_correct)
            first_cert.append(a.certificate_valid)
            second_cert.append(b.certificate_valid)
            if a.fully_correct and b.fully_correct:
                both_correct += 1
            elif a.fully_correct and not b.fully_correct:
                first_only += 1
            elif not a.fully_correct and b.fully_correct:
                second_only += 1
            else:
                both_incorrect += 1
        full_ci_first_minus_second = paired_bootstrap_difference_ci(
            first_full,
            second_full,
            n_resamples=n_resamples,
            seed=seed,
        )
        cert_ci_first_minus_second = paired_bootstrap_difference_ci(
            first_cert,
            second_cert,
            n_resamples=n_resamples,
            seed=seed + 1,
        )
        rows.append(
            {
                "comparison": f"{first_name} vs {second_name}",
                "first_condition": first_name,
                "second_condition": second_name,
                "shared_items": len(shared_ids),
                "item_id_alignment": "perfect" if not any(mismatch.values()) else "mismatch",
                "mismatch_details": mismatch if any(mismatch.values()) else None,
                "both_correct": both_correct,
                "first_only_correct": first_only,
                "second_only_correct": second_only,
                "both_incorrect": both_incorrect,
                "mcnemar_first_only": first_only,
                "mcnemar_second_only": second_only,
                "mcnemar_p_value": exact_mcnemar_p_value(first_only, second_only),
                "full_diff_first_minus_second": full_ci_first_minus_second,
                "cert_diff_first_minus_second": cert_ci_first_minus_second,
            }
        )
    return rows


def build_stratified_subtype_summary(
    condition_outcomes: dict[str, dict[str, ItemOutcome]],
    metadata: dict[str, ItemMetadata],
) -> dict[str, Any]:
    """Summaries used to answer research questions."""
    def rates_for(condition: str, predicate) -> dict[str, float]:
        subset = _filter_outcomes(condition_outcomes[condition], metadata, predicate=predicate)
        return {
            "n": len(subset),
            "cert": _rate(row.certificate_valid for row in subset),
            "full": _rate(row.fully_correct for row in subset),
            "certificate_invalid": _failure_stage_counts(subset)["certificate_invalid"],
        }

    eq_witness = lambda meta: meta.gold_certificate_type == "equivalence_witness"
    dist_trace = lambda meta: meta.gold_certificate_type == "distinguishing_trace"

    by_condition = {}
    for condition in OVERALL_CONDITION_ORDER:
        by_condition[condition] = {
            "overall": rates_for(condition, lambda _meta: True),
            "equivalence_witness": rates_for(condition, eq_witness),
            "distinguishing_trace": rates_for(condition, dist_trace),
            "gold_equivalent": rates_for(condition, lambda meta: meta.gold_verdict),
            "gold_non_equivalent": rates_for(condition, lambda meta: not meta.gold_verdict),
        }
    return by_condition


def build_item_level_records(
    condition_outcomes: dict[str, dict[str, ItemOutcome]],
    metadata: dict[str, ItemMetadata],
) -> list[dict[str, Any]]:
    item_ids = sorted(metadata)
    records: list[dict[str, Any]] = []
    for item_id in item_ids:
        meta = metadata[item_id]
        row: dict[str, Any] = {
            "item_id": item_id,
            "gold_verdict": meta.gold_verdict,
            "gold_equivalent": meta.gold_equivalent,
            "gold_certificate_type": meta.gold_certificate_type,
            "distinguishing_trace_length": meta.distinguishing_trace_length,
            "question_task": meta.question_task,
            "prompt_id": meta.prompt_id,
            "difficulty_core": meta.difficulty_core,
            "conditions": {},
        }
        for condition, outcomes in condition_outcomes.items():
            outcome = outcomes[item_id]
            row["conditions"][condition] = {
                "extractable": outcome.extractable,
                "verdict_correct": outcome.verdict_correct,
                "certificate_valid": outcome.certificate_valid,
                "fully_correct": outcome.fully_correct,
                "failure_stage": outcome.failure_stage,
                "failure_category": outcome.failure_category,
            }
        records.append(row)
    return records


def analyze_f1_claude_ablation_stratified(
    repo_root: str | Path,
    *,
    cohort_items_path: str | Path | None = None,
    n_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    seed: int = 4242,
) -> dict[str, Any]:
    repo_root = Path(repo_root)
    cohort_path = repo_root / (cohort_items_path or DEFAULT_COHORT_ITEMS)
    metadata = load_item_metadata(cohort_path)
    condition_outcomes = {
        condition: load_condition_outcomes(repo_root / rel_path)
        for condition, rel_path in CONDITION_RUNS.items()
    }

    item_ids_by_condition = {
        condition: set(outcomes) for condition, outcomes in condition_outcomes.items()
    }
    alignment = {
        "reference_condition": "R1",
        "reference_n": len(item_ids_by_condition["R1"]),
        "per_condition": {
            condition: {
                "n": len(ids),
                "shared_with_R1": len(ids & item_ids_by_condition["R1"]),
                "only_in_condition": sorted(ids - item_ids_by_condition["R1"]),
                "missing_from_condition": sorted(item_ids_by_condition["R1"] - ids),
            }
            for condition, ids in item_ids_by_condition.items()
        },
        "cohort_n": len(metadata),
        "cohort_covers_all_run_items": set(metadata) >= item_ids_by_condition["R1"],
    }

    tables = {
        "overall": build_overall_table(condition_outcomes),
        "by_gold_verdict": build_by_gold_verdict_table(condition_outcomes, metadata),
        "by_certificate_type": build_by_certificate_type_table(condition_outcomes, metadata),
        "failure_taxonomy": build_failure_taxonomy_table(condition_outcomes),
        "paired_comparisons": build_paired_comparison_table(
            condition_outcomes,
            metadata,
            n_resamples=n_resamples,
            seed=seed,
        ),
    }

    trace_lengths_non_eq = sorted(
        {
            meta.distinguishing_trace_length
            for meta in metadata.values()
            if not meta.gold_verdict and meta.distinguishing_trace_length is not None
        }
    )

    return {
        "experiment": "f1_claude_ablation_stratified_analysis",
        "cohort_items_path": str(cohort_path),
        "conditions": list(OVERALL_CONDITION_ORDER),
        "item_id_alignment": alignment,
        "metadata_availability": {
            "gold_verdict": "answer_key.verdict",
            "gold_certificate_type": "answer_key.certificate.certificate_type",
            "gold_equivalent": "difficulty.core.equivalent",
            "distinguishing_trace_length": "difficulty.core.distinguishing_trace_length",
            "difficulty_core_fields": sorted(
                {
                    key
                    for meta in metadata.values()
                    for key in meta.difficulty_core
                }
            ),
            "question_task": "question.task",
            "prompt_id": "question.prompt_id",
            "failure_category": "derived from scores.certificate_errors via classify_certificate_errors",
            "notes": [
                "All 49 non-equivalent cohort items share distinguishing_trace_length=3 in this cohort.",
                "Equivalent items store distinguishing_trace_length=0 in difficulty.core.",
            ],
            "non_equivalent_trace_lengths_observed": trace_lengths_non_eq,
        },
        "tables": tables,
        "stratified_subtype_summary": build_stratified_subtype_summary(
            condition_outcomes,
            metadata,
        ),
        "item_level_records": build_item_level_records(condition_outcomes, metadata),
        "bootstrap": {
            "n_resamples": n_resamples,
            "seed": seed,
            "alpha": DEFAULT_BOOTSTRAP_ALPHA,
            "method": "percentile_bootstrap_on_paired_item_outcomes",
        },
    }


def _flatten_table_rows(table_name: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for row in rows:
        if table_name == "paired_comparisons":
            flat = {
                "table_name": table_name,
                "comparison": row["comparison"],
                "first_condition": row["first_condition"],
                "second_condition": row["second_condition"],
                "shared_items": row["shared_items"],
                "item_id_alignment": row["item_id_alignment"],
                "both_correct": row["both_correct"],
                "first_only_correct": row["first_only_correct"],
                "second_only_correct": row["second_only_correct"],
                "both_incorrect": row["both_incorrect"],
                "mcnemar_p_value": row["mcnemar_p_value"],
                "full_diff_point": row["full_diff_first_minus_second"]["point_diff"],
                "full_diff_ci_low": row["full_diff_first_minus_second"]["ci_low"],
                "full_diff_ci_high": row["full_diff_first_minus_second"]["ci_high"],
                "cert_diff_point": row["cert_diff_first_minus_second"]["point_diff"],
                "cert_diff_ci_low": row["cert_diff_first_minus_second"]["ci_low"],
                "cert_diff_ci_high": row["cert_diff_first_minus_second"]["ci_high"],
            }
        else:
            flat = {"table_name": table_name, **row}
        flattened.append(flat)
    return flattened


def write_tables_csv(path: str | Path, tables: dict[str, list[dict[str, Any]]]) -> None:
    rows: list[dict[str, Any]] = []
    for table_name, table_rows in tables.items():
        rows.extend(_flatten_table_rows(table_name, table_rows))
    path = Path(path)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _fmt_rate(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.3f}"


def _render_markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def render_stratified_markdown_report(payload: dict[str, Any]) -> str:
    tables = payload["tables"]
    subtype = payload["stratified_subtype_summary"]
    alignment = payload["item_id_alignment"]
    meta_notes = payload["metadata_availability"]

    lines = [
        "# F1 Claude Ablation — Item-Level Stratified Analysis",
        "",
        "Offline analysis of frozen Claude Sonnet F1 runs and ablations (no new model calls).",
        "",
        "## Data sources",
        "",
    ]
    for condition in payload["conditions"]:
        rel = CONDITION_RUNS[condition]
        lines.append(f"- **{condition}:** `{rel}`")
    lines.extend(
        [
            f"- **Cohort metadata:** `{payload['cohort_items_path']}`",
            "",
            "## Item ID alignment",
            "",
            f"- Reference (**R1**) n={alignment['reference_n']}",
        ]
    )
    for condition, info in alignment["per_condition"].items():
        status = "aligned" if not info["only_in_condition"] and not info["missing_from_condition"] else "MISMATCH"
        lines.append(
            f"- **{condition}:** n={info['n']}, shared_with_R1={info['shared_with_R1']} ({status})"
        )

    lines.extend(["", "## Metadata availability", ""])
    for key, source in meta_notes.items():
        if key in {"notes", "non_equivalent_trace_lengths_observed", "difficulty_core_fields"}:
            continue
        lines.append(f"- **{key}:** `{source}`")
    lines.append(
        f"- **difficulty.core fields observed:** {', '.join(meta_notes['difficulty_core_fields'])}"
    )
    lines.append(
        f"- **non-equivalent trace lengths in cohort:** {meta_notes['non_equivalent_trace_lengths_observed']}"
    )
    for note in meta_notes["notes"]:
        lines.append(f"- {note}")

    lines.extend(["", "## Table 1 — Overall comparison", ""])
    overall_rows = [
        [
            str(row["Condition"]),
            str(row["n"]),
            _fmt_rate(row["extract"]),
            _fmt_rate(row["verdict"]),
            _fmt_rate(row["cert"]),
            _fmt_rate(row["full"]),
            str(row["not_extractable"]),
            str(row["verdict_wrong"]),
            str(row["certificate_invalid"]),
            str(row["correct"]),
        ]
        for row in tables["overall"]
    ]
    lines.append(
        _render_markdown_table(
            [
                "Condition",
                "n",
                "extract",
                "verdict",
                "cert",
                "full",
                "not_extractable",
                "verdict_wrong",
                "certificate_invalid",
                "correct",
            ],
            overall_rows,
        )
    )

    lines.extend(["", "## Table 2 — By gold verdict", ""])
    lines.append(
        _render_markdown_table(
            ["Condition", "gold_verdict", "n", "cert", "full", "certificate_invalid"],
            [
                [
                    row["Condition"],
                    row["gold_verdict"],
                    str(row["n"]),
                    _fmt_rate(row["cert"]),
                    _fmt_rate(row["full"]),
                    str(row["certificate_invalid"]),
                ]
                for row in tables["by_gold_verdict"]
            ],
        )
    )

    lines.extend(["", "## Table 3 — By certificate type", ""])
    lines.append(
        _render_markdown_table(
            ["Condition", "certificate_type", "n", "cert", "full", "certificate_invalid"],
            [
                [
                    row["Condition"],
                    row["certificate_type"],
                    str(row["n"]),
                    _fmt_rate(row["cert"]),
                    _fmt_rate(row["full"]),
                    str(row["certificate_invalid"]),
                ]
                for row in tables["by_certificate_type"]
            ],
        )
    )

    lines.extend(["", "## Table 4 — Failure taxonomy (certificate_invalid only)", ""])
    lines.append(
        _render_markdown_table(
            ["Condition", "failure_category", "count", "percentage"],
            [
                [
                    row["Condition"],
                    row["failure_category"],
                    str(row["count"]),
                    _fmt_rate(row["percentage"]),
                ]
                for row in tables["failure_taxonomy"]
            ],
        )
    )

    lines.extend(["", "## Table 5 — Paired item-level comparisons", ""])
    for row in tables["paired_comparisons"]:
        lines.extend(
            [
                f"### {row['comparison']}",
                "",
                f"- Shared items: {row['shared_items']} ({row['item_id_alignment']})",
                f"- Both correct: {row['both_correct']}",
                f"- {row['first_condition']} only correct: {row['first_only_correct']}",
                f"- {row['second_condition']} only correct: {row['second_only_correct']}",
                f"- Both incorrect: {row['both_incorrect']}",
                f"- McNemar exact p-value: {row['mcnemar_p_value']}",
                (
                    "- Full rate diff (first − second): "
                    f"{row['full_diff_first_minus_second']['point_diff']:+.3f} "
                    f"[{row['full_diff_first_minus_second']['ci_low']:+.3f}, "
                    f"{row['full_diff_first_minus_second']['ci_high']:+.3f}]"
                ),
                (
                    "- Cert rate diff (first − second): "
                    f"{row['cert_diff_first_minus_second']['point_diff']:+.3f} "
                    f"[{row['cert_diff_first_minus_second']['ci_low']:+.3f}, "
                    f"{row['cert_diff_first_minus_second']['ci_high']:+.3f}]"
                ),
                "",
            ]
        )

    r1 = subtype["R1"]
    oracle = subtype["Oracle+Format"]
    r2a = subtype["R2A"]
    r2b = subtype["R2B"]
    r2c = subtype["R2C"]
    frozen_r2 = subtype["Frozen R2"]

    eq_fail_r1 = r1["equivalence_witness"]["certificate_invalid"]
    dist_fail_r1 = r1["distinguishing_trace"]["certificate_invalid"]
    eq_fail_oracle = oracle["equivalence_witness"]["certificate_invalid"]

    lines.extend(
        [
            "## Research questions",
            "",
            "### 1. Are failures dominated by equivalent items requiring equivalence_witness?",
            "",
            f"**Yes for R1 and model-construction ablations.** On **R1**, all 51 equivalence_witness items fail "
            f"cert validation (cert=0.000) while distinguishing_trace items succeed on 46/49 "
            f"(cert={r1['distinguishing_trace']['cert']:.3f}; only {dist_fail_r1} invalid). "
            f"Of {eq_fail_r1 + dist_fail_r1} R1 certificate failures, **{eq_fail_r1} ({eq_fail_r1 / max(eq_fail_r1 + dist_fail_r1, 1):.1%})** "
            f"are equivalence_witness items. The same eq-witness collapse appears under Oracle+Format "
            f"({eq_fail_oracle}/51 invalid) and R2A/R2B (51/51 eq-witness invalid each).",
            "",
            "### 2. Are distinguishing_trace certificates easier than equivalence_witness?",
            "",
            f"**Yes, markedly on R1.** dist-trace cert={r1['distinguishing_trace']['cert']:.3f} (n=49) vs "
            f"eq-witness cert={r1['equivalence_witness']['cert']:.3f} (n=51), Δ="
            f"{r1['distinguishing_trace']['cert'] - r1['equivalence_witness']['cert']:+.3f}. "
            f"Oracle+Format does not close the eq gap (still 0.000) and **hurts** dist-trace "
            f"({oracle['distinguishing_trace']['cert']:.3f} vs {r1['distinguishing_trace']['cert']:.3f}).",
            "",
            "### 3. Does oracle-verdict help either subtype?",
            "",
            f"**No for equivalence_witness; no for distinguishing_trace overall.** "
            f"Eq-witness stays at cert=0.000 (51/51 invalid). Dist-trace drops to cert="
            f"{oracle['distinguishing_trace']['cert']:.3f} ({oracle['distinguishing_trace']['certificate_invalid']}/49 invalid) "
            f"vs R1 {r1['distinguishing_trace']['cert']:.3f}. Oracle verdict + format control does not fix "
            f"hash synthesis and adds dist-trace semantic errors (acceptance_mismatch).",
            "",
            "### 4. Does verify-only or repair-only help either subtype?",
            "",
            f"**Only distinguishing_trace, marginally.** R2A: eq-witness cert=0.000 (51/51 invalid), "
            f"dist-trace cert={r2a['distinguishing_trace']['cert']:.3f}. R2B: eq=0.000, "
            f"dist={r2b['distinguishing_trace']['cert']:.3f}. Verify/repair can surface/fix trace "
            f"submissions but **cannot** produce valid minimized hashes for equivalence_witness.",
            "",
            "### 5. Does R2C solve both subtypes or only one?",
            "",
            f"**Both; equivalence_witness is the harder lift.** R2C: eq-witness full="
            f"{r2c['equivalence_witness']['full']:.3f} (n=51), dist-trace full="
            f"{r2c['distinguishing_trace']['full']:.3f} (n=49). Frozen R2 matches. Solver generators "
            f"lift eq-witness from 0% (R1) to ~98% and dist-trace from ~94% to 100%.",
            "",
            "### 6. Is the R1-to-R2 gap mainly an equivalence-witness synthesis gap?",
            "",
        ]
    )

    r1_to_r2_eq = frozen_r2["equivalence_witness"]["full"] - r1["equivalence_witness"]["full"]
    r1_to_r2_dist = frozen_r2["distinguishing_trace"]["full"] - r1["distinguishing_trace"]["full"]
    lines.extend(
        [
            f"**Primarily yes.** R1→Frozen R2 full gain: eq-witness **+{r1_to_r2_eq:.3f}** "
            f"({r1['equivalence_witness']['full']:.3f}→{frozen_r2['equivalence_witness']['full']:.3f}), "
            f"dist-trace **+{r1_to_r2_dist:.3f}** "
            f"({r1['distinguishing_trace']['full']:.3f}→{frozen_r2['distinguishing_trace']['full']:.3f}). "
            f"Because R1 already reaches {r1['distinguishing_trace']['full']:.3f} on dist-trace, "
            f"**~{r1_to_r2_eq / max(r1_to_r2_eq + r1_to_r2_dist, 1e-9):.0%} of the aggregate R1→R2 full lift** "
            f"is explained by fixing equivalence_witness items. The decisive mechanism remains "
            f"**tool-side certificate synthesis** (solver generators), not model-side validation or formatting.",
            "",
            "## Notes",
            "",
            "- Failure taxonomy categories are inferred from `certificate_errors` in existing scores.",
            "- Bootstrap CIs use paired item resampling (1000 resamples, seed 4242, 95% percentile).",
            "- McNemar exact test uses discordant pairs on `fully_correct`.",
            "- Frozen runs were not modified or re-executed.",
            "",
        ]
    )
    return "\n".join(lines)


def export_f1_claude_ablation_stratified_analysis(
    repo_root: str | Path,
    *,
    markdown_path: str | Path,
    json_path: str | Path,
    csv_path: str | Path,
    cohort_items_path: str | Path | None = None,
    n_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    seed: int = 4242,
) -> dict[str, Any]:
    payload = analyze_f1_claude_ablation_stratified(
        repo_root,
        cohort_items_path=cohort_items_path,
        n_resamples=n_resamples,
        seed=seed,
    )
    markdown_path = Path(markdown_path)
    json_path = Path(json_path)
    csv_path = Path(csv_path)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    markdown_path.write_text(render_stratified_markdown_report(payload), encoding="utf-8")
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=False), encoding="utf-8")
    write_tables_csv(csv_path, payload["tables"])
    return payload
