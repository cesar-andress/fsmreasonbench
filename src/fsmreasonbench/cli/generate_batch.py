"""Generate a JSONL batch of self-verifying C2 reachability items."""

from __future__ import annotations

import argparse
import json
import sys

from fsmreasonbench.evaluator.batch import generate_c2_batch
from fsmreasonbench.evaluator.jsonl import write_jsonl
from fsmreasonbench.generator.reachability import ReachabilityGeneratorConfig


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a JSONL batch of C2 items")
    parser.add_argument("--n", type=int, required=True, help="Number of items to generate")
    parser.add_argument("--seed", type=int, default=1, help="Base generator seed (default: 1)")
    parser.add_argument("--out", required=True, help="Output JSONL path")
    parser.add_argument("--state-count", type=int, default=5)
    args = parser.parse_args(argv)

    if args.n < 1:
        parser.error("--n must be >= 1")

    config = ReachabilityGeneratorConfig(state_count=args.state_count)
    try:
        items = generate_c2_batch(args.n, args.seed, config=config)
    except (ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    write_jsonl(args.out, (item.to_full_dict() for item in items))
    print(
        json.dumps(
            {
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
