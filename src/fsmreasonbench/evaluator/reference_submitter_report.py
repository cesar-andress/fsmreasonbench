"""Reference submitter evaluation reports for frozen exploratory cohorts."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from fsmreasonbench.baselines.reference_submitter import run_reference_submitter
from fsmreasonbench.evaluator.batch import evaluate_baseline_on_items
from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.evaluator.jsonl import load_items_jsonl
from fsmreasonbench.evaluator.models import ScoringRecord
from fsmreasonbench.evaluator.scorer import score_item
from fsmreasonbench.evaluator.summary import summarize_scoring_records
from fsmreasonbench.items.assembly import BenchmarkItem

REFERENCE_SUBMITTER_JSON_FIELDS: tuple[str, ...] = (
    "cohort_id",
    "family",
    "system",
    "items_path",
    "n",
    "extractability_rate",
    "verdict_accuracy",
    "certificate_valid_rate",
    "fully_correct_rate",
)

REFERENCE_SUBMITTER_CSV_FIELDS: tuple[str, ...] = REFERENCE_SUBMITTER_JSON_FIELDS

DEFAULT_REFERENCE_SUBMITTER_COHORTS: tuple[dict[str, str], ...] = (
    {
        "cohort_id": "c2-reachability-level3-v0.1-exploratory",
        "family": "C2",
        "items_path": "cohorts/v0.1-exploratory/c2-reachability-level3/items.jsonl",
    },
    {
        "cohort_id": "f1-mixed-level3-v0.1-exploratory",
        "family": "F1",
        "items_path": "cohorts/v0.1-exploratory/f1-mixed-level3/items.jsonl",
    },
)


def evaluate_reference_submitter_on_items(
    items: list[BenchmarkItem],
) -> list[ScoringRecord]:
    """Score reference submissions through the same parser/scorer path as models."""
    if not items:
        return []
    family = items[0].family
    if any(item.family != family for item in items):
        raise ValueError("batch items must share the same family")
    return [
        score_item(item, run_reference_submitter(item))
        for item in items
    ]


def _summary_row(
    *,
    cohort_id: str,
    family: str,
    system: str,
    items_path: str,
    summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "cohort_id": cohort_id,
        "family": family,
        "system": system,
        "items_path": items_path,
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
    return [
        _summary_row(
            cohort_id=cohort_id,
            family=family,
            system="oracle",
            items_path=items_path,
            summary=summarize_scoring_records(oracle_records),
        ),
        _summary_row(
            cohort_id=cohort_id,
            family=family,
            system="reference_submitter",
            items_path=items_path,
            summary=summarize_scoring_records(reference_records),
        ),
    ]


def build_reference_submitter_report(
    repo_root: str | Path,
    cohorts: tuple[dict[str, str], ...] | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    selected = cohorts if cohorts is not None else DEFAULT_REFERENCE_SUBMITTER_COHORTS
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


def assert_reference_submitter_complete(rows: list[dict[str, Any]]) -> None:
    reference_rows = [
        row for row in rows if row["system"] == "reference_submitter"
    ]
    failures = [
        row
        for row in reference_rows
        if row["fully_correct_rate"] != 1.0 or row["certificate_valid_rate"] != 1.0
    ]
    if failures:
        details = ", ".join(
            f"{row['cohort_id']} (fully_correct={row['fully_correct_rate']})"
            for row in failures
        )
        raise ValueError(f"reference submitter completeness check failed: {details}")


def write_reference_submitter_csv(
    path: str | Path,
    rows: list[dict[str, Any]],
) -> None:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(REFERENCE_SUBMITTER_CSV_FIELDS))
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row[field] for field in REFERENCE_SUBMITTER_CSV_FIELDS})


def render_reference_submitter_markdown(payload: dict[str, Any]) -> str:
    rows = payload["rows"]
    lines = [
        "# Reference Submitter Report",
        "",
        "Comparison of the symbolic **oracle baseline** and the **reference submitter** on",
        "frozen exploratory cohorts (`v0.1-exploratory`).",
        "",
        "## Interpretation",
        "",
        "| Ceiling | Meaning |",
        "|---------|---------|",
        "| **Oracle** | The certificate contract is **satisfiable** on every item; the verifier",
        "accepts oracle-built witnesses. |",
        "| **Reference submitter** | The contract is **achievable without oracle certificate",
        "injection**: an independent reasoning workflow computes verdicts from the supplied FSMs,",
        "builds certificates through the public submission schema, and passes the same",
        "parser/scorer path as models. |",
        "",
        "This does **not** establish human performance or frontier-model performance.",
        "It narrows the remaining construct-validity ambiguity: when models fail",
        "`certificate_valid_rate` but both ceilings are 1.0, failures are unlikely to be",
        "explained solely by contract unsatisfiability or by oracle-only certificate injection.",
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

    reference_rows = [row for row in rows if row["system"] == "reference_submitter"]
    if reference_rows and all(row["fully_correct_rate"] == 1.0 for row in reference_rows):
        lines.extend(
            [
                "",
                "## Contract achievability",
                "",
                "On both frozen exploratory cohorts, `reference_submitter` achieves",
                "`fully_correct_rate = 1.0`, matching the oracle ceiling.",
                "The certificate contract is therefore achievable through a non-oracle workflow",
                "that never reads `answer_key.certificate`.",
            ]
        )

    lines.extend(
        [
            "",
            "## Suggested paper paragraph",
            "",
            "The symbolic oracle ceiling establishes that the certificate contract is satisfiable",
            "on every evaluated item and that the verifier accepts correct witnesses.",
            "The reference submitter reproduces that outcome using only evaluatee-visible FSMs:",
            "it computes verdicts with independent decision procedures, constructs certificates",
            "through the same public submission schema used by models, and is scored by the",
            "standard parser and verifier pipeline without reading gold certificates.",
            "When oracle and reference submitter both reach `fully_correct_rate = 1.0` while",
            "exploratory models do not, contract unsatisfiability and oracle certificate injection",
            "are ruled out as explanations for model `certificate_invalid` outcomes; remaining",
            "ambiguity concerns model-specific witness construction rather than benchmark",
            "impossibility.",
            "Neither ceiling establishes human or frontier-model performance.",
            "",
        ]
    )
    return "\n".join(lines)


def export_reference_submitter_report(
    repo_root: str | Path,
    *,
    out_json: str | Path,
    out_csv: str | Path,
    out_md: str | Path,
    cohorts: tuple[dict[str, str], ...] | None = None,
    strict: bool = True,
) -> dict[str, Path]:
    payload = build_reference_submitter_report(repo_root, cohorts=cohorts)
    if strict:
        assert_reference_submitter_complete(payload["rows"])

    json_path = Path(out_json)
    csv_path = Path(out_csv)
    md_path = Path(out_md)
    dump_json(json_path, payload)
    write_reference_submitter_csv(csv_path, payload["rows"])
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_reference_submitter_markdown(payload), encoding="utf-8")
    return {"json": json_path, "csv": csv_path, "md": md_path}


def validate_reference_submitter_row(row: dict[str, Any]) -> None:
    for field in REFERENCE_SUBMITTER_JSON_FIELDS:
        if field not in row:
            raise ValueError(f"missing required field: {field}")
