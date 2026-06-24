"""Run F1 R2 attribution ablation (R2A verify-only, R2B repair-only, R2C generator-assisted)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fsmreasonbench.cohort.expanded_n100 import EXPANDED_COHORT_ROOT, resolve_cohort_bundle
from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.evaluator.r2_attribution_report import (
    finalize_r2_attribution_mode_run,
    finalize_r2_attribution_study,
)
from fsmreasonbench.evaluator.jsonl import load_items_jsonl
from fsmreasonbench.runners.ollama_batch import OllamaBatchConfig
from fsmreasonbench.runners.providers.base import (
    ANTHROPIC_COST_WARNING,
    GenerateBackendConfig,
    build_generate_factory,
)
from fsmreasonbench.runners.r2_attribution_batch import run_r2_attribution_batch
from fsmreasonbench.runners.r2_attribution_prompts import R2AttributionMode

DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
DEFAULT_PARENT_DIR = "runs/ablations_f1_r2_attribution_claude_n100_v1"
DEFAULT_BASELINE = "runs/frontier_claude_sonnet_tools_n100_v2"
DEFAULT_ORACLE = "runs/ablations_f1_oracle_verdict_format_control_claude_n100_v1"
DEFAULT_TIMEOUT = 86400.0
DEFAULT_MAX_TOKENS = 2048


def _parse_mode(value: str) -> R2AttributionMode:
    normalized = value.strip().upper()
    try:
        return R2AttributionMode(normalized)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"invalid mode {value!r}; expected R2A, R2B, or R2C"
        ) from exc


def _modes_from_args(args: argparse.Namespace) -> list[R2AttributionMode]:
    if args.all_modes:
        return list(R2AttributionMode)
    if args.mode is None:
        raise SystemExit("specify --mode R2A|R2B|R2C or --all")
    return [args.mode]


def main(argv: list[str] | None = None) -> int:
    repo_root = find_repo_root()
    parser = argparse.ArgumentParser(
        description="F1 R2 attribution ablation: decompose certificate construction vs tools",
    )
    parser.add_argument(
        "--parent-dir",
        type=Path,
        default=repo_root / DEFAULT_PARENT_DIR,
        help=f"Study root (default: {DEFAULT_PARENT_DIR})",
    )
    parser.add_argument(
        "--mode",
        type=_parse_mode,
        default=None,
        help="Run one mode: R2A, R2B, or R2C",
    )
    parser.add_argument(
        "--all",
        dest="all_modes",
        action="store_true",
        help="Run all three modes sequentially",
    )
    parser.add_argument(
        "--baseline-dir",
        type=Path,
        default=repo_root / DEFAULT_BASELINE,
        help=f"Frozen Claude tools run (default: {DEFAULT_BASELINE})",
    )
    parser.add_argument(
        "--oracle-dir",
        type=Path,
        default=repo_root / DEFAULT_ORACLE,
        help=f"Frozen oracle-verdict ablation (default: {DEFAULT_ORACLE})",
    )
    parser.add_argument(
        "--cohort-root",
        type=Path,
        default=repo_root / EXPANDED_COHORT_ROOT,
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-items", type=int, default=100)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--provider-retries", type=int, default=3)
    parser.add_argument("--provider-retry-backoff", type=float, default=5.0)
    parser.add_argument("--provider-max-retry-delay", type=float, default=120.0)
    parser.add_argument("--provider-sleep-between-items", type=float, default=0.0)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Regenerate aggregate report from existing mode summaries",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Smoke mode: n=5 per condition",
    )
    args = parser.parse_args(argv)

    bundle = resolve_cohort_bundle(args.cohort_root)
    _c2_items_path, f1_items_path, _c2_cohort_id, f1_cohort_id = bundle
    items = load_items_jsonl(f1_items_path)
    max_items = 5 if args.smoke else args.max_items
    args.parent_dir.mkdir(parents=True, exist_ok=True)

    if args.report_only:
        combined = finalize_r2_attribution_study(
            args.parent_dir,
            frozen_tools_root=args.baseline_dir,
            oracle_ablation_root=args.oracle_dir,
            cohort_id=f1_cohort_id,
            temperature=args.temperature,
        )
        print(
            json.dumps(
                {
                    "report": str(args.parent_dir / "report.md"),
                    "combined_summary": str(args.parent_dir / "combined_summary.json"),
                    "modes_completed": len(combined.get("track_rows", [])),
                },
                indent=2,
            )
        )
        return 0

    modes = _modes_from_args(args)
    print(ANTHROPIC_COST_WARNING, file=sys.stderr)
    generate_factory = build_generate_factory(
        GenerateBackendConfig(
            provider="anthropic",
            timeout=args.timeout,
            max_tokens=args.max_tokens,
        )
    )
    generate = generate_factory(args.model, args.temperature)
    batch_config = OllamaBatchConfig(
        model=args.model,
        temperature=args.temperature,
        timeout=args.timeout,
        max_items=max_items,
        resume_items=not args.force,
        force_cell=args.force,
        provider="anthropic",
        max_tokens=args.max_tokens,
        provider_retries=args.provider_retries,
        provider_retry_backoff_seconds=args.provider_retry_backoff,
        provider_max_retry_delay_seconds=args.provider_max_retry_delay,
        provider_sleep_between_items=args.provider_sleep_between_items,
    )

    run_results: list[dict[str, object]] = []
    for mode in modes:
        mode_dir = args.parent_dir / mode.value
        result = run_r2_attribution_batch(
            items,
            generate,
            mode_dir,
            batch_config,
            mode,
        )
        finalize_r2_attribution_mode_run(
            mode_dir,
            summary=result.summary,
            cohort_id=f1_cohort_id,
            temperature=args.temperature,
        )
        run_results.append(
            {
                "mode": mode.value,
                "out_dir": str(result.out_dir),
                "n": result.summary.get("n"),
                "certificate_valid_rate": result.summary.get("certificate_valid_rate"),
                "fully_correct_rate": result.summary.get("fully_correct_rate"),
                "infrastructure_failures": result.infrastructure_failures,
            }
        )

    combined = finalize_r2_attribution_study(
        args.parent_dir,
        frozen_tools_root=args.baseline_dir,
        oracle_ablation_root=args.oracle_dir,
        cohort_id=f1_cohort_id,
        temperature=args.temperature,
    )
    print(
        json.dumps(
            {
                "parent_dir": str(args.parent_dir),
                "max_items_requested": max_items,
                "modes": run_results,
                "report": str(args.parent_dir / "report.md"),
                "combined_summary": str(args.parent_dir / "combined_summary.json"),
                "modes_in_report": len(combined.get("track_rows", [])),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
