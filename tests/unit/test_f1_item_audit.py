"""Tests for F1 item audit diagnostics."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fsmreasonbench.cli.audit_f1_items import main as audit_f1_cli_main
from fsmreasonbench.evaluator.f1_item_audit import (
    audit_f1_item,
    is_simple_repeated_pattern,
    summarize_f1_audit,
    write_f1_audit_report,
)
from fsmreasonbench.evaluator.jsonl import write_jsonl
from fsmreasonbench.generator.separation import (
    SeparationGeneratorConfig,
    generate_separation_item,
)


def test_is_simple_repeated_pattern_detects_motifs() -> None:
    assert is_simple_repeated_pattern(("a",))
    assert is_simple_repeated_pattern(("b", "b", "b"))
    assert is_simple_repeated_pattern(("a", "b", "a", "b"))
    assert is_simple_repeated_pattern(("x", "y", "x", "y", "x", "y"))
    assert not is_simple_repeated_pattern(("a", "b", "c"))


def test_constructive_item_final_acceptance_only_difference() -> None:
    item = generate_separation_item(
        7,
        SeparationGeneratorConfig(
            min_distinguishing_trace_length=4,
            max_distinguishing_trace_length=4,
            target_distinguishing_trace_length=4,
            mode="constructive",
        ),
    )
    diagnostics = audit_f1_item(item)
    assert diagnostics.trace_length == 4
    assert diagnostics.final_acceptance_only_difference is True
    assert diagnostics.sink_transition_ratio > 0.5
    assert diagnostics.branching_along_witness == (3, 3, 3, 3)


def test_random_item_audit_runs() -> None:
    item = generate_separation_item(
        11,
        SeparationGeneratorConfig(
            min_distinguishing_trace_length=2,
            max_distinguishing_trace_length=2,
            mode="random",
        ),
    )
    diagnostics = audit_f1_item(item)
    assert diagnostics.trace_length == 2
    assert diagnostics.gold_distinguishing_trace


def test_summarize_f1_audit_metrics() -> None:
    constructive = audit_f1_item(
        generate_separation_item(
            3,
            SeparationGeneratorConfig(
                min_distinguishing_trace_length=3,
                max_distinguishing_trace_length=3,
                target_distinguishing_trace_length=3,
                mode="constructive",
            ),
        )
    )
    repeated = audit_f1_item(
        generate_separation_item(
            5,
            SeparationGeneratorConfig(
                min_distinguishing_trace_length=3,
                max_distinguishing_trace_length=3,
                target_distinguishing_trace_length=3,
                mode="constructive",
            ),
        )
    )
    summary = summarize_f1_audit([constructive, repeated])
    assert summary.n_items == 2
    assert summary.unique_gold_traces >= 1
    assert 0.0 <= summary.repeated_trace_rate <= 1.0
    assert summary.final_acceptance_only_rate == 1.0


def test_write_f1_audit_report_jsonl(tmp_path: Path) -> None:
    item = generate_separation_item(
        9,
        SeparationGeneratorConfig(
            min_distinguishing_trace_length=5,
            max_distinguishing_trace_length=5,
            target_distinguishing_trace_length=5,
            mode="constructive",
        ),
    )
    items_path = tmp_path / "items.jsonl"
    write_jsonl(items_path, [item.to_full_dict()])
    out_path = tmp_path / "audit.json"

    payload = write_f1_audit_report(str(items_path), str(out_path))
    assert out_path.exists()
    assert payload["summary"]["n_items"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["trace_length"] == 5


def test_audit_f1_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    item = generate_separation_item(
        13,
        SeparationGeneratorConfig(
            min_distinguishing_trace_length=3,
            max_distinguishing_trace_length=3,
            target_distinguishing_trace_length=3,
            mode="constructive",
        ),
    )
    items_path = tmp_path / "items.jsonl"
    out_path = tmp_path / "audit.json"
    write_jsonl(items_path, [item.to_full_dict()])

    rc = audit_f1_cli_main(["--items", str(items_path), "--out", str(out_path)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "repeated_trace_rate" in captured.out
    summary = json.loads(out_path.read_text(encoding="utf-8"))
    assert summary["summary"]["n_items"] == 1


def test_audit_rejects_non_f1_items(tmp_path: Path) -> None:
    from fsmreasonbench.generator.reachability import (
        ReachabilityGeneratorConfig,
        generate_reachability_item,
    )

    item = generate_reachability_item(1, ReachabilityGeneratorConfig(state_count=4))
    items_path = tmp_path / "items.jsonl"
    write_jsonl(items_path, [item.to_full_dict()])
    with pytest.raises(ValueError, match="family F1"):
        write_f1_audit_report(str(items_path), str(tmp_path / "audit.json"))
