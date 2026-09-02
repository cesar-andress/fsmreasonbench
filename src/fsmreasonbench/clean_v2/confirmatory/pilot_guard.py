"""Blinded engineering pilot report guard."""

from __future__ import annotations

import re
from typing import Any

# Forbidden scientific outputs in pilot reports.
FORBIDDEN_KEY_SUBSTRINGS = (
    "witness_valid_rate",
    "condition_wise",
    "paired_rd",
    "risk_difference",
    "p_value",
    "pvalue",
    "holm",
    "rq2_contrast",
    "rq3_contrast",
    "effect_estimate",
    "model_wise_effect",
    "mean_paired",
)

FORBIDDEN_PATTERNS = (
    re.compile(r"witness[_\s-]?valid.*\b(rate|by[_\s-]?condition)\b", re.I),
    re.compile(r"\bp\s*[=<>]\s*0\.\d+", re.I),
    re.compile(r"\bholmed?\b", re.I),
    re.compile(r"risk\s*difference", re.I),
    re.compile(r"RQ[123].*(contrast|effect|significant)", re.I),
)

ALLOWED_TOP_LEVEL_KEYS = frozenset(
    {
        "report_type",
        "blinded",
        "artifact_completeness",
        "schema_health",
        "aggregate_extraction_mechanics",
        "token_usage",
        "latency",
        "cost",
        "infrastructure_errors",
        "verifier_call_counts",
        "at_least_one_valid_witness_feasibility",
        "notes",
        "pilot_item_ids",
        "n_generations",
        "models_wired",
        "conditions_wired",
    }
)


def build_pilot_report(raw_metrics: dict[str, Any]) -> dict[str, Any]:
    """
    Construct a pilot report from engineering metrics only.

    Strips any scientific effect/rate keys. Feasibility bits are allowed only as
    aggregate at-least-one-valid-witness per feasible contract (not condition-wise rates).
    """
    report = {
        "report_type": "blinded_engineering_pilot",
        "blinded": True,
        "artifact_completeness": raw_metrics.get("artifact_completeness"),
        "schema_health": raw_metrics.get("schema_health"),
        "aggregate_extraction_mechanics": raw_metrics.get("aggregate_extraction_mechanics"),
        "token_usage": raw_metrics.get("token_usage"),
        "latency": raw_metrics.get("latency"),
        "cost": raw_metrics.get("cost"),
        "infrastructure_errors": raw_metrics.get("infrastructure_errors"),
        "verifier_call_counts": raw_metrics.get("verifier_call_counts"),
        "at_least_one_valid_witness_feasibility": raw_metrics.get(
            "at_least_one_valid_witness_feasibility"
        ),
        "pilot_item_ids": raw_metrics.get("pilot_item_ids"),
        "n_generations": raw_metrics.get("n_generations"),
        "models_wired": raw_metrics.get("models_wired"),
        "conditions_wired": raw_metrics.get("conditions_wired"),
        "notes": (
            "Pilot generations are excluded from confirmatory analysis. "
            "Pilot items remain in the confirmatory cohort. "
            "Condition-wise witness-valid rates and RQ contrasts are forbidden."
        ),
    }
    violations = validate_pilot_report(report)
    if violations:
        raise ValueError(f"pilot report guard rejected output: {violations}")
    return report


def validate_pilot_report(report: dict[str, Any] | str) -> list[str]:
    """Return list of guard violations (empty = ok)."""
    violations: list[str] = []
    if isinstance(report, str):
        blob = report
        for pat in FORBIDDEN_PATTERNS:
            if pat.search(blob):
                violations.append(f"forbidden_pattern:{pat.pattern}")
        return violations

    blob = str(report)
    for pat in FORBIDDEN_PATTERNS:
        if pat.search(blob):
            violations.append(f"forbidden_pattern:{pat.pattern}")

    def walk(obj: Any, path: str = "") -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                key = str(k).lower()
                for sub in FORBIDDEN_KEY_SUBSTRINGS:
                    if sub in key:
                        violations.append(f"forbidden_key:{path}.{k}")
                walk(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(v, f"{path}[{i}]")

    walk(report)
    # Disallow nested condition×model rate tables.
    if "per_condition" in report or "per_model_rates" in report:
        violations.append("forbidden_nested_rate_table")
    return violations


def assert_pilot_report_safe(report: dict[str, Any] | str) -> None:
    violations = validate_pilot_report(report)
    if violations:
        raise AssertionError(f"Pilot scientific leak: {violations}")
