"""Competent ceiling reports comparing oracle, reference, and competent submitters."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from fsmreasonbench.baselines.competent_submitter import (
    run_competent_submitter,
    serialize_competent_submission,
)
from fsmreasonbench.evaluator.batch import evaluate_baseline_on_items
from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.evaluator.jsonl import load_items_jsonl
from fsmreasonbench.evaluator.models import ScoringRecord
from fsmreasonbench.evaluator.reference_submitter_report import (
    DEFAULT_REFERENCE_SUBMITTER_COHORTS,
    evaluate_reference_submitter_on_items,
)
from fsmreasonbench.evaluator.scorer import score_item
from fsmreasonbench.evaluator.summary import summarize_scoring_records
from fsmreasonbench.items.assembly import BenchmarkItem

COMPETENT_CEILING_JSON_FIELDS: tuple[str, ...] = (
    "cohort_id",
    "family",
    "system",
    "n",
    "extractability_rate",
    "verdict_accuracy",
    "certificate_valid_rate",
    "fully_correct_rate",
)

COMPETENT_CEILING_CSV_FIELDS: tuple[str, ...] = COMPETENT_CEILING_JSON_FIELDS

CEILING_SYSTEMS: frozenset[str] = frozenset(
    {"oracle", "reference_submitter", "competent_submitter"}
)

DEFAULT_COMPETENT_CEILING_COHORTS: tuple[dict[str, str], ...] = DEFAULT_REFERENCE_SUBMITTER_COHORTS


def evaluate_competent_submitter_on_items(
    items: list[BenchmarkItem],
) -> tuple[list[ScoringRecord], list[tuple[str, tuple[dict[str, Any], ...]]]]:
    """Score competent submissions through the same parser/scorer path as models."""
    if not items:
        return [], []
    family = items[0].family
    if any(item.family != family for item in items):
        raise ValueError("batch items must share the same family")

    records: list[ScoringRecord] = []
    logs: list[tuple[str, tuple[dict[str, Any], ...]]] = []
    for item in items:
        run = run_competent_submitter(item)
        raw = serialize_competent_submission(run)
        records.append(score_item(item, raw))
        logs.append((item.item_id, run.reasoning_log))
    return records, logs


def _summary_row(
    *,
    cohort_id: str,
    family: str,
    system: str,
    summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "cohort_id": cohort_id,
        "family": family,
        "system": system,
        "n": summary["n"],
        "extractability_rate": summary["extractability_rate"],
        "verdict_accuracy": summary["verdict_accuracy"],
        "certificate_valid_rate": summary["certificate_valid_rate"],
        "fully_correct_rate": summary["fully_correct_rate"],
    }


def evaluate_cohort_systems(
    repo_root: Path,
    *,
    cohort_id: str,
    family: str,
    items_path: str,
) -> list[dict[str, Any]]:
    resolved_items = (repo_root / items_path).resolve()
    items = load_items_jsonl(resolved_items)
    oracle_records = evaluate_baseline_on_items("oracle", items)
    reference_records = evaluate_reference_submitter_on_items(items)
    competent_records, _ = evaluate_competent_submitter_on_items(items)
    return [
        _summary_row(
            cohort_id=cohort_id,
            family=family,
            system="oracle",
            summary=summarize_scoring_records(oracle_records),
        ),
        _summary_row(
            cohort_id=cohort_id,
            family=family,
            system="reference_submitter",
            summary=summarize_scoring_records(reference_records),
        ),
        _summary_row(
            cohort_id=cohort_id,
            family=family,
            system="competent_submitter",
            summary=summarize_scoring_records(competent_records),
        ),
    ]


def build_competent_ceiling_report(
    repo_root: str | Path,
    cohorts: tuple[dict[str, str], ...] | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    selected = cohorts if cohorts is not None else DEFAULT_COMPETENT_CEILING_COHORTS
    rows: list[dict[str, Any]] = []
    for cohort in selected:
        rows.extend(
            evaluate_cohort_systems(
                root,
                cohort_id=cohort["cohort_id"],
                family=cohort["family"],
                items_path=cohort["items_path"],
            )
        )
    return {"rows": rows}


def assert_competent_ceiling_complete(rows: list[dict[str, Any]]) -> None:
    ceiling_rows = [row for row in rows if row["system"] in CEILING_SYSTEMS]
    failures: list[str] = []
    for row in ceiling_rows:
        for metric in (
            "extractability_rate",
            "verdict_accuracy",
            "certificate_valid_rate",
            "fully_correct_rate",
        ):
            if row[metric] != 1.0:
                failures.append(
                    f"{row['cohort_id']}/{row['system']} {metric}={row[metric]}"
                )
    if failures:
        raise ValueError(
            "competent ceiling completeness check failed: " + "; ".join(failures)
        )


def write_competent_ceiling_csv(
    path: str | Path,
    rows: list[dict[str, Any]],
) -> None:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(COMPETENT_CEILING_CSV_FIELDS))
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row[field] for field in COMPETENT_CEILING_CSV_FIELDS})


def render_competent_ceiling_markdown(payload: dict[str, Any]) -> str:
    rows = payload["rows"]
    lines = [
        "# Competent Ceiling Report",
        "",
        "Comparison of **oracle**, **reference submitter**, and **competent submitter**",
        "on frozen exploratory cohorts (`v0.1-exploratory`).",
        "",
        "## System definitions",
        "",
        "| System | Role |",
        "|--------|------|",
        "| **oracle** | Symbolic ceiling via oracle procedures and certificate builders. |",
        "| **reference_submitter** | Non-oracle workflow using oracle decision procedures and public",
        "certificate builders; no `answer_key.certificate` access. |",
        "| **competent_submitter** | R1-style step-simulator agent: bounded runtime simulation only",
        "(`simulate`, `reachable_states`, `accepts_trace`, `minimized_dfa_hash`); explicit",
        "reasoning logs; public submission schema; no `fsmreasonbench.oracle` imports. |",
        "",
        "## Results",
        "",
        "| cohort | family | system | n | extract | verdict | cert | full |",
        "|--------|--------|--------|--:|--------:|--------:|-----:|-----:|",
    ]
    for row in rows:
        lines.append(
            "| `{cohort}` | {family} | {system} | {n} | "
            "{extract:.3f} | {verdict:.3f} | {cert:.3f} | {full:.3f} |".format(
                cohort=row["cohort_id"],
                family=row["family"],
                system=row["system"],
                n=row["n"],
                extract=row["extractability_rate"],
                verdict=row["verdict_accuracy"],
                cert=row["certificate_valid_rate"],
                full=row["fully_correct_rate"],
            )
        )

    competent_rows = [row for row in rows if row["system"] == "competent_submitter"]
    reference_rows = [row for row in rows if row["system"] == "reference_submitter"]
    competent_full = (
        competent_rows
        and all(row["fully_correct_rate"] == 1.0 for row in competent_rows)
    )
    reference_full = (
        reference_rows
        and all(row["fully_correct_rate"] == 1.0 for row in reference_rows)
    )

    lines.extend(["", "## Interpretation", ""])
    if competent_full and reference_full:
        lines.extend(
            [
                "**Does `competent_submitter` add evidence beyond `reference_submitter`?**",
                "Partially, but not on contract satisfiability. Both reach `fully_correct_rate = 1.0`",
                "on the frozen exploratory C2/F1 cohorts, so M2 contract-unsatisfiability and",
                "oracle-certificate-injection threats remain equally ruled out.",
                "",
                "The incremental value is **process coverage**, not a higher ceiling:",
                "`competent_submitter` shows an auditable R1-style step-simulator workflow",
                "(logged BFS / product exploration / trace replay) can assemble verifier-valid",
                "certificates without importing oracle modules. That narrows the remaining gap",
                "toward tool-augmented human or model behaviour, but does not substitute for",
                "human-expert or frontier-model evaluation.",
                "",
                "**M2 impact:** unchanged on contract impossibility; slightly strengthened on",
                "encoding-only explanations when models fail despite all three ceilings at 1.0.",
                "",
                "**Still missing for Q1 construct-validity closure:**",
                "- human-expert ceiling on a stratified public sample;",
                "- frontier-model panel on frozen `v1.0-public` cohorts with adequate power;",
                "- R1/R2 track runners and F2 non-materialized composition (separate milestones).",
            ]
        )
    else:
        lines.append(
            "One or more ceiling systems did not reach `fully_correct_rate = 1.0`; "
            "investigate before drawing M2 conclusions."
        )

    lines.extend(
        [
            "",
            "## Suggested paper paragraph",
            "",
            "We report three evaluator-facing ceilings on frozen exploratory cohorts.",
            "The oracle baseline establishes contract satisfiability.",
            "The reference submitter reproduces full correctness without reading gold certificates,",
            "ruling out oracle-only certificate injection.",
            "The competent submitter adds an R1-style step-simulator workflow with auditable",
            "reasoning logs and no oracle-module imports; it matches the other ceilings on C2 and F1",
            "exploratory slices.",
            "When exploratory models fail `certificate_valid_rate` while all three ceilings remain",
            "at 1.0, remaining construct-validity concern shifts toward model-specific witness",
            "construction rather than benchmark impossibility or hidden gold-certificate dependence.",
            "Neither ceiling establishes human performance or frontier-model capability.",
            "",
        ]
    )
    return "\n".join(lines)


def export_competent_ceiling_report(
    repo_root: str | Path,
    *,
    out_json: str | Path,
    out_csv: str | Path,
    out_md: str | Path,
    cohorts: tuple[dict[str, str], ...] | None = None,
    strict: bool = True,
) -> dict[str, Path]:
    payload = build_competent_ceiling_report(repo_root, cohorts=cohorts)
    if strict:
        assert_competent_ceiling_complete(payload["rows"])

    json_path = Path(out_json)
    csv_path = Path(out_csv)
    md_path = Path(out_md)
    dump_json(json_path, payload)
    write_competent_ceiling_csv(csv_path, payload["rows"])
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_competent_ceiling_markdown(payload), encoding="utf-8")
    return {"json": json_path, "csv": csv_path, "md": md_path}


def validate_competent_ceiling_row(row: dict[str, Any]) -> None:
    for field in COMPETENT_CEILING_JSON_FIELDS:
        if field not in row:
            raise ValueError(f"missing required field: {field}")
