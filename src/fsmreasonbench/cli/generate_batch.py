"""Generate a JSONL batch of self-verifying benchmark items."""

from __future__ import annotations

import argparse
import json
import sys

from fsmreasonbench.evaluator.batch import generate_batch
from fsmreasonbench.evaluator.jsonl import write_jsonl
from fsmreasonbench.generator.reachability import ReachabilityGeneratorConfig
from fsmreasonbench.generator.separation import SeparationGeneratorConfig


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a JSONL batch of benchmark items")
    parser.add_argument("--family", choices=["C2", "F1"], default="C2")
    parser.add_argument("--n", type=int, required=True, help="Number of items to generate")
    parser.add_argument("--seed", type=int, default=1, help="Base generator seed (default: 1)")
    parser.add_argument("--out", required=True, help="Output JSONL path")
    parser.add_argument("--state-count", type=int, default=5, help="C2 state count")
    parser.add_argument("--state-count-a", type=int, default=4, help="F1 |Q_A|")
    parser.add_argument("--state-count-b", type=int, default=4, help="F1 |Q_B|")
    parser.add_argument("--alphabet-size", type=int, default=3, help="F1 alphabet size")
    parser.add_argument(
        "--min-distinguishing-trace-length",
        type=int,
        default=2,
        help="F1 minimum distinguishing trace length (default: 2)",
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
        help="F1 generation retries per item (default: 64)",
    )
    args = parser.parse_args(argv)

    if args.n < 1:
        parser.error("--n must be >= 1")

    c2_config = ReachabilityGeneratorConfig(state_count=args.state_count)
    f1_config = SeparationGeneratorConfig(
        state_count_a=args.state_count_a,
        state_count_b=args.state_count_b,
        alphabet_size=args.alphabet_size,
        min_distinguishing_trace_length=args.min_distinguishing_trace_length,
        max_distinguishing_trace_length=args.max_distinguishing_trace_length,
        max_retries=args.max_retries,
    )
    try:
        items = generate_batch(
            args.family,
            args.n,
            args.seed,
            c2_config=c2_config,
            f1_config=f1_config,
        )
    except (ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    write_jsonl(args.out, (item.to_full_dict() for item in items))
    print(
        json.dumps(
            {
                "family": args.family,
                "n": len(items),
                "seed": args.seed,
                "out": args.out,
                "self_verified": True,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
