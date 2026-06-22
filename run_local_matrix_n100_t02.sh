#!/usr/bin/env bash
set -euo pipefail

cd ~/papers/fsmreasonbench/fsmreasonbench

export PYTHONPATH=src

OUT_DIR="runs/local_matrix_n100_t02_v1"

python -m fsmreasonbench.cli.run_track_pilot_models \
  --models qwen2.5-coder:7b,llama3.1:8b,mistral-nemo:12b,gemma2:9b \
  --families C2,F1 \
  --tracks R0,R1,R2 \
  --temperatures 0.2 \
  --max-items 100 \
  --timeout 1200 \
  --out-dir "$OUT_DIR" \
  --retry-failed \
  --incremental-safe

python -m fsmreasonbench.cli.experiment_status \
  --root "$OUT_DIR" \
  --models qwen2.5-coder:7b,llama3.1:8b,mistral-nemo:12b,gemma2:9b \
  --families C2,F1 \
  --tracks R0,R1,R2 \
  --temperatures 0.2

python -m fsmreasonbench.cli.plot_local_matrix \
  --summary "$OUT_DIR/combined_summary.json" \
  --out-dir "$OUT_DIR/plots"

python -m fsmreasonbench.cli.export_extractability_audit \
  --root "$OUT_DIR" \
  --out "docs/extractability_audit_n100_t02.md"

python -m fsmreasonbench.cli.plan_reruns \
  --root "$OUT_DIR" \
  --models qwen2.5-coder:7b,llama3.1:8b,mistral-nemo:12b,gemma2:9b \
  --families C2,F1 \
  --tracks R0,R1,R2 \
  --temperatures 0.2 \
  --write-scripts \
  --incremental-safe \
  --timeout 1200

python -m fsmreasonbench.cli.export_local_matrix_analysis \
  --follow-root "$OUT_DIR" \
  --pilot-root runs/local_matrix_v1 \
  --temperature 0.2 \
  --expected-n 100 \
  --extractability-audit docs/extractability_audit_n100_t02.md \
  --out docs/local_matrix_n100_t02_analysis.md

echo "DONE: $OUT_DIR"
