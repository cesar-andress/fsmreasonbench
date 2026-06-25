#!/usr/bin/env bash
# Read-only reproduction of ACM TOSEM manuscript tables from frozen runs.
# Does NOT call model APIs. Requires Python >= 3.11 and frozen run trees under runs/.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PYTHON="${PYTHON:-python3.12}"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  PYTHON=python3
fi

export PYTHONPATH=src

echo "==> FSMReasonBench TOSEM table reproduction (read-only)"
echo "    Python: $($PYTHON --version 2>&1)"
echo "    Repo:   $REPO_ROOT"
echo

for summary in \
  runs/frontier_claude_sonnet_tools_n100_v2/combined_summary.json \
  runs/frontier_gpt_tools_n100_v1/combined_summary.json \
  runs/local_matrix_n100_t02_v2/combined_summary.json; do
  if [[ ! -f "$summary" ]]; then
    echo "ERROR: missing frozen summary: $summary" >&2
    echo "       Include run trees from the Zenodo tarball or restore from archive." >&2
    exit 2
  fi
done

echo "==> export_tosem_empirical_package (Claude+GPT frontier, gap, local matrix, McNemar)"
"$PYTHON" -m fsmreasonbench.cli.export_tosem_empirical_package

echo
echo "==> export_tmlr_empirical_package (Claude ablations, complexity figure, bootstrap appendix)"
"$PYTHON" -m fsmreasonbench.cli.export_tmlr_empirical_package

echo
echo "==> artifact_health"
"$PYTHON" -m fsmreasonbench.cli.artifact_health

echo
echo "Done. LaTeX tables: ${REPO_ROOT}/../paper/tables/"
echo "TOSEM manifest:     ${REPO_ROOT}/docs/tosem_empirical_package_v1/package_manifest.json"
