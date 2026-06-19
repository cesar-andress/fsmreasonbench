"""Tests for artifact health checks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fsmreasonbench.cli.artifact_health import main as artifact_health_main
from fsmreasonbench.dev.artifact_health import (
    build_artifact_health_report,
    discover_schemas,
    format_artifact_health_report,
    verify_example_items,
)


def test_discover_schemas_finds_repo_schemas() -> None:
    from fsmreasonbench.dev.doc_consistency import find_repo_root

    repo = find_repo_root()
    schemas = discover_schemas(repo)
    assert "schema/fsm.schema.json" in schemas
    assert "schema/certificate/reachability.schema.json" in schemas


def test_verify_example_items_in_real_repo() -> None:
    from fsmreasonbench.dev.doc_consistency import find_repo_root

    repo = find_repo_root()
    results = verify_example_items(repo)
    assert results
    assert all(result.ok for result in results), results


def test_build_report_ok_in_real_repo() -> None:
    from fsmreasonbench.dev.doc_consistency import find_repo_root

    report = build_artifact_health_report(find_repo_root())
    assert report.package_version
    assert ("C2", "calibration") in report.families
    assert ("F1", "flagship") in report.families
    assert report.schemas
    assert report.ok


def test_format_report_includes_sections() -> None:
    from fsmreasonbench.dev.doc_consistency import find_repo_root

    report = build_artifact_health_report(find_repo_root())
    text = format_artifact_health_report(report)
    assert "Package version:" in text
    assert "Available families:" in text
    assert "Schemas present" in text
    assert "Example items (self-verify):" in text
    assert "Tests:" in text


def test_min_repo_missing_examples_marks_unhealthy(tmp_path: Path) -> None:
    repo = _make_min_repo(tmp_path)
    report = build_artifact_health_report(repo)
    assert not report.ok
    assert report.examples == ()


def test_min_repo_with_valid_example(tmp_path: Path) -> None:
    from fsmreasonbench.dev.doc_consistency import find_repo_root

    repo = find_repo_root()
    source = repo / "examples" / "item_C2_reachability_seed42.json"
    target_repo = _make_min_repo(tmp_path)
    examples = target_repo / "examples"
    examples.mkdir(exist_ok=True)
    (examples / "item_C2_reachability_seed42.json").write_text(
        source.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    report = build_artifact_health_report(target_repo)
    assert len(report.examples) == 1
    assert report.examples[0].ok


def test_cli_on_real_repo(capsys: pytest.CaptureFixture[str]) -> None:
    rc = artifact_health_main([])
    assert rc == 0
    out = capsys.readouterr().out
    assert "artifact health" in out.lower()
    assert "pytest" in out


def test_cli_fails_when_example_invalid(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _make_min_repo(tmp_path)
    examples = repo / "examples"
    examples.mkdir(exist_ok=True)
    (examples / "item_bad.json").write_text(
        json.dumps({"family": "C2", "item_id": "x", "answer_key": {}}),
        encoding="utf-8",
    )
    rc = artifact_health_main(["--repo-root", str(repo)])
    assert rc == 1
    assert "FAIL" in capsys.readouterr().out


def _make_min_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "schema" / "certificate").mkdir(parents=True)
    (repo / "examples").mkdir(parents=True)
    (repo / "src" / "fsmreasonbench").mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname='fsmreasonbench'\n", encoding="utf-8")
    (repo / "schema" / "fsm.schema.json").write_text("{}", encoding="utf-8")
    (repo / "schema" / "VERSION").write_text("1.0.0-draft\n", encoding="utf-8")
    return repo
