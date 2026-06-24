"""Run C2 existential-vs-universal Claude ablation (R1, Oracle, R2A/R2B/R2C)."""

from __future__ import annotations

import argparse
import json
import sys
from enum import Enum
from pathlib import Path

from fsmreasonbench.cohort.c2_balanced_n100 import (
    BALANCED_C2_COHORT_ID,
    build_balanced_c2_cohort,
    resolve_balanced_c2_cohort,
)
from fsmreasonbench.cohort.expanded_n100 import EXPANDED_COHORT_ROOT
from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.evaluator.ablation_report import finalize_ablation_run
from fsmreasonbench.evaluator.c2_existential_universal_report import (
    finalize_c2_mode_run,
    finalize_c2_study,
    write_pointer_doc,
)
from fsmreasonbench.evaluator.jsonl import load_items_jsonl
from fsmreasonbench.runners.c2_ablation_batch import run_c2_oracle_verdict_ablation_batch
from fsmreasonbench.runners.c2_ablation_prompts import C2_ABLATION_CONDITION_ID
from fsmreasonbench.runners.c2_attribution_batch import run_c2_attribution_batch
from fsmreasonbench.runners.c2_attribution_prompts import C2AttributionMode
from fsmreasonbench.runners.ollama_batch import OllamaBatchConfig
from fsmreasonbench.runners.ollama_track_batch import run_ollama_track_batch
from fsmreasonbench.runners.providers.base import (
    ANTHROPIC_COST_WARNING,
    GenerateBackendConfig,
    build_generate_factory,
)
from fsmreasonbench.tracks.models import TrackId

DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
DEFAULT_PARENT_DIR = "runs/ablations_c2_existential_universal_claude_n100_v1"
DEFAULT_TIMEOUT = 86400.0
DEFAULT_MAX_TOKENS = 2048


class C2StudyCondition(str, Enum):
    R1 = "R1"
    ORACLE = "Oracle"
    R2A = "R2A"
    R2B = "R2B"
    R2C = "R2C"


ALL_CONDITIONS = list(C2StudyCondition)


def _parse_condition(value: str) -> C2StudyCondition:
    normalized = value.strip()
    aliases = {
        "oracle": C2StudyCondition.ORACLE,
        "oracle+format": C2StudyCondition.ORACLE,
        "oracle_format": C2StudyCondition.ORACLE,
    }
    key = normalized.lower().replace("-", "")
    if key in aliases:
        return aliases[key]
    try:
        return C2StudyCondition(normalized.upper() if normalized.upper() in {"R1", "R2A", "R2B", "R2C"} else normalized)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"invalid condition {value!r}; expected R1, Oracle, R2A, R2B, or R2C"
        ) from exc


def _conditions_from_args(args: argparse.Namespace) -> list[C2StudyCondition]:
    if args.all_conditions:
        return ALL_CONDITIONS
    if args.condition is None:
        raise SystemExit("specify --condition or --all")
    return [args.condition]


def main(argv: list[str] | None = None) -> int:
    repo_root = find_repo_root()
    parser = argparse.ArgumentParser(
        description="C2 existential-vs-universal Claude ablation (balanced n=100 cohort)",
    )
    parser.add_argument(
        "--parent-dir",
        type=Path,
        default=repo_root / DEFAULT_PARENT_DIR,
    )
    parser.add_argument("--condition", type=_parse_condition, default=None)
    parser.add_argument("--all", dest="all_conditions", action="store_true")
    parser.add_argument(
        "--cohort-root",
        type=Path,
        default=repo_root / EXPANDED_COHORT_ROOT,
    )
    parser.add_argument(
        "--freeze-cohort",
        action="store_true",
        help="Generate balanced 50/50 C2 cohort before running",
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
    parser.add_argument("--smoke", action="store_true", help="Smoke mode: n=5 per condition")
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Regenerate aggregate report from existing condition summaries",
    )
    args = parser.parse_args(argv)

    if args.freeze_cohort:
        build_balanced_c2_cohort(repo_root, cohort_root=args.cohort_root)
        print(json.dumps({"cohort_frozen": True, "cohort_root": str(args.cohort_root)}, indent=2))
        if not args.all_conditions and args.condition is None and not args.report_only:
            return 0

    items_path, cohort_id = resolve_balanced_c2_cohort(args.cohort_root)
    if not items_path.exists():
        print(
            f"Balanced cohort missing at {items_path}; run with --freeze-cohort first.",
            file=sys.stderr,
        )
        return 1

    items = load_items_jsonl(items_path)
    max_items = 5 if args.smoke else args.max_items
    args.parent_dir.mkdir(parents=True, exist_ok=True)

    if args.report_only:
        combined = finalize_c2_study(
            args.parent_dir,
            cohort_id=cohort_id,
            cohort_items_path=items_path,
            temperature=args.temperature,
        )
        write_pointer_doc(repo_root, args.parent_dir)
        print(
            json.dumps(
                {
                    "report": str(args.parent_dir / "report.md"),
                    "combined_summary": str(args.parent_dir / "combined_summary.json"),
                    "conditions_completed": len(combined.get("track_rows", [])),
                },
                indent=2,
            )
        )
        return 0

    print(ANTHROPIC_COST_WARNING, file=sys.stderr)
    generate = build_generate_factory(
        GenerateBackendConfig(
            provider="anthropic",
            timeout=args.timeout,
            max_tokens=args.max_tokens,
        )
    )(args.model, args.temperature)
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
    for condition in _conditions_from_args(args):
        cond_dir = args.parent_dir / condition.value
        if condition == C2StudyCondition.R1:
            result = run_ollama_track_batch(
                items,
                generate,
                cond_dir / "results.jsonl",
                batch_config,
                TrackId.R1,
                out_dir=cond_dir,
            )
            finalize_c2_mode_run(
                cond_dir,
                summary=result.summary,
                condition_label="R1",
                cohort_id=cohort_id,
                temperature=args.temperature,
            )
            run_results.append({"condition": "R1", "n": result.summary.get("n")})
        elif condition == C2StudyCondition.ORACLE:
            result = run_c2_oracle_verdict_ablation_batch(
                items,
                generate,
                cond_dir,
                batch_config,
            )
            finalize_ablation_run(
                cond_dir,
                summary=result.summary,
                cohort_id=cohort_id,
                temperature=args.temperature,
            )
            finalize_c2_mode_run(
                cond_dir,
                summary=result.summary,
                condition_label="Oracle+Format",
                cohort_id=cohort_id,
                temperature=args.temperature,
            )
            run_results.append({"condition": "Oracle", "n": result.summary.get("n")})
        else:
            mode = C2AttributionMode(condition.value)
            result = run_c2_attribution_batch(
                items,
                generate,
                cond_dir,
                batch_config,
                mode,
            )
            finalize_c2_mode_run(
                cond_dir,
                summary=result.summary,
                condition_label=condition.value,
                cohort_id=cohort_id,
                temperature=args.temperature,
            )
            run_results.append({"condition": condition.value, "n": result.summary.get("n")})

    if args.all_conditions or len(_conditions_from_args(args)) == len(ALL_CONDITIONS):
        finalize_c2_study(
            args.parent_dir,
            cohort_id=cohort_id,
            cohort_items_path=items_path,
            temperature=args.temperature,
        )
        write_pointer_doc(repo_root, args.parent_dir)

    print(json.dumps({"runs": run_results, "parent_dir": str(args.parent_dir)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
