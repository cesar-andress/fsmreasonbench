"""Run a frozen frontier campaign from a JSON manifest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dataclasses import replace

from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.experiments.frontier_campaigns import (
    build_track_pilot_config,
    load_frontier_campaign_config,
)
from fsmreasonbench.runners.providers.base import (
    ANTHROPIC_COST_WARNING,
    GEMINI_COST_WARNING,
    OPENAI_COST_WARNING,
    GenerateBackendConfig,
    build_generate_factory,
)
from fsmreasonbench.runners.track_pilot_models import run_track_pilot_models


def main(argv: list[str] | None = None) -> int:
    repo_root = find_repo_root()
    parser = argparse.ArgumentParser(
        description="Execute a frozen frontier campaign manifest (Claude-parity protocol)",
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to configs/frontier/*.json campaign manifest",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Regenerate combined_summary.json and report.md without API calls",
    )
    parser.add_argument(
        "--estimate-only",
        action="store_true",
        help="Write frontier_estimate.json and exit without API calls",
    )
    parser.add_argument(
        "--provider-dry-run",
        action="store_true",
        help="Write provider_dry_run.json without API calls",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned cell actions without calling models",
    )
    parser.add_argument(
        "--smoke-only",
        action="store_true",
        help="Run one OpenAI smoke request and exit (no campaign cells)",
    )
    args = parser.parse_args(argv)

    campaign = load_frontier_campaign_config(repo_root / args.config)
    if args.smoke_only:
        if campaign.provider != "openai":
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": f"--smoke-only supports provider=openai only; got {campaign.provider!r}",
                    },
                    indent=2,
                )
            )
            return 2
        from fsmreasonbench.runners.providers.openai import run_openai_smoke_test

        payload = run_openai_smoke_test(model=campaign.model, max_tokens=campaign.max_tokens)
        payload["ok"] = True
        print(json.dumps(payload, indent=2))
        return 0

    config = build_track_pilot_config(campaign, repo_root)
    if args.report_only:
        config = replace(config, report_only=True)
    if args.estimate_only:
        config = replace(config, estimate_only=True)
    if args.provider_dry_run:
        config = replace(config, provider_dry_run=True)
    if args.dry_run:
        config = replace(config, dry_run=True)

    if campaign.provider == "anthropic" and not (
        args.report_only or args.estimate_only or args.provider_dry_run or args.dry_run
    ):
        print(ANTHROPIC_COST_WARNING, file=sys.stderr)
    if campaign.provider == "openai" and not (
        args.report_only or args.estimate_only or args.provider_dry_run or args.dry_run
    ):
        print(OPENAI_COST_WARNING, file=sys.stderr)
    if campaign.provider == "gemini" and not (
        args.report_only or args.estimate_only or args.provider_dry_run or args.dry_run
    ):
        print(GEMINI_COST_WARNING, file=sys.stderr)

    if args.report_only or args.estimate_only or args.provider_dry_run or args.dry_run:
        run_track_pilot_models(config, generate_factory=lambda _m, _t: (_ for _ in ()).throw(
            AssertionError("generate factory must not be invoked")
        ))
    else:
        factory = build_generate_factory(
            GenerateBackendConfig(
                provider=campaign.provider,  # type: ignore[arg-type]
                timeout=config.timeout,
                max_tokens=config.max_tokens,
            )
        )
        run_track_pilot_models(config, generate_factory=factory)

    print(
        json.dumps(
            {
                "campaign_id": campaign.campaign_id,
                "provider": campaign.provider,
                "model": campaign.model,
                "out_dir": str(config.out_dir),
                "tracks": list(campaign.tracks),
                "families": list(campaign.families),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
