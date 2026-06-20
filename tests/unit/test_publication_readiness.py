"""Tests for publication readiness reporting."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from fsmreasonbench.cli.publication_readiness import main as publication_readiness_main
from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.reporting.publication_readiness import (
    build_publication_readiness_report,
    render_publication_readiness_report,
    write_publication_readiness_report,
)


def test_build_report_on_real_repo() -> None:
    report = build_publication_readiness_report(find_repo_root())
    assert report.implemented_families == ("C2", "F1")
    assert report.exploratory_cohort_count >= 2
    assert report.dataset_card_present
    assert report.release_notes_present
    assert report.zenodo_docs_present
    assert report.cohorts
    assert all(cohort.validation_status == "PASS" for cohort in report.cohorts)


def test_render_report_is_deterministic_for_same_repo() -> None:
    repo = find_repo_root()
    first = render_publication_readiness_report(build_publication_readiness_report(repo))
    second = render_publication_readiness_report(build_publication_readiness_report(repo))
    assert first == second
    assert first.startswith("# Publication Readiness Report\n")


def test_write_report_creates_markdown(tmp_path: Path) -> None:
    repo = _make_minimal_repo(tmp_path / "repo")
    out_path = tmp_path / "report.md"
    report = write_publication_readiness_report(repo, out_path)
    assert out_path.is_file()
    text = out_path.read_text(encoding="utf-8")
    assert "# Publication Readiness Report" in text
    assert "docs/dataset_card.md" in text
    assert report.dataset_card_present


def test_synthetic_invalid_cohort_surfaces_open_issues(tmp_path: Path) -> None:
    repo = _make_minimal_repo(tmp_path / "repo")
    cohort_dir = repo / "cohorts/v0.1-exploratory/bad"
    cohort_dir.mkdir(parents=True)
    (cohort_dir / "manifest.json").write_text(
        json.dumps(
            {
                "manifest_version": "0.1-exploratory",
                "release_tier": "exploratory",
                "cohort_id": "bad-v0.1-exploratory",
                "created_at": "2026-01-01T00:00:00Z",
                "item_count": 0,
                "family_counts": {},
                "difficulty_summary": {},
                "source_items_path": "/tmp/items.jsonl",
                "generator_notes": "test",
                "items": [],
                "cohort_fingerprint": "deadbeef",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (cohort_dir / "sha256sums.txt").write_text("", encoding="utf-8")
    (cohort_dir / "README.md").write_text("# bad\n", encoding="utf-8")

    report = build_publication_readiness_report(repo)
    assert any("invalid cohort" in issue for issue in report.open_issues)
    assert any(entry.status == "FAIL" for entry in report.reproducibility_checklist)


def test_duplicate_cohort_ids_detected(tmp_path: Path) -> None:
    repo = _make_minimal_repo(tmp_path / "repo")
    for name in ("a", "b"):
        cohort_dir = repo / f"cohorts/dup/{name}"
        cohort_dir.mkdir(parents=True)
        _write_minimal_valid_cohort(cohort_dir, cohort_id="dup-id")

    report = build_publication_readiness_report(repo)
    assert any("duplicate cohort_id" in issue for issue in report.open_issues)


def test_missing_manifest_reported(tmp_path: Path) -> None:
    repo = _make_minimal_repo(tmp_path / "repo")
    orphan = repo / "cohorts/orphan"
    orphan.mkdir(parents=True)
    (orphan / "items.jsonl").write_text("{}\n", encoding="utf-8")

    report = build_publication_readiness_report(repo)
    assert any("missing manifest.json" in issue for issue in report.open_issues)


def test_evidence_inventory_detects_docs_and_paper_tables(tmp_path: Path) -> None:
    repo = _make_minimal_repo(tmp_path / "repo")
    pilot = repo / "docs/pilot_v0_report.md"
    pilot.write_text("# pilot\n", encoding="utf-8")
    _set_mtime(pilot, "2026-01-02T10:00:00Z")

    paper_table = repo.parent / "paper/tables/pilot_metrics.tex"
    paper_table.parent.mkdir(parents=True, exist_ok=True)
    paper_table.write_text("% table\n", encoding="utf-8")
    _set_mtime(paper_table, "2026-01-03T11:00:00Z")

    report = build_publication_readiness_report(repo)
    paths = {artifact.path for artifact in report.evidence}
    assert "docs/pilot_v0_report.md" in paths
    assert "../paper/tables/pilot_metrics.tex" in paths


def test_cli_writes_report_and_returns_zero_on_missing_optional_docs(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _make_minimal_repo(tmp_path / "repo")
    out_path = tmp_path / "docs/publication_readiness.md"
    rc = publication_readiness_main(
        ["--repo-root", str(repo), "--out", str(out_path), "--json"]
    )
    assert rc == 0
    assert out_path.is_file()
    payload = json.loads(capsys.readouterr().out)
    assert payload["dataset_card_present"] is True
    assert payload["release_notes_present"] is False


def _make_minimal_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "pyproject.toml").write_text("[project]\nname='fsmreasonbench'\n", encoding="utf-8")
    (path / "src" / "fsmreasonbench").mkdir(parents=True, exist_ok=True)

    for relative in (
        "docs/dataset_card.md",
        "docs/specification/BENCHMARK_SPEC.md",
        "docs/specification/certificate_formats.md",
        "docs/zenodo/REPRODUCIBILITY.md",
        "docs/zenodo/RELEASE_CHECKLIST.md",
        "docs/zenodo/DATASET_STRUCTURE.md",
    ):
        file_path = path / relative
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(f"# {relative}\n", encoding="utf-8")
    return path


def _write_minimal_valid_cohort(cohort_dir: Path, *, cohort_id: str) -> None:
    items_path = cohort_dir / "items.jsonl"
    cohort_dir.mkdir(parents=True, exist_ok=True)
    items_path.write_text("", encoding="utf-8")
    manifest = {
        "manifest_version": "0.1-exploratory",
        "release_tier": "exploratory",
        "cohort_id": cohort_id,
        "created_at": "2026-01-01T00:00:00Z",
        "item_count": 0,
        "family_counts": {},
        "difficulty_summary": {},
        "source_items_path": str(items_path),
        "generator_notes": "test",
        "items": [],
        "cohort_fingerprint": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    }
    (cohort_dir / "manifest.json").write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
    (cohort_dir / "sha256sums.txt").write_text(
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  items.jsonl\n",
        encoding="utf-8",
    )
    (cohort_dir / "README.md").write_text(f"# {cohort_id}\n", encoding="utf-8")


def _set_mtime(path: Path, iso_timestamp: str) -> None:
    dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
    ts = dt.replace(tzinfo=UTC).timestamp()
    path.touch()
    import os

    os.utime(path, (ts, ts))
