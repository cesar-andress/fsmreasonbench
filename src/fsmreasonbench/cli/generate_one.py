"""Generate one self-verifying C2 reachability benchmark item."""

from __future__ import annotations

import argparse
import json
import sys

from fsmreasonbench.generator.reachability import (
    ReachabilityGeneratorConfig,
    generate_reachability_fsm,
    pick_target_state,
)
from fsmreasonbench.items.assembly import assemble_reachability_item, self_verify_item


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate one C2 reachability item")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--state-count", type=int, default=5)
    parser.add_argument("--output", type=str, default="-")
    args = parser.parse_args(argv)

    config = ReachabilityGeneratorConfig(state_count=args.state_count)
    fsm = generate_reachability_fsm(args.seed, config)
    target = pick_target_state(args.seed, fsm)
    item = assemble_reachability_item(fsm, target, seed=args.seed)
    self_verify_item(item)

    payload = item.to_full_dict()
    text = json.dumps(payload, indent=2, sort_keys=True)
    if args.output == "-":
        print(text)
    else:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(text)
    print(f"self-verification OK (item_id={item.item_id})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
