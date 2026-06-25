"""CLI: frontier campaign run-to-run replicate study (Experiment A)."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.evaluator.replicate_stability_export import (
    export_replicate_stability_package,
)
from fsmreasonbench.experiments.frontier_campaigns import (
    build_track_pilot_config,
    load_frontier_campaign_config,
)
from fsmreasonbench.experiments.replicate_studies import (
    build_aggregate_replicates,
    build_replicate_track_pilot_config,
    load_replicate_study_config,
    list_pending_replicates,
    replicate_campaign_out_dir,
    replicate_study_root,
    write_aggregate_replicates,
)
from fsmreasonbench.runners.providers.base import (
    ANTHROPIC_COST_WARNING,
    GEMINI_COST_WARNING,
    OPENAI_COST_WARNING,
    GenerateBackendConfig,
    build_generate_factory,
)
from fsmreasonbench.runners.track_pilot_models import run_track_pilot_models


def _print_cost_warning(provider: str, *, report_only: bool) -> None:
    if report_only:
        return
    if provider == "anthropic":
        print(ANTHROPIC_COST_WARNING, file=sys.stderr)
    elif provider == "openai":
        print(OPENAI_COST_WARNING, file=sys.stderr)
    elif provider == "gemini":
        print(GEMINI_COST_WARNING, file=sys.stderr)


def _run_single_replicate(
    repo_root: Path,
    campaign_config_path: Path,
    study_root: Path,
    replicate_id: int,
    *,
    report_only: bool,
    dry_run: bool,
    estimate_only: bool,
    provider_dry_run: bool,
) -> dict[str, object]:
    campaign = load_frontier_campaign_config(campaign_config_path)
    config = build_replicate_track_pilot_config(
        campaign,
        repo_root,
        replicate_id=replicate_id,
        study_root=study_root,
    )
    if report_only:
        config = replace(config, report_only=True)
    if dry_run:
        config = replace(config, dry_run=True)
    if estimate_only:
        config = replace(config, estimate_only=True)
    if provider_dry_run:
        config = replace(config, provider_dry_run=True)

    _print_cost_warning(campaign.provider, report_only=report_only)

    if report_only or estimate_only or provider_dry_run or dry_run:
        run_track_pilot_models(
            config,
            generate_factory=lambda _m, _t: (_ for _ in ()).throw(
                AssertionError("generate factory must not be invoked")
            ),
        )
    else:
        factory = build_generate_factory(
            GenerateBackendConfig(
                provider=campaign.provider,  # type: ignore[arg-type]
                timeout=config.timeout,
                max_tokens=config.max_tokens,
            )
        )
        run_track_pilot_models(config, generate_factory=factory)

    rep_dir = replicate_campaign_out_dir(study_root, replicate_id)
    return {
        "replicate_id": replicate_id,
        "replicate_dir": str(rep_dir),
        "combined_summary": str(rep_dir / "combined_summary.json"),
    }


def main(argv: list[str] | None = None) -> int:
    repo_root = find_repo_root()
    parser = argparse.ArgumentParser(
        description=(
            "Run frontier campaign replicates for run-to-run stability (Experiment A). "
            "Does not modify frozen single-run campaigns."
        ),
    )
    parser.add_argument(
        "--study-config",
        help="JSON study config (see configs/studies/*.json)",
    )
    parser.add_argument(
        "--config",
        help="Frontier campaign manifest (alternative to --study-config)",
    )
    parser.add_argument(
        "--replicates",
        type=int,
        default=1,
        help="Number of replicate executions (default: 1)",
    )
    parser.add_argument(
        "--replicate-id",
        type=int,
        default=None,
        help="Run a single replicate index (1-based)",
    )
    parser.add_argument(
        "--study-root",
        type=Path,
        default=None,
        help="Override replicate study root directory",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Regenerate summaries without API calls",
    )
    parser.add_argument(
        "--aggregate-only",
        action="store_true",
        help="Write aggregate_replicates.json and stability exports only",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
    )
    parser.add_argument(
        "--estimate-only",
        action="store_true",
    )
    parser.add_argument(
        "--provider-dry-run",
        action="store_true",
    )
    args = parser.parse_args(argv)

    if args.study_config:
        study = load_replicate_study_config(repo_root / args.study_config)
        campaign_config_path = repo_root / study.base_campaign_config
        replicates = study.replicates
        study_root = repo_root / study.study_root
        bootstrap_resamples = study.bootstrap_resamples
        bootstrap_seed = study.bootstrap_seed
    elif args.config:
        campaign_config_path = repo_root / args.config
        campaign = load_frontier_campaign_config(campaign_config_path)
        replicates = args.replicates
        study_root = args.study_root or replicate_study_root(repo_root / campaign.out_dir)
        bootstrap_resamples = 1000
        bootstrap_seed = 4242
    else:
        parser.error("specify --study-config or --config")

    if args.study_root is not None:
        study_root = args.study_root

    campaign = load_frontier_campaign_config(campaign_config_path)
    study_root.mkdir(parents=True, exist_ok=True)

    if args.aggregate_only:
        payload = build_aggregate_replicates(
            study_root,
            campaign_id=campaign.campaign_id,
            provider=campaign.provider,
            model=campaign.resolved_model,
            bootstrap_resamples=bootstrap_resamples,
            bootstrap_seed=bootstrap_seed,
        )
        agg_path = write_aggregate_replicates(study_root, payload)
        export_paths = export_replicate_stability_package(
            repo_root,
            study_root=study_root,
            campaign_id=campaign.campaign_id,
        )
        print(
            json.dumps(
                {
                    "aggregate_replicates": str(agg_path),
                    **export_paths,
                },
                indent=2,
            )
        )
        return 0

    if args.replicate_id is not None:
        replicate_ids = [args.replicate_id]
    else:
        if args.report_only:
            replicate_ids = list(range(1, replicates + 1))
        else:
            replicate_ids = list_pending_replicates(study_root, replicates) or list(
                range(1, replicates + 1)
            )

    run_results: list[dict[str, object]] = []
    for replicate_id in replicate_ids:
        if replicate_id < 1 or replicate_id > replicates:
            print(f"invalid replicate_id {replicate_id}", file=sys.stderr)
            return 2
        run_results.append(
            _run_single_replicate(
                repo_root,
                campaign_config_path,
                study_root,
                replicate_id,
                report_only=args.report_only,
                dry_run=args.dry_run,
                estimate_only=args.estimate_only,
                provider_dry_run=args.provider_dry_run,
            )
        )

    payload = build_aggregate_replicates(
        study_root,
        campaign_id=campaign.campaign_id,
        provider=campaign.provider,
        model=campaign.resolved_model,
        bootstrap_resamples=bootstrap_resamples,
        bootstrap_seed=bootstrap_seed,
    )
    agg_path = write_aggregate_replicates(study_root, payload)
    export_paths = export_replicate_stability_package(
        repo_root,
        study_root=study_root,
        campaign_id=campaign.campaign_id,
    )

    print(
        json.dumps(
            {
                "study_root": str(study_root),
                "replicates_requested": replicates,
                "runs": run_results,
                "aggregate_replicates": str(agg_path),
                **export_paths,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
