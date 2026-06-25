#!/usr/bin/env bash
# Execute GPT frontier campaigns using frozen JSON manifests (Claude-parity protocol).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

usage() {
  cat <<'EOF'
Usage: scripts/run_frontier_gpt_campaign.sh [smoke|full|r1|r2|report|export]

  smoke   REQUIRED FIRST — one OpenAI request to validate provider wiring
  full    Run C2+F1 R1/R2 campaign (after smoke succeeds)
  r1      Run R1-only slice into shared run root (after smoke succeeds)
  r2      Run R2-only slice into shared run root (after smoke succeeds)
  report  Regenerate combined_summary.json from on-disk artifacts
  export  Regenerate docs/ and paper/tables/ analysis exports

Requires OPENAI_API_KEY for smoke/execution modes (not report/export).
Model resolves via OPENAI_MODEL (default gpt-5) or pass --model to smoke CLI.
EOF
}

MODE="${1:-smoke}"
export PYTHONPATH=src

case "$MODE" in
  smoke)
    python -m fsmreasonbench.cli.run_openai_provider_smoke --model gpt
    ;;
  full)
    python -m fsmreasonbench.cli.run_frontier_campaign \
      --config configs/frontier/frontier_gpt_tools_n100_v1.json
    ;;
  r1)
    python -m fsmreasonbench.cli.run_frontier_campaign \
      --config configs/frontier/frontier_gpt_r1_n100_v1.json
    ;;
  r2)
    python -m fsmreasonbench.cli.run_frontier_campaign \
      --config configs/frontier/frontier_gpt_r2_n100_v1.json
    ;;
  report)
    python -m fsmreasonbench.cli.run_frontier_campaign \
      --config configs/frontier/frontier_gpt_tools_n100_v1.json \
      --report-only
    ;;
  export)
    python -m fsmreasonbench.cli.export_tosem_empirical_package
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    echo "Unknown mode: $MODE" >&2
    usage
    exit 2
    ;;
esac
