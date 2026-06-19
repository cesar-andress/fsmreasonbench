"""Pilot evaluation Markdown report generation from scoring JSONL files."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fsmreasonbench.evaluator.inspect_failures import inspect_failures
from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.evaluator.jsonl import read_jsonl
from fsmreasonbench.evaluator.models import FailureStage, ScoringRecord
from fsmreasonbench.evaluator.summary import summarize_scoring_records

_FAILURE_STAGE_ORDER = tuple(stage.value for stage in FailureStage)
_FAILURE_SAMPLE_STAGES = tuple(
    stage.value for stage in FailureStage if stage is not FailureStage.CORRECT
)

PILOT_V0_INTERPRETATION = (
    "Verdict accuracy overstates reasoning success: the model often emits extractable "
    "JSON and correct high-level verdicts while failing to produce executable certificates."
)

PILOT_V0_FAILURE_MODES: tuple[dict[str, str], ...] = (
    {
        "family": "C2",
        "mode": "trace_payload_objects",
        "description": "C2 trace payload uses objects instead of symbol strings",
    },
    {
        "family": "C2",
        "mode": "unreachability_incomplete",
        "description": "C2 unreachability witness omits reachable states",
    },
    {
        "family": "F1",
        "mode": "generic_non_replayable_trace",
        "description": (
            'F1 repeatedly emits generic traces such as ["a", "b"] that are not replayable'
        ),
    },
)


@dataclass(frozen=True, slots=True)
class ScoreRunSummary:
    """Aggregated metrics for one scoring JSONL input."""

    label: str
    source_path: str
    n: int
    extractability_rate: float
    verdict_accuracy: float
    certificate_valid_rate: float
    fully_correct_rate: float
    failure_stage_counts: dict[str, int]
    top_certificate_failure_reasons: tuple[tuple[str, int], ...]
    sample_failures_by_stage: dict[str, tuple[dict[str, Any], ...]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "source_path": self.source_path,
            "n": self.n,
            "extractability_rate": self.extractability_rate,
            "verdict_accuracy": self.verdict_accuracy,
            "certificate_valid_rate": self.certificate_valid_rate,
            "fully_correct_rate": self.fully_correct_rate,
            "failure_stage_counts": dict(self.failure_stage_counts),
            "top_certificate_failure_reasons": [
                {"reason": reason, "count": count}
                for reason, count in self.top_certificate_failure_reasons
            ],
            "sample_failures_by_stage": {
                stage: list(samples)
                for stage, samples in self.sample_failures_by_stage.items()
            },
        }


def build_pilot_report(
    score_paths: list[str | Path],
    *,
    sample_limit: int = 5,
    top_reason_limit: int = 10,
    labels: list[str] | None = None,
) -> list[ScoreRunSummary]:
    """Build pilot report sections from one or more scoring JSONL files."""
    if not score_paths:
        raise ValueError("at least one scores file is required")
    if sample_limit < 1:
        raise ValueError("sample_limit must be >= 1")
    if top_reason_limit < 1:
        raise ValueError("top_reason_limit must be >= 1")
    if labels is not None and len(labels) != len(score_paths):
        raise ValueError("labels length must match score_paths length")

    summaries: list[ScoreRunSummary] = []
    for index, path in enumerate(score_paths):
        resolved = Path(path)
        label = labels[index] if labels is not None else resolved.stem
        records = [ScoringRecord.from_dict(row) for row in read_jsonl(resolved)]
        summaries.append(
            _summarize_score_run(
                label=label,
                source_path=str(resolved),
                records=records,
                sample_limit=sample_limit,
                top_reason_limit=top_reason_limit,
            )
        )
    return summaries


def render_pilot_report_markdown(summaries: list[ScoreRunSummary]) -> str:
    """Render pilot evaluation summaries as Markdown."""
    lines = [
        "# FSMReasonBench Pilot Evaluation Report",
        "",
        f"Score inputs: {len(summaries)}",
        "",
    ]

    for summary in summaries:
        lines.extend(_render_run_section(summary))

    return "\n".join(lines).rstrip() + "\n"


def write_pilot_report(
    score_paths: list[str | Path],
    out_path: str | Path,
    *,
    sample_limit: int = 5,
    top_reason_limit: int = 10,
    labels: list[str] | None = None,
) -> Path:
    """Generate and write a pilot Markdown report."""
    summaries = build_pilot_report(
        score_paths,
        sample_limit=sample_limit,
        top_reason_limit=top_reason_limit,
        labels=labels,
    )
    destination = Path(out_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_pilot_report_markdown(summaries), encoding="utf-8")
    return destination


@dataclass(frozen=True, slots=True)
class PilotV0FamilyRun:
    """One family slice in a pilot v0 report."""

    family: str
    scores_path: str | Path
    results_path: str | Path


def build_pilot_v0_summary(
    runs: list[PilotV0FamilyRun],
    *,
    model: str,
    temperature: float,
    sample_limit: int = 5,
    top_reason_limit: int = 10,
    interpretation: str = PILOT_V0_INTERPRETATION,
    representative_failure_modes: tuple[dict[str, str], ...] = PILOT_V0_FAILURE_MODES,
) -> dict[str, Any]:
    """Build a structured pilot v0 summary across C2/F1 score runs."""
    if not runs:
        raise ValueError("at least one family run is required")

    families: dict[str, Any] = {}
    for run in runs:
        summary = build_pilot_report(
            [run.scores_path],
            sample_limit=sample_limit,
            top_reason_limit=top_reason_limit,
            labels=[run.family],
        )[0]
        inspection = inspect_failures(
            run.scores_path,
            run.results_path,
            limit=sample_limit,
        )
        families[run.family] = {
            "family": run.family,
            "scores_path": str(run.scores_path),
            "results_path": str(run.results_path),
            "n": summary.n,
            "extractability_rate": summary.extractability_rate,
            "verdict_accuracy": summary.verdict_accuracy,
            "certificate_valid_rate": summary.certificate_valid_rate,
            "fully_correct_rate": summary.fully_correct_rate,
            "failure_stage_counts": summary.failure_stage_counts,
            "top_certificate_failure_reasons": [
                {"reason": reason, "count": count}
                for reason, count in summary.top_certificate_failure_reasons
            ],
            "sample_failures_by_stage": inspection.get("samples_by_stage", {}),
        }

    n_per_family = next(iter(families.values()))["n"]
    if any(section["n"] != n_per_family for section in families.values()):
        n_per_family = {family: section["n"] for family, section in families.items()}

    return {
        "pilot_version": "v0",
        "model": model,
        "temperature": temperature,
        "n_per_family": n_per_family,
        "interpretation": interpretation,
        "representative_failure_modes": list(representative_failure_modes),
        "families": families,
    }


def render_pilot_v0_markdown(payload: dict[str, Any]) -> str:
    """Render the pilot v0 Markdown report."""
    lines = [
        "# FSMReasonBench Pilot v0 Report",
        "",
        "## Run configuration",
        "",
        f"- **Model:** `{payload['model']}`",
        f"- **Temperature:** {payload['temperature']}",
        f"- **Items per family:** {payload['n_per_family']}",
        "",
    ]

    for family, section in payload["families"].items():
        lines.extend(
            [
                f"## {family} summary",
                "",
                "| Metric | Value |",
                "|--------|------:|",
                f"| n | {section['n']} |",
                f"| extractability_rate | {section['extractability_rate']:.3f} |",
                f"| verdict_accuracy | {section['verdict_accuracy']:.3f} |",
                f"| certificate_valid_rate | {section['certificate_valid_rate']:.3f} |",
                f"| fully_correct_rate | {section['fully_correct_rate']:.3f} |",
                "",
                "### Failure stage counts",
                "",
                "| Stage | Count |",
                "|-------|------:|",
            ]
        )
        for stage in _FAILURE_STAGE_ORDER:
            lines.append(f"| {stage} | {section['failure_stage_counts'].get(stage, 0)} |")

        lines.extend(["", "### Top certificate failure reasons", ""])
        reasons = section["top_certificate_failure_reasons"]
        if reasons:
            lines.extend(["| Reason | Count |", "|--------|------:|"])
            for entry in reasons:
                escaped = entry["reason"].replace("|", "\\|")
                lines.append(f"| {escaped} | {entry['count']} |")
        else:
            lines.append("_None recorded._")

        samples = section.get("sample_failures_by_stage", {})
        if samples:
            lines.extend(["", "### Sample failures", ""])
            for stage in _FAILURE_SAMPLE_STAGES:
                stage_samples = samples.get(stage, [])
                if not stage_samples:
                    continue
                lines.append(f"#### {stage}")
                lines.append("")
                for sample in stage_samples:
                    lines.append(f"- `{sample['item_id']}`")
                    lines.append(f"  - verdict_correct: {sample['verdict_correct']}")
                    lines.append(f"  - certificate_valid: {sample['certificate_valid']}")
                    if sample.get("certificate_errors"):
                        lines.append(f"  - certificate_errors: {sample['certificate_errors']}")
                    excerpt = sample.get("raw_response_excerpt")
                    if excerpt:
                        lines.append(f"  - raw_response excerpt: `{excerpt[:200]}`")
                    parsed = sample.get("parsed_submission")
                    if parsed is not None:
                        lines.append(
                            "  - parsed_submission: "
                            f"`{json.dumps(parsed, sort_keys=True)[:200]}`"
                        )
                lines.append("")

    lines.extend(
        [
            "## Interpretation",
            "",
            payload["interpretation"],
            "",
            "## Representative failure modes",
            "",
        ]
    )
    for mode in payload["representative_failure_modes"]:
        lines.append(f"- **{mode['family']}:** {mode['description']}")

    return "\n".join(lines).rstrip() + "\n"


def write_pilot_v0_artifacts(
    runs: list[PilotV0FamilyRun],
    report_path: str | Path,
    summary_path: str | Path,
    *,
    model: str,
    temperature: float,
    sample_limit: int = 5,
    top_reason_limit: int = 10,
) -> tuple[Path, Path]:
    """Write pilot v0 Markdown report and JSON summary."""
    payload = build_pilot_v0_summary(
        runs,
        model=model,
        temperature=temperature,
        sample_limit=sample_limit,
        top_reason_limit=top_reason_limit,
    )
    report_destination = Path(report_path)
    summary_destination = Path(summary_path)
    report_destination.parent.mkdir(parents=True, exist_ok=True)
    summary_destination.parent.mkdir(parents=True, exist_ok=True)
    report_destination.write_text(render_pilot_v0_markdown(payload), encoding="utf-8")
    dump_json(summary_destination, payload)
    return report_destination, summary_destination


def _summarize_score_run(
    *,
    label: str,
    source_path: str,
    records: list[ScoringRecord],
    sample_limit: int,
    top_reason_limit: int,
) -> ScoreRunSummary:
    summary = summarize_scoring_records(records)
    grouped: dict[str, list[ScoringRecord]] = defaultdict(list)
    for record in records:
        grouped[record.failure_stage.value].append(record)

    sample_failures_by_stage: dict[str, tuple[dict[str, Any], ...]] = {}
    for stage in _FAILURE_SAMPLE_STAGES:
        samples = tuple(
            _failure_sample_dict(record)
            for record in grouped[stage][:sample_limit]
        )
        if samples:
            sample_failures_by_stage[stage] = samples

    return ScoreRunSummary(
        label=label,
        source_path=source_path,
        n=summary["n"],
        extractability_rate=summary["extractability_rate"],
        verdict_accuracy=summary["verdict_accuracy"],
        certificate_valid_rate=summary["certificate_valid_rate"],
        fully_correct_rate=summary["fully_correct_rate"],
        failure_stage_counts=summary["failure_stage_counts"],
        top_certificate_failure_reasons=_top_certificate_failure_reasons(
            records,
            limit=top_reason_limit,
        ),
        sample_failures_by_stage=sample_failures_by_stage,
    )


def _failure_sample_dict(record: ScoringRecord) -> dict[str, Any]:
    sample = {
        "item_id": record.item_id,
        "family": record.family,
        "failure_stage": record.failure_stage.value,
        "verdict_correct": record.verdict_correct,
        "certificate_valid": record.certificate_valid,
        "fully_correct": record.fully_correct,
    }
    if record.parse_errors:
        sample["parse_errors"] = list(record.parse_errors)
    if record.certificate_errors:
        sample["certificate_errors"] = list(record.certificate_errors)
    return sample


def _top_certificate_failure_reasons(
    records: list[ScoringRecord],
    *,
    limit: int,
) -> tuple[tuple[str, int], ...]:
    counter: Counter[str] = Counter()
    for record in records:
        for error in record.certificate_errors:
            counter[error] += 1
    return tuple(counter.most_common(limit))


def _render_run_section(summary: ScoreRunSummary) -> list[str]:
    lines = [
        f"## {summary.label}",
        "",
        f"Source: `{summary.source_path}`",
        "",
        "### Summary",
        "",
        "| Metric | Value |",
        "|--------|------:|",
        f"| n | {summary.n} |",
        f"| extractability_rate | {summary.extractability_rate:.3f} |",
        f"| verdict_accuracy | {summary.verdict_accuracy:.3f} |",
        f"| certificate_valid_rate | {summary.certificate_valid_rate:.3f} |",
        f"| fully_correct_rate | {summary.fully_correct_rate:.3f} |",
        "",
        "### Failure stage counts",
        "",
        "| Stage | Count |",
        "|-------|------:|",
    ]
    for stage in _FAILURE_STAGE_ORDER:
        count = summary.failure_stage_counts.get(stage, 0)
        lines.append(f"| {stage} | {count} |")

    lines.extend(["", "### Top certificate failure reasons", ""])
    if summary.top_certificate_failure_reasons:
        lines.extend(
            [
                "| Reason | Count |",
                "|--------|------:|",
            ]
        )
        for reason, count in summary.top_certificate_failure_reasons:
            escaped = reason.replace("|", "\\|")
            lines.append(f"| {escaped} | {count} |")
    else:
        lines.append("_None recorded._")

    lines.extend(["", "### Sample failures", ""])
    if not summary.sample_failures_by_stage:
        lines.append("_No failures in this run._")
        lines.append("")
        return lines

    for stage in _FAILURE_SAMPLE_STAGES:
        samples = summary.sample_failures_by_stage.get(stage, ())
        if not samples:
            continue
        lines.append(f"#### {stage}")
        lines.append("")
        for sample in samples:
            lines.append(f"- `{sample['item_id']}` ({sample['family']})")
            lines.append(f"  - verdict_correct: {sample['verdict_correct']}")
            lines.append(f"  - certificate_valid: {sample['certificate_valid']}")
            if "parse_errors" in sample:
                lines.append(f"  - parse_errors: {sample['parse_errors']}")
            if "certificate_errors" in sample:
                lines.append(f"  - certificate_errors: {sample['certificate_errors']}")
        lines.append("")

    return lines
