"""Generate one self-verifying benchmark item."""

from __future__ import annotations

import argparse
import json
import sys

from fsmreasonbench.generator.reachability import (
    ReachabilityGeneratorConfig,
    generate_reachability_item,
)
from fsmreasonbench.generator.separation import (
    SeparationGeneratorConfig,
    generate_separation_item,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate one benchmark item")
    parser.add_argument("--family", choices=["C2", "F1"], default="C2")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--state-count", type=int, default=5)
    parser.add_argument("--state-count-a", type=int, default=4)
    parser.add_argument("--state-count-b", type=int, default=4)
    parser.add_argument("--alphabet-size", type=int, default=3)
    parser.add_argument("--min-witness-length", type=int, default=1)
    parser.add_argument("--max-witness-length", type=int, default=12)
    parser.add_argument(
        "--min-distinguishing-trace-length",
        type=int,
        default=2,
        help="F1 minimum distinguishing trace length (default: 2; use 1 for smoke items)",
    )
    parser.add_argument(
        "--max-distinguishing-trace-length",
        type=int,
        default=12,
        help="F1 maximum distinguishing trace length (default: 12)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=64,
        help="F1 generation retries (default: 64)",
    )
    parser.add_argument(
        "--allow-initial-target",
        action="store_true",
        help="Allow positive C2 items with empty trace to initial state",
    )
    parser.add_argument(
        "--positive-only",
        action="store_true",
        help="Force a reachable C2 target",
    )
    parser.add_argument(
        "--negative-only",
        action="store_true",
        help="Force an unreachable C2 target",
    )
    parser.add_argument("--output", type=str, default="-")
    args = parser.parse_args(argv)

    if args.family == "C2":
        if args.positive_only and args.negative_only:
            parser.error("--positive-only and --negative-only are mutually exclusive")
        force = True if args.positive_only else False if args.negative_only else None
        config = ReachabilityGeneratorConfig(
            state_count=args.state_count,
            min_witness_length=args.min_witness_length,
            max_witness_length=args.max_witness_length,
            allow_initial_target=args.allow_initial_target,
            include_negative=not args.positive_only,
        )
        item = generate_reachability_item(args.seed, config, force_positive=force)
    else:
        config = SeparationGeneratorConfig(
            state_count_a=args.state_count_a,
            state_count_b=args.state_count_b,
            alphabet_size=args.alphabet_size,
            min_distinguishing_trace_length=args.min_distinguishing_trace_length,
            max_distinguishing_trace_length=args.max_distinguishing_trace_length,
            max_retries=args.max_retries,
        )
        try:
            item = generate_separation_item(args.seed, config)
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2

    payload = item.to_full_dict()
    text = json.dumps(payload, indent=2, sort_keys=True)
    if args.output == "-":
        print(text)
    else:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(text)
    print(
        f"self-verification OK (family={item.family}, item_id={item.item_id})",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
