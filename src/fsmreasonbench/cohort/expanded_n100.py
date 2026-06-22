"""Generate and freeze v0.1-expanded-n100 exploratory cohorts (100 items each)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fsmreasonbench.cohort.freeze import freeze_cohort
from fsmreasonbench.cohort.validate import validate_cohort
from fsmreasonbench.evaluator.batch import assert_unique_item_ids, generate_c2_batch
from fsmreasonbench.evaluator.jsonl import read_jsonl, write_jsonl
from fsmreasonbench.generator.reachability import ReachabilityGeneratorConfig
from fsmreasonbench.generator.separation import (
    SeparationGeneratorConfig,
    generate_separation_item,
)
from fsmreasonbench.items.assembly import BenchmarkItem

EXPANDED_COHORT_VERSION = "v0.1-expanded-n100"
EXPANDED_COHORT_ROOT = f"cohorts/{EXPANDED_COHORT_VERSION}"
C2_SUBDIR = "c2-reachability-level3"
F1_SUBDIR = "f1-mixed-level3"
C2_COHORT_ID = "c2-reachability-level3-v0.1-expanded-n100"
F1_COHORT_ID = "f1-mixed-level3-v0.1-expanded-n100"
DEFAULT_ITEM_COUNT = 100

# Seeds are disjoint from v0.1-exploratory (C2 batch seed 3001 × 20; F1 seeds 103001–103020).
C2_BATCH_SEED = 4001
F1_SEED_START = 203001

C2_GENERATOR_CONFIG = ReachabilityGeneratorConfig(
    min_witness_length=3,
    max_witness_length=12,
)
F1_GENERATOR_CONFIG = SeparationGeneratorConfig(
    min_distinguishing_trace_length=3,
    max_distinguishing_trace_length=3,
    include_equivalent=True,
    equivalent_ratio=0.5,
)

C2_GENERATION_PARAMETERS: dict[str, Any] = {
    "family": "C2",
    "generator": "fsmreasonbench.generator.reachability",
    "batch_seed": C2_BATCH_SEED,
    "item_count": DEFAULT_ITEM_COUNT,
    "config": {
        "min_witness_length": C2_GENERATOR_CONFIG.min_witness_length,
        "max_witness_length": C2_GENERATOR_CONFIG.max_witness_length,
        "state_count": C2_GENERATOR_CONFIG.state_count,
        "include_negative": C2_GENERATOR_CONFIG.include_negative,
    },
}

F1_GENERATION_PARAMETERS: dict[str, Any] = {
    "family": "F1",
    "generator": "fsmreasonbench.generator.separation",
    "seed_start": F1_SEED_START,
    "seed_end": F1_SEED_START + DEFAULT_ITEM_COUNT - 1,
    "item_count": DEFAULT_ITEM_COUNT,
    "config": {
        "min_distinguishing_trace_length": F1_GENERATOR_CONFIG.min_distinguishing_trace_length,
        "max_distinguishing_trace_length": F1_GENERATOR_CONFIG.max_distinguishing_trace_length,
        "include_equivalent": F1_GENERATOR_CONFIG.include_equivalent,
        "equivalent_ratio": F1_GENERATOR_CONFIG.equivalent_ratio,
        "mode": "constructive_decoy",
    },
}


@dataclass(frozen=True, slots=True)
class ExpandedCohortPaths:
    """Resolved paths for the expanded n=100 cohort bundle."""

    root: Path
    c2_dir: Path
    f1_dir: Path
    c2_items: Path
    f1_items: Path
    c2_cohort_id: str
    f1_cohort_id: str


def resolve_expanded_cohort_paths(
    repo_root: str | Path,
    *,
    cohort_root: str | Path | None = None,
) -> ExpandedCohortPaths:
    root = Path(cohort_root) if cohort_root is not None else Path(repo_root) / EXPANDED_COHORT_ROOT
    return ExpandedCohortPaths(
        root=root,
        c2_dir=root / C2_SUBDIR,
        f1_dir=root / F1_SUBDIR,
        c2_items=root / C2_SUBDIR / "items.jsonl",
        f1_items=root / F1_SUBDIR / "items.jsonl",
        c2_cohort_id=C2_COHORT_ID,
        f1_cohort_id=F1_COHORT_ID,
    )


def generate_c2_expanded_items(
    n: int = DEFAULT_ITEM_COUNT,
    *,
    batch_seed: int = C2_BATCH_SEED,
    config: ReachabilityGeneratorConfig | None = None,
) -> list[BenchmarkItem]:
    """Generate n C2 reachability level-3 items with deterministic batch seeds."""
    items = generate_c2_batch(n, batch_seed, config=config or C2_GENERATOR_CONFIG)
    assert_unique_item_ids(items)
    return items


def generate_f1_expanded_items(
    n: int = DEFAULT_ITEM_COUNT,
    *,
    seed_start: int = F1_SEED_START,
    config: SeparationGeneratorConfig | None = None,
) -> list[BenchmarkItem]:
    """Generate n F1 mixed level-3 items using consecutive generator seeds."""
    config = config or F1_GENERATOR_CONFIG
    items: list[BenchmarkItem] = []
    seen_ids: set[str] = set()
    for offset in range(n):
        seed = seed_start + offset
        item = generate_separation_item(seed, config)
        if item.item_id in seen_ids:
            raise ValueError(f"duplicate item_id at F1 seed {seed}: {item.item_id}")
        seen_ids.add(item.item_id)
        items.append(item)
    assert_unique_item_ids(items)
    return items


def assert_disjoint_from_reference(
    items: list[BenchmarkItem],
    reference_items_path: str | Path,
    *,
    label: str,
) -> None:
    reference_ids = {
        record["item_id"]
        for record in read_jsonl(reference_items_path)
        if isinstance(record.get("item_id"), str)
    }
    overlap = sorted({item.item_id for item in items} & reference_ids)
    if overlap:
        raise ValueError(
            f"{label} shares {len(overlap)} item_id(s) with reference cohort: "
            + ", ".join(overlap[:5])
        )


def write_items_jsonl(path: str | Path, items: list[BenchmarkItem]) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(destination, (item.to_full_dict() for item in items))
    return destination


def freeze_expanded_family_cohort(
    *,
    items: list[BenchmarkItem],
    staging_path: Path,
    cohort_dir: Path,
    cohort_id: str,
    generator_notes: str,
    generation_parameters: dict[str, Any],
) -> dict[str, Any]:
    write_items_jsonl(staging_path, items)
    return freeze_cohort(
        staging_path,
        cohort_id,
        cohort_dir,
        generator_notes=generator_notes,
        generation_parameters=generation_parameters,
    )


def build_expanded_cohorts(
    repo_root: str | Path,
    *,
    item_count: int = DEFAULT_ITEM_COUNT,
    cohort_root: str | Path | None = None,
    reference_root: str | Path | None = None,
    validate: bool = True,
) -> dict[str, Any]:
    """Generate, freeze, and optionally validate both expanded cohort directories."""
    if item_count < 1:
        raise ValueError("item_count must be >= 1")

    repo_root = Path(repo_root)
    paths = resolve_expanded_cohort_paths(repo_root, cohort_root=cohort_root)
    reference_root = Path(reference_root) if reference_root is not None else repo_root / "cohorts/v0.1-exploratory"
    staging_root = repo_root / "runs" / "_expanded_n100_staging"
    staging_root.mkdir(parents=True, exist_ok=True)

    c2_items = generate_c2_expanded_items(item_count)
    f1_items = generate_f1_expanded_items(item_count)

    c2_reference = reference_root / C2_SUBDIR / "items.jsonl"
    f1_reference = reference_root / F1_SUBDIR / "items.jsonl"
    if c2_reference.is_file():
        assert_disjoint_from_reference(c2_items, c2_reference, label="C2 expanded cohort")
    if f1_reference.is_file():
        assert_disjoint_from_reference(f1_items, f1_reference, label="F1 expanded cohort")

    c2_params = {**C2_GENERATION_PARAMETERS, "item_count": item_count, "batch_seed": C2_BATCH_SEED}
    f1_params = {
        **F1_GENERATION_PARAMETERS,
        "item_count": item_count,
        "seed_start": F1_SEED_START,
        "seed_end": F1_SEED_START + item_count - 1,
    }

    c2_manifest = freeze_expanded_family_cohort(
        items=c2_items,
        staging_path=staging_root / "c2_items.jsonl",
        cohort_dir=paths.c2_dir,
        cohort_id=paths.c2_cohort_id,
        generator_notes=(
            "Expanded exploratory C2 reachability cohort (witness length level 3), "
            f"n={item_count}, batch_seed={C2_BATCH_SEED}. "
            "Disjoint from v0.1-exploratory item IDs."
        ),
        generation_parameters=c2_params,
    )
    f1_manifest = freeze_expanded_family_cohort(
        items=f1_items,
        staging_path=staging_root / "f1_items.jsonl",
        cohort_dir=paths.f1_dir,
        cohort_id=paths.f1_cohort_id,
        generator_notes=(
            "Expanded exploratory F1 mixed cohort (distinguishing trace length level 3), "
            f"n={item_count}, seeds {F1_SEED_START}–{F1_SEED_START + item_count - 1}, "
            "equivalent_ratio=0.5, constructive_decoy. "
            "Disjoint from v0.1-exploratory item IDs."
        ),
        generation_parameters=f1_params,
    )

    paths.root.mkdir(parents=True, exist_ok=True)
    bundle_readme = render_expanded_bundle_readme(
        paths=paths,
        item_count=item_count,
        c2_manifest=c2_manifest,
        f1_manifest=f1_manifest,
    )
    (paths.root / "README.md").write_text(bundle_readme, encoding="utf-8")

    result: dict[str, Any] = {
        "cohort_root": str(paths.root),
        "item_count": item_count,
        "c2": c2_manifest,
        "f1": f1_manifest,
        "validation": {},
    }

    if validate:
        c2_report = validate_cohort(paths.c2_dir)
        f1_report = validate_cohort(paths.f1_dir)
        if not c2_report.valid:
            raise ValueError("C2 expanded cohort validation failed: " + "; ".join(c2_report.errors))
        if not f1_report.valid:
            raise ValueError("F1 expanded cohort validation failed: " + "; ".join(f1_report.errors))
        result["validation"] = {
            "c2": c2_report.to_dict(),
            "f1": f1_report.to_dict(),
        }

    return result


def load_cohort_id_from_manifest(cohort_dir: str | Path) -> str:
    manifest = json.loads((Path(cohort_dir) / "manifest.json").read_text(encoding="utf-8"))
    cohort_id = manifest.get("cohort_id")
    if not isinstance(cohort_id, str) or not cohort_id.strip():
        raise ValueError(f"missing cohort_id in {cohort_dir}/manifest.json")
    return cohort_id


def resolve_cohort_bundle(
    cohort_root: str | Path,
) -> tuple[Path, Path, str, str]:
    """Return item paths and cohort IDs for a two-family cohort root directory."""
    root = Path(cohort_root)
    c2_dir = root / C2_SUBDIR
    f1_dir = root / F1_SUBDIR
    return (
        c2_dir / "items.jsonl",
        f1_dir / "items.jsonl",
        load_cohort_id_from_manifest(c2_dir),
        load_cohort_id_from_manifest(f1_dir),
    )


def render_expanded_bundle_readme(
    *,
    paths: ExpandedCohortPaths,
    item_count: int,
    c2_manifest: dict[str, Any],
    f1_manifest: dict[str, Any],
) -> str:
    return f"""# Exploratory cohort bundle `{EXPANDED_COHORT_VERSION}`

Expanded frozen cohorts for powered local-matrix runs (`--max-items {item_count}`).

| Family | Directory | cohort_id | item_count | fingerprint |
|--------|-----------|-----------|------------|-------------|
| C2 | `{C2_SUBDIR}/` | `{paths.c2_cohort_id}` | {item_count} | `{c2_manifest["cohort_fingerprint"]}` |
| F1 | `{F1_SUBDIR}/` | `{paths.f1_cohort_id}` | {item_count} | `{f1_manifest["cohort_fingerprint"]}` |

The v0.1-exploratory 20-item cohorts remain immutable. These expanded snapshots use
disjoint generator seeds and item IDs.

## Validate

```bash
PYTHONPATH=src python -m fsmreasonbench.cli.validate_cohort --cohort-dir {C2_SUBDIR}
PYTHONPATH=src python -m fsmreasonbench.cli.validate_cohort --cohort-dir {F1_SUBDIR}
```

## Regenerate (deterministic)

```bash
PYTHONPATH=src python -m fsmreasonbench.cli.generate_expanded_cohort --repo-root .
```
"""
