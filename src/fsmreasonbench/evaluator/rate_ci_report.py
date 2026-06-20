"""Bootstrap confidence intervals for exploratory rate summaries."""

from __future__ import annotations

import csv
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fsmreasonbench.evaluator.bootstrap import (
    DEFAULT_BOOTSTRAP_ALPHA,
    DEFAULT_BOOTSTRAP_RESAMPLES,
    _fully_correct_rate,
    _percentile,
    _verdict_accuracy,
)
from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.evaluator.jsonl import read_jsonl
from fsmreasonbench.evaluator.models import ScoringRecord
from fsmreasonbench.evaluator.summary import summarize_scoring_records
RATE_CI_JSON_FIELDS: tuple[str, ...] = (
    "source_name",
    "family",
    "model",
    "difficulty_level",
    "n",
    "verdict_accuracy",
    "verdict_accuracy_ci_low",
    "verdict_accuracy_ci_high",
    "certificate_valid_rate",
    "certificate_valid_rate_ci_low",
    "certificate_valid_rate_ci_high",
    "fully_correct_rate",
    "fully_correct_rate_ci_low",
    "fully_correct_rate_ci_high",
)

RATE_CI_CSV_FIELDS: tuple[str, ...] = RATE_CI_JSON_FIELDS

_LEVEL_PATTERN = re.compile(r"^(?:min_witness_length|min_distinguishing_trace_length)_(\d+)$")


def _certificate_valid_rate(records: list[ScoringRecord]) -> float:
    extractable = [record for record in records if record.extractable]
    if not extractable:
        return 0.0
    valid = sum(1 for record in extractable if record.certificate_valid is True)
    return valid / len(extractable)


def bootstrap_rate_cis(
    records: list[ScoringRecord],
    *,
    n_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    seed: int = 0,
    alpha: float = DEFAULT_BOOTSTRAP_ALPHA,
) -> dict[str, float]:
    """Compute percentile bootstrap CIs for verdict, certificate, and full correctness."""
    if n_resamples < 1:
        raise ValueError("n_resamples must be >= 1")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be in (0, 1)")

    point_verdict = _verdict_accuracy(records)
    point_certificate = _certificate_valid_rate(records)
    point_fully_correct = _fully_correct_rate(records)
    if not records:
        return {
            "verdict_accuracy_ci_low": point_verdict,
            "verdict_accuracy_ci_high": point_verdict,
            "certificate_valid_rate_ci_low": point_certificate,
            "certificate_valid_rate_ci_high": point_certificate,
            "fully_correct_rate_ci_low": point_fully_correct,
            "fully_correct_rate_ci_high": point_fully_correct,
        }

    rng = random.Random(seed)
    population = tuple(records)
    sample_size = len(population)
    verdict_samples: list[float] = []
    certificate_samples: list[float] = []
    fully_correct_samples: list[float] = []

    for _ in range(n_resamples):
        sample = [population[rng.randrange(sample_size)] for _ in range(sample_size)]
        verdict_samples.append(_verdict_accuracy(sample))
        certificate_samples.append(_certificate_valid_rate(sample))
        fully_correct_samples.append(_fully_correct_rate(sample))

    low_q = alpha / 2.0
    high_q = 1.0 - alpha / 2.0
    return {
        "verdict_accuracy_ci_low": _percentile(verdict_samples, low_q),
        "verdict_accuracy_ci_high": _percentile(verdict_samples, high_q),
        "certificate_valid_rate_ci_low": _percentile(certificate_samples, low_q),
        "certificate_valid_rate_ci_high": _percentile(certificate_samples, high_q),
        "fully_correct_rate_ci_low": _percentile(fully_correct_samples, low_q),
        "fully_correct_rate_ci_high": _percentile(fully_correct_samples, high_q),
    }


def summarize_rates_with_bootstrap(
    records: list[ScoringRecord],
    *,
    n_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    seed: int = 0,
) -> dict[str, Any]:
    """Point-rate summary plus bootstrap CIs for all three headline rates."""
    summary = summarize_scoring_records(records)
    summary.update(
        bootstrap_rate_cis(records, n_resamples=n_resamples, seed=seed),
    )
    return summary


def model_name_from_dir(model_dir: str) -> str:
    """Reverse ``model_dir_name`` for standard Ollama tags used in this repo."""
    if "_" not in model_dir:
        return model_dir
    prefix, suffix = model_dir.rsplit("_", 1)
    return f"{prefix}:{suffix}"


def parse_difficulty_level(level_dir_name: str) -> int | None:
    match = _LEVEL_PATTERN.match(level_dir_name)
    if match is None:
        return None
    return int(match.group(1))


@dataclass(frozen=True, slots=True)
class RateCiScanConfig:
    roots: tuple[str | Path, ...]
    n_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES
    seed: int = 4242


def _iter_capability_surface_score_files(root: Path) -> list[tuple[str, Path]]:
    matches: list[tuple[str, Path]] = []
    for scores_path in sorted(root.glob("*/*/min_*/*/scores.jsonl")):
        family = scores_path.parents[2].name
        level_dir = scores_path.parents[1].name
        model_dir = scores_path.parent.name
        source_name = (
            f"{root.name}/{family}/{level_dir}/{model_dir}/scores.jsonl"
        )
        matches.append((source_name, scores_path))
    return matches


def _iter_pilot_score_files(root: Path) -> list[tuple[str, Path]]:
    matches: list[tuple[str, Path]] = []
    for scores_path in sorted(root.glob("*/*/scores.jsonl")):
        model_dir = scores_path.parents[1].name
        family = scores_path.parent.name
        source_name = f"{root.name}/{model_dir}/{family}/scores.jsonl"
        matches.append((source_name, scores_path))
    return matches


def discover_rate_ci_score_files(roots: list[str | Path]) -> list[tuple[str, Path]]:
    """Discover score files under capability-surface and pilot run trees."""
    discovered: list[tuple[str, Path]] = []
    for root_value in roots:
        root = Path(root_value).resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"score root not found: {root}")
        if root.name == "pilot_v1":
            discovered.extend(_iter_pilot_score_files(root))
        else:
            discovered.extend(_iter_capability_surface_score_files(root))
    return discovered


def build_rate_ci_row(
    source_name: str,
    scores_path: Path,
    *,
    n_resamples: int,
    seed: int,
) -> dict[str, Any]:
    records = [ScoringRecord.from_dict(record) for record in read_jsonl(scores_path)]
    summary = summarize_rates_with_bootstrap(
        records,
        n_resamples=n_resamples,
        seed=seed,
    )
    parts = Path(source_name).parts
    if "pilot_v1" in parts:
        model_dir = parts[-3]
        family = parts[-2]
        difficulty_level = None
    else:
        family = parts[-4]
        level_dir = parts[-3]
        model_dir = parts[-2]
        difficulty_level = parse_difficulty_level(level_dir)

    return {
        "source_name": source_name,
        "family": family,
        "model": model_name_from_dir(model_dir),
        "difficulty_level": difficulty_level,
        "n": summary["n"],
        "verdict_accuracy": summary["verdict_accuracy"],
        "verdict_accuracy_ci_low": summary["verdict_accuracy_ci_low"],
        "verdict_accuracy_ci_high": summary["verdict_accuracy_ci_high"],
        "certificate_valid_rate": summary["certificate_valid_rate"],
        "certificate_valid_rate_ci_low": summary["certificate_valid_rate_ci_low"],
        "certificate_valid_rate_ci_high": summary["certificate_valid_rate_ci_high"],
        "fully_correct_rate": summary["fully_correct_rate"],
        "fully_correct_rate_ci_low": summary["fully_correct_rate_ci_low"],
        "fully_correct_rate_ci_high": summary["fully_correct_rate_ci_high"],
    }


def build_rate_ci_report(
    roots: list[str | Path],
    *,
    n_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    seed: int = 4242,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for source_name, scores_path in discover_rate_ci_score_files(roots):
        rows.append(
            build_rate_ci_row(
                source_name,
                scores_path,
                n_resamples=n_resamples,
                seed=seed,
            )
        )
    return {
        "bootstrap_resamples": n_resamples,
        "bootstrap_seed": seed,
        "roots": [str(Path(root).resolve()) for root in roots],
        "rows": rows,
    }


def write_rate_ci_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(RATE_CI_CSV_FIELDS))
        writer.writeheader()
        for row in rows:
            csv_row = dict(row)
            if csv_row["difficulty_level"] is None:
                csv_row["difficulty_level"] = ""
            writer.writerow({field: csv_row[field] for field in RATE_CI_CSV_FIELDS})


def render_rate_ci_markdown(payload: dict[str, Any]) -> str:
    rows = payload["rows"]
    lines = [
        "# Rate Confidence Interval Report",
        "",
        f"**Bootstrap resamples:** {payload['bootstrap_resamples']}",
        f"**Bootstrap seed:** {payload['bootstrap_seed']}",
        "",
        "Percentile bootstrap confidence intervals (95%) for exploratory model runs.",
        "Computed from existing `scores.jsonl` files only; no LLM re-runs.",
        "",
        f"**Score roots:** {len(payload['roots'])}",
    ]
    for root in payload["roots"]:
        lines.append(f"- `{root}`")
    lines.extend(["", f"**Rows:** {len(rows)}", ""])

    if not rows:
        lines.append("_No score files discovered._")
        return "\n".join(lines) + "\n"

    wide_rows = [row for row in rows if row["n"] >= 20]
    lines.extend(
        [
            "## Sample-size note",
            "",
            "Most capability-surface cells use `n=20` items per model per level.",
            "Bootstrap intervals are therefore wide; per-level rate movements should be",
            "read as descriptive capability profiles, not ranked performance claims.",
            "",
            "## Example rows (first five)",
            "",
            "| source | family | model | level | n | verdict [CI] | cert [CI] | full [CI] |",
            "|--------|--------|-------|------:|--:|--------------|-----------|-----------|",
        ]
    )
    for row in rows[:5]:
        level = row["difficulty_level"] if row["difficulty_level"] is not None else "—"
        lines.append(
            "| `{source}` | {family} | {model} | {level} | {n} | "
            "{verdict:.2f} [{vlo:.2f}, {vhi:.2f}] | "
            "{cert:.2f} [{clo:.2f}, {chi:.2f}] | "
            "{full:.2f} [{flo:.2f}, {fhi:.2f}] |".format(
                source=row["source_name"],
                family=row["family"],
                model=row["model"],
                level=level,
                n=row["n"],
                verdict=row["verdict_accuracy"],
                vlo=row["verdict_accuracy_ci_low"],
                vhi=row["verdict_accuracy_ci_high"],
                cert=row["certificate_valid_rate"],
                clo=row["certificate_valid_rate_ci_low"],
                chi=row["certificate_valid_rate_ci_high"],
                full=row["fully_correct_rate"],
                flo=row["fully_correct_rate_ci_low"],
                fhi=row["fully_correct_rate_ci_high"],
            )
        )

    if wide_rows:
        avg_width = sum(
            row["fully_correct_rate_ci_high"] - row["fully_correct_rate_ci_low"]
            for row in wide_rows
        ) / len(wide_rows)
        lines.extend(
            [
                "",
                "## Interval width (fully correct rate)",
                "",
                f"Mean CI width across rows with `n>=20`: **{avg_width:.3f}**.",
            ]
        )

    lines.append("")
    return "\n".join(lines)


def export_rate_ci_report(
    roots: list[str | Path],
    *,
    out_json: str | Path,
    out_csv: str | Path,
    out_md: str | Path,
    n_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    seed: int = 4242,
) -> dict[str, Path]:
    payload = build_rate_ci_report(roots, n_resamples=n_resamples, seed=seed)
    json_path = Path(out_json)
    csv_path = Path(out_csv)
    md_path = Path(out_md)
    dump_json(json_path, payload)
    write_rate_ci_csv(csv_path, payload["rows"])
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_rate_ci_markdown(payload), encoding="utf-8")
    return {"json": json_path, "csv": csv_path, "md": md_path}


def validate_rate_ci_row(row: dict[str, Any]) -> None:
    for field in RATE_CI_JSON_FIELDS:
        if field not in row:
            raise ValueError(f"missing required field: {field}")
