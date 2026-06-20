"""Exploratory cohort freeze workflow."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.evaluator.jsonl import read_jsonl, write_jsonl
from fsmreasonbench.items.assembly import BenchmarkItem, self_verify_item
from fsmreasonbench.models.serialization import content_hash

COHORT_ARTIFACT_FILES: tuple[str, ...] = (
    "items.jsonl",
    "manifest.json",
    "sha256sums.txt",
    "README.md",
)
MANIFEST_VERSION = "0.1-exploratory"
RELEASE_TIER = "exploratory"


def freeze_cohort(
    items_path: str | Path,
    cohort_id: str,
    out_dir: str | Path,
    *,
    generator_notes: str | None = None,
    created_at: datetime | None = None,
) -> dict[str, Any]:
    """Copy and seal an exploratory cohort with manifest and checksums."""
    items_path = Path(items_path).resolve()
    out_dir = Path(out_dir)
    if not items_path.is_file():
        raise FileNotFoundError(f"items JSONL not found: {items_path}")
    if not cohort_id.strip():
        raise ValueError("cohort_id must be non-empty")

    raw_records = read_jsonl(items_path)
    if not raw_records:
        raise ValueError(f"items JSONL is empty: {items_path}")

    items = [item_from_record(record) for record in raw_records]
    for item in items:
        self_verify_item(item)

    out_dir.mkdir(parents=True, exist_ok=True)
    items_out = out_dir / "items.jsonl"
    write_jsonl(items_out, raw_records)

    item_entries = _build_item_entries(items_out, items)
    manifest_body = {
        "manifest_version": MANIFEST_VERSION,
        "release_tier": RELEASE_TIER,
        "cohort_id": cohort_id,
        "created_at": _format_timestamp(created_at or datetime.now(tz=UTC)),
        "item_count": len(items),
        "family_counts": dict(sorted(Counter(item.family for item in items).items())),
        "difficulty_summary": build_difficulty_summary(items),
        "source_items_path": str(items_path),
        "generator_notes": generator_notes or default_generator_notes(items, items_path),
        "items": item_entries,
    }
    manifest_body["cohort_fingerprint"] = compute_cohort_fingerprint(item_entries)

    manifest_path = out_dir / "manifest.json"
    dump_json(manifest_path, manifest_body)

    readme_path = out_dir / "README.md"
    readme_path.write_text(
        render_cohort_readme(cohort_id=cohort_id, manifest=manifest_body),
        encoding="utf-8",
    )

    checksums_path = out_dir / "sha256sums.txt"
    checksums_path.write_text(
        render_sha256sums(out_dir, files=("items.jsonl", "manifest.json", "README.md")),
        encoding="utf-8",
    )

    return manifest_body


def item_from_record(record: dict[str, Any]) -> BenchmarkItem:
    from fsmreasonbench.evaluator.io import item_from_dict

    return item_from_dict(record)


def canonical_jsonl_line(record: dict[str, Any]) -> str:
    return json.dumps(record, sort_keys=True)


def hash_jsonl_line(line: str) -> str:
    return hashlib.sha256(line.encode("utf-8")).hexdigest()


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_difficulty_summary(items: list[BenchmarkItem]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        grouped.setdefault(item.family, []).append(item.difficulty)

    for family in sorted(grouped):
        difficulties = grouped[family]
        family_summary: dict[str, Any] = {
            "item_count": len(difficulties),
            "generator_seed_range": _seed_range(difficulties),
        }
        cores = [entry.get("core", {}) for entry in difficulties if isinstance(entry.get("core"), dict)]
        if family == "F1":
            equivalent = [core.get("equivalent") for core in cores]
            family_summary["equivalent_count"] = sum(1 for value in equivalent if value is True)
            family_summary["non_equivalent_count"] = sum(1 for value in equivalent if value is False)
            trace_lengths = [
                core["distinguishing_trace_length"]
                for core in cores
                if core.get("equivalent") is False and "distinguishing_trace_length" in core
            ]
            if trace_lengths:
                family_summary["distinguishing_trace_length"] = _numeric_stats(trace_lengths)
        elif family == "C2":
            witness_lengths = [
                core["witness_length"] for core in cores if "witness_length" in core
            ]
            state_counts = [core["|Q|"] for core in cores if "|Q|" in core]
            if witness_lengths:
                family_summary["witness_length"] = _numeric_stats(witness_lengths)
            if state_counts:
                family_summary["state_count"] = _numeric_stats(state_counts)
        summary[family] = family_summary
    return summary


def default_generator_notes(items: list[BenchmarkItem], source_path: Path) -> str:
    families = ", ".join(sorted({item.family for item in items}))
    return (
        f"Exploratory cohort frozen from source JSONL ({source_path.name}). "
        f"Families: {families}. Every item passed self_verify_item at freeze time. "
        "This snapshot is not a Zenodo release and carries no DOI."
    )


def compute_cohort_fingerprint(item_entries: list[dict[str, str]]) -> str:
    payload = [
        {"item_id": entry["item_id"], "sha256": entry["sha256"]}
        for entry in sorted(item_entries, key=lambda entry: entry["item_id"])
    ]
    return content_hash({"items": payload})


def render_sha256sums(cohort_dir: Path, *, files: tuple[str, ...]) -> str:
    lines = [f"{hash_file(cohort_dir / name)}  {name}" for name in files]
    return "\n".join(lines) + "\n"


def render_cohort_readme(*, cohort_id: str, manifest: dict[str, Any]) -> str:
    families = ", ".join(f"{family} ({count})" for family, count in manifest["family_counts"].items())
    return f"""# Exploratory cohort `{cohort_id}`

**Release tier:** {manifest["release_tier"]}  
**Manifest version:** {manifest["manifest_version"]}  
**Created:** {manifest["created_at"]}  
**Item count:** {manifest["item_count"]}  
**Families:** {families}

This directory is a **non-final, pre-Zenodo cohort snapshot** for reproducible exploratory
studies. It is not version `v1.0-public`, has no DOI, and must not be cited as a final
benchmark result.

## Contents

| File | Purpose |
|------|---------|
| `items.jsonl` | Full benchmark items (including answer keys) |
| `manifest.json` | Cohort metadata, per-item SHA-256 digests, aggregate fingerprint |
| `sha256sums.txt` | Checksums for bundled files |
| `README.md` | This file |

## Validate integrity

```bash
python -m fsmreasonbench.cli.validate_cohort --cohort-dir .
```

## Generator notes

{manifest["generator_notes"]}

## Fingerprint

`cohort_fingerprint`: `{manifest["cohort_fingerprint"]}`
"""


def _build_item_entries(items_path: Path, items: list[BenchmarkItem]) -> list[dict[str, str]]:
    lines = items_path.read_text(encoding="utf-8").splitlines()
    if len(lines) != len(items):
        raise ValueError("items.jsonl line count mismatch after write")

    entries: list[dict[str, str]] = []
    for item, line in zip(items, lines, strict=True):
        if not line.strip():
            raise ValueError("items.jsonl contains blank line")
        entries.append(
            {
                "item_id": item.item_id,
                "family": item.family,
                "sha256": hash_jsonl_line(line),
            }
        )
    return entries


def _numeric_stats(values: list[int]) -> dict[str, int | float]:
    return {
        "min": min(values),
        "max": max(values),
        "mean": sum(values) / len(values),
    }


def _seed_range(difficulties: list[dict[str, Any]]) -> dict[str, int] | None:
    seeds = [entry["generator_seed"] for entry in difficulties if "generator_seed" in entry]
    if not seeds:
        return None
    return {"min": min(seeds), "max": max(seeds)}


def _format_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
