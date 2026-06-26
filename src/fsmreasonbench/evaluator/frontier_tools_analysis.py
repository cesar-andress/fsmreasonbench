"""Analysis exports for frozen frontier tool-track campaigns (provider-agnostic)."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable

from fsmreasonbench.evaluator.bootstrap import DEFAULT_BOOTSTRAP_ALPHA, DEFAULT_BOOTSTRAP_RESAMPLES
from fsmreasonbench.evaluator.f1_claude_ablation_stratified_analysis import (
    ItemMetadata,
    ItemOutcome,
    exact_mcnemar_p_value,
    load_condition_outcomes,
    load_item_metadata,
    paired_bootstrap_difference_ci,
)
from fsmreasonbench.evaluator.tmlr_empirical_package import bootstrap_rate_ci
from fsmreasonbench.experiments.frontier_campaigns import (
    FrontierCampaignConfig,
    frontier_cell_scores_path,
    frontier_combined_summary_path,
    load_frontier_campaign_config,
)
from fsmreasonbench.runners.providers.base import resolve_provider_model


def _load_combined_summary(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def discover_completed_cells(
    combined_summary: dict[str, Any],
    *,
    repo_root: Path | None = None,
) -> list[dict[str, Any]]:
    """Return cell_inventory entries with on-disk scores (completed or partial)."""
    cells: list[dict[str, Any]] = []
    for cell in combined_summary.get("cell_inventory", []):
        run_dir = cell.get("run_dir")
        if not run_dir:
            continue
        run_path = Path(str(run_dir))
        if not run_path.is_absolute() and repo_root is not None:
            run_path = repo_root / run_path
        scores_path = run_path / "scores.jsonl"
        if scores_path.is_file():
            cells.append(cell)
    return cells


def _tracks_from_cells(cells: Iterable[dict[str, Any]]) -> tuple[str, ...]:
    return tuple(sorted({str(cell["track"]) for cell in cells if cell.get("track")}))


def _cell_has_scores(
    campaign: FrontierCampaignConfig,
    repo_root: Path,
    *,
    family: str,
    track: str,
) -> bool:
    return frontier_cell_scores_path(
        campaign, repo_root=repo_root, family=family, track=track
    ).is_file()


def _format_track_caption(tracks: Iterable[str]) -> str:
    ordered = [track for track in ("R0", "R1", "R2") if track in set(tracks)]
    if not ordered:
        return "selected tracks"
    if len(ordered) == 1:
        return f"track {ordered[0]}"
    return "tracks " + "/".join(ordered)


def _latex_escape(text: str) -> str:
    return (
        text.replace("\\", "\\textbackslash{}")
        .replace("_", "\\_")
        .replace("%", "\\%")
        .replace("&", "\\&")
    )


def _format_rate(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.3f}"


def build_summary_table_rows(combined_summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cell in combined_summary.get("cell_inventory", []):
        rows.append(
            {
                "family": cell.get("family"),
                "track": cell.get("track"),
                "n": cell.get("n"),
                "extractability_rate": cell.get("extractability_rate"),
                "verdict_accuracy": cell.get("verdict_accuracy"),
                "certificate_valid_rate": cell.get("certificate_valid_rate"),
                "fully_correct_rate": cell.get("fully_correct_rate"),
                "provider_error_count": cell.get("provider_error_count", 0),
                "status": cell.get("status"),
            }
        )
    return sorted(rows, key=lambda row: (row["family"], row["track"]))


def render_frontier_tools_latex_table(
    *,
    campaign_id: str,
    model_label: str,
    rows: list[dict[str, Any]],
    table_label: str,
    tracks_caption: str | None = None,
) -> str:
    source_path = _latex_escape(campaign_id)
    from fsmreasonbench.evaluator.paper_table_style import frozen_n100_caption

    caption = frozen_n100_caption(f"{model_label} tool-track rates")
    lines = [
        f"% Frozen frontier tools run. Source: {source_path}/combined_summary.json",
        "\\begin{table}[t]",
        "  \\centering",
        f"  \\caption{{{caption}}}",
        f"  \\label{{{table_label}}}",
        "  \\setlength{\\tabcolsep}{4pt}",
        "  \\begin{tabular}{@{}llrrrrr@{}}",
        "    \\toprule",
        "    Fam. & Track & $n$ & Extract. & Verdict & Cert. & Full \\\\",
        "    \\midrule",
    ]
    for row in rows:
        lines.append(
            "    "
            + " & ".join(
                [
                    str(row["family"]),
                    str(row["track"]),
                    str(row["n"]),
                    _format_rate(row["extractability_rate"]),
                    _format_rate(row["verdict_accuracy"]),
                    _format_rate(row["certificate_valid_rate"]),
                    _format_rate(row["fully_correct_rate"]),
                ]
            )
            + " \\\\"
        )
    lines.extend(
        [
            "    \\bottomrule",
            "  \\end{tabular}",
            "\\end{table}",
        ]
    )
    return "\n".join(lines) + "\n"


def _subtype_rows(
    outcomes: dict[str, ItemOutcome],
    metadata: dict[str, ItemMetadata],
    *,
    track: str,
) -> dict[str, dict[str, Any]]:
    by_type: dict[str, list[ItemOutcome]] = {
        "equivalence_witness": [],
        "distinguishing_trace": [],
    }
    for item_id, outcome in outcomes.items():
        meta = metadata[item_id]
        by_type[meta.gold_certificate_type].append(outcome)
    result: dict[str, dict[str, Any]] = {}
    for cert_type, subset in by_type.items():
        extractable = [row for row in subset if row.extractable]
        verdict_correct = sum(1 for row in extractable if row.verdict_correct is True)
        result[cert_type] = {
            "track": track,
            "certificate_type": cert_type,
            "n": len(subset),
            "extract": round(
                sum(1 for row in subset if row.extractable) / len(subset), 4
            )
            if subset
            else 0.0,
            "verdict": round(verdict_correct / len(extractable), 4) if extractable else 0.0,
            "cert": round(
                sum(1 for row in subset if row.certificate_valid) / len(subset), 4
            )
            if subset
            else 0.0,
            "full": round(
                sum(1 for row in subset if row.fully_correct) / len(subset), 4
            )
            if subset
            else 0.0,
        }
    return result


def build_f1_subtype_tables(
    campaign: FrontierCampaignConfig,
    repo_root: Path,
    *,
    cohort_items_path: Path,
    available_tracks: Iterable[str] | None = None,
) -> dict[str, Any]:
    metadata = load_item_metadata(cohort_items_path)
    if available_tracks is None:
        tracks = [
            track
            for track in campaign.tracks
            if track in {"R1", "R2"}
            and _cell_has_scores(campaign, repo_root, family="F1", track=track)
        ]
    else:
        tracks = [
            track
            for track in available_tracks
            if track in {"R1", "R2"}
            and _cell_has_scores(campaign, repo_root, family="F1", track=track)
        ]
    by_track: dict[str, Any] = {}
    for track in tracks:
        scores_path = frontier_cell_scores_path(
            campaign, repo_root=repo_root, family="F1", track=track
        )
        outcomes = load_condition_outcomes(scores_path)
        by_track[track] = _subtype_rows(outcomes, metadata, track=track)
    return {
        "campaign_id": campaign.campaign_id,
        "provider": campaign.provider,
        "model": campaign.model,
        "resolved_model": resolve_provider_model(campaign.provider, campaign.model),
        "cohort_items_path": str(cohort_items_path),
        "tracks_analyzed": tracks,
        "by_track": by_track,
    }


def _scores_path_for_cell(
    campaign: FrontierCampaignConfig,
    repo_root: Path,
    *,
    family: str,
    track: str,
    completed_cells: list[dict[str, Any]] | None = None,
) -> Path | None:
    if completed_cells:
        for cell in completed_cells:
            if cell.get("family") == family and cell.get("track") == track:
                run_dir = Path(str(cell["run_dir"]))
                if not run_dir.is_absolute():
                    run_dir = repo_root / run_dir
                candidate = run_dir / "scores.jsonl"
                if candidate.is_file():
                    return candidate
    candidate = frontier_cell_scores_path(
        campaign, repo_root=repo_root, family=family, track=track
    )
    return candidate if candidate.is_file() else None


def build_paired_track_comparisons(
    campaign: FrontierCampaignConfig,
    repo_root: Path,
    *,
    family: str = "F1",
    completed_cells: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    r1_path = _scores_path_for_cell(
        campaign, repo_root, family=family, track="R1", completed_cells=completed_cells
    )
    r2_path = _scores_path_for_cell(
        campaign, repo_root, family=family, track="R2", completed_cells=completed_cells
    )
    if r1_path is None or r2_path is None:
        return []
    r1 = load_condition_outcomes(r1_path)
    r2 = load_condition_outcomes(r2_path)
    shared = sorted(set(r1) & set(r2))
    comparisons: list[dict[str, Any]] = []
    for metric_name, getter in (
        ("certificate_valid", lambda row: row.certificate_valid),
        ("fully_correct", lambda row: row.fully_correct),
    ):
        first_only = second_only = 0
        first_vals: list[bool] = []
        second_vals: list[bool] = []
        for item_id in shared:
            first_val = getter(r1[item_id])
            second_val = getter(r2[item_id])
            first_vals.append(first_val)
            second_vals.append(second_val)
            if first_val and not second_val:
                first_only += 1
            elif second_val and not first_val:
                second_only += 1
        comparisons.append(
            {
                "comparison": f"{family} R1 vs R2 ({metric_name}, n={len(shared)})",
                "paired_items": len(shared),
                "first_track": "R1",
                "second_track": "R2",
                "metric": metric_name,
                "first_rate": asdict(bootstrap_rate_ci(first_vals, seed=6101)),
                "second_rate": asdict(bootstrap_rate_ci(second_vals, seed=6102)),
                "diff_first_minus_second": paired_bootstrap_difference_ci(
                    first_vals, second_vals, seed=6103
                ),
                "mcnemar_first_only": first_only,
                "mcnemar_second_only": second_only,
                "mcnemar_p_value": exact_mcnemar_p_value(first_only, second_only),
                "test_type": "paired_mcnemar_on_same_item_ids",
            }
        )
    return comparisons


def export_frontier_tools_n100_package(
    repo_root: Path,
    *,
    campaign_config_path: str | Path,
    json_out: str | Path | None = None,
    latex_out: str | Path | None = None,
    markdown_out: str | Path | None = None,
    subtype_json_out: str | Path | None = None,
    uncertainty_json_out: str | Path | None = None,
    cohort_items_path: str | Path | None = None,
    model_label: str | None = None,
    table_label: str | None = None,
) -> dict[str, Any]:
    campaign = load_frontier_campaign_config(campaign_config_path)
    combined_path = frontier_combined_summary_path(campaign, repo_root)
    if not combined_path.exists():
        raise FileNotFoundError(f"missing combined summary: {combined_path}")
    combined_summary = _load_combined_summary(combined_path)
    completed_cells = discover_completed_cells(combined_summary, repo_root=repo_root)
    available_tracks = _tracks_from_cells(completed_cells)
    summary_rows = build_summary_table_rows(
        {"cell_inventory": completed_cells},
    )
    resolved_model = resolve_provider_model(campaign.provider, campaign.model)
    label = model_label or resolved_model
    table_label_value = table_label or f"tab:{campaign.campaign_id.replace('_', '-')}-summary"

    cohort_path = Path(
        cohort_items_path
        or repo_root / "cohorts/v0.1-expanded-n100/f1-mixed-level3/items.jsonl"
    )
    subtype_tables = build_f1_subtype_tables(
        campaign,
        repo_root,
        cohort_items_path=cohort_path,
        available_tracks=available_tracks,
    )
    paired = build_paired_track_comparisons(
        campaign, repo_root, family="F1", completed_cells=completed_cells
    )
    paired.extend(
        build_paired_track_comparisons(
            campaign, repo_root, family="C2", completed_cells=completed_cells
        )
    )

    payload: dict[str, Any] = {
        "campaign_id": campaign.campaign_id,
        "provider": campaign.provider,
        "model": campaign.model,
        "resolved_model": resolved_model,
        "combined_summary_path": str(combined_path.relative_to(repo_root)),
        "tracks_available": list(available_tracks),
        "cells_exported": len(completed_cells),
        "summary_rows": summary_rows,
        "f1_subtype_tables": subtype_tables,
        "paired_track_comparisons": paired,
        "partial_run_note": (
            None
            if set(available_tracks) >= set(campaign.tracks)
            else (
                "Export includes only cells with on-disk scores.jsonl; "
                f"campaign manifest tracks={list(campaign.tracks)} "
                f"but available={list(available_tracks)}."
            )
        ),
        "bootstrap_settings": {
            "n_resamples": DEFAULT_BOOTSTRAP_RESAMPLES,
            "alpha": DEFAULT_BOOTSTRAP_ALPHA,
            "method": "percentile_bootstrap",
        },
    }

    if json_out is not None:
        out = Path(json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    if latex_out is not None:
        latex = render_frontier_tools_latex_table(
            campaign_id=campaign.out_dir,
            model_label=label,
            rows=summary_rows,
            table_label=table_label_value,
            tracks_caption=_format_track_caption(available_tracks),
        )
        Path(latex_out).parent.mkdir(parents=True, exist_ok=True)
        Path(latex_out).write_text(latex, encoding="utf-8")

    if markdown_out is not None:
        lines = [
            f"# Frontier tools summary — {campaign.campaign_id}",
            "",
            f"- Provider: `{campaign.provider}`",
            f"- Model: `{resolved_model}`",
            f"- Run root: `{campaign.out_dir}`",
            "",
            "| Family | Track | n | Extract | Verdict | Cert | Full | Provider errors |",
            "|--------|-------|---:|--------:|--------:|-----:|-----:|----------------:|",
        ]
        for row in summary_rows:
            lines.append(
                "| {family} | {track} | {n} | {extractability_rate:.3f} | "
                "{verdict_accuracy:.3f} | {certificate_valid_rate:.3f} | "
                "{fully_correct_rate:.3f} | {provider_error_count} |".format(**row)
            )
        Path(markdown_out).parent.mkdir(parents=True, exist_ok=True)
        Path(markdown_out).write_text("\n".join(lines) + "\n", encoding="utf-8")

    if subtype_json_out is not None:
        out = Path(subtype_json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(subtype_tables, indent=2) + "\n", encoding="utf-8")

    if uncertainty_json_out is not None:
        out = Path(uncertainty_json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(
                {
                    "campaign_id": campaign.campaign_id,
                    "paired_track_comparisons": paired,
                    "bootstrap_settings": payload["bootstrap_settings"],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    return payload
