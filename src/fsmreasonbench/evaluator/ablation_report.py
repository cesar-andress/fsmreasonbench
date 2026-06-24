"""Report generation for F1 oracle-verdict ablation runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fsmreasonbench.evaluator.failure_taxonomy import (
    analyze_failure_taxonomy,
    format_failure_taxonomy_report,
)
from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.runners.cell_failure import SCORES_JSONL
from fsmreasonbench.runners.experiment_cells import RESULTS_JSONL


def _load_baseline_f1_cells(
    baseline_root: Path,
) -> dict[str, dict[str, Any]]:
    combined_path = baseline_root / "combined_summary.json"
    if not combined_path.exists():
        return {}
    payload = json.loads(combined_path.read_text(encoding="utf-8"))
    rows = {
        row["track"]: row
        for row in payload.get("track_rows", [])
        if row.get("family") == "F1" and row.get("status") == "completed"
    }
    return rows


def _format_rate(row: dict[str, Any], key: str) -> str:
    value = row.get(key)
    if value is None:
        return "—"
    return f"{float(value):.3f}"


def _failure_stage_line(row: dict[str, Any]) -> str:
    counts = row.get("failure_stage_counts") or {}
    return (
        f"not_ext={counts.get('not_extractable', 0)}, "
        f"verdict_wrong={counts.get('verdict_wrong', 0)}, "
        f"cert_invalid={counts.get('certificate_invalid', 0)}, "
        f"correct={counts.get('correct', 0)}"
    )


def render_ablation_report(
    *,
    run_dir: Path,
    summary: dict[str, Any],
    baseline_root: Path | None = None,
    taxonomy_payload: dict[str, Any] | None = None,
) -> str:
    baseline = _load_baseline_f1_cells(baseline_root) if baseline_root else {}
    r1 = baseline.get("R1", {})
    r2 = baseline.get("R2", {})

    repair = summary.get("json_repair_metrics") or {}
    repair_delta = summary.get("json_repair_delta") or {}

    lines = [
        "# F1 Oracle-Verdict Format-Control Ablation Report",
        "",
        f"- **Run root:** `{run_dir}`",
        f"- **Condition:** `{summary.get('ablation_condition')}`",
        f"- **Model:** `{summary.get('model')}`",
        f"- **Family / track:** F1 / `{summary.get('track')}`",
        f"- **n:** {summary.get('n')}",
        "",
        "## Primary metrics (standard parser)",
        "",
        f"- **extractability_rate:** {_format_rate(summary, 'extractability_rate')}",
        f"- **verdict_accuracy:** {_format_rate(summary, 'verdict_accuracy')}",
        f"- **certificate_valid_rate:** {_format_rate(summary, 'certificate_valid_rate')}",
        f"- **fully_correct_rate:** {_format_rate(summary, 'fully_correct_rate')}",
        "",
        "## JSON-repair metrics (smart-quote normalization + standard extract)",
        "",
    ]
    if repair:
        lines.extend(
            [
                f"- **extractability_rate:** {_format_rate(repair, 'extractability_rate')}",
                f"- **verdict_accuracy:** {_format_rate(repair, 'verdict_accuracy')}",
                f"- **certificate_valid_rate:** {_format_rate(repair, 'certificate_valid_rate')}",
                f"- **fully_correct_rate:** {_format_rate(repair, 'fully_correct_rate')}",
                "",
                "### Delta (repair − primary)",
                "",
                f"- extractability: {repair_delta.get('extractability_rate', 0.0):+.3f}",
                f"- verdict: {repair_delta.get('verdict_accuracy', 0.0):+.3f}",
                f"- certificate: {repair_delta.get('certificate_valid_rate', 0.0):+.3f}",
                f"- fully correct: {repair_delta.get('fully_correct_rate', 0.0):+.3f}",
                "",
            ]
        )
    else:
        lines.extend(["- JSON repair scoring not enabled.", ""])

    fs = summary.get("failure_stage_counts") or {}
    lines.extend(
        [
            "## Failure-stage decomposition (primary)",
            "",
            "| Stage | Count |",
            "|-------|------:|",
            f"| not_extractable | {fs.get('not_extractable', 0)} |",
            f"| provider_error | {fs.get('provider_error', 0)} |",
            f"| verdict_wrong | {fs.get('verdict_wrong', 0)} |",
            f"| certificate_invalid | {fs.get('certificate_invalid', 0)} |",
            f"| correct | {fs.get('correct', 0)} |",
            "",
            "## Comparison vs frozen Claude Sonnet tools (`frontier_claude_sonnet_tools_n100_v2`)",
            "",
            "| Condition | Extract | Verdict | Cert | Full | Failure stages |",
            "|-----------|--------:|--------:|-----:|-----:|----------------|",
        ]
    )

    def _row(label: str, row: dict[str, Any]) -> str:
        return (
            f"| {label} | {_format_rate(row, 'extractability_rate')} | "
            f"{_format_rate(row, 'verdict_accuracy')} | "
            f"{_format_rate(row, 'certificate_valid_rate')} | "
            f"{_format_rate(row, 'fully_correct_rate')} | "
            f"{_failure_stage_line(row)} |"
        )

    lines.append(
        _row(
            "Ablation (oracle verdict + format control)",
            {
                "extractability_rate": summary.get("extractability_rate"),
                "verdict_accuracy": summary.get("verdict_accuracy"),
                "certificate_valid_rate": summary.get("certificate_valid_rate"),
                "fully_correct_rate": summary.get("fully_correct_rate"),
                "failure_stage_counts": fs,
            },
        )
    )
    if r1:
        lines.append(_row("Claude F1 R1 (tools, frozen)", r1))
    if r2:
        lines.append(_row("Claude F1 R2 (tools, frozen)", r2))

    lines.extend(
        [
            "",
            "## Research questions",
            "",
            "1. **Does providing the correct verdict improve certificate_valid_rate?** "
            f"Compare ablation cert={_format_rate(summary, 'certificate_valid_rate')} "
            f"vs Claude F1 R1 cert={_format_rate(r1, 'certificate_valid_rate') if r1 else '—'}.",
            "2. **Does strict schema + examples improve certificate_valid_rate?** "
            "Ablation adds oracle verdict + worked examples vs standard R1 tool protocol.",
            "3. **Does the gap to R2 remain?** "
            f"Ablation full={_format_rate(summary, 'fully_correct_rate')} "
            f"vs Claude F1 R2 full={_format_rate(r2, 'fully_correct_rate') if r2 else '—'}.",
            "4. **Are remaining failures semantic or formatting-related?** "
            "See certificate failure taxonomy below; compare primary vs JSON-repair deltas.",
            "",
        ]
    )

    if taxonomy_payload is not None:
        lines.extend(
            [
                "## Certificate failure taxonomy",
                "",
                format_failure_taxonomy_report(taxonomy_payload),
            ]
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Verdict is oracle-fixed in the prompt; verdict_wrong indicates model disobedience, not uncertainty.",
            "- Do not compare to contaminated `frontier_claude_sonnet_full_n100_v1`.",
            "- Frozen baseline: `runs/frontier_claude_sonnet_tools_n100_v2`.",
            "",
        ]
    )
    return "\n".join(lines)


def finalize_ablation_run(
    run_dir: Path,
    *,
    summary: dict[str, Any],
    baseline_root: Path | None = None,
    cohort_id: str | None = None,
    temperature: float | None = None,
) -> dict[str, Any]:
    """Write combined_summary.json, report.md, and certificate taxonomy artifacts."""
    run_dir = Path(run_dir)
    taxonomy_payload = analyze_failure_taxonomy(
        run_dir / SCORES_JSONL,
        run_dir / RESULTS_JSONL,
    )
    dump_json(run_dir / "certificate_failure_taxonomy.json", taxonomy_payload)

    report = render_ablation_report(
        run_dir=run_dir,
        summary=summary,
        baseline_root=baseline_root,
        taxonomy_payload=taxonomy_payload,
    )
    (run_dir / "report.md").write_text(report, encoding="utf-8")

    track_row = {
        "model": summary.get("model"),
        "family": "F1",
        "track": summary.get("track"),
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
        "json_repair_metrics": summary.get("json_repair_metrics"),
    }
    combined = {
        "experiment": "ablation",
        "ablation_condition": summary.get("ablation_condition"),
        "models": [summary.get("model")],
        "families": ["F1"],
        "tracks": [summary.get("track")],
        "temperatures": [temperature] if temperature is not None else [],
        "max_items": summary.get("n"),
        "cohort_ids": {"F1": cohort_id} if cohort_id else {},
        "track_rows": [track_row],
        "cell_status_counts": {"completed": 1, "expected": 1},
    }
    dump_json(run_dir / "combined_summary.json", combined)
    return combined
