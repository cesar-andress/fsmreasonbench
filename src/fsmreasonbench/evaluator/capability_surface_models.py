"""Model capability-surface evaluation across difficulty levels."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from fsmreasonbench.evaluator.batch import generate_batch
from fsmreasonbench.evaluator.capability_surface import (
    C2_DIFFICULTY_AXIS,
    DEFAULT_C2_LEVELS,
    DEFAULT_F1_LEVELS,
    F1_DIFFICULTY_AXIS,
    _level_seed,
)
from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.evaluator.jsonl import write_jsonl
from fsmreasonbench.generator.reachability import ReachabilityGeneratorConfig
from fsmreasonbench.generator.separation import separation_config_for_level
from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.runners.ollama_batch import GenerateFn, OllamaBatchConfig, run_ollama_batch
from fsmreasonbench.runners.pilot_models import model_dir_name

GenerateFactory = Callable[[str], GenerateFn]

_MODEL_CSV_FIELDS = (
    "family",
    "difficulty_level",
    "model",
    "extractability_rate",
    "verdict_accuracy",
    "certificate_valid_rate",
    "fully_correct_rate",
)


@dataclass(frozen=True, slots=True)
class CapabilitySurfaceModelsConfig:
    models: tuple[str, ...]
    out_dir: str | Path
    families: tuple[str, ...] = ("C2", "F1")
    c2_levels: tuple[int, ...] = DEFAULT_C2_LEVELS
    f1_levels: tuple[int, ...] = DEFAULT_F1_LEVELS
    n_per_level: int = 20
    seed: int = 1
    temperature: float = 0.0
    timeout: float = 120.0
    skip_completed: bool = True


@dataclass(frozen=True, slots=True)
class CapabilitySurfaceModelsResult:
    rows: list[dict[str, Any]]
    out_dir: Path


def run_capability_surface_models(
    config: CapabilitySurfaceModelsConfig,
    generate_factory: GenerateFactory,
) -> CapabilitySurfaceModelsResult:
    """
    Sweep C2/F1 difficulty levels for each Ollama model.

    Layout::

        {out_dir}/{family}/{axis}_{level}/items.jsonl
        {out_dir}/{family}/{axis}_{level}/{model_dir}/scores.jsonl
        {out_dir}/{family}/{axis}_{level}/{model_dir}/results.jsonl
        {out_dir}/combined_summary.json
        {out_dir}/combined_summary.csv
        {out_dir}/report.md
    """
    if not config.models:
        raise ValueError("at least one model is required")
    if config.n_per_level < 1:
        raise ValueError("n_per_level must be >= 1")

    root = Path(config.out_dir)
    root.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []

    for family in config.families:
        axis, levels = _family_axis_levels(config, family)
        for level in levels:
            level_dir = root / family / f"{axis}_{level}"
            level_dir.mkdir(parents=True, exist_ok=True)
            items_path = level_dir / "items.jsonl"
            if items_path.exists():
                from fsmreasonbench.evaluator.jsonl import load_items_jsonl

                items = load_items_jsonl(items_path)
            else:
                items = _generate_level_items(
                    family,
                    level,
                    config.n_per_level,
                    _level_seed(config.seed, family, level),
                )
                write_jsonl(items_path, (item.to_full_dict() for item in items))

            for model in config.models:
                model_dir = level_dir / model_dir_name(model)
                summary_path = model_dir / "summary.json"
                if config.skip_completed and summary_path.exists():
                    summary = json.loads(summary_path.read_text(encoding="utf-8"))
                    rows.append(_row_from_summary(summary, family, level, model, model_dir))
                    continue

                generate = generate_factory(model)
                batch_result = run_ollama_batch(
                    items,
                    generate,
                    model_dir / "results.jsonl",
                    OllamaBatchConfig(
                        model=model,
                        temperature=config.temperature,
                        timeout=config.timeout,
                    ),
                    out_dir=model_dir,
                )
                rows.append(
                    {
                        "family": family,
                        "difficulty_axis": axis,
                        "difficulty_level": level,
                        "model": model,
                        "model_dir": model_dir_name(model),
                        "n": batch_result.summary["n"],
                        "extractability_rate": batch_result.summary["extractability_rate"],
                        "verdict_accuracy": batch_result.summary["verdict_accuracy"],
                        "certificate_valid_rate": batch_result.summary["certificate_valid_rate"],
                        "fully_correct_rate": batch_result.summary["fully_correct_rate"],
                        "failure_stage_counts": batch_result.summary["failure_stage_counts"],
                    }
                )

    payload = {
        "families": list(config.families),
        "models": list(config.models),
        "n_per_level": config.n_per_level,
        "seed": config.seed,
        "temperature": config.temperature,
        "rows": rows,
    }
    dump_json(root / "combined_summary.json", payload)
    write_capability_surface_models_csv(root / "combined_summary.csv", rows)
    (root / "report.md").write_text(
        render_capability_surface_models_report(rows),
        encoding="utf-8",
    )
    return CapabilitySurfaceModelsResult(rows=rows, out_dir=root)


def write_capability_surface_models_csv(
    path: str | Path,
    rows: list[dict[str, Any]],
) -> None:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_MODEL_CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "family": row["family"],
                    "difficulty_level": row["difficulty_level"],
                    "model": row["model"],
                    "extractability_rate": row["extractability_rate"],
                    "verdict_accuracy": row["verdict_accuracy"],
                    "certificate_valid_rate": row["certificate_valid_rate"],
                    "fully_correct_rate": row["fully_correct_rate"],
                }
            )


def render_capability_surface_models_report(rows: list[dict[str, Any]]) -> str:
    """Render Markdown comparing models across difficulty levels."""
    if not rows:
        return "# Model Capability Surface Report\n\n_No runs recorded._\n"

    families = list(dict.fromkeys(row["family"] for row in rows))
    models = list(dict.fromkeys(row["model"] for row in rows))
    levels_by_family: dict[str, list[int]] = {}
    for row in rows:
        levels_by_family.setdefault(row["family"], [])
        if row["difficulty_level"] not in levels_by_family[row["family"]]:
            levels_by_family[row["family"]].append(row["difficulty_level"])
    for family in levels_by_family:
        levels_by_family[family].sort()

    indexed = {
        (row["family"], row["difficulty_level"], row["model"]): row for row in rows
    }

    lines = [
        "# Model Capability Surface Report",
        "",
        f"Models: {len(models)}",
        f"Families: {', '.join(families)}",
        "",
    ]

    for metric, title in (
        ("fully_correct_rate", "Fully correct rate"),
        ("verdict_accuracy", "Verdict accuracy"),
        ("certificate_valid_rate", "Certificate valid rate"),
        ("extractability_rate", "Extractability rate"),
    ):
        for family in families:
            levels = levels_by_family[family]
            lines.extend([f"## {family} — {title}", ""])
            header = "| Model | " + " | ".join(f"L{level}" for level in levels) + " |"
            sep = "|-------|" + "|".join(["------:"] * len(levels)) + "|"
            lines.extend([header, sep])
            for model in models:
                values = []
                for level in levels:
                    row = indexed.get((family, level, model))
                    values.append(f"{row[metric]:.3f}" if row else "—")
                lines.append(f"| `{model}` | " + " | ".join(values) + " |")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _row_from_summary(
    summary: dict[str, Any],
    family: str,
    level: int,
    model: str,
    model_dir: Path,
) -> dict[str, Any]:
    axis = C2_DIFFICULTY_AXIS if family == "C2" else F1_DIFFICULTY_AXIS
    return {
        "family": family,
        "difficulty_axis": axis,
        "difficulty_level": level,
        "model": model,
        "model_dir": model_dir_name(model),
        "n": summary["n"],
        "extractability_rate": summary["extractability_rate"],
        "verdict_accuracy": summary["verdict_accuracy"],
        "certificate_valid_rate": summary["certificate_valid_rate"],
        "fully_correct_rate": summary["fully_correct_rate"],
        "failure_stage_counts": summary["failure_stage_counts"],
        "scores_path": str(model_dir / "scores.jsonl"),
        "results_path": str(model_dir / "results.jsonl"),
    }


def _family_axis_levels(
    config: CapabilitySurfaceModelsConfig,
    family: str,
) -> tuple[str, tuple[int, ...]]:
    if family == "C2":
        return C2_DIFFICULTY_AXIS, config.c2_levels
    if family == "F1":
        return F1_DIFFICULTY_AXIS, config.f1_levels
    raise ValueError(f"unsupported family: {family!r}")


def _generate_level_items(
    family: str,
    level: int,
    n: int,
    seed: int,
) -> list[BenchmarkItem]:
    if family == "C2":
        return generate_batch(
            "C2",
            n,
            seed,
            c2_config=ReachabilityGeneratorConfig(
                min_witness_length=level,
                max_witness_length=12,
            ),
        )
    return generate_batch(
        "F1",
        n,
        seed,
        f1_config=separation_config_for_level(level),
    )
