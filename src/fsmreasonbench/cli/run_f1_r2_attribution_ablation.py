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
    OPENAI_COST_WARNING,
    GenerateBackendConfig,
    ProviderId,
    build_generate_factory,
    resolve_provider_model,
)
from fsmreasonbench.runners.r2_attribution_batch import run_r2_attribution_batch
from fsmreasonbench.runners.r2_attribution_prompts import R2AttributionMode

DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"
DEFAULT_OPENAI_MODEL = "gpt-4.1"
DEFAULT_PARENT_DIR_ANTHROPIC = "runs/ablations_f1_r2_attribution_claude_n100_v1"
DEFAULT_PARENT_DIR_OPENAI = "runs/ablations_f1_r2_attribution_gpt_n100_v1"
DEFAULT_BASELINE_ANTHROPIC = "runs/frontier_claude_sonnet_tools_n100_v2"
DEFAULT_BASELINE_OPENAI = "runs/frontier_gpt_tools_n100_v1"
DEFAULT_ORACLE_CLAUDE = "runs/ablations_f1_oracle_verdict_format_control_claude_n100_v1"
DEFAULT_ORACLE_OPENAI = "runs/ablations_f1_oracle_verdict_format_control_gpt_n100_v1"
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


def _default_parent_dir(provider: ProviderId, repo_root: Path) -> Path:
    rel = (
        DEFAULT_PARENT_DIR_OPENAI
        if provider == "openai"
        else DEFAULT_PARENT_DIR_ANTHROPIC
    )
    return repo_root / rel


def _default_oracle_dir(provider: ProviderId, repo_root: Path) -> Path:
    rel = DEFAULT_ORACLE_OPENAI if provider == "openai" else DEFAULT_ORACLE_CLAUDE
    return repo_root / rel


def _default_baseline_dir(provider: ProviderId, repo_root: Path) -> Path:
    rel = (
        DEFAULT_BASELINE_OPENAI
        if provider == "openai"
        else DEFAULT_BASELINE_ANTHROPIC
    )
    return repo_root / rel


def _default_model(provider: ProviderId) -> str:
    return DEFAULT_OPENAI_MODEL if provider == "openai" else DEFAULT_ANTHROPIC_MODEL


def _resolve_max_items(args: argparse.Namespace) -> int:
    if args.smoke:
        return 1 if args.provider == "openai" else 5
    return args.max_items


def _enrich_r2_attribution_summary(
    summary: dict[str, object],
    *,
    provider: ProviderId,
    resolved_model: str,
    model_arg: str,
    temperature: float,
) -> dict[str, object]:
    enriched = dict(summary)
    enriched["provider"] = provider
    enriched["resolved_model"] = resolved_model
    enriched["temperature"] = temperature
    if model_arg != resolved_model:
        enriched["model_arg"] = model_arg
    return enriched


def _assert_openai_r2c_smoke_passed(mode_dir: Path) -> None:
    scores_path = mode_dir / "scores.jsonl"
    if not scores_path.exists():
        raise SystemExit(f"smoke failed: missing {scores_path}")
    rows = [
        json.loads(line)
        for line in scores_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows:
        raise SystemExit("smoke failed: scores.jsonl is empty")
    row = rows[0]
    if row.get("provider_error_count", 0) or row.get("failure_stage") == "provider_error":
        raise SystemExit(
            f"smoke failed: provider error on item {row.get('item_id')!r}"
        )
    if not row.get("certificate_valid"):
        raise SystemExit(
            "smoke failed: certificate_valid=false "
            f"(item_id={row.get('item_id')!r}, errors={row.get('certificate_errors')})"
        )
    transcript_path = mode_dir / "transcripts" / f"{row['item_id']}.json"
    if not transcript_path.exists():
        raise SystemExit(f"smoke failed: missing transcript {transcript_path}")
    transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
    audit = transcript.get("audit_log") or {}
    tool_names = [
        inv.get("tool_name")
        for inv in audit.get("tool_invocations") or []
        if isinstance(inv, dict)
    ]
    if "solver.equivalence_certificate" not in tool_names and (
        "solver.distinguishing_certificate" not in tool_names
    ):
        raise SystemExit(
            "smoke failed: audit_log missing solver certificate-builder invocation "
            f"(tools={tool_names})"
        )
    if not audit.get("certificate_assembly"):
        raise SystemExit("smoke failed: audit_log.certificate_assembly is empty")


def main(argv: list[str] | None = None) -> int:
    repo_root = find_repo_root()
    parser = argparse.ArgumentParser(
        description="F1 R2 attribution ablation: decompose certificate construction vs tools",
    )
    parser.add_argument(
        "--provider",
        choices=("anthropic", "openai"),
        default="anthropic",
        help="Model backend (default: anthropic; openai uses identical R2A/R2B/R2C protocol)",
    )
    parser.add_argument(
        "--parent-dir",
        type=Path,
        default=None,
        help=(
            "Study root (default: "
            f"{DEFAULT_PARENT_DIR_ANTHROPIC} or {DEFAULT_PARENT_DIR_OPENAI})"
        ),
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
        help="Run all three modes sequentially (R2A, R2B, R2C)",
    )
    parser.add_argument(
        "--baseline-dir",
        type=Path,
        default=None,
        help="Frozen tools run for comparison (provider-specific default)",
    )
    parser.add_argument(
        "--oracle-dir",
        type=Path,
        default=None,
        help=(
            "Oracle-verdict ablation for comparison "
            f"(default: {DEFAULT_ORACLE_CLAUDE} or {DEFAULT_ORACLE_OPENAI})"
        ),
    )
    parser.add_argument(
        "--cohort-root",
        type=Path,
        default=repo_root / EXPANDED_COHORT_ROOT,
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model alias or id (default: Claude Sonnet or gpt-4.1 by provider)",
    )
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
        help="Smoke mode: n=5 per condition (anthropic) or n=1 (openai)",
    )
    args = parser.parse_args(argv)

    provider: ProviderId = args.provider
    parent_dir = args.parent_dir or _default_parent_dir(provider, repo_root)
    baseline_dir = args.baseline_dir or _default_baseline_dir(provider, repo_root)
    oracle_dir = args.oracle_dir or _default_oracle_dir(provider, repo_root)
    model_arg = args.model or _default_model(provider)
    resolved_model = resolve_provider_model(provider, model_arg)
    max_items = _resolve_max_items(args)

    bundle = resolve_cohort_bundle(args.cohort_root)
    _c2_items_path, f1_items_path, _c2_cohort_id, f1_cohort_id = bundle
    items = load_items_jsonl(f1_items_path)
    parent_dir.mkdir(parents=True, exist_ok=True)

    if args.report_only:
        combined = finalize_r2_attribution_study(
            parent_dir,
            frozen_tools_root=baseline_dir,
            oracle_ablation_root=oracle_dir,
            cohort_id=f1_cohort_id,
            temperature=args.temperature,
            provider=provider,
            resolved_model=resolved_model,
            expected_modes=tuple(R2AttributionMode),
        )
        print(
            json.dumps(
                {
                    "provider": provider,
                    "resolved_model": resolved_model,
                    "report": str(parent_dir / "report.md"),
                    "combined_summary": str(parent_dir / "combined_summary.json"),
                    "modes_completed": len(combined.get("track_rows", [])),
                },
                indent=2,
            )
        )
        return 0

    modes = _modes_from_args(args)
    cost_warning = OPENAI_COST_WARNING if provider == "openai" else ANTHROPIC_COST_WARNING
    print(cost_warning, file=sys.stderr)

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

    run_results: list[dict[str, object]] = []
    for mode in modes:
        mode_dir = parent_dir / mode.value
        result = run_r2_attribution_batch(
            items,
            generate,
            mode_dir,
            batch_config,
            mode,
        )
        summary = _enrich_r2_attribution_summary(
            result.summary,
            provider=provider,
            resolved_model=resolved_model,
            model_arg=model_arg,
            temperature=args.temperature,
        )
        finalize_r2_attribution_mode_run(
            mode_dir,
            summary=summary,
            cohort_id=f1_cohort_id,
            temperature=args.temperature,
            provider=provider,
            resolved_model=resolved_model,
            model_arg=model_arg if model_arg != resolved_model else None,
        )
        run_results.append(
            {
                "mode": mode.value,
                "out_dir": str(result.out_dir),
                "n": summary.get("n"),
                "certificate_valid_rate": summary.get("certificate_valid_rate"),
                "fully_correct_rate": summary.get("fully_correct_rate"),
                "provider_error_count": summary.get("provider_error_count", 0),
                "resolved_model": resolved_model,
                "infrastructure_failures": result.infrastructure_failures,
            }
        )
        if args.smoke and mode == R2AttributionMode.R2C:
            _assert_openai_r2c_smoke_passed(mode_dir)

    combined = finalize_r2_attribution_study(
        parent_dir,
        frozen_tools_root=baseline_dir,
        oracle_ablation_root=oracle_dir,
        cohort_id=f1_cohort_id,
        temperature=args.temperature,
        provider=provider,
        resolved_model=resolved_model,
        expected_modes=tuple(modes),
    )
    print(
        json.dumps(
            {
                "provider": provider,
                "resolved_model": resolved_model,
                "parent_dir": str(parent_dir),
                "max_items_requested": max_items,
                "modes": run_results,
                "report": str(parent_dir / "report.md"),
                "combined_summary": str(parent_dir / "combined_summary.json"),
                "modes_in_report": len(combined.get("track_rows", [])),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
