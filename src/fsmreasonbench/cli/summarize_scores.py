"""Summarize a JSONL batch of scoring records."""

from __future__ import annotations

import argparse
import json
import sys

from fsmreasonbench.evaluator.io import dump_json
from fsmreasonbench.evaluator.jsonl import read_jsonl
from fsmreasonbench.evaluator.models import ScoringRecord
from fsmreasonbench.evaluator.summary import summarize_scoring_records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize scoring records JSONL")
    parser.add_argument("--scores", required=True, help="Input scoring records JSONL")
    parser.add_argument("--out", help="Optional path to write summary JSON")
    args = parser.parse_args(argv)

    try:
        records = [
            ScoringRecord.from_dict(record) for record in read_jsonl(args.scores)
        ]
    except (ValueError, OSError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    summary = summarize_scoring_records(records)
    text = json.dumps(summary, indent=2, sort_keys=True)
    print(text)
    if args.out:
        dump_json(args.out, summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
