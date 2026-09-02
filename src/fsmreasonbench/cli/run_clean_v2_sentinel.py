"""CLI: run clean_v2 deterministic sentinel campaign (no external models)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fsmreasonbench.clean_v2.sentinel import run_sentinel_campaign
from fsmreasonbench.dev.doc_consistency import find_repo_root


def main(argv: list[str] | None = None) -> int:
    repo = find_repo_root()
    parser = argparse.ArgumentParser(description="Run clean_v2 mock sentinel campaign")
    parser.add_argument(
        "--cohort-items",
        type=Path,
        default=repo / "cohorts/v0.1-expanded-n100/f1-mixed-level3/items.jsonl",
    )
    parser.add_argument(
        "--out-root",
        type=Path,
        default=repo / "runs/clean_v2_sentinel",
    )
    parser.add_argument("--no-overwrite", action="store_true")
    args = parser.parse_args(argv)
    payload = run_sentinel_campaign(
        cohort_items_path=args.cohort_items,
        out_root=args.out_root,
        overwrite=not args.no_overwrite,
    )
    print(json.dumps({k: payload[k] for k in payload if k != "summary"}, indent=2))
    print(json.dumps({"summary": payload["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
