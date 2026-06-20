"""Failure taxonomy analysis for scored benchmark runs."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fsmreasonbench.evaluator.jsonl import read_jsonl
from fsmreasonbench.evaluator.models import FailureStage, ScoringRecord

TAXONOMY_CATEGORIES: tuple[str, ...] = (
    "wrong_trace_format",
    "replay_failure",
    "incomplete_reachability_set",
    "acceptance_mismatch",
    "equivalence_hash_mismatch",
    "wrong_certificate_type",
    "wrong_fsm_ids",
    "malformed_certificate_payload",
    "other",
)

_CERTIFICATE_INVALID = FailureStage.CERTIFICATE_INVALID.value


@dataclass(frozen=True, slots=True)
class TaxonomyBucket:
    """Aggregate counts for one taxonomy category."""

    count: int
    percentage: float
    sample_item_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "percentage": self.percentage,
            "sample_item_ids": list(self.sample_item_ids),
        }


def classify_certificate_errors(errors: tuple[str, ...]) -> str:
    """Map verifier certificate errors to a taxonomy category."""
    if not errors:
        return "other"

    lowered = " ".join(errors).lower()
    rules: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("wrong_certificate_type", ("unsupported certificate_type",)),
        ("wrong_fsm_ids", ("fsm_ids mismatch", "fsm_ids must be")),
        (
            "equivalence_hash_mismatch",
            (
                "minimized_hash_a mismatch",
                "minimized_hash_b mismatch",
                "minimized hashes differ",
            ),
        ),
        (
            "incomplete_reachability_set",
            ("missing reachable states", "extra non-reachable states"),
        ),
        (
            "acceptance_mismatch",
            (
                "acceptance.a mismatch",
                "acceptance.b mismatch",
                "trace must distinguish",
                "acceptance values equal",
            ),
        ),
        (
            "replay_failure",
            (
                "trace replay failed",
                "simulation failed",
                "state_sequence does not match replay",
            ),
        ),
        (
            "wrong_trace_format",
            (
                "trace and state_sequence must be arrays",
                "trace symbols must be strings",
                "state_sequence entries must be strings",
                "state_sequence length must be",
                "state_sequence must start at initial state",
                "state_sequence must end at target",
                "payload.trace must be an array of strings",
            ),
        ),
        (
            "malformed_certificate_payload",
            (
                "certificate payload must be an object",
                "payload must be an object",
                "payload.acceptance must be an object",
                "payload.acceptance.",
                "payload.equivalent must be true",
                "must be a non-empty string",
                "target_state mismatch",
                "reachable_states must be an array",
                "reachable_states entries must be strings",
            ),
        ),
    )
    for category, patterns in rules:
        if any(pattern in lowered for pattern in patterns):
            return category
    return "other"


def analyze_failure_taxonomy(
    scores_path: str | Path,
    results_path: str | Path,
    *,
    sample_limit: int = 5,
) -> dict[str, Any]:
    """Classify certificate_invalid failures in one scored run."""
    if sample_limit < 1:
        raise ValueError("sample_limit must be >= 1")

    scores_path = Path(scores_path)
    results_path = Path(results_path)
    records = [ScoringRecord.from_dict(row) for row in read_jsonl(scores_path)]
    _validate_results_path(results_path)

    return _build_taxonomy_payload(
        records,
        source={
            "scores": str(scores_path),
            "results": str(results_path),
        },
        sample_limit=sample_limit,
    )


def analyze_failure_taxonomy_batch(
    root: str | Path,
    *,
    sample_limit: int = 5,
) -> dict[str, Any]:
    """Analyze all scored runs under ``root`` that contain scores and results JSONL."""
    root = Path(root)
    if not root.is_dir():
        raise FileNotFoundError(f"root directory not found: {root}")

    pairs = discover_scored_run_pairs(root)
    if not pairs:
        raise ValueError(f"no scored run pairs found under {root}")

    runs: list[dict[str, Any]] = []
    aggregate_records: list[ScoringRecord] = []
    for scores_path, results_path in pairs:
        records = [ScoringRecord.from_dict(row) for row in read_jsonl(scores_path)]
        payload = _build_taxonomy_payload(
            records,
            source={
                "scores": str(scores_path),
                "results": str(results_path),
                "relative_path": str(scores_path.parent.relative_to(root)),
            },
            sample_limit=sample_limit,
        )
        runs.append(payload)
        aggregate_records.extend(
            record
            for record in records
            if record.failure_stage is FailureStage.CERTIFICATE_INVALID
        )

    aggregate = _build_taxonomy_payload(
        aggregate_records,
        source={"root": str(root), "runs": len(runs)},
        sample_limit=sample_limit,
        include_failure_stage_summary=False,
    )
    aggregate["label"] = "aggregate"

    return {
        "root": str(root),
        "run_count": len(runs),
        "runs": runs,
        "aggregate": aggregate,
    }


def discover_scored_run_pairs(root: Path) -> list[tuple[Path, Path]]:
    """Find ``(scores.jsonl, results.jsonl)`` pairs under ``root``."""
    pairs: list[tuple[Path, Path]] = []
    for scores_path in sorted(root.rglob("scores.jsonl")):
        results_path = scores_path.parent / "results.jsonl"
        if results_path.is_file():
            pairs.append((scores_path, results_path))
    return pairs


def format_failure_taxonomy_report(payload: dict[str, Any]) -> str:
    """Render a human-readable taxonomy summary."""
    if "runs" in payload:
        lines = [
            f"Failure taxonomy batch (root={payload['root']}, runs={payload['run_count']})",
            "=" * 48,
        ]
        aggregate = payload["aggregate"]
        lines.extend(_format_taxonomy_section(aggregate, title="Aggregate"))
        for run in payload["runs"]:
            rel = run["source"].get("relative_path", run["source"]["scores"])
            lines.extend(_format_taxonomy_section(run, title=f"Run {rel}"))
        return "\n".join(lines) + "\n"

    lines = [
        f"Failure taxonomy (n={payload['n']}, certificate_invalid={payload['certificate_invalid_count']})",
        "=" * 48,
    ]
    lines.extend(_format_taxonomy_section(payload))
    return "\n".join(lines) + "\n"


def _build_taxonomy_payload(
    records: list[ScoringRecord],
    *,
    source: dict[str, Any],
    sample_limit: int,
    include_failure_stage_summary: bool = True,
) -> dict[str, Any]:
    certificate_invalid = [
        record for record in records if record.failure_stage is FailureStage.CERTIFICATE_INVALID
    ]
    groups = _build_family_stage_groups(certificate_invalid, sample_limit=sample_limit)
    overall_taxonomy = _build_taxonomy_buckets(certificate_invalid, sample_limit=sample_limit)

    payload: dict[str, Any] = {
        "source": source,
        "n": len(records),
        "certificate_invalid_count": len(certificate_invalid),
        "groups": groups,
        "overall": {
            "failure_stage": _CERTIFICATE_INVALID,
            "n": len(certificate_invalid),
            "taxonomy": overall_taxonomy,
        },
    }
    if include_failure_stage_summary:
        payload["failure_stage_summary_by_family"] = _failure_stage_summary_by_family(records)
    return payload


def _build_family_stage_groups(
    records: list[ScoringRecord],
    *,
    sample_limit: int,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[ScoringRecord]] = defaultdict(list)
    for record in records:
        grouped[record.family].append(record)

    groups: list[dict[str, Any]] = []
    for family in sorted(grouped):
        family_records = grouped[family]
        groups.append(
            {
                "family": family,
                "failure_stage": _CERTIFICATE_INVALID,
                "n": len(family_records),
                "taxonomy": _build_taxonomy_buckets(
                    family_records,
                    sample_limit=sample_limit,
                ),
            }
        )
    return groups


def _build_taxonomy_buckets(
    records: list[ScoringRecord],
    *,
    sample_limit: int,
) -> dict[str, dict[str, Any]]:
    buckets: dict[str, list[str]] = {category: [] for category in TAXONOMY_CATEGORIES}
    for record in records:
        category = classify_certificate_errors(record.certificate_errors)
        buckets[category].append(record.item_id)

    total = len(records)
    return {
        category: TaxonomyBucket(
            count=len(item_ids),
            percentage=(len(item_ids) / total if total else 0.0),
            sample_item_ids=tuple(item_ids[:sample_limit]),
        ).to_dict()
        for category, item_ids in buckets.items()
    }


def _failure_stage_summary_by_family(records: list[ScoringRecord]) -> dict[str, dict[str, int]]:
    summary: dict[str, Counter[str]] = defaultdict(Counter)
    for record in records:
        summary[record.family][record.failure_stage.value] += 1
    return {
        family: {
            stage.value: counts.get(stage.value, 0) for stage in FailureStage
        }
        for family, counts in sorted(summary.items())
    }


def _format_taxonomy_section(payload: dict[str, Any], *, title: str | None = None) -> list[str]:
    lines: list[str] = []
    if title is not None:
        lines.extend(["", title, "-" * len(title)])
    lines.append(
        f"certificate_invalid: {payload['certificate_invalid_count']} / {payload['n']}"
    )
    taxonomy = payload["overall"]["taxonomy"]
    for category in TAXONOMY_CATEGORIES:
        bucket = taxonomy[category]
        if bucket["count"] == 0:
            continue
        lines.append(
            f"  {category}: {bucket['count']} ({bucket['percentage']:.1%}) "
            f"sample={bucket['sample_item_ids']}"
        )
    return lines


def _validate_results_path(results_path: Path) -> None:
    if not results_path.is_file():
        raise FileNotFoundError(f"results JSONL not found: {results_path}")
