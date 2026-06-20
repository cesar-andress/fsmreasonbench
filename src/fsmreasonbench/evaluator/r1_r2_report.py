"""R1/R2 track evaluation reports and delegation-gap summaries."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.evaluator.jsonl import load_items_jsonl
from fsmreasonbench.evaluator.reference_submitter_report import DEFAULT_REFERENCE_SUBMITTER_COHORTS
from fsmreasonbench.evaluator.summary import summarize_scoring_records
from fsmreasonbench.tracks.delegation import DELEGATION_GAP_METRICS, compute_delegation_gap
from fsmreasonbench.tracks.models import TrackId, TrackRunResult
from fsmreasonbench.tracks.replay import replay_audit_log
from fsmreasonbench.tracks.runner import run_track

R1_R2_JSON_FIELDS: tuple[str, ...] = (
    "cohort_id",
    "family",
    "track",
    "n",
    "extractability_rate",
    "verdict_accuracy",
    "certificate_valid_rate",
    "fully_correct_rate",
    "tool_invocation_count_mean",
)

DEFAULT_R1_R2_COHORTS: tuple[dict[str, str], ...] = DEFAULT_REFERENCE_SUBMITTER_COHORTS


def _fsm_index_from_item(item) -> dict:
    index = {item.fsm.fsm_id: item.fsm}
    if item.fsm_b is not None:
        index[item.fsm_b.fsm_id] = item.fsm_b
    return index


def evaluate_track_on_items(
    track: TrackId,
    items: list,
) -> tuple[list[TrackRunResult], dict[str, Any]]:
    results = [run_track(item, track) for item in items]
    records = [result.scoring_record for result in results]
    summary = summarize_scoring_records(records)
    tool_counts = [len(result.audit_log.tool_invocations) for result in results]
    summary["tool_invocation_count_mean"] = (
        sum(tool_counts) / len(tool_counts) if tool_counts else 0.0
    )
    summary["track"] = track.value
    return results, summary


def evaluate_cohort_tracks(
    repo_root: Path,
    *,
    cohort_id: str,
    family: str,
    items_path: str,
) -> tuple[list[dict[str, Any]], list[TrackRunResult], dict[str, Any]]:
    items = load_items_jsonl((repo_root / items_path).resolve())
    r0_results, r0_summary = evaluate_track_on_items(TrackId.R0, items)
    r1_results, r1_summary = evaluate_track_on_items(TrackId.R1, items)
    r2_results, r2_summary = evaluate_track_on_items(TrackId.R2, items)

    for item, result in zip(items, r0_results, strict=True):
        replay_audit_log(result.audit_log, fsm_by_id=_fsm_index_from_item(item))
    for item, result in zip(items, r1_results, strict=True):
        replay_audit_log(result.audit_log, fsm_by_id=_fsm_index_from_item(item))
    for item, result in zip(items, r2_results, strict=True):
        replay_audit_log(result.audit_log, fsm_by_id=_fsm_index_from_item(item))

    rows = []
    for summary in (r0_summary, r1_summary, r2_summary):
        rows.append(
            {
                "cohort_id": cohort_id,
                "family": family,
                **summary,
            }
        )

    delegation = compute_delegation_gap(rows[0], rows[2])
    delegation["cohort_id"] = cohort_id
    return rows, r0_results, delegation


def build_r1_r2_report(
    repo_root: str | Path,
    cohorts: tuple[dict[str, str], ...] | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    selected = cohorts if cohorts is not None else DEFAULT_R1_R2_COHORTS

    track_rows: list[dict[str, Any]] = []
    delegation_rows: list[dict[str, Any]] = []
    example_transcripts: list[dict[str, Any]] = []

    for cohort in selected:
        rows, r0_results, delegation = evaluate_cohort_tracks(
            root,
            cohort_id=cohort["cohort_id"],
            family=cohort["family"],
            items_path=cohort["items_path"],
        )
        track_rows.extend(rows)
        delegation_rows.append(delegation)

        if not example_transcripts and r0_results:
            example = r0_results[0]
            example_transcripts.append(
                {
                    "cohort_id": cohort["cohort_id"],
                    "track": example.track.value,
                    "item_id": example.scoring_record.item_id,
                    "audit_log": example.audit_log.to_dict(),
                    "raw_response": json.loads(example.raw_response),
                }
            )

    return {
        "track_rows": track_rows,
        "delegation_gaps": delegation_rows,
        "example_transcripts": example_transcripts,
    }


def assert_track_reference_complete(rows: list[dict[str, Any]]) -> None:
    failures = []
    for row in rows:
        for metric in (
            "extractability_rate",
            "verdict_accuracy",
            "certificate_valid_rate",
            "fully_correct_rate",
        ):
            if row[metric] != 1.0:
                failures.append(
                    f"{row['cohort_id']}/{row['track']} {metric}={row[metric]}"
                )
    if failures:
        raise ValueError(
            "track reference completeness check failed: " + "; ".join(failures)
        )


def write_r1_r2_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(R1_R2_JSON_FIELDS))
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row[field] for field in R1_R2_JSON_FIELDS})


def render_r1_r2_markdown(payload: dict[str, Any], *, example_item_path: str | None = None) -> str:
    track_rows = payload["track_rows"]
    delegation_gaps = payload["delegation_gaps"]
    examples = payload.get("example_transcripts", [])

    lines = [
        "# R1/R2 Track Report",
        "",
        "First operational evaluation tracks on frozen exploratory cohorts.",
        "",
        "## Track definitions",
        "",
        "| Track | Permitted | Forbidden | Artifact agent |",
        "|-------|-----------|-----------|----------------|",
        "| **R0** | Scratchpad / inline reasoning | Tools, oracle, answer keys | `run_r0_agent` |",
        "| **R1** | `step(fsm_id, state, symbol)` + scratchpad | Oracle, global solvers | `run_r1_agent` |",
        "| **R2** | Registered solver tools + certificate assembly | Gold certificate copy | `run_r2_agent` |",
        "",
        "See `docs/r1_r2_design_review.md` for normative semantics and trust boundaries.",
        "",
        "## Reproducibility guarantees",
        "",
        "- Every R1/R2 tool call is logged in `audit_log.tool_invocations` with inputs, outputs, and provenance.",
        "- `replay_audit_log()` re-executes invocations and verifies output equality.",
        "- Track transcripts store `tracks_version`, `track`, and full audit logs under `{out_dir}/transcripts/`.",
        "- Scoring uses unchanged `parse_submission` / `score_item` (backward compatible `ScoringRecord`).",
        "",
        "## Track results",
        "",
        "| cohort | family | track | n | extract | verdict | cert | full | tools/item |",
        "|--------|--------|-------|--:|--------:|--------:|-----:|-----:|-----------:|",
    ]

    for row in track_rows:
        lines.append(
            "| `{cohort}` | {family} | {track} | {n} | "
            "{extract:.3f} | {verdict:.3f} | {cert:.3f} | {full:.3f} | {tools:.1f} |".format(
                cohort=row["cohort_id"],
                family=row["family"],
                track=row["track"],
                n=row["n"],
                extract=row["extractability_rate"],
                verdict=row["verdict_accuracy"],
                cert=row["certificate_valid_rate"],
                full=row["fully_correct_rate"],
                tools=row["tool_invocation_count_mean"],
            )
        )

    lines.extend(["", "## Delegation gap Δ_R2_R0", ""])
    lines.append("| cohort | family | metric | R0 | R2 | Δ |")
    lines.append("|--------|--------|--------|---:|---:|--:|")

    for gap_row in delegation_gaps:
        cohort_id = gap_row["cohort_id"]
        family = gap_row["family"]
        r0 = next(r for r in track_rows if r["cohort_id"] == cohort_id and r["track"] == "R0")
        r2 = next(r for r in track_rows if r["cohort_id"] == cohort_id and r["track"] == "R2")
        for metric in DELEGATION_GAP_METRICS:
            delta = gap_row["delegation_gap"][metric]
            lines.append(
                f"| `{cohort_id}` | {family} | {metric} | "
                f"{r0[metric]:.3f} | {r2[metric]:.3f} | {delta:+.3f} |"
            )

    lines.extend(
        [
            "",
            "Reference agents on exploratory cohorts achieve identical rates; "
            "Δ = 0 is expected. Non-zero delegation gaps appear when R0 systems "
            "(e.g. LLMs without tools) underperform R2 solver-delegation pipelines on the same items.",
            "",
            "## Example transcripts",
            "",
        ]
    )

    if examples:
        example = examples[0]
        lines.append(f"Item `{example['item_id']}` ({example['track']}, cohort `{example['cohort_id']}`):")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(example["audit_log"], indent=2, sort_keys=True)[:2500])
        lines.append("```")
    elif example_item_path:
        lines.append(f"Example item: `{example_item_path}`")

    lines.append("")
    return "\n".join(lines)


def export_r1_r2_report(
    repo_root: str | Path,
    *,
    out_json: str | Path = "docs/r1_r2_summary.json",
    out_csv: str | Path = "docs/r1_r2_summary.csv",
    out_md: str | Path = "docs/r1_r2_report.md",
    cohorts: tuple[dict[str, str], ...] | None = None,
    strict: bool = True,
) -> dict[str, Path]:
    payload = build_r1_r2_report(repo_root, cohorts=cohorts)
    if strict:
        assert_track_reference_complete(payload["track_rows"])

    json_path = Path(out_json)
    csv_path = Path(out_csv)
    md_path = Path(out_md)
    dump_json(json_path, payload)
    write_r1_r2_csv(csv_path, payload["track_rows"])
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(
        render_r1_r2_markdown(
            payload,
            example_item_path="examples/item_C2_reachability_seed42.json",
        ),
        encoding="utf-8",
    )
    return {"json": json_path, "csv": csv_path, "md": md_path}
