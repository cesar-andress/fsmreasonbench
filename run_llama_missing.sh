#!/bin/bash
set -e

export PYTHONPATH=src

# C2

python -m fsmreasonbench.cli.run_track_pilot_models \
  --models llama3.1:8b \
  --families C2 \
  --tracks R2 \
  --temperatures 0 \
  --max-items 20 \
  --timeout 900 \
  --out-dir runs/local_matrix_v1 \
  --retry-failed \
  --incremental-safe

python -m fsmreasonbench.cli.run_track_pilot_models \
  --models llama3.1:8b \
  --families C2 \
  --tracks R1 \
  --temperatures 0.2 \
  --max-items 20 \
  --timeout 900 \
  --out-dir runs/local_matrix_v1 \
  --retry-failed \
  --incremental-safe

python -m fsmreasonbench.cli.run_track_pilot_models \
  --models llama3.1:8b \
  --families C2 \
  --tracks R2 \
  --temperatures 0.2 \
  --max-items 20 \
  --timeout 900 \
  --out-dir runs/local_matrix_v1 \
  --retry-failed \
  --incremental-safe

python -m fsmreasonbench.cli.run_track_pilot_models \
  --models llama3.1:8b \
  --families C2 \
  --tracks R1 \
  --temperatures 0.7 \
  --max-items 20 \
  --timeout 900 \
  --out-dir runs/local_matrix_v1 \
  --retry-failed \
  --incremental-safe

python -m fsmreasonbench.cli.run_track_pilot_models \
  --models llama3.1:8b \
  --families C2 \
  --tracks R2 \
  --temperatures 0.7 \
  --max-items 20 \
  --timeout 900 \
  --out-dir runs/local_matrix_v1 \
  --retry-failed \
  --incremental-safe

# F1

python -m fsmreasonbench.cli.run_track_pilot_models \
  --models llama3.1:8b \
  --families F1 \
  --tracks R1 \
  --temperatures 0 \
  --max-items 20 \
  --timeout 900 \
  --out-dir runs/local_matrix_v1 \
  --retry-failed \
  --incremental-safe

python -m fsmreasonbench.cli.run_track_pilot_models \
  --models llama3.1:8b \
  --families F1 \
  --tracks R2 \
  --temperatures 0 \
  --max-items 20 \
  --timeout 900 \
  --out-dir runs/local_matrix_v1 \
  --retry-failed \
  --incremental-safe

python -m fsmreasonbench.cli.run_track_pilot_models \
  --models llama3.1:8b \
  --families F1 \
  --tracks R1 \
  --temperatures 0.2 \
  --max-items 20 \
  --timeout 900 \
  --out-dir runs/local_matrix_v1 \
  --retry-failed \
  --incremental-safe

python -m fsmreasonbench.cli.run_track_pilot_models \
  --models llama3.1:8b \
  --families F1 \
  --tracks R2 \
  --temperatures 0.2 \
  --max-items 20 \
  --timeout 900 \
  --out-dir runs/local_matrix_v1 \
  --retry-failed \
  --incremental-safe

python -m fsmreasonbench.cli.run_track_pilot_models \
  --models llama3.1:8b \
  --families F1 \
  --tracks R1 \
  --temperatures 0.7 \
  --max-items 20 \
  --timeout 900 \
  --out-dir runs/local_matrix_v1 \
  --retry-failed \
  --incremental-safe

python -m fsmreasonbench.cli.run_track_pilot_models \
  --models llama3.1:8b \
  --families F1 \
  --tracks R2 \
  --temperatures 0.7 \
  --max-items 20 \
  --timeout 900 \
  --out-dir runs/local_matrix_v1 \
  --retry-failed \
  --incremental-safe

echo
echo "Final:"
find runs/local_matrix_v1 -name summary.json | wc -l

python -m fsmreasonbench.cli.experiment_status \
  --root runs/local_matrix_v1
