"""Score a C2 submission against a benchmark item."""

from __future__ import annotations

import argparse
import json
import sys

from fsmreasonbench.evaluator.io import dump_json, load_item, load_json, load_transcript
from fsmreasonbench.evaluator.transcript import record_transcript


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score a C2 reachability submission")
    parser.add_argument("--item", required=True, help="Path to full benchmark item JSON")
    parser.add_argument("--submission", required=True, help="Path to submission JSON")
    parser.add_argument(
        "--transcript-out",
        help="Optional path to write evaluation transcript JSON",
    )
    parser.add_argument(
        "--scoring-out",
        help="Optional path to write scoring record JSON only",
    )
    args = parser.parse_args(argv)

    item = load_item(args.item)
    if item.family not in {"C2", "F1"}:
        print(f"ERROR: unsupported family={item.family!r}", file=sys.stderr)
        return 2

    raw_response = load_json(args.submission)
    transcript = record_transcript(item, raw_response)

    scoring_json = json.dumps(transcript.scoring_record.to_dict(), indent=2, sort_keys=True)
    print(scoring_json)

    if args.scoring_out:
        dump_json(args.scoring_out, transcript.scoring_record.to_dict())
    if args.transcript_out:
        dump_json(args.transcript_out, transcript.to_dict())

    return 0 if transcript.scoring_record.fully_correct else 1


if __name__ == "__main__":
    raise SystemExit(main())
