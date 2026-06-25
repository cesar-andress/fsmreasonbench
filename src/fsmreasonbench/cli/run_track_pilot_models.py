"""Run multi-model R0/R1/R2 track pilot on frozen exploratory cohorts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fsmreasonbench.cohort.expanded_n100 import resolve_cohort_bundle
from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.runners.experiment_cells import DEFAULT_STALE_RUNNING_SECONDS
from fsmreasonbench.runners.providers.base import (
    ANTHROPIC_COST_WARNING,
    GEMINI_COST_WARNING,
    OPENAI_COST_WARNING,
    GenerateBackendConfig,
    build_generate_factory,
    resolve_provider_model,
)
from fsmreasonbench.runners.track_pilot_models import (
    DEFAULT_C2_COHORT_ID,
    DEFAULT_C2_ITEMS,
    DEFAULT_F1_COHORT_ID,
    DEFAULT_F1_ITEMS,
    EXPANDED_COHORT_ROOT,
    TrackPilotModelsConfig,
    apply_incremental_safe,
    infer_matrix_layout,
    parse_temperatures,
    run_track_pilot_models,
)
from fsmreasonbench.tracks.models import TrackId


def _parse_csv(raw: str) -> tuple[str, ...]:
    values = tuple(part.strip() for part in raw.split(",") if part.strip())
    if not values:
        raise ValueError("expected at least one value")
    return values


def _add_bool_flag(parser: argparse.ArgumentParser, name: str, default: bool, help_text: str) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument(f"--{name}", dest=name.replace("-", "_"), action="store_true", help=help_text)
    group.add_argument(
        f"--no-{name}",
        dest=name.replace("-", "_"),
        action="store_false",
        help=f"Disable --{name}",
    )
    parser.set_defaults(**{name.replace("-", "_"): default})


def main(argv: list[str] | None = None) -> int:
    repo_root = find_repo_root()
    parser = argparse.ArgumentParser(
        description="Run R0/R1/R2 track pilot across Ollama, Anthropic, OpenAI, or Gemini backends",
    )
    parser.add_argument(
        "--provider",
        choices=("ollama", "anthropic", "openai", "gemini"),
        default="ollama",
        help="Model backend (default: ollama)",
    )
    parser.add_argument(
        "--models",
        default="qwen2.5-coder:7b,llama3.1:8b,mistral-nemo:12b,gemma2:9b",
        help="Comma-separated model names for the selected provider",
    )
    parser.add_argument(
        "--families",
        default="C2,F1",
        help="Comma-separated families (default: C2,F1)",
    )
    parser.add_argument(
        "--tracks",
        default="R0,R1,R2",
        help="Comma-separated tracks (default: R0,R1,R2)",
    )
    parser.add_argument(
        "--c2-items",
        default=str(repo_root / DEFAULT_C2_ITEMS),
        help=f"C2 items JSONL (default: {DEFAULT_C2_ITEMS})",
    )
    parser.add_argument(
        "--f1-items",
        default=str(repo_root / DEFAULT_F1_ITEMS),
        help=f"F1 items JSONL (default: {DEFAULT_F1_ITEMS})",
    )
    parser.add_argument(
        "--cohort-root",
        type=Path,
        help=(
            "Cohort bundle root with c2-reachability-level3/ and f1-mixed-level3/ "
            f"(e.g. {EXPANDED_COHORT_ROOT}); overrides --c2-items/--f1-items and cohort IDs"
        ),
    )
    parser.add_argument(
        "--c2-cohort-id",
        help="Cohort ID recorded in reports (default: inferred from items path or manifest)",
    )
    parser.add_argument(
        "--f1-cohort-id",
        help="Cohort ID recorded in reports (default: inferred from items path or manifest)",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=20,
        help="Max items per cell (default: 20)",
    )
    parser.add_argument(
        "--temperatures",
        help="Comma-separated sampling temperatures (e.g. 0,0.2,0.7)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Single temperature when --temperatures is not set (default: 0.0)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="Per-item HTTP timeout in seconds (default: 120; use --no-timeout to disable)",
    )
    parser.add_argument(
        "--no-timeout",
        action="store_true",
        help="Disable per-item HTTP timeout (cell-level --cell-timeout still applies if set)",
    )
    parser.add_argument(
        "--item-timeout",
        type=float,
        help="Per-item timeout in seconds (default: inherit --timeout)",
    )
    parser.add_argument(
        "--cell-timeout",
        type=float,
        help="Per-cell timeout in seconds (default: no cell-level timeout)",
    )
    parser.add_argument(
        "--provider-retries",
        type=int,
        help="Per-item retry count for transient provider errors or Ollama timeouts (default: inherit --ollama-retries or 0)",
    )
    parser.add_argument(
        "--ollama-retries",
        type=int,
        default=0,
        help="Alias for --provider-retries on Ollama timeout recovery (default: 0)",
    )
    _add_bool_flag(
        parser,
        "ollama-restart-on-timeout",
        default=False,
        help_text="Run `ollama stop <model>` and wait before retrying a timed-out item",
    )
    _add_bool_flag(
        parser,
        "skip-item-on-timeout",
        default=True,
        help_text="Mark timed-out items as infrastructure failures and continue the cell (default: true)",
    )
    parser.add_argument(
        "--provider-retry-backoff",
        "--provider-backoff-base",
        type=float,
        default=5.0,
        dest="provider_retry_backoff",
        help="Base seconds for exponential provider retry backoff with jitter (default: 5)",
    )
    parser.add_argument(
        "--provider-sleep-between-items",
        type=float,
        default=0.0,
        help="Seconds to sleep after each scored item (Gemini throttling; default: 0)",
    )
    parser.add_argument(
        "--provider-max-retry-delay",
        type=float,
        default=120.0,
        help="Cap seconds for a single provider retry sleep (default: 120)",
    )
    parser.add_argument(
        "--ollama-stop-delay",
        type=float,
        default=5.0,
        help="Seconds to wait after `ollama stop` before retry (default: 5)",
    )
    parser.add_argument(
        "--fail-cell-after-item-failures",
        type=int,
        help="Fail the cell after N item infrastructure failures (default: unlimited)",
    )
    parser.add_argument(
        "--max-cells",
        type=int,
        help="Stop after executing N cells (default: unlimited)",
    )
    parser.add_argument(
        "--sleep-between-cells",
        type=float,
        default=5.0,
        help="Seconds to sleep between cells (default: 5)",
    )
    parser.add_argument(
        "--stop-after-failures",
        type=int,
        default=3,
        help="Stop after N consecutive cell failures (default: 3)",
    )
    parser.add_argument(
        "--stale-running-seconds",
        type=float,
        default=DEFAULT_STALE_RUNNING_SECONDS,
        help=f"Treat running cells as stale after N seconds (default: {DEFAULT_STALE_RUNNING_SECONDS:g})",
    )
    parser.add_argument(
        "--out-dir",
        default="runs/track_pilot_v1",
        help="Output directory (default: runs/track_pilot_v1)",
    )
    parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434",
        help="Ollama base URL (default: http://localhost:11434)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run all cells (alias for --force-all)",
    )
    parser.add_argument(
        "--force-all",
        action="store_true",
        help="Re-run all cells even when completed",
    )
    parser.add_argument(
        "--force-cell",
        action="store_true",
        help="Wipe cell outputs before each run (disables item-level resume for that cell)",
    )
    _add_bool_flag(
        parser,
        "resume-items",
        default=True,
        help_text="Resume partial cells from existing scores.jsonl (default: true)",
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Retry failed, missing, partial, stale-running, and orphan running cells; skip completed",
    )
    parser.add_argument(
        "--skip-failed",
        action="store_true",
        help="Skip cells with error.json (do not retry failed cells)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=8192,
        help="Anthropic/OpenAI max_tokens per request (default: 8192)",
    )
    parser.add_argument(
        "--provider-dry-run",
        action="store_true",
        help="Build provider request payloads and write provider_dry_run.json without API calls",
    )
    parser.add_argument(
        "--estimate-only",
        action="store_true",
        help="Write frontier_estimate.json with planned item/API-call counts and exit",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned cell actions without calling models",
    )
    parser.add_argument(
        "--incremental-safe",
        action="store_true",
        help="Resume partial cells and stop after the first cell failure (sleep=10s between cells)",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Regenerate combined_summary.json and report.md from on-disk cell artifacts",
    )
    _add_bool_flag(
        parser,
        "matrix-layout",
        default=None,
        help_text="Use temp_{temperature}/ track directories (auto for local_matrix runs)",
    )
    args = parser.parse_args(argv)

    if args.max_items < 1:
        parser.error("--max-items must be >= 1")
    if args.max_tokens < 1:
        parser.error("--max-tokens must be >= 1")
    if args.ollama_retries < 0:
        parser.error("--ollama-retries must be >= 0")
    if args.provider_retries is not None and args.provider_retries < 0:
        parser.error("--provider-retries must be >= 0")
    if args.provider_retry_backoff < 0:
        parser.error("--provider-retry-backoff must be >= 0")
    if args.provider_max_retry_delay < 0:
        parser.error("--provider-max-retry-delay must be >= 0")
    if args.provider_sleep_between_items < 0:
        parser.error("--provider-sleep-between-items must be >= 0")
    if args.ollama_stop_delay < 0:
        parser.error("--ollama-stop-delay must be >= 0")
    if args.fail_cell_after_item_failures is not None and args.fail_cell_after_item_failures < 1:
        parser.error("--fail-cell-after-item-failures must be >= 1")
    if args.estimate_only and args.report_only:
        parser.error("--estimate-only cannot be combined with --report-only")
    if args.provider_dry_run and args.report_only:
        parser.error("--provider-dry-run cannot be combined with --report-only")
    if args.provider == "anthropic" and not args.report_only:
        print(ANTHROPIC_COST_WARNING, file=sys.stderr)
    if args.provider == "openai" and not args.report_only:
        print(OPENAI_COST_WARNING, file=sys.stderr)
    if args.provider == "gemini" and not args.report_only:
        print(GEMINI_COST_WARNING, file=sys.stderr)

    try:
        models = _parse_csv(args.models)
        model_args = models
        if args.provider in {"anthropic", "openai", "gemini"}:
            models = tuple(resolve_provider_model(args.provider, model) for model in models)
        else:
            models = tuple(models)
        families = _parse_csv(args.families)
        tracks = _parse_csv(args.tracks)
        temperatures = (
            parse_temperatures(args.temperatures)
            if args.temperatures
            else (args.temperature,)
        )
        for family in families:
            if family not in {"C2", "F1"}:
                raise ValueError(f"unsupported family: {family!r}")
        for track in tracks:
            TrackId(track)
    except ValueError as exc:
        parser.error(str(exc))

    if args.retry_failed and args.skip_failed:
        parser.error("--retry-failed and --skip-failed are mutually exclusive")
    force_all = args.force or args.force_all
    if force_all and args.retry_failed:
        parser.error("--force/--force-all and --retry-failed are mutually exclusive")
    if args.report_only and force_all:
        parser.error("--report-only cannot be combined with --force/--force-all")
    if args.dry_run and force_all:
        parser.error("--dry-run cannot be combined with --force/--force-all")
    if args.no_timeout and args.timeout != 120.0:
        parser.error("--no-timeout cannot be combined with an explicit --timeout value")

    request_timeout = None if args.no_timeout else args.timeout

    if args.matrix_layout is None:
        matrix_layout = infer_matrix_layout(args.out_dir) or args.temperatures is not None
    else:
        matrix_layout = args.matrix_layout

    c2_items_path = Path(args.c2_items)
    f1_items_path = Path(args.f1_items)
    c2_cohort_id = args.c2_cohort_id or DEFAULT_C2_COHORT_ID
    f1_cohort_id = args.f1_cohort_id or DEFAULT_F1_COHORT_ID
    if args.cohort_root is not None:
        c2_items_path, f1_items_path, c2_cohort_id, f1_cohort_id = resolve_cohort_bundle(
            args.cohort_root
        )

    resolved_provider_retries = (
        args.provider_retries
        if args.provider_retries is not None
        else args.ollama_retries
    )

    config = apply_incremental_safe(
        TrackPilotModelsConfig(
            models=models,
            model_args=tuple(model_args),
            families=families,
            tracks=tracks,
            c2_items_path=c2_items_path,
            f1_items_path=f1_items_path,
            out_dir=args.out_dir,
            max_items=args.max_items,
            temperatures=temperatures,
            timeout=request_timeout,
            skip_completed=not force_all and not args.retry_failed,
            retry_failed=args.retry_failed,
            skip_failed=args.skip_failed,
            force=args.force,
            force_all=force_all,
            force_cell=args.force_cell,
            resume_items=args.resume_items,
            dry_run=args.dry_run,
            report_only=args.report_only,
            max_cells=args.max_cells,
            cell_timeout=args.cell_timeout,
            item_timeout=args.item_timeout,
            ollama_retries=resolved_provider_retries,
            provider_retries=resolved_provider_retries,
            ollama_restart_on_timeout=args.ollama_restart_on_timeout,
            skip_item_on_timeout=args.skip_item_on_timeout,
            ollama_stop_delay_seconds=args.ollama_stop_delay,
            provider_retry_backoff_seconds=args.provider_retry_backoff,
            provider_max_retry_delay_seconds=args.provider_max_retry_delay,
            provider_sleep_between_items=args.provider_sleep_between_items,
            fail_cell_after_item_failures=args.fail_cell_after_item_failures,
            sleep_between_cells=args.sleep_between_cells,
            stop_after_failures=args.stop_after_failures,
            stale_running_seconds=args.stale_running_seconds,
            incremental_safe=args.incremental_safe,
            matrix_layout=matrix_layout,
            c2_cohort_id=c2_cohort_id,
            f1_cohort_id=f1_cohort_id,
            provider=args.provider,
            max_tokens=args.max_tokens,
            provider_dry_run=args.provider_dry_run,
            estimate_only=args.estimate_only,
            ollama_base_url=args.ollama_url,
        )
    )

    backend = GenerateBackendConfig(
        provider=args.provider,
        timeout=request_timeout,
        max_tokens=args.max_tokens,
        ollama_base_url=args.ollama_url,
        provider_dry_run=args.provider_dry_run,
    )

    def generate_factory(model: str, temperature: float):
        factory = build_generate_factory(
            GenerateBackendConfig(
                provider=backend.provider,
                temperature=temperature,
                timeout=(
                    args.item_timeout
                    if args.item_timeout is not None
                    else request_timeout
                ),
                max_tokens=backend.max_tokens,
                ollama_base_url=backend.ollama_base_url,
            )
        )
        return factory(model, temperature)

    try:
        result = run_track_pilot_models(config, generate_factory)
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    counts = result.cell_status_counts
    incomplete = sum(
        counts.get(key, 0)
        for key in ("failed", "missing", "partial", "running", "stale-running")
    )
    print(
        json.dumps(
            {
                "out_dir": str(result.out_dir),
                "models": list(models),
                "families": list(families),
                "tracks": list(tracks),
                "temperatures": list(temperatures),
                "provider": args.provider,
                "cells_completed": counts.get("completed", 0),
                "cells_incomplete": incomplete,
                "cell_status_counts": counts,
                "combined_summary": str(result.out_dir / "combined_summary.json"),
                "report": str(result.out_dir / "report.md"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if incomplete == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
