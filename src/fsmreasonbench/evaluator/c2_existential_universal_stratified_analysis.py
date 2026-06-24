"""C2 existential-vs-universal stratified analysis (Claude ablations + local matrix)."""

from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from fsmreasonbench.evaluator.failure_taxonomy import classify_certificate_errors
from fsmreasonbench.evaluator.f1_claude_ablation_stratified_analysis import (
    ItemOutcome,
    _failure_stage_counts,
    _rate,
    _verdict_rate,
    load_condition_outcomes,
)
from fsmreasonbench.evaluator.jsonl import load_items_jsonl, read_jsonl

DEFAULT_BALANCED_COHORT = (
    "cohorts/v0.1-expanded-n100/c2-reachability-balanced-n100/items.jsonl"
)
DEFAULT_UNBALANCED_COHORT = (
    "cohorts/v0.1-expanded-n100/c2-reachability-level3/items.jsonl"
)
DEFAULT_STUDY_ROOT = "runs/ablations_c2_existential_universal_claude_n100_v1"
DEFAULT_LOCAL_MATRIX_ROOT = "runs/local_matrix_n100_t02_v2"

CONDITION_DIRS: dict[str, str] = {
    "R1": "R1",
    "Oracle+Format": "Oracle",
    "R2A": "R2A",
    "R2B": "R2B",
    "R2C": "R2C",
}

OVERALL_CONDITION_ORDER: tuple[str, ...] = (
    "R1",
    "Oracle+Format",
    "R2A",
    "R2B",
    "R2C",
)

CERTIFICATE_TYPES = ("trace_witness", "unreachability_witness")
EXISTENTIAL_TYPE = "trace_witness"
UNIVERSAL_TYPE = "unreachability_witness"


@dataclass(frozen=True, slots=True)
class C2ItemMetadata:
    item_id: str
    gold_verdict: bool
    gold_certificate_type: str
    reachable: bool
    subtype: str
    witness_length: int | None
    reachable_set_size: int | None
    state_count: int | None
    alphabet_size: int | None
    transition_count: int | None


def load_c2_item_metadata(cohort_items_path: str | Path) -> dict[str, C2ItemMetadata]:
    items = load_items_jsonl(cohort_items_path)
    metadata: dict[str, C2ItemMetadata] = {}
    for item in items:
        core = dict(item.difficulty.get("core") or {})
        cert = item.answer_key.get("certificate") or {}
        cert_type = str(cert.get("certificate_type", "unknown"))
        reachable = bool(item.answer_key["verdict"])
        witness_len = core.get("witness_length")
        if witness_len is not None:
            witness_len = int(witness_len)
        reachable_set_size = core.get("reachable_set_size")
        if reachable_set_size is not None:
            reachable_set_size = int(reachable_set_size)
        metadata[item.item_id] = C2ItemMetadata(
            item_id=item.item_id,
            gold_verdict=reachable,
            gold_certificate_type=cert_type,
            reachable=reachable,
            subtype=str(core.get("subtype", "existential" if reachable else "universal")),
            witness_length=witness_len,
            reachable_set_size=reachable_set_size,
            state_count=int(core["state_count"]) if core.get("state_count") is not None else None,
            alphabet_size=int(core["alphabet_size"]) if core.get("alphabet_size") is not None else None,
            transition_count=(
                int(core["transition_count"]) if core.get("transition_count") is not None else None
            ),
        )
    return metadata


def _filter_outcomes(
    outcomes: dict[str, ItemOutcome],
    metadata: dict[str, C2ItemMetadata],
    *,
    predicate,
) -> list[ItemOutcome]:
    return [
        outcomes[item_id]
        for item_id, meta in metadata.items()
        if item_id in outcomes and predicate(meta)
    ]


def build_overall_table(
    condition_outcomes: dict[str, dict[str, ItemOutcome]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for condition in OVERALL_CONDITION_ORDER:
        if condition not in condition_outcomes:
            continue
        outcomes = list(condition_outcomes[condition].values())
        fs = _failure_stage_counts(outcomes)
        rows.append(
            {
                "condition": condition,
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


def build_by_certificate_type_table(
    condition_outcomes: dict[str, dict[str, ItemOutcome]],
    metadata: dict[str, C2ItemMetadata],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for condition in OVERALL_CONDITION_ORDER:
        if condition not in condition_outcomes:
            continue
        for cert_type in CERTIFICATE_TYPES:
            subset = _filter_outcomes(
                condition_outcomes[condition],
                metadata,
                predicate=lambda meta, ct=cert_type: meta.gold_certificate_type == ct,
            )
            fs = _failure_stage_counts(subset)
            rows.append(
                {
                    "condition": condition,
                    "certificate_type": cert_type,
                    "n": len(subset),
                    "extract": round(_rate(row.extractable for row in subset), 3),
                    "verdict": round(_verdict_rate(subset), 3),
                    "cert": round(_rate(row.certificate_valid for row in subset), 3),
                    "full": round(_rate(row.fully_correct for row in subset), 3),
                    "certificate_invalid": fs["certificate_invalid"],
                }
            )
    return rows


def build_by_gold_verdict_table(
    condition_outcomes: dict[str, dict[str, ItemOutcome]],
    metadata: dict[str, C2ItemMetadata],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for condition in OVERALL_CONDITION_ORDER:
        if condition not in condition_outcomes:
            continue
        for reachable in (True, False):
            label = "reachable" if reachable else "unreachable"
            subset = _filter_outcomes(
                condition_outcomes[condition],
                metadata,
                predicate=lambda meta, r=reachable: meta.reachable is r,
            )
            fs = _failure_stage_counts(subset)
            rows.append(
                {
                    "condition": condition,
                    "gold_verdict": label,
                    "n": len(subset),
                    "extract": round(_rate(row.extractable for row in subset), 3),
                    "verdict": round(_verdict_rate(subset), 3),
                    "cert": round(_rate(row.certificate_valid for row in subset), 3),
                    "full": round(_rate(row.fully_correct for row in subset), 3),
                    "certificate_invalid": fs["certificate_invalid"],
                }
            )
    return rows


def build_failure_taxonomy_table(
    condition_outcomes: dict[str, dict[str, ItemOutcome]],
    metadata: dict[str, C2ItemMetadata],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for condition in OVERALL_CONDITION_ORDER:
        if condition not in condition_outcomes:
            continue
        for cert_type in CERTIFICATE_TYPES:
            subset_meta = {
                item_id: meta
                for item_id, meta in metadata.items()
                if meta.gold_certificate_type == cert_type
            }
            categories = Counter(
                condition_outcomes[condition][item_id].failure_category
                for item_id in subset_meta
                if item_id in condition_outcomes[condition]
                and condition_outcomes[condition][item_id].failure_category is not None
            )
            total = sum(categories.values())
            for category, count in sorted(categories.items(), key=lambda item: (-item[1], item[0])):
                rows.append(
                    {
                        "condition": condition,
                        "certificate_type": cert_type,
                        "failure_category": category,
                        "count": count,
                        "percentage": round(count / total, 3) if total else 0.0,
                    }
                )
    return rows


def build_existential_universal_gap_table(
    condition_outcomes: dict[str, dict[str, ItemOutcome]],
    metadata: dict[str, C2ItemMetadata],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for condition in OVERALL_CONDITION_ORDER:
        if condition not in condition_outcomes:
            continue
        existential = _filter_outcomes(
            condition_outcomes[condition],
            metadata,
            predicate=lambda meta: meta.gold_certificate_type == EXISTENTIAL_TYPE,
        )
        universal = _filter_outcomes(
            condition_outcomes[condition],
            metadata,
            predicate=lambda meta: meta.gold_certificate_type == UNIVERSAL_TYPE,
        )
        ex_full = _rate(row.fully_correct for row in existential)
        un_full = _rate(row.fully_correct for row in universal)
        ex_cert = _rate(row.certificate_valid for row in existential)
        un_cert = _rate(row.certificate_valid for row in universal)
        rows.append(
            {
                "condition": condition,
                "existential_cert_full": round(ex_full, 3),
                "universal_cert_full": round(un_full, 3),
                "existential_cert_rate": round(ex_cert, 3),
                "universal_cert_rate": round(un_cert, 3),
                "subtype_gap": round(ex_full - un_full, 3),
            }
        )
    return rows


def discover_local_matrix_c2_cells(matrix_root: Path) -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    for scores_path in sorted(matrix_root.glob("*/C2/temp_*/R*/scores.jsonl")):
        rel = scores_path.relative_to(matrix_root)
        cells.append(
            {
                "model_dir": rel.parts[0],
                "track": rel.parts[-2],
                "temperature": float(rel.parts[2].removeprefix("temp_")),
                "scores_path": scores_path,
            }
        )
    return cells


def build_local_matrix_subtype_table(
    matrix_root: Path,
    metadata: dict[str, C2ItemMetadata],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cell in discover_local_matrix_c2_cells(matrix_root):
        outcomes = load_condition_outcomes(cell["scores_path"])
        for cert_type in CERTIFICATE_TYPES:
            subset = _filter_outcomes(
                outcomes,
                metadata,
                predicate=lambda meta, ct=cert_type: meta.gold_certificate_type == ct,
            )
            rows.append(
                {
                    "model": cell["model_dir"],
                    "track": cell["track"],
                    "certificate_type": cert_type,
                    "n": len(subset),
                    "extract": round(_rate(row.extractable for row in subset), 3),
                    "verdict": round(_verdict_rate(subset), 3),
                    "cert": round(_rate(row.certificate_valid for row in subset), 3),
                    "full": round(_rate(row.fully_correct for row in subset), 3),
                }
            )
    return rows


def load_study_condition_outcomes(study_root: Path) -> dict[str, dict[str, ItemOutcome]]:
    loaded: dict[str, dict[str, ItemOutcome]] = {}
    for condition, subdir in CONDITION_DIRS.items():
        scores_path = study_root / subdir / "scores.jsonl"
        if scores_path.exists():
            loaded[condition] = load_condition_outcomes(scores_path)
    return loaded


def run_c2_existential_universal_stratified_analysis(
    *,
    study_root: str | Path,
    cohort_items_path: str | Path,
    local_matrix_root: str | Path | None = DEFAULT_LOCAL_MATRIX_ROOT,
    local_matrix_cohort_items_path: str | Path | None = DEFAULT_UNBALANCED_COHORT,
) -> dict[str, Any]:
    study_root = Path(study_root)
    metadata = load_c2_item_metadata(cohort_items_path)
    condition_outcomes = load_study_condition_outcomes(study_root)

    tables = {
        "table1_overall_by_condition": build_overall_table(condition_outcomes),
        "table2_by_certificate_subtype": build_by_certificate_type_table(
            condition_outcomes, metadata
        ),
        "table3_by_gold_verdict": build_by_gold_verdict_table(condition_outcomes, metadata),
        "table4_failure_taxonomy": build_failure_taxonomy_table(condition_outcomes, metadata),
        "table5_existential_universal_gap": build_existential_universal_gap_table(
            condition_outcomes, metadata
        ),
    }
    if local_matrix_root is not None and local_matrix_cohort_items_path is not None:
        matrix_path = Path(local_matrix_root)
        matrix_cohort = Path(local_matrix_cohort_items_path)
        if matrix_path.exists() and matrix_cohort.exists():
            matrix_metadata = load_c2_item_metadata(matrix_cohort)
            tables["table6_local_matrix_c2_subtype"] = build_local_matrix_subtype_table(
                matrix_path, matrix_metadata
            )

    return {
        "study_root": str(study_root),
        "cohort_items_path": str(cohort_items_path),
        "metadata_item_count": len(metadata),
        "conditions_loaded": list(condition_outcomes.keys()),
        "tables": tables,
        "certificate_contract_note": (
            "unreachability_witness requires payload.reachable_states to match the "
            "exact canonical reachable set from the verifier (not a valid sub/superset)."
        ),
    }


def write_stratified_csv(tables: dict[str, Any], csv_path: Path) -> None:
    sections: list[tuple[str, list[dict[str, Any]]]] = [
        ("Table 1: Overall by condition", tables.get("table1_overall_by_condition", [])),
        ("Table 2: By certificate subtype", tables.get("table2_by_certificate_subtype", [])),
        ("Table 3: By gold verdict", tables.get("table3_by_gold_verdict", [])),
        ("Table 4: Failure taxonomy", tables.get("table4_failure_taxonomy", [])),
        ("Table 5: Existential-vs-universal gap", tables.get("table5_existential_universal_gap", [])),
        ("Table 6: Local model C2 subtype", tables.get("table6_local_matrix_c2_subtype", [])),
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        for title, rows in sections:
            writer.writerow([title])
            if not rows:
                writer.writerow(["(no data)"])
                writer.writerow([])
                continue
            fieldnames = list(rows[0].keys())
            writer.writerow(fieldnames)
            for row in rows:
                writer.writerow([row.get(key) for key in fieldnames])
            writer.writerow([])


def export_c2_existential_universal_stratified_analysis(
    *,
    study_root: str | Path = DEFAULT_STUDY_ROOT,
    cohort_items_path: str | Path = DEFAULT_BALANCED_COHORT,
    local_matrix_root: str | Path | None = DEFAULT_LOCAL_MATRIX_ROOT,
    local_matrix_cohort_items_path: str | Path | None = DEFAULT_UNBALANCED_COHORT,
    json_out: str | Path = "docs/c2_existential_universal_stratified_analysis.json",
    csv_out: str | Path = "docs/c2_existential_universal_stratified_tables.csv",
) -> dict[str, Any]:
    payload = run_c2_existential_universal_stratified_analysis(
        study_root=study_root,
        cohort_items_path=cohort_items_path,
        local_matrix_root=local_matrix_root,
        local_matrix_cohort_items_path=local_matrix_cohort_items_path,
    )
    json_path = Path(json_out)
    csv_path = Path(csv_out)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    write_stratified_csv(payload["tables"], csv_path)
    return payload
