"""Bootstrap uncertainty export for frozen local open-weight matrix cells."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fsmreasonbench.evaluator.bootstrap import DEFAULT_BOOTSTRAP_ALPHA, DEFAULT_BOOTSTRAP_RESAMPLES
from fsmreasonbench.evaluator.frontier_tools_analysis import discover_completed_cells
from fsmreasonbench.evaluator.jsonl import read_jsonl
from fsmreasonbench.evaluator.models import ScoringRecord
from fsmreasonbench.evaluator.rate_ci_report import bootstrap_rate_cis
from fsmreasonbench.evaluator.summary import summarize_scoring_records
from fsmreasonbench.evaluator.tmlr_empirical_package import RateWithCI

DEFAULT_MATRIX_ROOT = "runs/local_matrix_n100_t02_v2"
DEFAULT_JSON_OUT = "docs/local_matrix_n100_t02_bootstrap_summary.json"
DEFAULT_BOOTSTRAP_SEED_BASE = 4242

LAYER_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("extractability_rate", "extractability_rate_ci_low", "extractability_rate_ci_high"),
    ("verdict_accuracy", "verdict_accuracy_ci_low", "verdict_accuracy_ci_high"),
    ("certificate_valid_rate", "certificate_valid_rate_ci_low", "certificate_valid_rate_ci_high"),
    ("fully_correct_rate", "fully_correct_rate_ci_low", "fully_correct_rate_ci_high"),
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rate_with_ci(
    *,
    rate: float,
    n: int,
    successes: int,
    ci_low: float,
    ci_high: float,
) -> RateWithCI:
    return RateWithCI(
        rate=round(rate, 4),
        n=n,
        successes=successes,
        ci_low=round(ci_low, 4),
        ci_high=round(ci_high, 4),
    )


def _layer_metrics_from_records(
    records: list[ScoringRecord],
    *,
    n_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    seed: int = DEFAULT_BOOTSTRAP_SEED_BASE,
    alpha: float = DEFAULT_BOOTSTRAP_ALPHA,
) -> dict[str, RateWithCI]:
    summary = summarize_scoring_records(records)
    cis = bootstrap_rate_cis(
        records,
        n_resamples=n_resamples,
        seed=seed,
        alpha=alpha,
    )
    extractable = sum(1 for record in records if record.extractable)
    verdict_successes = sum(
        1 for record in records if record.extractable and record.verdict_correct is True
    )
    cert_successes = sum(
        1 for record in records if record.extractable and record.certificate_valid is True
    )
    full_successes = sum(1 for record in records if record.fully_correct)
    return {
        "extractability_rate": _rate_with_ci(
            rate=summary["extractability_rate"],
            n=summary["n"],
            successes=extractable,
            ci_low=cis["extractability_rate_ci_low"],
            ci_high=cis["extractability_rate_ci_high"],
        ),
        "verdict_accuracy": _rate_with_ci(
            rate=summary["verdict_accuracy"],
            n=extractable,
            successes=verdict_successes,
            ci_low=cis["verdict_accuracy_ci_low"],
            ci_high=cis["verdict_accuracy_ci_high"],
        ),
        "certificate_valid_rate": _rate_with_ci(
            rate=summary["certificate_valid_rate"],
            n=extractable,
            successes=cert_successes,
            ci_low=cis["certificate_valid_rate_ci_low"],
            ci_high=cis["certificate_valid_rate_ci_high"],
        ),
        "fully_correct_rate": _rate_with_ci(
            rate=summary["fully_correct_rate"],
            n=summary["n"],
            successes=full_successes,
            ci_low=cis["fully_correct_rate_ci_low"],
            ci_high=cis["fully_correct_rate_ci_high"],
        ),
    }


def _cell_sort_key(cell: dict[str, Any]) -> tuple[str, str, str]:
    return (str(cell.get("model", "")), str(cell.get("family", "")), str(cell.get("track", "")))


def analyze_local_matrix_bootstrap(
    repo_root: Path,
    *,
    matrix_combined_summary: str | Path = DEFAULT_MATRIX_ROOT + "/combined_summary.json",
    n_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    seed_base: int = DEFAULT_BOOTSTRAP_SEED_BASE,
    alpha: float = DEFAULT_BOOTSTRAP_ALPHA,
) -> dict[str, Any]:
    combined_path = repo_root / matrix_combined_summary
    combined = _load_json(combined_path)
    cells = discover_completed_cells(combined, repo_root=repo_root)
    cells = sorted(cells, key=_cell_sort_key)

    rows: list[dict[str, Any]] = []
    for index, cell in enumerate(cells):
        run_dir = Path(str(cell["run_dir"]))
        if not run_dir.is_absolute():
            run_dir = repo_root / run_dir
        scores_path = run_dir / "scores.jsonl"
        records = [ScoringRecord.from_dict(row) for row in read_jsonl(scores_path)]
        metrics = _layer_metrics_from_records(
            records,
            n_resamples=n_resamples,
            seed=seed_base + index,
            alpha=alpha,
        )
        rows.append(
            {
                "model": cell.get("model"),
                "model_dir": cell.get("model_dir"),
                "family": cell.get("family"),
                "track": cell.get("track"),
                "run_dir": str(cell.get("run_dir")),
                "scores_path": str(scores_path.relative_to(repo_root)),
                "bootstrap_seed": seed_base + index,
                "metrics": {name: asdict(value) for name, value in metrics.items()},
            }
        )

    return {
        "experiment": "local_matrix_bootstrap_summary",
        "matrix_root": str(Path(matrix_combined_summary).parent),
        "bootstrap_settings": {
            "alpha": alpha,
            "method": "percentile_bootstrap",
            "n_resamples": n_resamples,
            "seed_base": seed_base,
            "seed_per_cell": "seed_base + cell_index (sorted by model, family, track)",
            "note": (
                "Percentile bootstrap CIs on item-level scores.jsonl rows; "
                "verdict and certificate rates condition on extractable submissions "
                "within each resample."
            ),
        },
        "cells": rows,
    }


def _format_rate_ci(metric: dict[str, Any]) -> str:
    return f"{metric['rate']:.3f} [{metric['ci_low']:.3f}, {metric['ci_high']:.3f}]"


def render_local_matrix_summary_latex(rows: list[dict[str, Any]]) -> str:
    source = _latex_escape("runs/local_matrix_n100_t02_v2/combined_summary.json")
    lines = [
        "% Generated by export_tosem_empirical_package from frozen scores.jsonl "
        "(bootstrap CIs via local_matrix_bootstrap_export).",
        "\\begin{table*}[t]",
        "  \\centering",
        "  \\caption{Frozen local open-weight matrix ($n{=}100$ per cell; temperature~$0.2$; "
        "cohorts \\texttt{v0.1-expanded-n100}). "
        "Each cell reports rate [95\\% CI] from percentile bootstrap "
        "($1000$ resamples; per-cell seed~$4242{+}$index); when the observed rate is $0$ or $1$, "
        "the interval is exact Clopper--Pearson from the frozen $k/n$ count "
        "(Appendix~\\ref{app:uncertainty}). "
        "Extract.: extractability rate ($n$ denominator); "
        "Verdict/Cert.: among extractable submissions; Full: fully correct ($n$ denominator). "
        "Source: " + source + ".}",
        "  \\label{tab:local-matrix-n100-summary}",
        "  \\scriptsize",
        "  \\setlength{\\tabcolsep}{2pt}",
        "  \\begin{tabular}{@{}lllrlccc@{}}",
        "    \\toprule",
        "    Model & Fam. & Track & $n$ & Extract. & Verdict & Cert. & Full \\\\",
        "    \\midrule",
    ]
    for row in rows:
        metrics = row["metrics"]
        model = _latex_escape(str(row["model"]))
        lines.append(
            "    "
            + " & ".join(
                [
                    f"\\texttt{{{model}}}",
                    str(row["family"]),
                    str(row["track"]),
                    "100",
                    _format_rate_ci(metrics["extractability_rate"]),
                    _format_rate_ci(metrics["verdict_accuracy"]),
                    _format_rate_ci(metrics["certificate_valid_rate"]),
                    _format_rate_ci(metrics["fully_correct_rate"]),
                ]
            )
            + " \\\\"
        )
    lines.extend(["    \\bottomrule", "  \\end{tabular}", "\\end{table*}", ""])
    return "\n".join(lines)


def _latex_escape(text: str) -> str:
    return (
        text.replace("\\", "\\textbackslash{}")
        .replace("_", "\\_")
        .replace("%", "\\%")
        .replace("&", "\\&")
    )


def export_local_matrix_bootstrap_package(
    repo_root: str | Path,
    *,
    json_out: str | Path | None = None,
    latex_out: str | Path | None = None,
    n_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    seed_base: int = DEFAULT_BOOTSTRAP_SEED_BASE,
) -> dict[str, Any]:
    root = Path(repo_root)
    payload = analyze_local_matrix_bootstrap(
        root,
        n_resamples=n_resamples,
        seed_base=seed_base,
    )
    json_path = root / (json_out or DEFAULT_JSON_OUT)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if latex_out is not None:
        latex_path = Path(latex_out)
        latex_path.parent.mkdir(parents=True, exist_ok=True)
        latex_path.write_text(
            render_local_matrix_summary_latex(payload["cells"]),
            encoding="utf-8",
        )
    payload["json_out"] = str(json_path)
    if latex_out is not None:
        payload["latex_out"] = str(latex_out)
    return payload
