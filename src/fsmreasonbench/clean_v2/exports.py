"""Exports and guards for clean_v2 model-performance tables."""

from __future__ import annotations

from typing import Any

from fsmreasonbench.clean_v2.provenance import (
    WitnessOrigin,
    assert_model_performance_row_allowed,
)


def export_primary_model_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Hard-guard export: only model_generated rows; raises on system/injected."""
    exported: list[dict[str, Any]] = []
    for row in rows:
        if row.get("export_class") == "system_level":
            continue
        assert_model_performance_row_allowed(row)
        exported.append(row)
    return exported


def export_system_level_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Explicit system-level export for SYS_CEILING / runner_injected diagnostics."""
    kept = []
    for row in rows:
        origin = (row.get("witness_provenance") or {}).get("witness_origin")
        if origin in {
            WitnessOrigin.TOOL_CONSTRUCTED.value,
            WitnessOrigin.RUNNER_INJECTED.value,
        } or row.get("export_class") == "system_level":
            kept.append(row)
    return kept
