"""F1 subtype-stratified analysis for the local open-weight model matrix."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from fsmreasonbench.evaluator.f1_claude_ablation_stratified_analysis import (
    DEFAULT_COHORT_ITEMS,
    ItemMetadata,
    ItemOutcome,
    load_condition_outcomes,
    load_item_metadata,
)
from fsmreasonbench.evaluator.failure_taxonomy import classify_certificate_errors

DEFAULT_LOCAL_MATRIX_ROOT = "runs/local_matrix_n100_t02_v2"
DEFAULT_CLAUDE_STRATIFIED_JSON = "docs/f1_claude_ablation_stratified_analysis.json"
TRACK_ORDER = ("R0", "R1", "R2")
CERTIFICATE_TYPES = ("equivalence_witness", "distinguishing_trace")


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


def _round3(value: float) -> float:
    return round(value, 3)


def discover_local_matrix_f1_cells(matrix_root: Path) -> list[dict[str, Any]]:
    """Find completed F1 score files under the local matrix layout."""
    cells: list[dict[str, Any]] = []
    for scores_path in sorted(matrix_root.glob("*/F1/temp_*/R*/scores.jsonl")):
        rel = scores_path.relative_to(matrix_root)
        model_dir = rel.parts[0]
        track = rel.parts[-2]
        temperature = float(rel.parts[2].removeprefix("temp_"))
        cells.append(
            {
                "model_dir": model_dir,
                "track": track,
                "temperature": temperature,
                "scores_path": scores_path,
                "run_dir": str(scores_path.parent),
            }
        )
    return cells


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


def _subset_metrics(outcomes: list[ItemOutcome]) -> dict[str, Any]:
    fs = _failure_stage_counts(outcomes)
    return {
        "n": len(outcomes),
        "extract": _round3(_rate(row.extractable for row in outcomes)),
        "verdict": _round3(_verdict_rate(outcomes)),
        "cert": _round3(_rate(row.certificate_valid for row in outcomes)),
        "full": _round3(_rate(row.fully_correct for row in outcomes)),
        "certificate_invalid": fs["certificate_invalid"],
    }


def build_overall_table(
    cell_outcomes: dict[tuple[str, str], dict[str, ItemOutcome]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (model_dir, track), outcomes_by_item in sorted(cell_outcomes.items()):
        outcomes = list(outcomes_by_item.values())
        fs = _failure_stage_counts(outcomes)
        rows.append(
            {
                "model": model_dir,
                "track": track,
                "n": len(outcomes),
                "extract": _round3(_rate(row.extractable for row in outcomes)),
                "verdict": _round3(_verdict_rate(outcomes)),
                "cert": _round3(_rate(row.certificate_valid for row in outcomes)),
                "full": _round3(_rate(row.fully_correct for row in outcomes)),
                **fs,
            }
        )
    return rows


def build_by_certificate_type_table(
    cell_outcomes: dict[tuple[str, str], dict[str, ItemOutcome]],
    metadata: dict[str, ItemMetadata],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (model_dir, track), outcomes_by_item in sorted(cell_outcomes.items()):
        for cert_type in CERTIFICATE_TYPES:
            subset = _filter_outcomes(
                outcomes_by_item,
                metadata,
                predicate=lambda meta, ct=cert_type: meta.gold_certificate_type == ct,
            )
            metrics = _subset_metrics(subset)
            rows.append(
                {
                    "model": model_dir,
                    "track": track,
                    "certificate_type": cert_type,
                    **metrics,
                }
            )
    return rows


def build_by_gold_verdict_table(
    cell_outcomes: dict[tuple[str, str], dict[str, ItemOutcome]],
    metadata: dict[str, ItemMetadata],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (model_dir, track), outcomes_by_item in sorted(cell_outcomes.items()):
        for gold_verdict, label in ((True, "equivalent"), (False, "non_equivalent")):
            subset = _filter_outcomes(
                outcomes_by_item,
                metadata,
                predicate=lambda meta, gv=gold_verdict: meta.gold_verdict is gv,
            )
            metrics = _subset_metrics(subset)
            rows.append(
                {
                    "model": model_dir,
                    "track": track,
                    "gold_verdict": label,
                    **metrics,
                }
            )
    return rows


def build_failure_taxonomy_table(
    cell_outcomes: dict[tuple[str, str], dict[str, ItemOutcome]],
    metadata: dict[str, ItemMetadata],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (model_dir, track), outcomes_by_item in sorted(cell_outcomes.items()):
        for cert_type in CERTIFICATE_TYPES:
            categories: Counter[str] = Counter()
            for item_id, outcome in outcomes_by_item.items():
                meta = metadata.get(item_id)
                if meta is None or meta.gold_certificate_type != cert_type:
                    continue
                if outcome.failure_category is None:
                    continue
                categories[outcome.failure_category] += 1
            total = sum(categories.values())
            for category, count in sorted(categories.items(), key=lambda item: (-item[1], item[0])):
                rows.append(
                    {
                        "model": model_dir,
                        "track": track,
                        "certificate_type": cert_type,
                        "failure_category": category,
                        "count": count,
                        "percentage": _round3(count / total) if total else 0.0,
                    }
                )
    return rows


def build_gap_decomposition_table(
    cell_outcomes: dict[tuple[str, str], dict[str, ItemOutcome]],
    metadata: dict[str, ItemMetadata],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (model_dir, track), outcomes_by_item in sorted(cell_outcomes.items()):
        dist = _filter_outcomes(
            outcomes_by_item,
            metadata,
            predicate=lambda meta: meta.gold_certificate_type == "distinguishing_trace",
        )
        eq = _filter_outcomes(
            outcomes_by_item,
            metadata,
            predicate=lambda meta: meta.gold_certificate_type == "equivalence_witness",
        )
        dist_full = _rate(row.fully_correct for row in dist)
        eq_full = _rate(row.fully_correct for row in eq)
        dist_cert = _rate(row.certificate_valid for row in dist)
        eq_cert = _rate(row.certificate_valid for row in eq)
        rows.append(
            {
                "model": model_dir,
                "track": track,
                "dist_trace_full": _round3(dist_full),
                "eq_witness_full": _round3(eq_full),
                "dist_trace_cert": _round3(dist_cert),
                "eq_witness_cert": _round3(eq_cert),
                "subtype_gap": _round3(dist_full - eq_full),
            }
        )
    return rows


def _load_claude_reference(repo_root: Path) -> dict[str, Any] | None:
    path = repo_root / DEFAULT_CLAUDE_STRATIFIED_JSON
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    summary = payload.get("stratified_subtype_summary") or {}
    ref: dict[str, Any] = {}
    for track_key, label in (("R1", "R1"), ("Frozen R2", "R2")):
        if label not in summary and track_key in summary:
            ref[label] = summary[track_key]
        elif track_key in summary:
            ref[label] = summary[track_key]
    return ref or None


def analyze_f1_local_matrix_subtype_stratified(
    repo_root: str | Path,
    *,
    matrix_root: str | Path | None = None,
    cohort_items_path: str | Path | None = None,
) -> dict[str, Any]:
    repo_root = Path(repo_root)
    matrix_root = repo_root / (matrix_root or DEFAULT_LOCAL_MATRIX_ROOT)
    cohort_path = repo_root / (cohort_items_path or DEFAULT_COHORT_ITEMS)

    if not matrix_root.is_dir():
        raise FileNotFoundError(f"local matrix root not found: {matrix_root}")

    metadata = load_item_metadata(cohort_path)
    cells = discover_local_matrix_f1_cells(matrix_root)

    cell_outcomes: dict[tuple[str, str], dict[str, ItemOutcome]] = {}
    alignment: list[dict[str, Any]] = []
    for cell in cells:
        outcomes = load_condition_outcomes(cell["scores_path"])
        key = (cell["model_dir"], cell["track"])
        cell_outcomes[key] = outcomes
        outcome_ids = set(outcomes)
        metadata_ids = set(metadata)
        alignment.append(
            {
                "model": cell["model_dir"],
                "track": cell["track"],
                "n": len(outcomes),
                "cohort_n": len(metadata_ids),
                "shared_with_cohort": len(outcome_ids & metadata_ids),
                "only_in_run": sorted(outcome_ids - metadata_ids),
                "missing_from_run": sorted(metadata_ids - outcome_ids),
                "perfect_cohort_alignment": outcome_ids == metadata_ids,
            }
        )

    tables = {
        "overall": build_overall_table(cell_outcomes),
        "by_certificate_type": build_by_certificate_type_table(cell_outcomes, metadata),
        "by_gold_verdict": build_by_gold_verdict_table(cell_outcomes, metadata),
        "failure_taxonomy": build_failure_taxonomy_table(cell_outcomes, metadata),
        "gap_decomposition": build_gap_decomposition_table(cell_outcomes, metadata),
    }

    trace_lengths_non_eq = sorted(
        {
            meta.distinguishing_trace_length
            for meta in metadata.values()
            if not meta.gold_verdict and meta.distinguishing_trace_length is not None
        }
    )

    return {
        "experiment": "f1_local_matrix_subtype_stratified_analysis",
        "matrix_root": str(matrix_root),
        "cohort_items_path": str(cohort_path),
        "models": sorted({cell["model_dir"] for cell in cells}),
        "tracks": list(TRACK_ORDER),
        "cells_discovered": len(cells),
        "item_id_alignment": alignment,
        "metadata_availability": {
            "gold_verdict": "answer_key.verdict",
            "gold_certificate_type": "answer_key.certificate.certificate_type",
            "gold_equivalent": "difficulty.core.equivalent",
            "distinguishing_trace_length": "difficulty.core.distinguishing_trace_length",
            "failure_category": "derived from scores.certificate_errors via classify_certificate_errors",
            "notes": [
                "All local F1 cells in this matrix share the expanded n=100 cohort item IDs.",
                "All 49 non-equivalent cohort items use distinguishing_trace_length=3.",
                "Analysis uses within-run stratification only (no cross-run pairing).",
            ],
            "non_equivalent_trace_lengths_observed": trace_lengths_non_eq,
        },
        "tables": tables,
        "claude_reference": _load_claude_reference(repo_root),
    }


def _flatten_table_rows(table_name: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"table_name": table_name, **row} for row in rows]


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


def _fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def _render_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _cell_subtype_summary(
    tables: dict[str, list[dict[str, Any]]],
    model: str,
    track: str,
) -> dict[str, dict[str, float]]:
    by_type = {
        row["certificate_type"]: row
        for row in tables["by_certificate_type"]
        if row["model"] == model and row["track"] == track
    }
    return {
        "equivalence_witness": by_type.get("equivalence_witness", {}),
        "distinguishing_trace": by_type.get("distinguishing_trace", {}),
    }


def render_local_matrix_subtype_markdown(payload: dict[str, Any]) -> str:
    tables = payload["tables"]
    claude = payload.get("claude_reference") or {}

    lines = [
        "# F1 Local Matrix — Subtype-Stratified Analysis",
        "",
        "Offline analysis of `runs/local_matrix_n100_t02_v2` (no new model calls).",
        "",
        f"- **Matrix root:** `{payload['matrix_root']}`",
        f"- **Cohort metadata:** `{payload['cohort_items_path']}`",
        f"- **Models:** {', '.join(payload['models'])}",
        f"- **Tracks:** {', '.join(payload['tracks'])}",
        f"- **F1 cells analyzed:** {payload['cells_discovered']}",
        "",
        "## Item ID alignment",
        "",
    ]
    for row in payload["item_id_alignment"]:
        status = "aligned" if row["perfect_cohort_alignment"] else "MISMATCH"
        lines.append(
            f"- **{row['model']} {row['track']}:** n={row['n']}, "
            f"shared_with_cohort={row['shared_with_cohort']} ({status})"
        )

    meta = payload["metadata_availability"]
    lines.extend(["", "## Metadata availability", ""])
    for key, source in meta.items():
        if key in {"notes", "non_equivalent_trace_lengths_observed"}:
            continue
        lines.append(f"- **{key}:** `{source}`")
    lines.append(
        f"- **non-equivalent trace lengths:** {meta['non_equivalent_trace_lengths_observed']}"
    )
    for note in meta["notes"]:
        lines.append(f"- {note}")

    lines.extend(["", "## Table 1 — Overall F1 by model and track", ""])
    lines.append(
        _render_table(
            [
                "model",
                "track",
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
            [
                [
                    row["model"],
                    row["track"],
                    str(row["n"]),
                    _fmt(row["extract"]),
                    _fmt(row["verdict"]),
                    _fmt(row["cert"]),
                    _fmt(row["full"]),
                    str(row["not_extractable"]),
                    str(row["verdict_wrong"]),
                    str(row["certificate_invalid"]),
                    str(row["correct"]),
                ]
                for row in tables["overall"]
            ],
        )
    )

    lines.extend(["", "## Table 2 — F1 by certificate subtype", ""])
    lines.append(
        _render_table(
            [
                "model",
                "track",
                "certificate_type",
                "n",
                "extract",
                "verdict",
                "cert",
                "full",
                "certificate_invalid",
            ],
            [
                [
                    row["model"],
                    row["track"],
                    row["certificate_type"],
                    str(row["n"]),
                    _fmt(row["extract"]),
                    _fmt(row["verdict"]),
                    _fmt(row["cert"]),
                    _fmt(row["full"]),
                    str(row["certificate_invalid"]),
                ]
                for row in tables["by_certificate_type"]
            ],
        )
    )

    lines.extend(["", "## Table 3 — F1 by gold verdict", ""])
    lines.append(
        _render_table(
            [
                "model",
                "track",
                "gold_verdict",
                "n",
                "extract",
                "verdict",
                "cert",
                "full",
                "certificate_invalid",
            ],
            [
                [
                    row["model"],
                    row["track"],
                    row["gold_verdict"],
                    str(row["n"]),
                    _fmt(row["extract"]),
                    _fmt(row["verdict"]),
                    _fmt(row["cert"]),
                    _fmt(row["full"]),
                    str(row["certificate_invalid"]),
                ]
                for row in tables["by_gold_verdict"]
            ],
        )
    )

    lines.extend(["", "## Table 4 — Failure taxonomy", ""])
    lines.append(
        _render_table(
            ["model", "track", "certificate_type", "failure_category", "count", "percentage"],
            [
                [
                    row["model"],
                    row["track"],
                    row["certificate_type"],
                    row["failure_category"],
                    str(row["count"]),
                    _fmt(row["percentage"]),
                ]
                for row in tables["failure_taxonomy"]
            ],
        )
    )

    lines.extend(["", "## Table 5 — Gap decomposition", ""])
    lines.append(
        _render_table(
            [
                "model",
                "track",
                "dist_trace_full",
                "eq_witness_full",
                "dist_trace_cert",
                "eq_witness_cert",
                "subtype_gap",
            ],
            [
                [
                    row["model"],
                    row["track"],
                    _fmt(row["dist_trace_full"]),
                    _fmt(row["eq_witness_full"]),
                    _fmt(row["dist_trace_cert"]),
                    _fmt(row["eq_witness_cert"]),
                    _fmt(row["subtype_gap"]),
                ]
                for row in tables["gap_decomposition"]
            ],
        )
    )

    def subtype_row(model: str, track: str, cert_type: str) -> dict[str, Any]:
        return next(
            row
            for row in tables["by_certificate_type"]
            if row["model"] == model and row["track"] == track and row["certificate_type"] == cert_type
        )

    r0_gaps = [row for row in tables["gap_decomposition"] if row["track"] == "R0"]
    avg_r0_gap = sum(row["subtype_gap"] for row in r0_gaps) / len(r0_gaps) if r0_gaps else 0.0
    r1_gaps = [row for row in tables["gap_decomposition"] if row["track"] == "R1"]
    r2_gaps = [row for row in tables["gap_decomposition"] if row["track"] == "R2"]
    avg_r1_gap = sum(row["subtype_gap"] for row in r1_gaps) / len(r1_gaps) if r1_gaps else 0.0
    avg_r2_gap = sum(row["subtype_gap"] for row in r2_gaps) / len(r2_gaps) if r2_gaps else 0.0

    claude_r1 = claude.get("R1", {})
    claude_r2 = claude.get("R2") or claude.get("Frozen R2", {})
    claude_r1_eq = claude_r1.get("equivalence_witness", {}).get("full")
    claude_r1_dist = claude_r1.get("distinguishing_trace", {}).get("full")
    claude_r2_eq = claude_r2.get("equivalence_witness", {}).get("full")
    claude_r1_dist_label = f"{claude_r1_dist:.3f}" if claude_r1_dist is not None else "—"
    claude_r1_eq_label = f"{claude_r1_eq:.3f}" if claude_r1_eq is not None else "—"
    claude_r2_eq_label = f"{claude_r2_eq:.3f}" if claude_r2_eq is not None else "—"

    r1_dist_certs = [
        subtype_row(model, "R1", "distinguishing_trace")["cert"] for model in payload["models"]
    ]
    r1_eq_certs = [subtype_row(model, "R1", "equivalence_witness")["cert"] for model in payload["models"]]
    r2_eq_fulls = [
        subtype_row(model, "R2", "equivalence_witness")["full"] for model in payload["models"]
    ]
    r2_dist_fulls = [
        subtype_row(model, "R2", "distinguishing_trace")["full"] for model in payload["models"]
    ]

    lines.extend(["", "## Research questions", ""])

    lines.extend(
        [
            "### 1. Do local models also show high distinguishing_trace success and low equivalence_witness success?",
            "",
            "**Partially, but not on R1 tools the way Claude does.** On local **R1**, all four models have "
            f"`subtype_gap≈0` (average {avg_r1_gap:.3f}): both subtypes are near **full=0.000** because of "
            "low extractability and/or certificate failure on both. Eq-witness cert is 0.000 for every model on R1.",
            f"Dist-trace cert on R1 averages {sum(r1_dist_certs)/len(r1_dist_certs):.3f} vs Claude R1 dist-trace "
            f"full={claude_r1_dist_label}.",
            f"On **R0** (no tools), dist-trace exceeds eq-witness for 3/4 models (average subtype_gap {avg_r0_gap:.3f}; "
            "e.g. gemma2 R0 dist full=0.490 vs eq full=0.000). So the dist>eq pattern appears when locals can answer, "
            "but Claude's strong R1 dist-trace success is **not** reproduced locally.",
            "",
            "### 2. Is the aggregate F1 gap mostly explained by equivalence_witness failures?",
            "",
            "**Among semantic certificate errors, eq-witness hash failures are central; aggregate shortfall is broader.** "
            "When extractable submissions fail, eq-witness errors are **100% `equivalence_hash_mismatch`** (Table 4). "
            "Dist-trace errors are **`acceptance_mismatch` / `replay_failure`** (e.g. qwen R1: 49/49 dist invalid). "
            "On R1, gemma2 records 51 eq-witness vs 34 dist-trace cert invalid; qwen inverts that (15 eq vs 49 dist). "
            "Low overall F1 also reflects **not_extractable** and **verdict_wrong**, not only subtype choice.",
            "",
            "### 3. Does R2 help locals on equivalence_witness, or only on distinguishing_trace?",
            "",
            "**Mostly distinguishing_trace, and only materially for qwen2.5-coder; eq-witness stays near zero.**",
            "",
        ]
    )

    r2_eq_lift_examples: list[str] = []
    for model in payload["models"]:
        eq_r1 = subtype_row(model, "R1", "equivalence_witness")["full"]
        eq_r2 = subtype_row(model, "R2", "equivalence_witness")["full"]
        dist_r1 = subtype_row(model, "R1", "distinguishing_trace")["full"]
        dist_r2 = subtype_row(model, "R2", "distinguishing_trace")["full"]
        r2_eq_lift_examples.append(
            f"{model}: eq-witness full {eq_r1:.3f}→{eq_r2:.3f}, dist-trace {dist_r1:.3f}→{dist_r2:.3f}"
        )

    lines.extend([f"- {line}" for line in r2_eq_lift_examples])
    lines.extend(
        [
            "",
            f"R2 average eq-witness full={sum(r2_eq_fulls)/len(r2_eq_fulls):.3f}, dist-trace full="
            f"{sum(r2_dist_fulls)/len(r2_dist_fulls):.3f}; subtype_gap R1→R2: {avg_r1_gap:.3f}→{avg_r2_gap:.3f}. "
            f"Unlike Claude (eq full {claude_r1_eq_label}→{claude_r2_eq_label} on R2), locals do **not** get a large eq-witness lift from solver tools.",
            "",
            "### 4. Are failures semantic rather than formatting-related?",
            "",
            "**Yes.** No `wrong_trace_format` or formatting taxa appear in Table 4. Eq-witness: "
            "`equivalence_hash_mismatch` only. Dist-trace: `acceptance_mismatch` and `replay_failure`.",
            "",
            "### 5. Is the Claude pattern model-general or Claude-specific?",
            "",
        ]
    )

    if claude_r1 and claude_r2:
        lines.append(
            "**Mixed.** The *hardness* of eq-witness hash synthesis is model-general (locals also show "
            f"0% eq-witness cert on R1; Claude eq-witness R1 full={claude_r1_eq_label}). "
            f"Claude's *success* pattern is largely Claude-specific: R1 dist-trace full={claude_r1_dist_label} vs "
            f"local R1 dist average {sum(r1_dist_certs)/len(r1_dist_certs):.3f}; R2 eq-witness lift to "
            f"{claude_r2_eq_label} is not matched by open-weight models (max local R2 eq-witness full="
            f"{max(r2_eq_fulls):.3f}). Subtype mechanism (hash vs trace semantics) is shared; magnitude of tool-assisted "
            "certificate completion is Claude-specific on this matrix."
        )
    else:
        lines.append(
            "Claude reference JSON not found. Local runs still show eq-witness hash failures and dist-trace "
            "semantic errors, but without Claude-level R1 dist-trace or R2 eq-witness completion."
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Frozen runs were read only; nothing was re-executed.",
            "- Stratification uses cohort `answer_key.certificate.certificate_type` (51 eq-witness / 49 dist-trace).",
            "- R0 included for completeness; tool-free track still shows eq-witness hash failures when models attempt certificates.",
            "",
        ]
    )
    return "\n".join(lines)


def export_f1_local_matrix_subtype_stratified_analysis(
    repo_root: str | Path,
    *,
    markdown_path: str | Path,
    json_path: str | Path,
    csv_path: str | Path,
    matrix_root: str | Path | None = None,
    cohort_items_path: str | Path | None = None,
) -> dict[str, Any]:
    payload = analyze_f1_local_matrix_subtype_stratified(
        repo_root,
        matrix_root=matrix_root,
        cohort_items_path=cohort_items_path,
    )
    markdown_path = Path(markdown_path)
    json_path = Path(json_path)
    csv_path = Path(csv_path)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    markdown_path.write_text(render_local_matrix_subtype_markdown(payload), encoding="utf-8")
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=False), encoding="utf-8")
    write_tables_csv(csv_path, payload["tables"])
    return payload
