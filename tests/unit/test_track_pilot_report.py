"""Track pilot markdown report rendering tests."""

from __future__ import annotations

from fsmreasonbench.runners.track_pilot_models import render_track_pilot_report


def _sample_payload() -> dict:
    return {
        "experiment": "local_matrix",
        "models": ["mock"],
        "families": ["C2"],
        "tracks": ["R0", "R1"],
        "temperatures": [0.0],
        "max_items": 20,
        "timeout": 120.0,
        "cohort_ids": {"C2": "test-c2", "F1": "test-f1"},
        "cell_status_counts": {"completed": 2},
        "track_rows": [
            {
                "model": "mock",
                "family": "C2",
                "track": "R0",
                "temperature": 0.0,
                "n": 20,
                "extractability_rate": 1.0,
                "verdict_accuracy": 0.5,
                "certificate_valid_rate": 0.25,
                "fully_correct_rate": 0.25,
                "tool_invocation_rate": 0.0,
                "average_tool_calls_per_item": 0.0,
                "failure_stage_counts": {
                    "not_extractable": 0,
                    "verdict_wrong": 10,
                    "certificate_invalid": 5,
                    "correct": 5,
                },
                "track_failure_counts": {},
                "status": "completed",
            },
            {
                "model": "mock",
                "family": "C2",
                "track": "R1",
                "temperature": 0.0,
                "n": 20,
                "extractability_rate": 0.0,
                "verdict_accuracy": 0.0,
                "certificate_valid_rate": 0.0,
                "fully_correct_rate": 0.0,
                "tool_invocation_rate": 1.0,
                "average_tool_calls_per_item": 3.0,
                "failure_stage_counts": {
                    "not_extractable": 20,
                    "verdict_wrong": 0,
                    "certificate_invalid": 0,
                    "correct": 0,
                },
                "track_failure_counts": {
                    "tool_execution_error": 18,
                    "final_submission_not_extractable": 0,
                    "verdict_wrong": 0,
                    "certificate_invalid": 2,
                    "correct": 0,
                    "no_tool_plan": 0,
                    "invalid_tool_plan": 0,
                    "disallowed_tool": 0,
                },
                "status": "completed",
            },
        ],
        "delegation_rows": [],
        "temperature_delta_rows": [],
        "incomplete_cells": [],
    }


def test_per_track_metrics_table_is_populated() -> None:
    report = render_track_pilot_report(_sample_payload())
    assert "| `mock` | 0 | R0 | 20 | 1.000 (20/20) |" in report
    assert "| `mock` | 0 | R1 | 20 | 0.000 (0/20) |" in report


def test_failure_movement_uses_failure_stage_not_extractable() -> None:
    report = render_track_pilot_report(_sample_payload())
    assert "## C2 — failure movement (failure_stage_counts)" in report
    assert "| `mock` | 0 | R1 | 20 | 0 | 0 | 0 |" in report


def test_zero_extractable_shows_undefined_rates() -> None:
    report = render_track_pilot_report(_sample_payload())
    assert "undefined (0 extractable)" in report
    assert "### Low-extractability cells (unsafe for reasoning comparisons)" in report
    assert "UNSAFE (<50% extractable)" in report


def test_metric_denominators_documented() -> None:
    report = render_track_pilot_report(_sample_payload())
    assert "### Metric denominators" in report
    assert "fully_correct_rate:** fully correct items / total n" in report
    assert "0.250 (5/20)" in report
