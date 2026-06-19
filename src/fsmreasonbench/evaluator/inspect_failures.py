"""Inspect failure modes in scored Ollama / baseline runs."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fsmreasonbench.evaluator.jsonl import read_jsonl
from fsmreasonbench.evaluator.models import FailureStage, ScoringRecord
from fsmreasonbench.evaluator.parser import parse_submission


DEFAULT_EXCERPT_LENGTH = 500
_FAILURE_STAGE_ORDER = tuple(stage.value for stage in FailureStage)


@dataclass(frozen=True, slots=True)
class FailureSample:
    """Representative scored item for one failure stage."""

    item_id: str
    failure_stage: str
    raw_response_excerpt: str
    parsed_submission: dict[str, Any] | None
    parse_errors: tuple[str, ...]
    certificate_errors: tuple[str, ...]
    verdict_correct: bool | None
    certificate_valid: bool | None
    fully_correct: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "failure_stage": self.failure_stage,
            "raw_response_excerpt": self.raw_response_excerpt,
            "parsed_submission": self.parsed_submission,
            "parse_errors": list(self.parse_errors),
            "certificate_errors": list(self.certificate_errors),
            "verdict_correct": self.verdict_correct,
            "certificate_valid": self.certificate_valid,
            "fully_correct": self.fully_correct,
        }


def inspect_failures(
    scores_path: str | Path,
    results_path: str | Path,
    *,
    limit: int = 5,
    excerpt_length: int = DEFAULT_EXCERPT_LENGTH,
) -> dict[str, Any]:
    """
    Aggregate failure stages and collect representative samples per stage.

    ``scores_path`` is a flat scoring-records JSONL. ``results_path`` is the
    companion run JSONL (e.g. Ollama batch output) keyed by ``item_id``.
    """
    if limit < 1:
        raise ValueError("limit must be >= 1")
    if excerpt_length < 1:
        raise ValueError("excerpt_length must be >= 1")

    records = [ScoringRecord.from_dict(row) for row in read_jsonl(scores_path)]
    results_by_id = _index_results(read_jsonl(results_path))

    stage_counts = Counter(record.failure_stage.value for record in records)
    samples_by_stage: dict[str, list[FailureSample]] = {
        stage: [] for stage in _FAILURE_STAGE_ORDER
    }

    grouped: dict[str, list[ScoringRecord]] = defaultdict(list)
    for record in records:
        grouped[record.failure_stage.value].append(record)

    for stage in _FAILURE_STAGE_ORDER:
        for record in grouped[stage][:limit]:
            run_record = results_by_id.get(record.item_id)
            if run_record is None:
                continue
            samples_by_stage[stage].append(
                _build_sample(record, run_record, excerpt_length=excerpt_length)
            )

    return {
        "n": len(records),
        "failure_stage_counts": {
            stage: stage_counts.get(stage, 0) for stage in _FAILURE_STAGE_ORDER
        },
        "samples_by_stage": {
            stage: [sample.to_dict() for sample in samples_by_stage[stage]]
            for stage in _FAILURE_STAGE_ORDER
            if samples_by_stage[stage]
        },
    }


def format_inspection_report(payload: dict[str, Any]) -> str:
    """Render a human-readable failure inspection report."""
    lines = [
        f"Failure inspection (n={payload['n']})",
        "=" * 32,
        "failure_stage counts:",
    ]
    for stage, count in payload["failure_stage_counts"].items():
        lines.append(f"  {stage}: {count}")

    samples_by_stage = payload.get("samples_by_stage", {})
    for stage in _FAILURE_STAGE_ORDER:
        samples = samples_by_stage.get(stage, [])
        if not samples:
            continue
        total = payload["failure_stage_counts"].get(stage, 0)
        lines.append("")
        lines.append(f"--- {stage} ({total} total, showing {len(samples)}) ---")
        for sample in samples:
            lines.extend(_format_sample_lines(sample))

    return "\n".join(lines) + "\n"


def _index_results(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        item_id = row.get("item_id")
        if not item_id:
            raise ValueError("results record missing item_id")
        if item_id in indexed:
            raise ValueError(f"duplicate item_id in results: {item_id!r}")
        indexed[item_id] = row
    return indexed


def _build_sample(
    record: ScoringRecord,
    run_record: dict[str, Any],
    *,
    excerpt_length: int,
) -> FailureSample:
    family = run_record.get("family", record.family)
    raw_response = run_record.get("raw_response")
    parsed_submission = _parsed_submission_from_run(raw_response, family)
    return FailureSample(
        item_id=record.item_id,
        failure_stage=record.failure_stage.value,
        raw_response_excerpt=_raw_response_excerpt(
            run_record,
            excerpt_length=excerpt_length,
        ),
        parsed_submission=parsed_submission,
        parse_errors=record.parse_errors,
        certificate_errors=record.certificate_errors,
        verdict_correct=record.verdict_correct,
        certificate_valid=record.certificate_valid,
        fully_correct=record.fully_correct,
    )


def _parsed_submission_from_run(
    raw_response: Any,
    family: str,
) -> dict[str, Any] | None:
    parse_result = parse_submission(raw_response, family)
    if not parse_result.extractable or parse_result.submission is None:
        return None
    submission = parse_result.submission
    return {
        "item_id": submission.item_id,
        "verdict": submission.verdict,
        "certificate": submission.certificate,
    }


def _raw_response_excerpt(
    run_record: dict[str, Any],
    *,
    excerpt_length: int,
) -> str:
    text = run_record.get("raw_response_text")
    if isinstance(text, str) and text:
        source = text
    else:
        raw_response = run_record.get("raw_response")
        if isinstance(raw_response, str):
            source = raw_response
        else:
            source = json.dumps(raw_response, sort_keys=True)

    if len(source) <= excerpt_length:
        return source
    return source[:excerpt_length] + "..."


def _format_sample_lines(sample: dict[str, Any]) -> list[str]:
    lines = [
        f"[item_id={sample['item_id']}]",
        f"  verdict_correct: {sample['verdict_correct']}",
        f"  certificate_valid: {sample['certificate_valid']}",
        f"  fully_correct: {sample['fully_correct']}",
    ]
    if sample["parse_errors"]:
        lines.append(f"  parse_errors: {sample['parse_errors']}")
    if sample["certificate_errors"]:
        lines.append(f"  certificate_errors: {sample['certificate_errors']}")
    lines.append(f"  raw_response excerpt: {sample['raw_response_excerpt']!r}")
    if sample["parsed_submission"] is None:
        lines.append("  parsed_submission: (not extractable)")
    else:
        parsed = json.dumps(sample["parsed_submission"], sort_keys=True)
        lines.append(f"  parsed_submission: {parsed}")
    return lines
