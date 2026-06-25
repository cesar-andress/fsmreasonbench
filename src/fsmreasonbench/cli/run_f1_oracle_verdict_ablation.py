"""Run F1 oracle-verdict + format-control certificate ablation."""

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
    OPENAI_COST_WARNING,
    GenerateBackendConfig,
    ProviderId,
    build_generate_factory,
    resolve_provider_model,
)

DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"
DEFAULT_OPENAI_MODEL = "gpt-4.1"
DEFAULT_OUT_DIR_CLAUDE = "runs/ablations_f1_oracle_verdict_format_control_claude_n100_v1"
DEFAULT_OUT_DIR_OPENAI = "runs/ablations_f1_oracle_verdict_format_control_gpt_n100_v1"
DEFAULT_BASELINE_CLAUDE = "runs/frontier_claude_sonnet_tools_n100_v2"
DEFAULT_BASELINE_OPENAI = "runs/frontier_gpt_tools_n100_v1"
DEFAULT_TIMEOUT = 86400.0
DEFAULT_MAX_TOKENS = 2048


def _default_out_dir(provider: ProviderId, repo_root: Path) -> Path:
    rel = DEFAULT_OUT_DIR_OPENAI if provider == "openai" else DEFAULT_OUT_DIR_CLAUDE
    return repo_root / rel


def _default_baseline_dir(provider: ProviderId, repo_root: Path) -> Path:
    rel = DEFAULT_BASELINE_OPENAI if provider == "openai" else DEFAULT_BASELINE_CLAUDE
    return repo_root / rel


def _default_model(provider: ProviderId) -> str:
    return DEFAULT_OPENAI_MODEL if provider == "openai" else DEFAULT_ANTHROPIC_MODEL


def main(argv: list[str] | None = None) -> int:
    repo_root = find_repo_root()
    parser = argparse.ArgumentParser(
        description=(
            "F1 oracle-verdict format-control ablation: fixed gold verdict, "
            "certificate-only submission, no tools"
        ),
    )
    parser.add_argument(
        "--provider",
        choices=("anthropic", "openai"),
        default="anthropic",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Run output directory (provider-specific default)",
    )
    parser.add_argument(
        "--baseline-dir",
        type=Path,
        default=None,
        help="Frozen tools run for comparison (provider-specific default)",
    )
    parser.add_argument(
        "--cohort-root",
        type=Path,
        default=repo_root / EXPANDED_COHORT_ROOT,
    )
    parser.add_argument("--model", default=None)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-items", type=int, default=100)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--provider-retries", type=int, default=3)
    parser.add_argument("--provider-retry-backoff", type=float, default=5.0)
    parser.add_argument("--provider-max-retry-delay", type=float, default=120.0)
    parser.add_argument("--provider-sleep-between-items", type=float, default=0.0)
    parser.add_argument("--no-json-repair", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args(argv)

    provider: ProviderId = args.provider
    out_dir = args.out_dir or _default_out_dir(provider, repo_root)
    baseline_dir = args.baseline_dir or _default_baseline_dir(provider, repo_root)
    model_arg = args.model or _default_model(provider)
    resolved_model = resolve_provider_model(provider, model_arg)

    bundle = resolve_cohort_bundle(args.cohort_root)
    _c2_items_path, f1_items_path, _c2_cohort_id, f1_cohort_id = bundle
    items = load_items_jsonl(f1_items_path)
    max_items = 5 if args.smoke else args.max_items

    if args.report_only:
        summary_path = out_dir / "summary.json"
        if not summary_path.exists():
            print(f"missing summary: {summary_path}", file=sys.stderr)
            return 1
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        finalize_ablation_run(
            out_dir,
            summary=summary,
            baseline_root=baseline_dir if baseline_dir.exists() else None,
            cohort_id=f1_cohort_id,
            temperature=args.temperature,
        )
        print(json.dumps({"report": str(out_dir / "report.md")}, indent=2))
        return 0

    warning = OPENAI_COST_WARNING if provider == "openai" else ANTHROPIC_COST_WARNING
    print(warning, file=sys.stderr)

    if provider == "openai":
        from fsmreasonbench.runners.providers.openai import print_openai_startup_validation

        print_openai_startup_validation(
            model=resolved_model,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
        )

    generate_factory = build_generate_factory(
        GenerateBackendConfig(
            provider=provider,
            timeout=args.timeout,
            max_tokens=args.max_tokens,
        )
    )
    generate = generate_factory(resolved_model, args.temperature)
    batch_config = OllamaBatchConfig(
        model=resolved_model,
        temperature=args.temperature,
        timeout=args.timeout,
        max_items=max_items,
        resume_items=not args.force,
        force_cell=args.force,
        provider=provider,
        max_tokens=args.max_tokens,
        provider_retries=args.provider_retries,
        provider_retry_backoff_seconds=args.provider_retry_backoff,
        provider_max_retry_delay_seconds=args.provider_max_retry_delay,
        provider_sleep_between_items=args.provider_sleep_between_items,
    )
    result = run_f1_oracle_verdict_ablation_batch(
        items,
        generate,
        out_dir,
        batch_config,
        json_repair=not args.no_json_repair,
    )
    finalize_ablation_run(
        out_dir,
        summary=result.summary,
        baseline_root=baseline_dir if baseline_dir.exists() else None,
        cohort_id=f1_cohort_id,
        temperature=args.temperature,
    )
    print(
        json.dumps(
            {
                "provider": provider,
                "resolved_model": resolved_model,
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
