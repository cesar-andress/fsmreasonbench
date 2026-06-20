"""Exploratory cohort validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fsmreasonbench.cohort.freeze import (
    COHORT_ARTIFACT_FILES,
    compute_cohort_fingerprint,
    hash_file,
    hash_jsonl_line,
    item_from_record,
)
from fsmreasonbench.evaluator.io import load_json
from fsmreasonbench.evaluator.jsonl import read_jsonl
from fsmreasonbench.items.assembly import self_verify_item


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Outcome of cohort directory validation."""

    cohort_dir: str
    valid: bool
    errors: tuple[str, ...] = field(default_factory=tuple)
    manifest: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "cohort_dir": self.cohort_dir,
            "valid": self.valid,
            "errors": list(self.errors),
            "manifest": self.manifest,
        }


def validate_cohort(cohort_dir: str | Path) -> ValidationReport:
    """Validate an exploratory cohort directory."""
    cohort_dir = Path(cohort_dir).resolve()
    errors: list[str] = []

    if not cohort_dir.is_dir():
        return ValidationReport(
            cohort_dir=str(cohort_dir),
            valid=False,
            errors=(f"cohort directory not found: {cohort_dir}",),
        )

    for name in COHORT_ARTIFACT_FILES:
        path = cohort_dir / name
        if not path.is_file():
            errors.append(f"missing required file: {name}")

    if errors:
        return ValidationReport(cohort_dir=str(cohort_dir), valid=False, errors=tuple(errors))

    manifest_path = cohort_dir / "manifest.json"
    checksums_path = cohort_dir / "sha256sums.txt"
    items_path = cohort_dir / "items.jsonl"

    manifest = load_json(manifest_path)
    _validate_checksums(cohort_dir, checksums_path, errors)
    _validate_manifest_fields(manifest, errors)
    _validate_items_file(items_path, manifest, errors)

    expected_fingerprint = compute_cohort_fingerprint(manifest["items"])
    if manifest.get("cohort_fingerprint") != expected_fingerprint:
        errors.append("cohort_fingerprint mismatch")

    return ValidationReport(
        cohort_dir=str(cohort_dir),
        valid=not errors,
        errors=tuple(errors),
        manifest=manifest,
    )


def format_validation_report(report: ValidationReport) -> str:
    status = "VALID" if report.valid else "INVALID"
    lines = [f"Cohort validation: {status}", f"Directory: {report.cohort_dir}"]
    if report.manifest is not None:
        lines.append(f"cohort_id: {report.manifest.get('cohort_id', '<missing>')}")
        lines.append(f"item_count: {report.manifest.get('item_count', '<missing>')}")
    if report.errors:
        lines.append("Errors:")
        lines.extend(f"  - {error}" for error in report.errors)
    return "\n".join(lines) + "\n"


def _validate_checksums(cohort_dir: Path, checksums_path: Path, errors: list[str]) -> None:
    entries = _parse_sha256sums(checksums_path)
    if not entries:
        errors.append("sha256sums.txt contains no entries")
        return

    listed = {name for _, name in entries}
    for name in ("items.jsonl", "manifest.json", "README.md"):
        if name not in listed:
            errors.append(f"sha256sums.txt missing entry for {name}")

    for digest, name in entries:
        path = cohort_dir / name
        if not path.is_file():
            errors.append(f"sha256sums references missing file: {name}")
            continue
        actual = hash_file(path)
        if actual != digest:
            errors.append(f"checksum mismatch for {name}")


def _validate_manifest_fields(manifest: dict[str, Any], errors: list[str]) -> None:
    required = (
        "manifest_version",
        "cohort_id",
        "created_at",
        "item_count",
        "family_counts",
        "difficulty_summary",
        "source_items_path",
        "generator_notes",
        "items",
        "cohort_fingerprint",
    )
    for key in required:
        if key not in manifest:
            errors.append(f"manifest.json missing field: {key}")

    items = manifest.get("items")
    if not isinstance(items, list):
        errors.append("manifest.items must be an array")
        return

    if manifest.get("item_count") != len(items):
        errors.append(
            "item_count mismatch: "
            f"manifest={manifest.get('item_count')}, items={len(items)}"
        )


def _validate_items_file(
    items_path: Path,
    manifest: dict[str, Any],
    errors: list[str],
) -> None:
    records = read_jsonl(items_path)
    manifest_items = manifest.get("items", [])
    if len(records) != len(manifest_items):
        errors.append(
            "items.jsonl count mismatch: "
            f"file={len(records)}, manifest={len(manifest_items)}"
        )

    manifest_by_id = {entry["item_id"]: entry for entry in manifest_items if "item_id" in entry}
    lines = items_path.read_text(encoding="utf-8").splitlines()
    if len(lines) != len(records):
        errors.append("items.jsonl contains blank or malformed lines")

    seen_ids: set[str] = set()
    for index, (record, line) in enumerate(zip(records, lines, strict=False), start=1):
        item_id = record.get("item_id")
        if not isinstance(item_id, str):
            errors.append(f"items.jsonl line {index}: missing item_id")
            continue
        if item_id in seen_ids:
            errors.append(f"duplicate item_id in items.jsonl: {item_id}")
        seen_ids.add(item_id)

        if not line.strip():
            errors.append(f"items.jsonl line {index}: blank line")
            continue

        expected_entry = manifest_by_id.get(item_id)
        if expected_entry is None:
            errors.append(f"manifest missing item entry for {item_id}")
        else:
            actual_hash = hash_jsonl_line(line)
            if expected_entry.get("sha256") != actual_hash:
                errors.append(f"item sha256 mismatch for {item_id}")

        try:
            item = item_from_record(record)
            self_verify_item(item)
        except (AssertionError, ValueError, KeyError) as exc:
            errors.append(f"self-verify failed for {item_id}: {exc}")


def _parse_sha256sums(path: Path) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 2:
            raise ValueError(f"invalid sha256sums line {line_number}: {raw_line!r}")
        entries.append((parts[0], parts[1]))
    return entries
