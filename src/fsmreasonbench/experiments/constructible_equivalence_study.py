"""F1 constructible equivalence witness study orchestration (Experiment A1)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fsmreasonbench.cohort.expanded_n100 import EXPANDED_COHORT_ROOT, resolve_cohort_bundle
from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.evaluator.jsonl import load_items_jsonl
from fsmreasonbench.items.assembly import BenchmarkItem

STUDY_ID = "f1_constructible_equivalence_n100_v1"
WITNESS_CONTRACT = "bisimulation_witness"
DEFAULT_TEMPERATURE = 0.2

DEFAULT_OUT_DIRS = {
    ("anthropic", "claude-sonnet-4-5-20250929"): "runs/f1_constructible_equivalence_claude_n100_v1",
    ("openai", "gpt-4.1"): "runs/f1_constructible_equivalence_gpt_n100_v1",
}


@dataclass(frozen=True, slots=True)
class ConstructibleEquivalenceCellConfig:
    provider: str
    model: str
    track: str
    out_dir: Path


@dataclass(frozen=True, slots=True)
class ConstructibleEquivalenceStudyConfig:
    study_id: str
    cohort_root: Path
    cells: tuple[ConstructibleEquivalenceCellConfig, ...]
    temperature: float = DEFAULT_TEMPERATURE


def filter_equivalence_subset(items: list[BenchmarkItem]) -> list[BenchmarkItem]:
    """Keep F1 items whose gold certificate is equivalence_witness (n=51 in frozen cohort)."""
    filtered: list[BenchmarkItem] = []
    for item in items:
        cert = item.answer_key.get("certificate") or {}
        if cert.get("certificate_type") == "equivalence_witness":
            filtered.append(item)
    return filtered


def load_constructible_equivalence_study_config(path: Path) -> ConstructibleEquivalenceStudyConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cells: list[ConstructibleEquivalenceCellConfig] = []
    for cell in payload.get("cells", []):
        cells.append(
            ConstructibleEquivalenceCellConfig(
                provider=str(cell["provider"]),
                model=str(cell["model"]),
                track=str(cell["track"]),
                out_dir=Path(cell["out_dir"]),
            )
        )
    return ConstructibleEquivalenceStudyConfig(
        study_id=str(payload.get("study_id", STUDY_ID)),
        cohort_root=Path(payload.get("cohort_root", EXPANDED_COHORT_ROOT)),
        cells=tuple(cells),
        temperature=float(payload.get("temperature", DEFAULT_TEMPERATURE)),
    )


def resolve_study_items(cohort_root: Path) -> tuple[list[BenchmarkItem], str]:
    bundle = resolve_cohort_bundle(cohort_root)
    _c2_items_path, f1_items_path, _c2_cohort_id, f1_cohort_id = bundle
    items = filter_equivalence_subset(load_items_jsonl(f1_items_path))
    return items, f1_cohort_id


def finalize_constructible_equivalence_study(
    study_root: Path,
    *,
    study_id: str,
    cohort_id: str,
    temperature: float,
) -> dict[str, Any]:
    track_rows: list[dict[str, Any]] = []
    for cell_dir in sorted(study_root.iterdir()):
        if not cell_dir.is_dir():
            continue
        summary_path = cell_dir / "summary.json"
        if not summary_path.exists():
            continue
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        track_rows.append(
            {
                "study_id": study_id,
                "witness_contract": WITNESS_CONTRACT,
                "subset": "f1_equivalence_n51",
                "track": summary.get("track", cell_dir.name),
                "model": summary.get("model"),
                "provider": summary.get("provider"),
                "temperature": temperature,
                "cohort_id": cohort_id,
                "n": summary.get("n"),
                "extractability_rate": summary.get("extractability_rate"),
                "verdict_accuracy": summary.get("verdict_accuracy"),
                "certificate_valid_rate": summary.get("certificate_valid_rate"),
                "fully_correct_rate": summary.get("fully_correct_rate"),
                "failure_stage_counts": summary.get("failure_stage_counts"),
                "provider_error_count": summary.get("provider_error_count", 0),
                "status": "completed" if summary.get("n") else "pending",
                "run_dir": str(cell_dir),
            }
        )
    combined = {
        "experiment": "f1_constructible_equivalence_witness",
        "study_id": study_id,
        "witness_contract": WITNESS_CONTRACT,
        "subset": "f1_equivalence_n51",
        "cohort_id": cohort_id,
        "temperature": temperature,
        "track_rows": track_rows,
    }
    dump_json(study_root / "combined_summary.json", combined)
    report_lines = [
        f"# F1 constructible equivalence witness study ({study_id})",
        "",
        f"- Witness contract: `{WITNESS_CONTRACT}` (state-pair bisimulation; no hash fields)",
        "- Subset: F1 equivalence items only (gold `equivalence_witness`, n≈51)",
        f"- Cohort: `{cohort_id}`",
        "",
        "## Cells",
        "",
        "| Track | Model | n | cert valid | fully correct |",
        "|-------|-------|---|------------|---------------|",
    ]
    for row in track_rows:
        report_lines.append(
            f"| {row.get('track')} | {row.get('model')} | {row.get('n')} | "
            f"{row.get('certificate_valid_rate')} | {row.get('fully_correct_rate')} |"
        )
    (study_root / "report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    return combined
