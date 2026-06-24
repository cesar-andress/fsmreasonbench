"""Run F1 oracle-verdict + format-control certificate ablation (Claude Sonnet)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fsmreasonbench.cohort.expanded_n100 import EXPANDED_COHORT_ROOT, resolve_cohort_bundle
from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.evaluator.ablation_report import finalize_ablation_run
from fsmreasonbench.evaluator.jsonl import load_items_jsonl
from fsmreasonbench.runners.ablation_batch import run_f1_oracle_verdict_ablation_batch
from fsmreasonbench.runners.ablation_prompts import ABLATION_CONDITION_ID
from fsmreasonbench.runners.ollama_batch import OllamaBatchConfig
from fsmreasonbench.runners.providers.base import (
    ANTHROPIC_COST_WARNING,
    GenerateBackendConfig,
    build_generate_factory,
)

DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
DEFAULT_OUT_DIR = "runs/ablations_f1_oracle_verdict_format_control_claude_n100_v1"
DEFAULT_BASELINE = "runs/frontier_claude_sonnet_tools_n100_v2"
# Match frozen Claude tools n=100 run (report.md item/item_timeout).
DEFAULT_TIMEOUT = 86400.0
DEFAULT_MAX_TOKENS = 2048


def main(argv: list[str] | None = None) -> int:
    repo_root = find_repo_root()
    parser = argparse.ArgumentParser(
        description=(
            "F1 oracle-verdict format-control ablation: fixed gold verdict, "
            "certificate-only submission, no tools"
        ),
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=repo_root / DEFAULT_OUT_DIR,
        help=f"Run output directory (default: {DEFAULT_OUT_DIR})",
    )
    parser.add_argument(
        "--baseline-dir",
        type=Path,
        default=repo_root / DEFAULT_BASELINE,
        help=f"Frozen Claude tools run for comparison (default: {DEFAULT_BASELINE})",
    )
    parser.add_argument(
        "--cohort-root",
        type=Path,
        default=repo_root / EXPANDED_COHORT_ROOT,
        help=f"F1 cohort bundle root (default: {EXPANDED_COHORT_ROOT})",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-items", type=int, default=100)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--provider-retries", type=int, default=3)
    parser.add_argument(
        "--provider-retry-backoff",
        type=float,
        default=5.0,
        help="Base seconds for provider retry backoff (default: 5)",
    )
    parser.add_argument(
        "--provider-max-retry-delay",
        type=float,
        default=120.0,
        help="Cap seconds for provider retry sleep (default: 120)",
    )
    parser.add_argument(
        "--provider-sleep-between-items",
        type=float,
        default=0.0,
    )
    parser.add_argument(
        "--no-json-repair",
        action="store_true",
        help="Disable JSON-repair secondary scoring",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run all items even if scores.jsonl exists",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Regenerate report/combined_summary from existing scores",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Smoke mode alias for --max-items 5 (overrides --max-items when set)",
    )
    args = parser.parse_args(argv)

    bundle = resolve_cohort_bundle(args.cohort_root)
    _c2_items_path, f1_items_path, _c2_cohort_id, f1_cohort_id = bundle
    items = load_items_jsonl(f1_items_path)
    max_items = 5 if args.smoke else args.max_items

    if args.report_only:
        summary_path = args.out_dir / "summary.json"
        if not summary_path.exists():
            print(f"missing summary: {summary_path}", file=sys.stderr)
            return 1
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        finalize_ablation_run(
            args.out_dir,
            summary=summary,
            baseline_root=args.baseline_dir if args.baseline_dir.exists() else None,
            cohort_id=f1_cohort_id,
            temperature=args.temperature,
        )
        print(json.dumps({"report": str(args.out_dir / "report.md")}, indent=2))
        return 0

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
    result = run_f1_oracle_verdict_ablation_batch(
        items,
        generate,
        args.out_dir,
        batch_config,
        json_repair=not args.no_json_repair,
    )
    finalize_ablation_run(
        args.out_dir,
        summary=result.summary,
        baseline_root=args.baseline_dir if args.baseline_dir.exists() else None,
        cohort_id=f1_cohort_id,
        temperature=args.temperature,
    )
    print(
        json.dumps(
            {
                "ablation_condition": ABLATION_CONDITION_ID,
                "out_dir": str(result.out_dir),
                "n": result.summary.get("n"),
                "max_items_requested": max_items,
                "infrastructure_failures": result.infrastructure_failures,
                "certificate_valid_rate": result.summary.get("certificate_valid_rate"),
                "fully_correct_rate": result.summary.get("fully_correct_rate"),
                "report": str(result.out_dir / "report.md"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
