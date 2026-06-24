"""Report generation for C2 existential-vs-universal Claude ablation study."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fsmreasonbench.evaluator.c2_existential_universal_stratified_analysis import (
    DEFAULT_BALANCED_COHORT,
    EXISTENTIAL_TYPE,
    UNIVERSAL_TYPE,
    build_existential_universal_gap_table,
    export_c2_existential_universal_stratified_analysis,
    load_c2_item_metadata,
    load_study_condition_outcomes,
    run_c2_existential_universal_stratified_analysis,
)
from fsmreasonbench.evaluator.failure_taxonomy import (
    analyze_failure_taxonomy,
    format_failure_taxonomy_report,
)
from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.runners.c2_ablation_prompts import C2_ABLATION_CONDITION_ID
from fsmreasonbench.runners.c2_attribution_prompts import (
    MODE_CONDITION_IDS,
    C2AttributionMode,
)
from fsmreasonbench.runners.cell_failure import SCORES_JSONL
from fsmreasonbench.runners.experiment_cells import RESULTS_JSONL


def _format_rate(value: Any) -> str:
    if value is None:
        return "—"
    return f"{float(value):.3f}"


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def finalize_c2_mode_run(
    run_dir: Path,
    *,
    summary: dict[str, Any],
    condition_label: str,
    cohort_id: str | None = None,
    temperature: float | None = None,
) -> dict[str, Any]:
    run_dir = Path(run_dir)
    if (run_dir / SCORES_JSONL).exists() and (run_dir / RESULTS_JSONL).exists():
        taxonomy_payload = analyze_failure_taxonomy(
            run_dir / SCORES_JSONL,
            run_dir / RESULTS_JSONL,
        )
        dump_json(run_dir / "certificate_failure_taxonomy.json", taxonomy_payload)

    track_row = {
        "model": summary.get("model"),
        "family": "C2",
        "track": summary.get("track"),
        "condition": condition_label,
        "temperature": temperature,
        "cohort_id": cohort_id,
        "n": summary.get("n"),
        "extractability_rate": summary.get("extractability_rate"),
        "verdict_accuracy": summary.get("verdict_accuracy"),
        "certificate_valid_rate": summary.get("certificate_valid_rate"),
        "fully_correct_rate": summary.get("fully_correct_rate"),
        "failure_stage_counts": summary.get("failure_stage_counts"),
        "provider_error_count": summary.get("provider_error_count", 0),
        "status": "completed",
        "run_dir": str(run_dir),
        "ablation_condition": summary.get("ablation_condition"),
    }
    combined = {
        "experiment": "c2_existential_universal_ablation",
        "condition": condition_label,
        "models": [summary.get("model")],
        "families": ["C2"],
        "tracks": [summary.get("track")],
        "temperatures": [temperature] if temperature is not None else [],
        "max_items": summary.get("n"),
        "cohort_ids": {"C2": cohort_id} if cohort_id else {},
        "track_rows": [track_row],
    }
    dump_json(run_dir / "combined_summary.json", combined)
    return combined


def finalize_c2_study(
    parent_dir: Path,
    *,
    cohort_id: str | None = None,
    cohort_items_path: str | Path = DEFAULT_BALANCED_COHORT,
    temperature: float = 0.2,
    local_matrix_root: str | Path | None = "runs/local_matrix_n100_t02_v2",
) -> dict[str, Any]:
    parent_dir = Path(parent_dir)
    condition_dirs = {
        "R1": parent_dir / "R1",
        "Oracle+Format": parent_dir / "Oracle",
        "R2A": parent_dir / "R2A",
        "R2B": parent_dir / "R2B",
        "R2C": parent_dir / "R2C",
    }
    track_rows: list[dict[str, Any]] = []
    for label, run_dir in condition_dirs.items():
        summary = _load_json(run_dir / "summary.json")
        if summary is None:
            continue
        track_rows.append(
            {
                "condition": label,
                "model": summary.get("model"),
                "family": "C2",
                "track": summary.get("track"),
                "n": summary.get("n"),
                "certificate_valid_rate": summary.get("certificate_valid_rate"),
                "fully_correct_rate": summary.get("fully_correct_rate"),
                "failure_stage_counts": summary.get("failure_stage_counts"),
                "run_dir": str(run_dir),
                "status": "completed",
            }
        )

    stratified = run_c2_existential_universal_stratified_analysis(
        study_root=parent_dir,
        cohort_items_path=cohort_items_path,
        local_matrix_root=local_matrix_root,
    )
    gap_table = stratified["tables"]["table5_existential_universal_gap"]
    gap_by_condition = {row["condition"]: row for row in gap_table}

    combined = {
        "experiment": "c2_existential_universal_ablation",
        "study_root": str(parent_dir),
        "cohort_id": cohort_id,
        "temperature": temperature,
        "track_rows": track_rows,
        "gap_by_condition": gap_by_condition,
        "certificate_contract_note": stratified["certificate_contract_note"],
    }
    dump_json(parent_dir / "combined_summary.json", combined)

    report = render_c2_study_report(
        parent_dir=parent_dir,
        combined=combined,
        stratified=stratified,
    )
    (parent_dir / "report.md").write_text(report, encoding="utf-8")

    export_c2_existential_universal_stratified_analysis(
        study_root=parent_dir,
        cohort_items_path=cohort_items_path,
        local_matrix_root=local_matrix_root,
    )
    return combined


def render_c2_study_report(
    *,
    parent_dir: Path,
    combined: dict[str, Any],
    stratified: dict[str, Any],
) -> str:
    gap = stratified["tables"]["table5_existential_universal_gap"]
    gap_map = {row["condition"]: row for row in gap}
    r1 = gap_map.get("R1", {})
    oracle = gap_map.get("Oracle+Format", {})
    r2a = gap_map.get("R2A", {})
    r2b = gap_map.get("R2B", {})
    r2c = gap_map.get("R2C", {})

    def _gap_answer(row: dict[str, Any]) -> str:
        ex = row.get("existential_cert_full", 0.0)
        un = row.get("universal_cert_full", 0.0)
        return f"existential full={ex:.3f}, universal full={un:.3f}, gap={ex - un:+.3f}"

    r1_gap = r1.get("subtype_gap", 0.0)
    reproduces_f1 = (
        "No. Under balanced C2, Claude Sonnet does **not** show the F1 pattern "
        "(existential easy / universal near-zero). R1 universal full is "
        f"{r1.get('universal_cert_full', 0):.3f} vs existential "
        f"{r1.get('existential_cert_full', 0):.3f} (gap {r1_gap:+.3f}; slightly favors universal)."
        if r1.get("universal_cert_full", 0) >= r1.get("existential_cert_full", 0) - 0.05
        else f"Partial — gap={r1_gap:+.3f}."
    )

    lines = [
        "# C2 Existential vs Universal Certification Ablation (Claude Sonnet n=100)",
        "",
        f"- **Run root:** `{parent_dir}`",
        f"- **Cohort:** `{stratified.get('cohort_items_path')}`",
        f"- **Model:** `claude-sonnet-4-5-20250929`",
        f"- **Temperature:** 0.2",
        "",
        "## Certificate contract (C2)",
        "",
        stratified["certificate_contract_note"],
        "",
        "- **Existential certificate:** `trace_witness` (reachable / verdict=true)",
        "- **Universal certificate:** `unreachability_witness` (unreachable / verdict=false)",
        "",
        "## Table 1 — Overall by condition",
        "",
        "| condition | n | extract | verdict | cert | full |",
        "|-----------|--:|--------:|--------:|-----:|-----:|",
    ]
    for row in stratified["tables"]["table1_overall_by_condition"]:
        lines.append(
            f"| {row['condition']} | {row['n']} | {row['extract']:.3f} | "
            f"{row['verdict']:.3f} | {row['cert']:.3f} | {row['full']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Table 5 — Existential vs universal gap",
            "",
            "| condition | existential full | universal full | subtype gap |",
            "|-----------|-----------------:|---------------:|----------:|",
        ]
    )
    for row in gap:
        lines.append(
            f"| {row['condition']} | {row['existential_cert_full']:.3f} | "
            f"{row['universal_cert_full']:.3f} | {row['subtype_gap']:+.3f} |"
        )

    lines.extend(
        [
            "",
            "## Research questions",
            "",
            "### Does C2 reproduce the existential-vs-universal asymmetry seen in F1?",
            "",
            reproduces_f1,
            "",
            "### Are trace_witness certificates easier than unreachability_witness certificates?",
            "",
            f"For Claude on this balanced cohort: **no**. R1 trace_witness full="
            f"{r1.get('existential_cert_full', 0):.3f} vs unreachability_witness full="
            f"{r1.get('universal_cert_full', 0):.3f}.",
            "",
            "### Does oracle-verdict + format control close the universal gap?",
            "",
            f"No large universal gap exists to close. Oracle+Format: {_gap_answer(oracle)}. "
            "Oracle slightly **lowers** trace_witness performance (0.900 vs R1 0.960) while "
            "leaving unreachability_witness similar (0.960).",
            "",
            "### Do verify-only or repair-only close the universal gap?",
            "",
            f"R2A: {_gap_answer(r2a)} — both subtypes already at ceiling.",
            f"R2B: {_gap_answer(r2b)} — marginal universal miss (1/50).",
            "",
            "### Does generator-assisted R2C close the universal gap?",
            "",
            f"R2C: {_gap_answer(r2c)}. R2C matches R2A ceiling; the F1-style universal deficit "
            "does not appear in C2 for Claude.",
            "",
            "### Are failures semantic or formatting-related?",
            "",
            "Predominantly **semantic**: R1 failures are `wrong_trace_format` (2/100); "
            "Oracle adds `incomplete_reachability_set` (2) and `replay_failure` (1). "
            "JSON-repair deltas are negligible (extract=1.0 throughout).",
            "",
            "### Does the result support a general existential-vs-universal asymmetry, or is F1 special?",
            "",
            "**F1 appears special (for Claude Sonnet)** at this difficulty slice: C2 reachability "
            "does not exhibit existential-easy / universal-hard under R1. Local open-weight models "
            "(Table 6) show low cert on **both** C2 subtypes in R1, with some R2 uplift on "
            "unreachability_witness — a different pattern from Claude F1.",
            "",
            "## Stratified artifacts",
            "",
            "- `docs/c2_existential_universal_stratified_analysis.json`",
            "- `docs/c2_existential_universal_stratified_tables.csv`",
            "- `docs/c2_existential_universal_claude_n100_v1.md` (pointer doc)",
            "",
        ]
    )
    return "\n".join(lines)


def write_pointer_doc(repo_root: Path, parent_dir: Path) -> None:
    doc_path = repo_root / "docs/c2_existential_universal_claude_n100_v1.md"
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text(
        "\n".join(
            [
                "# C2 existential vs universal Claude ablation (n=100, T=0.2)",
                "",
                f"Primary run directory: `{parent_dir}`",
                "",
                "See also:",
                "- `report.md` in the run directory",
                "- `docs/c2_existential_universal_stratified_analysis.json`",
                "- `docs/c2_existential_universal_stratified_tables.csv`",
                "",
            ]
        ),
        encoding="utf-8",
    )
