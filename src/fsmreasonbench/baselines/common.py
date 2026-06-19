"""Shared malformed baseline output."""

from __future__ import annotations

from fsmreasonbench.items.assembly import BenchmarkItem


def run_invalid_baseline(item: BenchmarkItem) -> str:
    """Malformed response for extractability-gate testing."""
    return f"NOT VALID JSON {{ item_id: {item.item_id}, verdict: maybe }}"
