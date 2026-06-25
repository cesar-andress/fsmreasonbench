#!/usr/bin/env bash
# Manual launcher for TOSEM extension experiments (A–E infrastructure).
# Does NOT run automatically; execute subcommands explicitly after reviewing costs.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
export PYTHONPATH=src

usage() {
  cat <<'EOF'
Usage: scripts/run_tosem_extension_campaigns.sh <command>

Experiment A — run-to-run stability (frontier replicates):
  replicate-claude-smoke     One replicate, n=100 smoke slice (verify wiring)
  replicate-claude           Run pending Claude replicates (study config)
  replicate-gpt-smoke        One GPT replicate smoke (--model gpt-4.1)
  replicate-gpt              Run pending GPT replicates
  replicate-aggregate        Regenerate aggregate_replicates.json + stability exports

Experiment B — GPT attribution ladder (mirrors Claude protocol):
  gpt-oracle-smoke           Oracle+Format smoke (n=5)
  gpt-oracle                 Full GPT Oracle+Format ablation
  gpt-r2-smoke               R2A/R2B/R2C smoke (n=1 each)
  gpt-r2-all                 Full GPT R2A/R2B/R2C ladder

Experiments C–E — read-only exports (no API):
  export-extensions          Write docs/ + paper/tables|figures extension_* artifacts

Requires ANTHROPIC_API_KEY / OPENAI_API_KEY for execution modes only.
Frozen TOSEM runs under runs/ are never modified by these commands.
EOF
}

cmd="${1:-help}"

case "$cmd" in
  replicate-claude-smoke)
    python -m fsmreasonbench.cli.run_frontier_replicate_study \
      --study-config configs/studies/claude_frontier_replicates_n100_v1.json \
      --replicate-id 1 \
      --replicates 1
    ;;
  replicate-claude)
    python -m fsmreasonbench.cli.run_frontier_replicate_study \
      --study-config configs/studies/claude_frontier_replicates_n100_v1.json
    ;;
  replicate-gpt-smoke)
    python -m fsmreasonbench.cli.run_frontier_replicate_study \
      --study-config configs/studies/gpt_frontier_replicates_n100_v1.json \
      --replicate-id 1 \
      --replicates 1
    ;;
  replicate-gpt)
    python -m fsmreasonbench.cli.run_frontier_replicate_study \
      --study-config configs/studies/gpt_frontier_replicates_n100_v1.json
    ;;
  replicate-aggregate)
    python -m fsmreasonbench.cli.run_frontier_replicate_study \
      --study-config configs/studies/claude_frontier_replicates_n100_v1.json \
      --aggregate-only
    python -m fsmreasonbench.cli.run_frontier_replicate_study \
      --study-config configs/studies/gpt_frontier_replicates_n100_v1.json \
      --aggregate-only
    ;;
  gpt-oracle-smoke)
    python -m fsmreasonbench.cli.run_f1_oracle_verdict_ablation \
      --provider openai \
      --model gpt-4.1 \
      --smoke \
      --force
    ;;
  gpt-oracle)
    python -m fsmreasonbench.cli.run_f1_oracle_verdict_ablation \
      --provider openai \
      --model gpt-4.1
    ;;
  gpt-r2-smoke)
    python -m fsmreasonbench.cli.run_f1_r2_attribution_ablation \
      --provider openai \
      --model gpt-4.1 \
      --all \
      --smoke \
      --force
    ;;
  gpt-r2-all)
    python -m fsmreasonbench.cli.run_f1_r2_attribution_ablation \
      --provider openai \
      --model gpt-4.1 \
      --all
    ;;
  export-extensions)
    python -m fsmreasonbench.cli.export_tosem_extension_experiments
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    echo "Unknown command: $cmd" >&2
    usage
    exit 2
    ;;
esac
