"""Oracle baseline ceiling reports for evaluated item batches."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from fsmreasonbench.evaluator.batch import evaluate_baseline_on_items
from fsmreasonbench.evaluator.io import dump_json, load_json
from fsmreasonbench.evaluator.jsonl import load_items_jsonl
from fsmreasonbench.evaluator.summary import summarize_scoring_records

ORACLE_CEILING_JSON_FIELDS: tuple[str, ...] = (
    "source_name",
    "family",
    "difficulty_level",
    "cohort_id",
    "n",
    "extractability_rate",
    "verdict_accuracy",
    "certificate_valid_rate",
    "fully_correct_rate",
)

ORACLE_CEILING_CSV_FIELDS: tuple[str, ...] = ORACLE_CEILING_JSON_FIELDS

DEFAULT_ORACLE_CEILING_BATCHES: tuple[dict[str, str], ...] = (
    {
        "source_name": "capability_surface_models/C2/min_witness_length_1/items.jsonl",
        "items_path": "runs/capability_surface_models/C2/min_witness_length_1/items.jsonl",
    },
    {
        "source_name": "capability_surface_models/C2/min_witness_length_2/items.jsonl",
        "items_path": "runs/capability_surface_models/C2/min_witness_length_2/items.jsonl",
    },
    {
        "source_name": "capability_surface_models/C2/min_witness_length_3/items.jsonl",
        "items_path": "runs/capability_surface_models/C2/min_witness_length_3/items.jsonl",
    },
    {
        "source_name": "capability_surface_models/C2/min_witness_length_4/items.jsonl",
        "items_path": "runs/capability_surface_models/C2/min_witness_length_4/items.jsonl",
    },
    {
        "source_name": "capability_surface_models/C2/min_witness_length_5/items.jsonl",
        "items_path": "runs/capability_surface_models/C2/min_witness_length_5/items.jsonl",
    },
    {
        "source_name": (
            "capability_surface_models_f1_mixed/F1/"
            "min_distinguishing_trace_length_1/items.jsonl"
        ),
        "items_path": (
            "runs/capability_surface_models_f1_mixed/F1/"
            "min_distinguishing_trace_length_1/items.jsonl"
        ),
    },
    {
        "source_name": (
            "capability_surface_models_f1_mixed/F1/"
            "min_distinguishing_trace_length_2/items.jsonl"
        ),
        "items_path": (
            "runs/capability_surface_models_f1_mixed/F1/"
            "min_distinguishing_trace_length_2/items.jsonl"
        ),
    },
    {
        "source_name": (
            "capability_surface_models_f1_mixed/F1/"
            "min_distinguishing_trace_length_3/items.jsonl"
        ),
        "items_path": (
            "runs/capability_surface_models_f1_mixed/F1/"
            "min_distinguishing_trace_length_3/items.jsonl"
        ),
    },
    {
        "source_name": (
            "capability_surface_models_f1_mixed/F1/"
            "min_distinguishing_trace_length_4/items.jsonl"
        ),
        "items_path": (
            "runs/capability_surface_models_f1_mixed/F1/"
            "min_distinguishing_trace_length_4/items.jsonl"
        ),
    },
    {
        "source_name": (
            "capability_surface_models_f1_mixed/F1/"
            "min_distinguishing_trace_length_5/items.jsonl"
        ),
        "items_path": (
            "runs/capability_surface_models_f1_mixed/F1/"
            "min_distinguishing_trace_length_5/items.jsonl"
        ),
    },
    {
        "source_name": "cohorts/v0.1-exploratory/c2-reachability-level3/items.jsonl",
        "items_path": "cohorts/v0.1-exploratory/c2-reachability-level3/items.jsonl",
        "cohort_id": "c2-reachability-level3-v0.1-exploratory",
    },
    {
        "source_name": "cohorts/v0.1-exploratory/f1-mixed-level3/items.jsonl",
        "items_path": "cohorts/v0.1-exploratory/f1-mixed-level3/items.jsonl",
        "cohort_id": "f1-mixed-level3-v0.1-exploratory",
    },
)


def _parse_difficulty_level(source_name: str) -> int | None:
    for token in Path(source_name).parts:
        if token.startswith("min_witness_length_"):
            return int(token.removeprefix("min_witness_length_"))
        if token.startswith("min_distinguishing_trace_length_"):
            return int(token.removeprefix("min_distinguishing_trace_length_"))
    return None


def evaluate_oracle_ceiling_batch(
    *,
    repo_root: Path,
    source_name: str,
    items_path: str | Path,
    cohort_id: str | None = None,
) -> dict[str, Any]:
    resolved_items = (repo_root / items_path).resolve()
    items = load_items_jsonl(resolved_items)
    records = evaluate_baseline_on_items("oracle", items)
    summary = summarize_scoring_records(records)
    family = items[0].family if items else "unknown"
    return {
        "source_name": source_name,
        "family": family,
        "difficulty_level": _parse_difficulty_level(source_name),
        "cohort_id": cohort_id,
        "n": summary["n"],
        "extractability_rate": summary["extractability_rate"],
        "verdict_accuracy": summary["verdict_accuracy"],
        "certificate_valid_rate": summary["certificate_valid_rate"],
        "fully_correct_rate": summary["fully_correct_rate"],
    }


def build_oracle_ceiling_report(
    repo_root: str | Path,
    batches: tuple[dict[str, str], ...] | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    selected = batches if batches is not None else DEFAULT_ORACLE_CEILING_BATCHES
    rows: list[dict[str, Any]] = []
    for batch in selected:
        rows.append(
            evaluate_oracle_ceiling_batch(
                repo_root=root,
                source_name=batch["source_name"],
                items_path=batch["items_path"],
                cohort_id=batch.get("cohort_id"),
            )
        )
    return {"baseline": "oracle", "rows": rows}


def assert_oracle_ceiling_complete(rows: list[dict[str, Any]]) -> None:
    failures = [
        row
        for row in rows
        if row["fully_correct_rate"] != 1.0 or row["certificate_valid_rate"] != 1.0
    ]
    if failures:
        details = ", ".join(
            f"{row['source_name']} (fully_correct={row['fully_correct_rate']})"
            for row in failures
        )
        raise ValueError(f"oracle ceiling check failed: {details}")


def write_oracle_ceiling_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(ORACLE_CEILING_CSV_FIELDS))
        writer.writeheader()
        for row in rows:
            csv_row = {
                field: "" if row.get(field) is None else row[field]
                for field in ORACLE_CEILING_CSV_FIELDS
            }
            writer.writerow(csv_row)


def render_oracle_ceiling_markdown(payload: dict[str, Any]) -> str:
    rows = payload["rows"]
    lines = [
        "# Oracle Ceiling Report",
        "",
        "**Baseline:** symbolic oracle (not a human or model ceiling).",
        "",
        "This report evaluates the oracle baseline on the exact item batches used in the",
        "current exploratory paper runs and on the two sealed exploratory cohort snapshots.",
        "",
        "## Interpretation",
        "",
        "- This is an **oracle/symbolic ceiling**, not a human or model ceiling.",
        "- It demonstrates that **certificate contracts are satisfiable** on the evaluated items.",
        "- It does **not** prove that certificate failures by LLMs are reasoning failures;",
        "  they may reflect certificate-expression or orchestration errors instead.",
        "",
        "## Batch results",
        "",
        "| source | family | level | cohort | n | extract | verdict | cert | full |",
        "|--------|--------|------:|--------|--:|--------:|--------:|-----:|-----:|",
    ]
    for row in rows:
        level = row["difficulty_level"] if row["difficulty_level"] is not None else "—"
        cohort = row["cohort_id"] if row["cohort_id"] is not None else "—"
        lines.append(
            "| `{source}` | {family} | {level} | {cohort} | {n} | "
            "{extract:.3f} | {verdict:.3f} | {cert:.3f} | {full:.3f} |".format(
                source=row["source_name"],
                family=row["family"],
                level=level,
                cohort=cohort,
                n=row["n"],
                extract=row["extractability_rate"],
                verdict=row["verdict_accuracy"],
                cert=row["certificate_valid_rate"],
                full=row["fully_correct_rate"],
            )
        )

    family_groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        key = row["family"]
        if row["cohort_id"] is not None:
            key = f"{row['family']} (frozen cohort)"
        family_groups.setdefault(key, []).append(row)

    lines.extend(["", "## Family-level ceiling", ""])
    for label, group_rows in family_groups.items():
        if all(row["fully_correct_rate"] == 1.0 for row in group_rows):
            lines.append(
                f"- **{label}:** `fully_correct_rate = 1.0` on all {len(group_rows)} evaluated batches."
            )
        else:
            lines.append(f"- **{label}:** incomplete oracle ceiling (see table).")

    lines.append("")
    return "\n".join(lines)


def export_oracle_ceiling_report(
    repo_root: str | Path,
    *,
    out_json: str | Path,
    out_csv: str | Path,
    out_md: str | Path,
    batches: tuple[dict[str, str], ...] | None = None,
    strict: bool = True,
) -> dict[str, Path]:
    payload = build_oracle_ceiling_report(repo_root, batches=batches)
    if strict:
        assert_oracle_ceiling_complete(payload["rows"])

    json_path = Path(out_json)
    csv_path = Path(out_csv)
    md_path = Path(out_md)
    dump_json(json_path, payload)
    write_oracle_ceiling_csv(csv_path, payload["rows"])
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_oracle_ceiling_markdown(payload), encoding="utf-8")
    return {"json": json_path, "csv": csv_path, "md": md_path}


def validate_oracle_ceiling_row(row: dict[str, Any]) -> None:
    for field in ORACLE_CEILING_JSON_FIELDS:
        if field not in row:
            raise ValueError(f"missing required field: {field}")


def load_oracle_ceiling_report(path: str | Path) -> dict[str, Any]:
    return load_json(path)
