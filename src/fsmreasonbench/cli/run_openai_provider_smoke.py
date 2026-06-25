"""Send one OpenAI Chat Completions request to validate provider wiring."""

from __future__ import annotations

import argparse
import json
import sys

from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.runners.providers.openai import (
    OPENAI_API_KIND,
    OPENAI_CHAT_COMPLETIONS_URL,
    run_openai_smoke_test,
)


def main(argv: list[str] | None = None) -> int:
    repo_root = find_repo_root()
    parser = argparse.ArgumentParser(
        description=(
            "OpenAI provider smoke test: one Chat Completions request before n=100 campaigns"
        ),
    )
    parser.add_argument(
        "--model",
        default="gpt",
        help="Model alias or explicit id (default: gpt → OPENAI_MODEL or gpt-5)",
    )
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args(argv)

    print(f"openai-smoke: api_kind={OPENAI_API_KIND}", file=sys.stderr)
    print(f"openai-smoke: endpoint={OPENAI_CHAT_COMPLETIONS_URL}", file=sys.stderr)

    try:
        payload = run_openai_smoke_test(
            model=args.model,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            timeout=args.timeout,
        )
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1

    payload["ok"] = True
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
