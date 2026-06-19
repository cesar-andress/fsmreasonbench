"""Tests for documentation consistency checker."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from fsmreasonbench.cli.check_docs import main as check_docs_main
from fsmreasonbench.dev.doc_consistency import (
    CANONICAL_IMPLEMENTED_FAMILIES,
    check_documentation,
    cli_module_exists,
    format_report,
    resolve_doc_reference,
)


def test_cli_module_exists_for_generate_one(tmp_path: Path) -> None:
    repo = _make_min_repo(tmp_path)
    assert cli_module_exists(repo, "generate_one")


def test_cli_module_missing(tmp_path: Path) -> None:
    repo = _make_min_repo(tmp_path)
    assert not cli_module_exists(repo, "nonexistent_cli")


def test_detects_missing_cli_reference(tmp_path: Path) -> None:
    repo = _make_min_repo(tmp_path)
    doc = repo / "docs" / "broken.md"
    doc.write_text(
        "Run `python -m fsmreasonbench.cli.missing_cli_tool --help`.\n",
        encoding="utf-8",
    )
    report = check_documentation(repo)
    kinds = {issue.kind for issue in report.issues}
    assert "missing_cli" in kinds


def test_detects_missing_file_reference(tmp_path: Path) -> None:
    repo = _make_min_repo(tmp_path)
    doc = repo / "docs" / "broken.md"
    doc.write_text("See [`examples/does_not_exist.json`](examples/does_not_exist.json).\n", encoding="utf-8")
    report = check_documentation(repo)
    assert any(issue.kind == "missing_file" for issue in report.issues)


def test_passes_for_valid_repo_layout(tmp_path: Path) -> None:
    repo = _make_min_repo(tmp_path)
    report = check_documentation(repo)
    assert report.ok, format_report(report)


def test_family_status_requires_c2_and_f1(tmp_path: Path) -> None:
    repo = _make_min_repo(tmp_path)
    status = repo / "PROJECT_STATUS.md"
    status.write_text("# Status\n\nOnly partial content.\n", encoding="utf-8")
    report = check_documentation(repo)
    assert any(issue.kind == "family_status" for issue in report.issues)


def test_family_cli_flags_invalid_family_arg(tmp_path: Path) -> None:
    repo = _make_min_repo(tmp_path)
    doc = repo / "docs" / "broken.md"
    doc.write_text(
        "PYTHONPATH=src python -m fsmreasonbench.cli.generate_one --family T2 --seed 1\n",
        encoding="utf-8",
    )
    report = check_documentation(repo)
    assert any(issue.kind == "family_cli" for issue in report.issues)


def test_resolve_doc_reference_finds_cli_module(tmp_path: Path) -> None:
    repo = _make_min_repo(tmp_path)
    doc = repo / "docs" / "guide.md"
    resolved = resolve_doc_reference(repo, doc, "generate_one.py")
    assert resolved is not None
    assert resolved.name == "generate_one.py"


def test_resolve_skips_runtime_output_basenames(tmp_path: Path) -> None:
    repo = _make_min_repo(tmp_path)
    doc = repo / "examples" / "README.md"
    assert resolve_doc_reference(repo, doc, "combined_summary.json") is None


def test_check_docs_cli_passes_on_min_repo(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _make_min_repo(tmp_path)
    rc = check_docs_main(["--repo-root", str(repo)])
    assert rc == 0
    assert "passed" in capsys.readouterr().out.lower()


def test_check_docs_cli_fails_on_broken_doc(tmp_path: Path) -> None:
    repo = _make_min_repo(tmp_path)
    (repo / "docs" / "broken.md").write_text(
        "python -m fsmreasonbench.cli.not_a_real_cli\n",
        encoding="utf-8",
    )
    rc = check_docs_main(["--repo-root", str(repo)])
    assert rc == 1


def test_canonical_implemented_families() -> None:
    assert CANONICAL_IMPLEMENTED_FAMILIES == frozenset({"C2", "F1"})


def _make_min_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "src" / "fsmreasonbench" / "cli").mkdir(parents=True)
    (repo / "src" / "fsmreasonbench" / "dev").mkdir(parents=True)
    (repo / "docs" / "zenodo").mkdir(parents=True)
    (repo / "examples").mkdir(parents=True)

    (repo / "pyproject.toml").write_text("[project]\nname='fsmreasonbench'\n", encoding="utf-8")
    (repo / "src" / "fsmreasonbench" / "cli" / "generate_one.py").write_text(
        "def main(): return 0\n",
        encoding="utf-8",
    )
    (repo / "src" / "fsmreasonbench" / "cli" / "check_docs.py").write_text(
        "def main(): return 0\n",
        encoding="utf-8",
    )
    (repo / "README.md").write_text(
        textwrap.dedent(
            """
            # FSMReasonBench

            Implemented families: C2 calibration, F1 flagship.
            `python -m fsmreasonbench.cli.generate_one --family C2 --seed 1`
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (repo / "PROJECT_STATUS.md").write_text(
        "Implemented families: C2 and F1.\n",
        encoding="utf-8",
    )
    (repo / "examples" / "README.md").write_text(
        "Families C2 and F1.\n",
        encoding="utf-8",
    )
    (repo / "docs" / "zenodo" / "README.md").write_text(
        "Implemented: C2, F1.\n",
        encoding="utf-8",
    )
    return repo
