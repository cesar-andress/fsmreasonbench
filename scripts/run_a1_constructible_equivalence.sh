#!/usr/bin/env bash
# Experiment A1: constructible bisimulation equivalence witness (manual launch only).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
export PYTHONPATH=src

usage() {
  cat <<'EOF'
Usage: scripts/run_a1_constructible_equivalence.sh <command>

Audit / export (no API):
  audit                 Run hostile bisimulation_witness verifier audit
  export-analysis       Hash vs bisimulation comparison tables (uses frozen + new runs)
  report                Regenerate combined_summary.json from on-disk cells

Smoke / full cells (require API keys):
  claude-r1-smoke       Claude R1, n=1 equivalence item
  claude-r1             Claude R1 full eq subset (n=51)
  claude-r2c-smoke      Claude R2C smoke
  claude-r2c            Claude R2C full eq subset
  gpt-r1-smoke          GPT-4.1 R1 smoke
  gpt-r1                GPT-4.1 R1 full
  gpt-r2c-smoke         GPT-4.1 R2C smoke
  gpt-r2c               GPT-4.1 R2C full
EOF
}

cmd="${1:-help}"

case "$cmd" in
  audit)
    python3.12 -m fsmreasonbench.cli.export_f1_bisimulation_witness_verifier_audit
    ;;
  export-analysis)
    python3.12 -m fsmreasonbench.cli.export_constructible_equivalence_analysis
    ;;
  report)
    python3.12 -m fsmreasonbench.cli.run_f1_constructible_equivalence_study --report-only
    ;;
  claude-r1-smoke)
    python3.12 -m fsmreasonbench.cli.run_f1_constructible_equivalence_study \
      --provider anthropic --track R1 --smoke --force
    ;;
  claude-r1)
    python3.12 -m fsmreasonbench.cli.run_f1_constructible_equivalence_study \
      --provider anthropic --track R1
    ;;
  claude-r2c-smoke)
    python3.12 -m fsmreasonbench.cli.run_f1_constructible_equivalence_study \
      --provider anthropic --track R2C --smoke --force
    ;;
  claude-r2c)
    python3.12 -m fsmreasonbench.cli.run_f1_constructible_equivalence_study \
      --provider anthropic --track R2C
    ;;
  gpt-r1-smoke)
    python3.12 -m fsmreasonbench.cli.run_f1_constructible_equivalence_study \
      --provider openai --model gpt-4.1 --track R1 --smoke --force
    ;;
  gpt-r1)
    python3.12 -m fsmreasonbench.cli.run_f1_constructible_equivalence_study \
      --provider openai --model gpt-4.1 --track R1
    ;;
  gpt-r2c-smoke)
    python3.12 -m fsmreasonbench.cli.run_f1_constructible_equivalence_study \
      --provider openai --model gpt-4.1 --track R2C --smoke --force
    ;;
  gpt-r2c)
    python3.12 -m fsmreasonbench.cli.run_f1_constructible_equivalence_study \
      --provider openai --model gpt-4.1 --track R2C
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
