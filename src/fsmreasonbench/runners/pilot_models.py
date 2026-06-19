"""Multi-model pilot evaluation across C2 and F1 Ollama runs."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.evaluator.jsonl import load_items_jsonl
from fsmreasonbench.evaluator.models import FailureStage
from fsmreasonbench.items.assembly import BenchmarkItem
from fsmreasonbench.runners.ollama_batch import GenerateFn, OllamaBatchConfig, run_ollama_batch

GenerateFactory = Callable[[str], GenerateFn]

_CSV_FIELDS = (
    "model",
    "family",
    "n",
    "extractability_rate",
    "verdict_accuracy",
    "certificate_valid_rate",
    "fully_correct_rate",
    "failure_stage_counts",
)
_FAILURE_STAGE_ORDER = tuple(stage.value for stage in FailureStage)


@dataclass(frozen=True, slots=True)
class PilotModelsConfig:
    models: tuple[str, ...]
    c2_items_path: str | Path
    f1_items_path: str | Path
    out_dir: str | Path
    max_items: int = 20
    temperature: float = 0.0
    timeout: float = 120.0


@dataclass(frozen=True, slots=True)
class PilotModelsResult:
    rows: list[dict[str, Any]]
    out_dir: Path


def model_dir_name(model: str) -> str:
    """Filesystem-safe directory name for an Ollama model tag."""
    return model.replace(":", "_").replace("/", "_")


def run_pilot_models(
    config: PilotModelsConfig,
    generate_factory: GenerateFactory,
) -> PilotModelsResult:
    """
    Run C2 and F1 pilot batches for each model and write comparative summaries.

    Layout::

        {out_dir}/{model_dir}/{family}/results.jsonl
        {out_dir}/{model_dir}/{family}/scores.jsonl
        {out_dir}/{model_dir}/{family}/transcripts/
        {out_dir}/combined_summary.json
        {out_dir}/combined_summary.csv
        {out_dir}/report.md
    """
    if not config.models:
        raise ValueError("at least one model is required")
    if config.max_items < 1:
        raise ValueError("max_items must be >= 1")

    root = Path(config.out_dir)
    root.mkdir(parents=True, exist_ok=True)

    c2_items = load_items_jsonl(config.c2_items_path)
    f1_items = load_items_jsonl(config.f1_items_path)
    _validate_family_items(c2_items, "C2")
    _validate_family_items(f1_items, "F1")

    rows: list[dict[str, Any]] = []
    for model in config.models:
        model_dir = model_dir_name(model)
        generate = generate_factory(model)
        for family, items in (("C2", c2_items), ("F1", f1_items)):
            run_dir = root / model_dir / family
            run_dir.mkdir(parents=True, exist_ok=True)
            results_path = run_dir / "results.jsonl"
            batch_result = run_ollama_batch(
                items,
                generate,
                results_path,
                OllamaBatchConfig(
                    model=model,
                    temperature=config.temperature,
                    timeout=config.timeout,
                    max_items=config.max_items,
                ),
                out_dir=run_dir,
            )
            row = {
                "model": model,
                "model_dir": model_dir,
                "family": family,
                **batch_result.summary,
                "scores_path": str(run_dir / "scores.jsonl"),
                "results_path": str(results_path),
            }
            rows.append(row)

    dump_json(root / "combined_summary.json", {"rows": rows})
    write_pilot_models_csv(root / "combined_summary.csv", rows)
    (root / "report.md").write_text(render_pilot_models_report(rows), encoding="utf-8")
    return PilotModelsResult(rows=rows, out_dir=root)


def write_pilot_models_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "model": row["model"],
                    "family": row["family"],
                    "n": row["n"],
                    "extractability_rate": row["extractability_rate"],
                    "verdict_accuracy": row["verdict_accuracy"],
                    "certificate_valid_rate": row["certificate_valid_rate"],
                    "fully_correct_rate": row["fully_correct_rate"],
                    "failure_stage_counts": json.dumps(
                        row["failure_stage_counts"],
                        sort_keys=True,
                    ),
                }
            )


def render_pilot_models_report(rows: list[dict[str, Any]]) -> str:
    """Render a comparative Markdown report across models and families."""
    models = list(dict.fromkeys(row["model"] for row in rows))
    families = list(dict.fromkeys(row["family"] for row in rows))
    indexed = {(row["model"], row["family"]): row for row in rows}

    lines = [
        "# Multi-Model Pilot Report",
        "",
        f"Models: {len(models)}",
        f"Families: {', '.join(families)}",
        "",
    ]

    metric_headers = (
        "extractability_rate",
        "verdict_accuracy",
        "certificate_valid_rate",
        "fully_correct_rate",
    )
    for family in families:
        lines.extend([f"## {family} comparison", ""])
        lines.append("| Model | " + " | ".join(metric_headers) + " |")
        lines.append("|-------|" + "|".join(["------:"] * len(metric_headers)) + "|")
        for model in models:
            row = indexed.get((model, family))
            if row is None:
                continue
            values = " | ".join(f"{row[metric]:.3f}" for metric in metric_headers)
            lines.append(f"| `{model}` | {values} |")
        lines.append("")

        lines.extend([f"### {family} failure stage counts", ""])
        stage_headers = list(_FAILURE_STAGE_ORDER)
        lines.append("| Model | " + " | ".join(stage_headers) + " |")
        lines.append("|-------|" + "|".join(["------:"] * len(stage_headers)) + "|")
        for model in models:
            row = indexed.get((model, family))
            if row is None:
                continue
            counts = row["failure_stage_counts"]
            stage_values = " | ".join(str(counts.get(stage, 0)) for stage in stage_headers)
            lines.append(f"| `{model}` | {stage_values} |")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _validate_family_items(items: list[BenchmarkItem], family: str) -> None:
    if not items:
        raise ValueError(f"{family} items JSONL is empty")
    if any(item.family != family for item in items):
        raise ValueError(f"all items must belong to family {family!r}")
