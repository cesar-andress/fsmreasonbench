#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=src
OUT=docs/_pytest_qa_summary.txt
python3.12 -m pytest tests/ -q --tb=no --disable-warnings > "$OUT" 2>&1 || echo "exit=$?" >> "$OUT"
echo "done" >> "$OUT"
