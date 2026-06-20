"""Exploratory cohort freeze and validation tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fsmreasonbench.cli.freeze_cohort import main as freeze_cohort_main
from fsmreasonbench.cli.validate_cohort import main as validate_cohort_main
from fsmreasonbench.cohort.freeze import freeze_cohort, hash_file
from fsmreasonbench.cohort.validate import validate_cohort
from fsmreasonbench.evaluator.batch import generate_c2_batch, generate_f1_batch
from fsmreasonbench.evaluator.jsonl import write_jsonl
from fsmreasonbench.generator.reachability import ReachabilityGeneratorConfig
from fsmreasonbench.generator.separation import SeparationGeneratorConfig


def _write_items(path: Path, family: str) -> None:
    if family == "C2":
        items = generate_c2_batch(3, seed=11, config=ReachabilityGeneratorConfig(state_count=4))
    else:
        items = generate_f1_batch(
            3,
            seed=21,
            config=SeparationGeneratorConfig(
                min_distinguishing_trace_length=2,
                max_distinguishing_trace_length=4,
                include_equivalent=True,
                equivalent_ratio=0.5,
            ),
        )
    write_jsonl(path, (item.to_full_dict() for item in items))


def test_freeze_cohort_writes_manifest_checksums_and_readme(tmp_path: Path) -> None:
    source = tmp_path / "source_items.jsonl"
    out_dir = tmp_path / "cohort"
    _write_items(source, "F1")

    manifest = freeze_cohort(
        source,
        "f1-test-v0.1-exploratory",
        out_dir,
        generator_notes="Synthetic F1 batch for unit tests.",
    )

    assert (out_dir / "items.jsonl").is_file()
    assert (out_dir / "manifest.json").is_file()
    assert (out_dir / "sha256sums.txt").is_file()
    assert (out_dir / "README.md").is_file()
    assert manifest["item_count"] == 3
    assert manifest["family_counts"] == {"F1": 3}
    assert manifest["release_tier"] == "exploratory"
    assert manifest["manifest_version"] == "0.1-exploratory"
    assert manifest["generator_notes"] == "Synthetic F1 batch for unit tests."
    assert len(manifest["items"]) == 3
    assert "F1" in manifest["difficulty_summary"]
    assert manifest["cohort_fingerprint"]


def test_validate_cohort_passes_for_fresh_freeze(tmp_path: Path) -> None:
    source = tmp_path / "c2_items.jsonl"
    out_dir = tmp_path / "cohort"
    _write_items(source, "C2")
    freeze_cohort(source, "c2-test-v0.1-exploratory", out_dir)

    report = validate_cohort(out_dir)
    assert report.valid, report.errors
    assert report.manifest is not None
    assert report.manifest["item_count"] == 3
    assert report.manifest["family_counts"] == {"C2": 3}


def test_validate_cohort_detects_checksum_and_self_verify_failures(tmp_path: Path) -> None:
    source = tmp_path / "c2_items.jsonl"
    out_dir = tmp_path / "cohort"
    _write_items(source, "C2")
    freeze_cohort(source, "c2-test-v0.1-exploratory", out_dir)

    readme_path = out_dir / "README.md"
    readme_path.write_text(readme_path.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8")
    report = validate_cohort(out_dir)
    assert not report.valid
    assert any("checksum mismatch" in error for error in report.errors)

    freeze_cohort(source, "c2-test-v0.1-exploratory", out_dir)
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    manifest["item_count"] = 999
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    checksums = (out_dir / "sha256sums.txt").read_text(encoding="utf-8").splitlines()
    checksums = [
        f"{hash_file(out_dir / 'manifest.json')}  manifest.json" if line.endswith("manifest.json") else line
        for line in checksums
    ]
    (out_dir / "sha256sums.txt").write_text("\n".join(checksums) + "\n", encoding="utf-8")

    report = validate_cohort(out_dir)
    assert not report.valid
    assert any("item_count mismatch" in error for error in report.errors)


def test_freeze_and_validate_clis(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "items.jsonl"
    out_dir = tmp_path / "out"
    _write_items(source, "F1")

    assert (
        freeze_cohort_main(
            [
                "--items",
                str(source),
                "--cohort-id",
                "cli-test-v0.1-exploratory",
                "--out-dir",
                str(out_dir),
                "--generator-notes",
                "CLI test cohort",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["item_count"] == 3

    assert validate_cohort_main(["--cohort-dir", str(out_dir)]) == 0
    assert "VALID" in capsys.readouterr().out
