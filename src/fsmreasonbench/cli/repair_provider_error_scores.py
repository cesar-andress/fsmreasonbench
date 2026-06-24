"""Repair misclassified provider/API failures in existing run cell artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.evaluator.jsonl import read_jsonl, write_jsonl
from fsmreasonbench.runners.cell_failure import SCORES_JSONL
from fsmreasonbench.runners.experiment_cells import RESULTS_JSONL
from fsmreasonbench.runners.infrastructure_failure import reclassify_provider_error_scoring_row
from fsmreasonbench.runners.ollama_batch import _build_summary_from_scores


def _discover_cell_dirs(root: Path) -> list[Path]:
    return sorted({scores_path.parent for scores_path in root.rglob(SCORES_JSONL)})


def _sync_results_scoring(results_path: Path, scores_by_item: dict[str, dict[str, Any]]) -> int:
    if not results_path.exists():
        return 0
    updated = 0
    rows: list[dict[str, Any]] = []
    for row in read_jsonl(results_path):
        item_id = row.get("item_id")
        if isinstance(item_id, str) and item_id in scores_by_item:
            row["scoring_record"] = dict(scores_by_item[item_id])
            track_failure = scores_by_item[item_id].get("track_failure_class")
            if track_failure is not None:
                row["track_failure_class"] = track_failure
            updated += 1
        rows.append(row)
    write_jsonl(results_path, rows)
    return updated


def repair_cell_dir(cell_dir: Path, *, dry_run: bool) -> dict[str, Any]:
    scores_path = cell_dir / SCORES_JSONL
    if not scores_path.exists():
        return {"cell_dir": str(cell_dir), "status": "skipped", "reason": "missing scores.jsonl"}

    rows = [dict(row) for row in read_jsonl(scores_path)]
    repaired_items: list[str] = []
    for row in rows:
        if reclassify_provider_error_scoring_row(row):
            item_id = row.get("item_id")
            if isinstance(item_id, str):
                repaired_items.append(item_id)

    if not repaired_items:
        return {
            "cell_dir": str(cell_dir),
            "status": "unchanged",
            "repaired": 0,
        }

    if dry_run:
        return {
            "cell_dir": str(cell_dir),
            "status": "would_repair",
            "repaired": len(repaired_items),
            "sample_item_ids": repaired_items[:5],
        }

    write_jsonl(scores_path, rows)
    scores_by_item = {
        str(row["item_id"]): row for row in rows if isinstance(row.get("item_id"), str)
    }
    results_updated = _sync_results_scoring(cell_dir / RESULTS_JSONL, scores_by_item)

    summary_path = cell_dir / "summary.json"
    summary_meta: dict[str, Any] = {}
    if summary_path.exists():
        summary_meta = json.loads(summary_path.read_text(encoding="utf-8"))
    summary = _build_summary_from_scores(
        scoring_rows=rows,
        model=str(summary_meta.get("model", "unknown")),
        family=str(summary_meta.get("family", "unknown")),
        track=str(summary_meta.get("track", "R0")),
        provider=summary_meta.get("provider"),
        max_tokens=summary_meta.get("max_tokens"),
    )
    dump_json(summary_path, summary)
    dump_json(cell_dir / "track_summary.json", summary)

    return {
        "cell_dir": str(cell_dir),
        "status": "repaired",
        "repaired": len(repaired_items),
        "results_rows_updated": results_updated,
        "provider_error_count": summary.get("provider_error_count", 0),
        "provider_rate_limit_count": summary.get("provider_rate_limit_count", 0),
        "provider_insufficient_credit_count": summary.get(
            "provider_insufficient_credit_count", 0
        ),
        "failure_stage_counts": summary.get("failure_stage_counts"),
        "model_extractability_rate": summary.get("model_extractability_rate"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Reclassify provider/API HTTP failures from not_extractable to provider_error "
            "and rebuild per-cell summaries."
        ),
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        required=True,
        help="Run root (e.g. runs/frontier_claude_sonnet_full_n100_v1)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report cells/items that would be repaired without writing files",
    )
    args = parser.parse_args(argv)

    root = args.run_dir.resolve()
    if not root.is_dir():
        print(f"ERROR: run dir not found: {root}", file=sys.stderr)
        return 2

    reports: list[dict[str, Any]] = []
    total_repaired = 0
    for cell_dir in _discover_cell_dirs(root):
        report = repair_cell_dir(cell_dir, dry_run=args.dry_run)
        reports.append(report)
        if report.get("status") in {"repaired", "would_repair"}:
            total_repaired += int(report.get("repaired", 0))

    payload = {
        "run_dir": str(root),
        "dry_run": args.dry_run,
        "cells_examined": len(reports),
        "items_repaired": total_repaired,
        "cells": reports,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    if total_repaired and not args.dry_run:
        print(
            "\nNext: regenerate the matrix report with --report-only on the same out-dir.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
