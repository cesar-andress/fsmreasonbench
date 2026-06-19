"""Deterministically rescore a saved evaluation transcript."""

from __future__ import annotations

import argparse
import json
import sys

from fsmreasonbench.evaluator.io import dump_json, load_transcript
from fsmreasonbench.evaluator.transcript import rescore_transcript


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rescore a saved C2 evaluation transcript")
    parser.add_argument("--transcript", required=True, help="Path to transcript JSON")
    parser.add_argument(
        "--scoring-out",
        help="Optional path to write rescored scoring record JSON",
    )
    args = parser.parse_args(argv)

    transcript = load_transcript(args.transcript)
    rescored = rescore_transcript(transcript)

    original = transcript.scoring_record.to_dict()
    rescored_dict = rescored.to_dict()
    print(json.dumps(rescored_dict, indent=2, sort_keys=True))

    if original != rescored_dict:
        print("ERROR: rescore produced different scoring record", file=sys.stderr)
        return 2

    if args.scoring_out:
        dump_json(args.scoring_out, rescored_dict)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
