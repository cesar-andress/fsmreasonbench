"""Hostile audit tests for bisimulation_witness verification."""

from __future__ import annotations

from fsmreasonbench.evaluator.f1_bisimulation_witness_verifier_audit import run_bisimulation_audit_battery


def test_bisimulation_audit_battery_all_pass() -> None:
    payload = run_bisimulation_audit_battery()
    assert payload["summary"]["all_passed"], payload["checks"]
