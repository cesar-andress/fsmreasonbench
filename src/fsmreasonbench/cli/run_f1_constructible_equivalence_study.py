"""CLI: F1 constructible bisimulation equivalence witness study (Experiment A1)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.experiments.constructible_equivalence_study import (
    finalize_constructible_equivalence_study,
    load_constructible_equivalence_study_config,
    resolve_study_items,
)
from fsmreasonbench.runners.constructible_equivalence_batch import (
    run_constructible_equivalence_batch,
    validate_constructible_smoke_gate,
)
from fsmreasonbench.runners.ollama_batch import OllamaBatchConfig
from fsmreasonbench.runners.providers.base import (
    ANTHROPIC_COST_WARNING,
    OPENAI_COST_WARNING,
    GenerateBackendConfig,
    ProviderId,
    build_generate_factory,
    resolve_provider_model,
)
from fsmreasonbench.tracks.models import TrackId

DEFAULT_TIMEOUT = 86400.0
DEFAULT_MAX_TOKENS = 8192


def main(argv: list[str] | None = None) -> int:
    repo_root = find_repo_root()
    parser = argparse.ArgumentParser(
        description=(
            "Run F1 constructible bisimulation equivalence witness study (A1). "
            "Does not modify frozen hash-witness runs."
        ),
    )
    parser.add_argument(
        "--study-config",
        default="configs/studies/f1_constructible_equivalence_n100_v1.json",
    )
    parser.add_argument("--provider", choices=("anthropic", "openai"))
    parser.add_argument("--model", default=None)
    parser.add_argument("--track", choices=("R1", "R2C"))
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--max-items", type=int, default=None)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--provider-retries", type=int, default=3)
    parser.add_argument("--provider-retry-backoff", type=float, default=5.0)
    parser.add_argument("--provider-max-retry-delay", type=float, default=120.0)
    parser.add_argument("--provider-sleep-between-items", type=float, default=0.0)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args(argv)

    study = load_constructible_equivalence_study_config(repo_root / args.study_config)
    items, cohort_id = resolve_study_items(repo_root / study.cohort_root)
    if args.smoke:
        items = items[:1]

    if args.report_only:
        study_roots = sorted({repo_root / cell.out_dir for cell in study.cells})
        for study_root in study_roots:
            finalize_constructible_equivalence_study(
                study_root,
                study_id=study.study_id,
                cohort_id=cohort_id,
                temperature=study.temperature,
            )
        print(json.dumps({"study_roots": [str(p) for p in study_roots]}, indent=2))
        return 0

    if not args.provider or not args.track:
        parser.error("specify --provider and --track (or use --report-only)")

    provider: ProviderId = args.provider
    model_arg = args.model or ("gpt-4.1" if provider == "openai" else "claude-sonnet-4-5-20250929")
    resolved_model = resolve_provider_model(provider, model_arg)
    temperature = args.temperature if args.temperature is not None else study.temperature
    track_id = TrackId.R2 if args.track == "R2C" else TrackId.R1

    matching = [
        cell
        for cell in study.cells
        if cell.provider == provider and cell.track == args.track
    ]
    if not matching:
        print("no matching cell in study config", file=sys.stderr)
        return 2
    cell = matching[0]
    out_dir = args.out_dir or (repo_root / cell.out_dir / args.track)

    print(OPENAI_COST_WARNING if provider == "openai" else ANTHROPIC_COST_WARNING, file=sys.stderr)

    batch_config = OllamaBatchConfig(
        model=resolved_model,
        temperature=temperature,
        timeout=args.timeout,
        max_items=args.max_items or len(items),
        resume_items=not args.force,
        force_cell=args.force,
        provider=provider,
        max_tokens=args.max_tokens,
        provider_retries=args.provider_retries,
        provider_retry_backoff_seconds=args.provider_retry_backoff,
        provider_max_retry_delay_seconds=args.provider_max_retry_delay,
        provider_sleep_between_items=args.provider_sleep_between_items,
    )
    factory = build_generate_factory(
        GenerateBackendConfig(
            provider=provider,
            timeout=args.timeout,
            max_tokens=args.max_tokens,
        )
    )
    generate = factory(resolved_model, temperature)
    result = run_constructible_equivalence_batch(
        items if batch_config.max_items is None else items[: batch_config.max_items],
        generate,
        out_dir,
        batch_config,
        track_id,
    )

    study_root = out_dir.parent
    combined = finalize_constructible_equivalence_study(
        study_root,
        study_id=study.study_id,
        cohort_id=cohort_id,
        temperature=temperature,
    )
    print(
        json.dumps(
            {
                "out_dir": str(out_dir),
                "summary": str(out_dir / "summary.json"),
                "combined_summary": str(study_root / "combined_summary.json"),
                "n_items": result.summary.get("n"),
                "extractability_rate": result.summary.get("extractability_rate"),
                "certificate_valid_rate": result.summary.get("certificate_valid_rate"),
                "cells_in_report": len(combined.get("track_rows", [])),
            },
            indent=2,
        )
    )
    if args.smoke:
        passed, smoke_report = validate_constructible_smoke_gate(
            result,
            track=args.track,
        )
        print(json.dumps({"smoke_gate": smoke_report}, indent=2))
        if not passed:
            print("constructible-equivalence smoke gate FAILED", file=sys.stderr)
            return 1
        print("constructible-equivalence smoke gate PASSED", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
