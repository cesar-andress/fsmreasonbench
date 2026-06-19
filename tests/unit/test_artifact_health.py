"""Tests for artifact health checks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fsmreasonbench.cli.artifact_health import main as artifact_health_main
from fsmreasonbench.dev.artifact_health import (
    REQUIRED_SCHEMAS,
    build_artifact_health_report,
    check_required_schemas,
    format_artifact_health_report,
)


def test_build_report_passes_in_real_repo() -> None:
    from fsmreasonbench.dev.doc_consistency import find_repo_root

    report = build_artifact_health_report(find_repo_root())
    assert report.ok
    assert report.status == "PASS"
    check_names = {check.name for check in report.checks}
    assert check_names == {
        "package_import",
        "required_schemas",
        "example_items",
        "cli_imports",
    }
    assert all(check.ok for check in report.checks)


def test_format_report_includes_pass_fail_summary() -> None:
    from fsmreasonbench.dev.doc_consistency import find_repo_root

    report = build_artifact_health_report(find_repo_root())
    text = format_artifact_health_report(report)
    assert "[PASS] package_import" in text
    assert "[PASS] required_schemas" in text
    assert "[PASS] example_items" in text
    assert "[PASS] cli_imports" in text
    assert "Status: PASS" in text


def test_missing_schema_marks_report_unhealthy(tmp_path: Path) -> None:
    repo = _make_repo_with_schemas(tmp_path, omit="schema/question.schema.json")
    schema_check = check_required_schemas(repo)
    assert not schema_check.ok
    assert "schema/question.schema.json" in schema_check.message

    report = build_artifact_health_report(repo)
    assert not report.ok
    assert report.status == "FAIL"
    schema_report = next(check for check in report.checks if check.name == "required_schemas")
    assert not schema_report.ok


def test_json_output_shape(capsys: pytest.CaptureFixture[str]) -> None:
    rc = artifact_health_main(["--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "PASS"
    assert isinstance(payload["checks"], list)
    assert {check["name"] for check in payload["checks"]} == {
        "package_import",
        "required_schemas",
        "example_items",
        "cli_imports",
    }
    for check in payload["checks"]:
        assert isinstance(check["ok"], bool)
        assert isinstance(check["message"], str)


def test_cli_fails_when_required_schema_missing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _make_repo_with_schemas(tmp_path, omit="schema/answer.schema.json")
    rc = artifact_health_main(["--repo-root", str(repo), "--json"])
    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "FAIL"
    schema_check = next(check for check in payload["checks"] if check["name"] == "required_schemas")
    assert schema_check["ok"] is False
    assert "schema/answer.schema.json" in schema_check["message"]


def test_cli_success_on_real_repo(capsys: pytest.CaptureFixture[str]) -> None:
    rc = artifact_health_main([])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Status: PASS" in out


def _make_repo_with_schemas(tmp_path: Path, *, omit: str | None = None) -> Path:
    repo = tmp_path / "repo"
    for relative_path in REQUIRED_SCHEMAS:
        if relative_path == omit:
            continue
        path = repo / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
    (repo / "pyproject.toml").write_text("[project]\nname='fsmreasonbench'\n", encoding="utf-8")
    return repo
